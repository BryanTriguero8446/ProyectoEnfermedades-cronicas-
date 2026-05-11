"""
build_datasets.py
─────────────────
1. Lee diabetic_data.csv del ZIP
2. Adapta las columnas al formato requerido
3. Agrega columna has_disease usando códigos ICD-9
4. Agrega has_disease a los 1100 registros sintéticos existentes
5. Añade 1500 registros reales a cada CSV
"""
import csv, zipfile, random, io, os
from pathlib import Path

random.seed(0)

ZIP   = "C:/Users/DELL/Downloads/diabetes+130-us+hospitals+for+years+1999-2008.zip"
BASE  = Path("C:/Users/DELL/Documents/1.-Bryan/UNIFRANZ/7MO SEMESTRE/TESTING/clinical_lens/ml_datasets")
COLS  = ["age","gender","bmi","glucose","systolic_bp","diastolic_bp","cholesterol","risk_level","has_disease"]
TARGET_EXTRA = 1500  # registros reales a agregar por dataset

# ─── helpers ──────────────────────────────────────────────────────────────────

def clamp(v, lo, hi): return max(lo, min(hi, v))
def normal(mu, s, lo=None, hi=None):
    v = random.gauss(mu, s)
    if lo is not None: v = max(lo, v)
    if hi is not None: v = min(hi, v)
    return v

AGE_MAP = {
    "[0-10)":5, "[10-20)":15, "[20-30)":25, "[30-40)":35,
    "[40-50)":45, "[50-60)":55, "[60-70)":65, "[70-80)":75,
    "[80-90)":85, "[90-100)":95,
}

def parse_age(s):
    mid = AGE_MAP.get(s.strip())
    if mid is None:
        return int(normal(55, 15, 18, 90))
    return int(normal(mid, 4, max(18, mid-8), mid+8))

def parse_gender(s):
    s = s.strip().lower()
    if s == "male":   return 1
    if s == "female": return 0
    return random.randint(0, 1)

def estimate_bmi(age, on_med, a1c, glu_cat):
    """Estima BMI a partir de perfil metabólico del paciente."""
    base = 26.0
    if on_med:
        base += normal(3.5, 1.5, 0, 8)
    if a1c in (">7", ">8"):
        base += normal(2.5, 1, 0, 5)
    if glu_cat in (">200", ">300"):
        base += normal(1.5, 1, 0, 4)
    if age > 50:
        base += normal(1.5, 0.5, 0, 3)
    return round(clamp(normal(base, 4, 16, 50), 16, 50), 1)

def estimate_glucose(glu_serum, a1c):
    """Estima glucosa en ayunas (mg/dL)."""
    if glu_serum == ">300":
        return round(normal(330, 45, 250, 450), 1)
    if glu_serum == ">200":
        return round(normal(230, 30, 200, 310), 1)
    if glu_serum == "Norm":
        return round(normal(92, 8, 70, 105), 1)
    # glu_serum == None → usar A1C
    if a1c == ">8":
        return round(normal(210, 35, 160, 300), 1)
    if a1c == ">7":
        return round(normal(155, 25, 126, 210), 1)
    if a1c == "Norm":
        return round(normal(90, 10, 65, 110), 1)
    # sin info → amplio rango diabético
    return round(normal(145, 40, 70, 350), 1)

def estimate_bp(age, has_htn, has_cardiac, glucose, bmi):
    """Estima presión arterial sistólica y diastólica."""
    if has_htn or has_cardiac:
        s = int(normal(148, 16, 130, 210))
        d = int(normal(92,  9,  80, 130))
    elif age > 60:
        s = int(normal(132, 12, 110, 165))
        d = int(normal(82,  8,  70, 100))
    elif bmi > 30 or glucose > 150:
        s = int(normal(128, 10, 110, 155))
        d = int(normal(82,  7,  72, 100))
    else:
        s = int(normal(118, 10,  90, 140))
        d = int(normal(76,  7,  60,  90))
    return clamp(s, 80, 220), clamp(d, 50, 130)

def estimate_cholesterol(age, bmi, on_med, has_cardiac):
    """Estima colesterol total (mg/dL)."""
    base = 195.0
    if age > 55: base += normal(18, 5, 0, 35)
    if bmi > 30: base += normal(15, 5, 0, 30)
    if on_med:   base += normal(8,  3, 0, 20)
    if has_cardiac: base += normal(20, 8, 0, 40)
    return round(clamp(normal(base, 35, 130, 420), 130, 420), 1)

def has_icd(codes, *ranges):
    """Devuelve True si algún código cae en los rangos dados."""
    for code in codes:
        try:
            n = float(code.split('.')[0])
            for lo, hi in ranges:
                if lo <= n <= hi:
                    return True
        except:
            pass
    return False

def risk_score_to_level(score):
    if score >= 65: return 2
    if score >= 35: return 1
    return 0

def compute_risk(dataset, age, bmi, glucose, sys, dia, chol):
    """Calcula risk_level según el tipo de dataset."""
    if dataset == "hipertension":
        sc = 0
        if sys >= 140 or dia >= 90: sc += 50
        elif sys >= 130 or dia >= 80: sc += 30
        elif sys >= 120: sc += 15
        if bmi >= 30: sc += 15
        elif bmi >= 25: sc += 8
        if age >= 60: sc += 12
        elif age >= 45: sc += 7
        if chol >= 240: sc += 8

    elif dataset == "renal":
        sc = 0
        if glucose >= 200: sc += 40
        elif glucose >= 150: sc += 25
        elif glucose >= 126: sc += 15
        if age >= 70: sc += 18
        elif age >= 60: sc += 12
        elif age >= 50: sc += 6
        if sys >= 140 or dia >= 90: sc += 15
        if bmi >= 30: sc += 8

    elif dataset == "higado_graso":
        sc = 0
        if bmi >= 35: sc += 40
        elif bmi >= 30: sc += 25
        elif bmi >= 25: sc += 12
        if chol >= 260: sc += 18
        elif chol >= 240: sc += 12
        elif chol >= 200: sc += 6
        if glucose >= 126: sc += 15
        elif glucose >= 100: sc += 8

    elif dataset == "insuficiencia_cardiaca":
        sc = 0
        if sys >= 160 or dia >= 100: sc += 40
        elif sys >= 140 or dia >= 90: sc += 25
        if age >= 70: sc += 20
        elif age >= 60: sc += 14
        elif age >= 50: sc += 7
        if chol >= 240: sc += 15
        elif chol >= 200: sc += 8
        if bmi >= 30: sc += 8

    else:
        sc = 0

    return risk_score_to_level(clamp(sc, 0, 100))

# ─── Cargar diabetic_data.csv ─────────────────────────────────────────────────
print("Leyendo diabetic_data.csv …")
patients = []
with zipfile.ZipFile(ZIP) as z:
    with z.open("diabetic_data.csv") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))
        for row in reader:
            age_raw    = row["age"].strip()
            gender_raw = row["gender"].strip()
            glu_serum  = row["max_glu_serum"].strip()
            a1c        = row["A1Cresult"].strip()
            on_med     = row["diabetesMed"].strip() == "Yes"
            insulin    = row["insulin"].strip() != "No"
            diags      = [row["diag_1"].strip(), row["diag_2"].strip(), row["diag_3"].strip()]

            # Filtrar géneros inválidos
            if gender_raw.lower() not in ("male", "female"):
                continue

            age    = parse_age(age_raw)
            gender = parse_gender(gender_raw)

            # Determinar comorbilidades para imputación realista
            has_htn     = has_icd(diags, (401, 405))
            has_cardiac = has_icd(diags, (428, 428))
            has_renal   = has_icd(diags, (580, 589))
            has_liver   = has_icd(diags, (571, 571))

            bmi   = estimate_bmi(age, on_med, a1c, glu_serum)
            glu   = estimate_glucose(glu_serum, a1c)
            sys, dia = estimate_bp(age, has_htn, has_cardiac, glu, bmi)
            chol  = estimate_cholesterol(age, bmi, on_med, has_cardiac)

            patients.append({
                "age": age, "gender": gender,
                "bmi": bmi, "glucose": glu,
                "systolic_bp": sys, "diastolic_bp": dia,
                "cholesterol": chol,
                "has_htn": has_htn, "has_cardiac": has_cardiac,
                "has_renal": has_renal, "has_liver": has_liver,
                "on_med": on_med, "a1c": a1c,
            })

print(f"  → {len(patients):,} registros válidos cargados")

# Mezclar para muestreo variado
random.shuffle(patients)

# ─── Configuración por dataset ────────────────────────────────────────────────
datasets = {
    "hipertension": {
        "file": "hipertension.csv",
        "has_disease_fn": lambda p: 1 if p["has_htn"] else 0,
    },
    "renal": {
        "file": "renal.csv",
        "has_disease_fn": lambda p: 1 if p["has_renal"] else 0,
    },
    "higado_graso": {
        "file": "higado_graso.csv",
        # Hígado graso: código 571 o proxy metabólico (BMI>30 + glucosa alta)
        "has_disease_fn": lambda p: 1 if (p["has_liver"] or (p["bmi"] > 30 and p["glucose"] > 126 and p["a1c"] in (">7", ">8"))) else 0,
    },
    "insuficiencia_cardiaca": {
        "file": "insuficiencia_cardiaca.csv",
        "has_disease_fn": lambda p: 1 if p["has_cardiac"] else 0,
    },
}

# ─── Procesar cada dataset ────────────────────────────────────────────────────
for ds_name, cfg in datasets.items():
    path = BASE / cfg["file"]
    fn   = cfg["has_disease_fn"]

    print(f"\nProcesando {cfg['file']} …")

    # 1) Leer registros existentes y agregar columna has_disease
    existing = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rl = int(row["risk_level"])
            # Para registros sintéticos: risk_level=2 → tiene la enfermedad
            row["has_disease"] = "1" if rl == 2 else "0"
            existing.append(row)

    print(f"  → {len(existing)} registros existentes (has_disease agregado)")

    # 2) Tomar 1500 registros del dataset real
    new_rows = []
    pool = patients.copy()
    random.shuffle(pool)

    for p in pool:
        if len(new_rows) >= TARGET_EXTRA:
            break
        rl = compute_risk(ds_name, p["age"], p["bmi"], p["glucose"],
                          p["systolic_bp"], p["diastolic_bp"], p["cholesterol"])
        hd = fn(p)
        new_rows.append({
            "age":          p["age"],
            "gender":       p["gender"],
            "bmi":          p["bmi"],
            "glucose":      p["glucose"],
            "systolic_bp":  p["systolic_bp"],
            "diastolic_bp": p["diastolic_bp"],
            "cholesterol":  p["cholesterol"],
            "risk_level":   rl,
            "has_disease":  hd,
        })

    print(f"  → {len(new_rows)} registros reales añadidos desde diabetic_data")

    # Estadísticas has_disease
    hd_existing = sum(1 for r in existing  if r["has_disease"] == "1")
    hd_new      = sum(1 for r in new_rows  if r["has_disease"] == 1)
    total       = len(existing) + len(new_rows)
    print(f"  → Total filas: {total} | has_disease=1: {hd_existing + hd_new} | has_disease=0: {total - hd_existing - hd_new}")

    # 3) Escribir CSV actualizado
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLS)
        writer.writeheader()
        # Registros existentes
        for r in existing:
            writer.writerow({c: r[c] for c in COLS})
        # Registros reales
        for r in new_rows:
            writer.writerow({c: r[c] for c in COLS})

    print(f"  ✓ Guardado: {path}")

print("\n¡Listo! Todos los datasets actualizados.")
