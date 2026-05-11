"""
build_diabetes.py
─────────────────
Genera ml_datasets/diabetes.csv con:
  - 1100 registros sinteticos
  - 1500 registros reales de diabetic_data.csv
  - Columnas: age, gender, bmi, glucose, systolic_bp, diastolic_bp, cholesterol, risk_level, has_disease
  - has_disease: ICD-9 250.xx para registros reales; risk_level==2 para sinteticos
"""
import csv, zipfile, random, io
from pathlib import Path

random.seed(42)

ZIP  = "C:/Users/DELL/Downloads/diabetes+130-us+hospitals+for+years+1999-2008.zip"
OUT  = Path("C:/Users/DELL/Documents/1.-Bryan/UNIFRANZ/7MO SEMESTRE/TESTING/clinical_lens/ml_datasets/diabetes.csv")
COLS = ["age","gender","bmi","glucose","systolic_bp","diastolic_bp","cholesterol","risk_level","has_disease"]

# ─── helpers ──────────────────────────────────────────────────────────────────

def clamp(v, lo, hi): return max(lo, min(hi, v))
def normal(mu, s, lo=None, hi=None):
    v = random.gauss(mu, s)
    if lo is not None: v = max(lo, v)
    if hi is not None: v = min(hi, v)
    return v

AGE_MAP = {
    "[0-10)":5,"[10-20)":15,"[20-30)":25,"[30-40)":35,
    "[40-50)":45,"[50-60)":55,"[60-70)":65,"[70-80)":75,
    "[80-90)":85,"[90-100)":95,
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
    base = 26.0
    if on_med:                            base += normal(3.5, 1.5, 0, 8)
    if a1c in (">7", ">8"):              base += normal(2.5, 1, 0, 5)
    if glu_cat in (">200", ">300"):      base += normal(1.5, 1, 0, 4)
    if age > 50:                          base += normal(1.5, 0.5, 0, 3)
    return round(clamp(normal(base, 4, 16, 50), 16, 50), 1)

def estimate_glucose(glu_serum, a1c):
    if glu_serum == ">300": return round(normal(330, 45, 250, 450), 1)
    if glu_serum == ">200": return round(normal(230, 30, 200, 310), 1)
    if glu_serum == "Norm": return round(normal(92, 8, 70, 105), 1)
    if a1c == ">8":         return round(normal(210, 35, 160, 300), 1)
    if a1c == ">7":         return round(normal(155, 25, 126, 210), 1)
    if a1c == "Norm":       return round(normal(90, 10, 65, 110), 1)
    return round(normal(145, 40, 70, 350), 1)

def estimate_bp(age, has_htn, has_cardiac, glucose, bmi):
    if has_htn or has_cardiac:
        s = int(normal(148, 16, 130, 210)); d = int(normal(92, 9, 80, 130))
    elif age > 60:
        s = int(normal(132, 12, 110, 165)); d = int(normal(82, 8, 70, 100))
    elif bmi > 30 or glucose > 150:
        s = int(normal(128, 10, 110, 155)); d = int(normal(82, 7, 72, 100))
    else:
        s = int(normal(118, 10, 90, 140));  d = int(normal(76, 7, 60, 90))
    return clamp(s, 80, 220), clamp(d, 50, 130)

def estimate_cholesterol(age, bmi, on_med, has_cardiac):
    base = 195.0
    if age > 55:     base += normal(18, 5, 0, 35)
    if bmi > 30:     base += normal(15, 5, 0, 30)
    if on_med:       base += normal(8,  3, 0, 20)
    if has_cardiac:  base += normal(20, 8, 0, 40)
    return round(clamp(normal(base, 35, 130, 420), 130, 420), 1)

def has_icd(codes, *ranges):
    for code in codes:
        try:
            n = float(code.split('.')[0])
            for lo, hi in ranges:
                if lo <= n <= hi:
                    return True
        except:
            pass
    return False

def compute_risk_diabetes(age, bmi, glucose, sys, dia, chol):
    """Risk score especifico para diabetes."""
    sc = 0
    # Glucosa es el factor principal
    if glucose >= 200:   sc += 45
    elif glucose >= 150: sc += 30
    elif glucose >= 126: sc += 18
    elif glucose >= 100: sc += 8
    # IMC
    if bmi >= 35:        sc += 20
    elif bmi >= 30:      sc += 13
    elif bmi >= 25:      sc += 6
    # Edad
    if age >= 65:        sc += 15
    elif age >= 50:      sc += 9
    elif age >= 40:      sc += 4
    # Presion arterial (asociada a diabetes tipo 2)
    if sys >= 140 or dia >= 90: sc += 10
    elif sys >= 130:             sc += 5
    # Colesterol
    if chol >= 240:      sc += 8
    elif chol >= 200:    sc += 4

    sc = clamp(sc, 0, 100)
    if sc >= 65: return 2
    if sc >= 35: return 1
    return 0

# ─── 1. Generar 1100 registros sinteticos ─────────────────────────────────────
print("Generando registros sinteticos...")

PROFILES = [
    # (prob, mu_age, mu_bmi, mu_glu, label)   -> distribucion realista de diabeticos
    (0.25, 52, 28, 105, "prediabetico"),      # pre-diabetes
    (0.35, 58, 32, 165, "diabetico_leve"),    # diabetes tipo 2 controlada
    (0.25, 63, 34, 225, "diabetico_medio"),   # diabetes moderada
    (0.15, 67, 36, 295, "diabetico_severo"),  # diabetes mal controlada
]

synthetic = []
N = 1100
for _ in range(N):
    r = random.random()
    cum = 0
    for prob, mu_age, mu_bmi, mu_glu, label in PROFILES:
        cum += prob
        if r <= cum:
            break

    age    = int(clamp(normal(mu_age, 9, 18, 90), 18, 90))
    gender = random.randint(0, 1)
    bmi    = round(clamp(normal(mu_bmi, 5, 16, 50), 16, 50), 1)
    glu    = round(clamp(normal(mu_glu, 40, 65, 450), 65, 450), 1)

    # Presion segun perfil
    htn_prob = 0.6 if mu_glu > 150 else 0.3
    has_htn  = random.random() < htn_prob
    if has_htn:
        sys = int(clamp(normal(148, 14, 130, 200), 80, 220))
        dia = int(clamp(normal(92, 8, 80, 125), 50, 130))
    elif age > 55 or bmi > 30:
        sys = int(clamp(normal(130, 10, 110, 165), 80, 220))
        dia = int(clamp(normal(83, 7, 70, 100), 50, 130))
    else:
        sys = int(clamp(normal(118, 9, 90, 145), 80, 220))
        dia = int(clamp(normal(76, 6, 60, 95), 50, 130))

    chol = round(clamp(normal(205 + (bmi - 25) * 2 + (age - 40) * 0.5, 35, 130, 420), 130, 420), 1)
    rl   = compute_risk_diabetes(age, bmi, glu, sys, dia, chol)

    synthetic.append({
        "age": age, "gender": gender, "bmi": bmi, "glucose": glu,
        "systolic_bp": sys, "diastolic_bp": dia, "cholesterol": chol,
        "risk_level": rl,
        "has_disease": 1 if rl == 2 else 0,
    })

dist = {0: 0, 1: 0, 2: 0}
for r in synthetic: dist[r["risk_level"]] += 1
print(f"  Sinteticos: Bajo={dist[0]} | Medio={dist[1]} | Alto={dist[2]}")
print(f"  has_disease=1: {sum(1 for r in synthetic if r['has_disease']==1)}")

# ─── 2. Cargar 1500 registros reales de diabetic_data.csv ────────────────────
print("Cargando registros reales de diabetic_data.csv...")
real_rows = []

with zipfile.ZipFile(ZIP) as z:
    with z.open("diabetic_data.csv") as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))
        pool   = []
        for row in reader:
            g = row["gender"].strip().lower()
            if g not in ("male", "female"):
                continue
            pool.append(row)

random.shuffle(pool)
print(f"  Pool disponible: {len(pool):,} registros")

for row in pool:
    if len(real_rows) >= 1500:
        break

    age_raw   = row["age"].strip()
    gender_raw= row["gender"].strip()
    glu_serum = row["max_glu_serum"].strip()
    a1c       = row["A1Cresult"].strip()
    on_med    = row["diabetesMed"].strip() == "Yes"
    diags     = [row["diag_1"].strip(), row["diag_2"].strip(), row["diag_3"].strip()]

    age    = parse_age(age_raw)
    gender = parse_gender(gender_raw)

    has_htn     = has_icd(diags, (401, 405))
    has_cardiac = has_icd(diags, (428, 428))
    has_diabetes= has_icd(diags, (250, 250))   # ICD-9 250.xx

    bmi  = estimate_bmi(age, on_med, a1c, glu_serum)
    glu  = estimate_glucose(glu_serum, a1c)
    sys, dia = estimate_bp(age, has_htn, has_cardiac, glu, bmi)
    chol = estimate_cholesterol(age, bmi, on_med, has_cardiac)
    rl   = compute_risk_diabetes(age, bmi, glu, sys, dia, chol)

    real_rows.append({
        "age": age, "gender": gender, "bmi": bmi, "glucose": glu,
        "systolic_bp": sys, "diastolic_bp": dia, "cholesterol": chol,
        "risk_level": rl,
        "has_disease": 1 if has_diabetes else 0,
    })

print(f"  Reales cargados: {len(real_rows)}")
print(f"  has_disease=1 (ICD-9 250): {sum(1 for r in real_rows if r['has_disease']==1)}")

# ─── 3. Escribir CSV final ────────────────────────────────────────────────────
all_rows = synthetic + real_rows
hd1 = sum(1 for r in all_rows if r["has_disease"] == 1)
print(f"\nTotal filas: {len(all_rows)} | has_disease=1: {hd1} | has_disease=0: {len(all_rows)-hd1}")

with open(OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=COLS)
    writer.writeheader()
    for r in all_rows:
        writer.writerow({c: r[c] for c in COLS})

print(f"Guardado: {OUT}")
