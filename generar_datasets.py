"""
generar_datasets.py
───────────────────
Genera datasets sintéticos clínicamente realistas para las 5 enfermedades.

Distribuciones basadas en:
  - ADA (American Diabetes Association) guidelines
  - JNC 8 Hypertension guidelines
  - KDIGO CKD guidelines
  - AASLD NAFLD guidelines
  - ESC Heart Failure guidelines

Prevalencias reales en adultos (Latinoamérica):
  Diabetes:              12%
  Hipertensión:          35%
  Enfermedad Renal:      13%
  Hígado Graso (NAFLD):  25%
  Insuficiencia Cardíaca: 3%
"""
import numpy as np
import pandas as pd
from pathlib import Path

RNG = np.random.default_rng(42)
N   = 8000          # filas por dataset
OUT = Path(__file__).parent / "ml_datasets"
OUT.mkdir(exist_ok=True)


# ─── Helpers de distribución ─────────────────────────────────────────────────

def clip(arr, lo, hi):
    return np.clip(arr, lo, hi)

def normal(mean, std, n):
    return RNG.normal(mean, std, n)

def uniform(lo, hi, n):
    return RNG.uniform(lo, hi, n)

def age_population(n):
    """Distribución de edades realista: más adultos 30-65."""
    return clip(normal(45, 15, n), 18, 85).astype(int)

def bmi_by_health(n, obese_frac=0.25):
    """BMI realista: mix de normal, sobrepeso y obeso."""
    idx_normal  = RNG.choice(n, int(n * 0.45), replace=False)
    idx_sobrepeso = RNG.choice(n, int(n * 0.30), replace=False)
    idx_obeso   = RNG.choice(n, int(n * obese_frac), replace=False)
    bmi = normal(26, 3, n)
    bmi[idx_normal]    = clip(normal(22, 2, len(idx_normal)),    17, 24.9)
    bmi[idx_sobrepeso] = clip(normal(27, 1.5, len(idx_sobrepeso)), 25, 29.9)
    bmi[idx_obeso]     = clip(normal(33, 4, len(idx_obeso)),     30, 50)
    return clip(bmi, 15, 55)

def cholesterol_population(n):
    """Colesterol: media ~195, algunos con hipercolesterolemia."""
    return clip(normal(195, 35, n), 100, 350)


# ─── DIABETES ────────────────────────────────────────────────────────────────
# Prevalencia real: ~12%. Factores clave: glucosa, BMI, edad.
# Glucosa normal (ayunas): 70-99   → no diabético
# Prediabetes:             100-125 → riesgo medio
# Diabetes:                ≥126    → has_disease=1

def dataset_diabetes(n=N):
    age = age_population(n)
    bmi = bmi_by_health(n, obese_frac=0.28)
    col = cholesterol_population(n)
    sbp = clip(normal(118, 15, n), 85, 200)
    dbp = clip(normal(76, 10, n), 50, 120)

    # Glucosa base según BMI y edad (relación fisiológica)
    glu_base = 82 + (bmi - 22) * 1.2 + (age - 30) * 0.15
    glu = clip(normal(glu_base, 8, n), 60, 110)

    # 12% diabéticos: glucosa alta, BMI alto, edad mayor
    n_diab = int(n * 0.12)
    idx_diab = RNG.choice(n, n_diab, replace=False)
    glu[idx_diab] = clip(normal(165, 40, n_diab), 126, 350)
    bmi[idx_diab] = clip(bmi[idx_diab] + normal(4, 2, n_diab), 25, 55)
    age[idx_diab] = clip(age[idx_diab] + normal(8, 5, n_diab), 30, 85)

    # 15% prediabéticos: glucosa 100-125
    n_pre = int(n * 0.15)
    idx_pre = RNG.choice(np.setdiff1d(np.arange(n), idx_diab), n_pre, replace=False)
    glu[idx_pre] = clip(normal(112, 7, n_pre), 100, 125)
    bmi[idx_pre] = clip(bmi[idx_pre] + normal(2, 1, n_pre), 22, 45)

    has_disease = np.zeros(n, dtype=int)
    has_disease[idx_diab] = 1

    # risk_level: 0=bajo, 1=medio(prediabetes/riesgo), 2=alto(diabetes)
    risk = np.zeros(n, dtype=int)
    risk[idx_pre] = 1
    risk[idx_diab] = 2
    # También riesgo medio si BMI≥30 y glucosa≥95 aunque no sean diabéticos
    mask_riesgo = (bmi >= 30) & (glu >= 95) & (has_disease == 0) & (risk == 0)
    risk[mask_riesgo] = 1

    df = pd.DataFrame({
        "age": age, "bmi": np.round(bmi, 1), "glucose": np.round(glu, 1),
        "systolic_bp": np.round(sbp).astype(int),
        "diastolic_bp": np.round(dbp).astype(int),
        "cholesterol": np.round(col).astype(int),
        "has_disease": has_disease, "risk_level": risk,
    })
    print(f"  Diabetes:    {n} filas | positivos={has_disease.sum()} ({has_disease.mean()*100:.1f}%) | glucose_media={glu.mean():.1f}")
    return df


# ─── HIPERTENSIÓN ────────────────────────────────────────────────────────────
# Prevalencia: ~35%. Factor clave: presión arterial sistólica y diastólica.
# Normal:   <120/80  → 0
# Elevada:  120-129  → riesgo medio
# Etapa 1:  130-139/80-89 → riesgo medio-alto
# Etapa 2:  ≥140/90  → has_disease=1

def dataset_hipertension(n=N):
    age = age_population(n)
    bmi = bmi_by_health(n, obese_frac=0.30)
    col = cholesterol_population(n)
    glu = clip(normal(93, 12, n), 65, 160)

    # BP base sube con edad y BMI
    sbp_base = 105 + (age - 30) * 0.5 + (bmi - 22) * 0.8
    sbp = clip(normal(sbp_base, 12, n), 85, 135)
    dbp = clip(sbp * 0.65 + normal(0, 6, n), 50, 90)

    # 35% hipertensos
    n_hta = int(n * 0.35)
    idx_hta = RNG.choice(n, n_hta, replace=False)
    sbp[idx_hta] = clip(normal(152, 15, n_hta), 140, 220)
    dbp[idx_hta] = clip(normal(95, 8, n_hta), 90, 130)
    age[idx_hta] = clip(age[idx_hta] + normal(6, 4, n_hta), 25, 85)
    bmi[idx_hta] = clip(bmi[idx_hta] + normal(3, 2, n_hta), 22, 55)

    has_disease = np.zeros(n, dtype=int)
    has_disease[idx_hta] = 1

    risk = np.zeros(n, dtype=int)
    risk[idx_hta] = 2
    mask_elevada = (sbp >= 120) & (sbp < 130) & (has_disease == 0)
    risk[mask_elevada] = 1
    mask_etapa1 = ((sbp >= 130) | (dbp >= 80)) & (has_disease == 0) & (risk == 0)
    risk[mask_etapa1] = 1

    df = pd.DataFrame({
        "age": age, "bmi": np.round(bmi, 1), "glucose": np.round(glu, 1),
        "systolic_bp": np.round(sbp).astype(int),
        "diastolic_bp": np.round(dbp).astype(int),
        "cholesterol": np.round(col).astype(int),
        "has_disease": has_disease, "risk_level": risk,
    })
    print(f"  Hipertensión:{n} filas | positivos={has_disease.sum()} ({has_disease.mean()*100:.1f}%) | sbp_media={sbp.mean():.1f}")
    return df


# ─── ENFERMEDAD RENAL CRÓNICA ────────────────────────────────────────────────
# Prevalencia: ~13%. Factores proxy: diabetes+HTA como causas principales, edad.

def dataset_renal(n=N):
    age = age_population(n)
    bmi = bmi_by_health(n, obese_frac=0.22)
    col = cholesterol_population(n)
    glu = clip(normal(92, 15, n), 65, 200)
    sbp = clip(normal(118, 14, n), 85, 200)
    dbp = clip(sbp * 0.66 + normal(0, 6, n), 50, 120)

    # 13% enfermedad renal: mayor edad, con diabetes o HTA previas
    n_renal = int(n * 0.13)
    idx_renal = RNG.choice(n, n_renal, replace=False)
    age[idx_renal]  = clip(age[idx_renal] + normal(12, 6, n_renal), 35, 85)
    glu[idx_renal]  = clip(normal(140, 40, n_renal), 100, 350)
    sbp[idx_renal]  = clip(normal(148, 16, n_renal), 130, 220)
    dbp[idx_renal]  = clip(normal(92, 8, n_renal), 80, 130)
    bmi[idx_renal]  = clip(bmi[idx_renal] + normal(3, 2, n_renal), 22, 55)

    has_disease = np.zeros(n, dtype=int)
    has_disease[idx_renal] = 1

    risk = np.zeros(n, dtype=int)
    risk[idx_renal] = 2
    mask_med = (age >= 55) & ((glu >= 110) | (sbp >= 130)) & (has_disease == 0)
    risk[mask_med] = 1

    df = pd.DataFrame({
        "age": age, "bmi": np.round(bmi, 1), "glucose": np.round(glu, 1),
        "systolic_bp": np.round(sbp).astype(int),
        "diastolic_bp": np.round(dbp).astype(int),
        "cholesterol": np.round(col).astype(int),
        "has_disease": has_disease, "risk_level": risk,
    })
    print(f"  Renal:       {n} filas | positivos={has_disease.sum()} ({has_disease.mean()*100:.1f}%) | age_media={age.mean():.1f}")
    return df


# ─── HÍGADO GRASO (NAFLD) ────────────────────────────────────────────────────
# Prevalencia: ~25%. Factores clave: BMI alto, colesterol, glucosa, triglicéridos proxy.

def dataset_nafld(n=N):
    age = age_population(n)
    bmi = bmi_by_health(n, obese_frac=0.35)
    col = cholesterol_population(n)
    glu = clip(normal(93, 14, n), 65, 160)
    sbp = clip(normal(118, 13, n), 85, 185)
    dbp = clip(sbp * 0.66 + normal(0, 5, n), 50, 110)

    # 25% NAFLD: BMI muy alto, colesterol y glucosa elevados
    n_nafld = int(n * 0.25)
    idx_nafld = RNG.choice(n, n_nafld, replace=False)
    bmi[idx_nafld]  = clip(normal(34, 5, n_nafld), 27, 55)
    col[idx_nafld]  = clip(normal(230, 35, n_nafld), 180, 380)
    glu[idx_nafld]  = clip(normal(115, 25, n_nafld), 90, 250)
    age[idx_nafld]  = clip(age[idx_nafld] + normal(4, 4, n_nafld), 20, 80)

    has_disease = np.zeros(n, dtype=int)
    has_disease[idx_nafld] = 1

    risk = np.zeros(n, dtype=int)
    risk[idx_nafld] = 2
    mask_med = (bmi >= 27) & ((col >= 200) | (glu >= 100)) & (has_disease == 0)
    risk[mask_med] = 1

    df = pd.DataFrame({
        "age": age, "bmi": np.round(bmi, 1), "glucose": np.round(glu, 1),
        "systolic_bp": np.round(sbp).astype(int),
        "diastolic_bp": np.round(dbp).astype(int),
        "cholesterol": np.round(col).astype(int),
        "has_disease": has_disease, "risk_level": risk,
    })
    print(f"  NAFLD:       {n} filas | positivos={has_disease.sum()} ({has_disease.mean()*100:.1f}%) | bmi_media={bmi.mean():.1f}")
    return df


# ─── INSUFICIENCIA CARDÍACA ───────────────────────────────────────────────────
# Prevalencia: ~3%. Factores: edad avanzada, hipertensión, diabetes crónica, IMC alto.

def dataset_cardiaco(n=N):
    age = age_population(n)
    bmi = bmi_by_health(n, obese_frac=0.28)
    col = cholesterol_population(n)
    glu = clip(normal(95, 16, n), 65, 180)
    sbp = clip(normal(120, 16, n), 85, 210)
    dbp = clip(sbp * 0.65 + normal(0, 6, n), 50, 125)

    # 3% insuficiencia cardíaca: edad muy avanzada + múltiples factores
    n_card = int(n * 0.03)
    idx_card = RNG.choice(n, n_card, replace=False)
    age[idx_card]  = clip(normal(68, 8, n_card), 50, 85)
    sbp[idx_card]  = clip(normal(158, 18, n_card), 140, 220)
    dbp[idx_card]  = clip(normal(96, 9, n_card), 85, 130)
    bmi[idx_card]  = clip(normal(32, 5, n_card), 25, 55)
    glu[idx_card]  = clip(normal(140, 40, n_card), 100, 320)
    col[idx_card]  = clip(normal(225, 40, n_card), 170, 370)

    has_disease = np.zeros(n, dtype=int)
    has_disease[idx_card] = 1

    risk = np.zeros(n, dtype=int)
    risk[idx_card] = 2
    mask_med = (age >= 55) & ((sbp >= 140) | (glu >= 120)) & (has_disease == 0)
    risk[mask_med] = 1

    df = pd.DataFrame({
        "age": age, "bmi": np.round(bmi, 1), "glucose": np.round(glu, 1),
        "systolic_bp": np.round(sbp).astype(int),
        "diastolic_bp": np.round(dbp).astype(int),
        "cholesterol": np.round(col).astype(int),
        "has_disease": has_disease, "risk_level": risk,
    })
    print(f"  Cardíaco:    {n} filas | positivos={has_disease.sum()} ({has_disease.mean()*100:.1f}%) | age_media={age.mean():.1f}")
    return df


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("GENERANDO DATASETS CLÍNICAMENTE REALISTAS")
    print("=" * 60)

    generadores = {
        "diabetes":               dataset_diabetes,
        "hipertension":           dataset_hipertension,
        "renal":                  dataset_renal,
        "higado_graso":           dataset_nafld,
        "insuficiencia_cardiaca": dataset_cardiaco,
    }

    for nombre, fn in generadores.items():
        df = fn(N)
        out = OUT / f"{nombre}.csv"
        df.to_csv(out, index=False)

    print()
    print("Datasets guardados en ml_datasets/")
    print("Ahora ejecuta: python train_models.py")
