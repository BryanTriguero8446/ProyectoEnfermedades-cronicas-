"""
train_models.py
───────────────
Entrena modelos de Machine Learning para las 5 enfermedades cronicas.

Para cada enfermedad genera DOS modelos:
  1. <enfermedad>_disease.pkl  -> Clasificador binario has_disease (0/1)
  2. <enfermedad>_risk.pkl     -> Clasificador multiclase risk_level (0=bajo, 1=medio, 2=alto)

Features usadas (6): age, bmi, glucose, systolic_bp, diastolic_bp, cholesterol
(Se excluye 'gender' porque el modelo de Django no tiene ese campo)
"""
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report
from sklearn.preprocessing import StandardScaler

BASE        = Path(__file__).parent
DATASETS    = BASE / "ml_datasets"
MODELS_DIR  = BASE / "prediccion" / "ml_models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

FEATURES = ["age", "bmi", "glucose", "systolic_bp", "diastolic_bp", "cholesterol"]

DATASETS_CONFIG = {
    "diabetes":               "diabetes.csv",
    "hipertension":           "hipertension.csv",
    "renal":                  "renal.csv",
    "higado_graso":           "higado_graso.csv",
    "insuficiencia_cardiaca": "insuficiencia_cardiaca.csv",
}


def entrenar_modelo(X_train, y_train, X_test, y_test, multiclase=False):
    """Entrena Random Forest y Gradient Boosting, devuelve el mejor."""
    candidatos = {
        "RandomForest": RandomForestClassifier(
            n_estimators=200, max_depth=12, min_samples_split=5,
            random_state=42, n_jobs=-1, class_weight="balanced"
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=150, max_depth=5, learning_rate=0.1,
            random_state=42
        ),
    }

    mejor_modelo = None
    mejor_score  = -1
    mejor_nombre = ""
    metricas     = {}

    for nombre, modelo in candidatos.items():
        modelo.fit(X_train, y_train)
        y_pred = modelo.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        avg = "weighted" if multiclase else "binary"
        p, r, f1, _ = precision_recall_fscore_support(
            y_test, y_pred, average=avg, zero_division=0
        )
        metricas[nombre] = {"acc": acc, "precision": p, "recall": r, "f1": f1}

        if f1 > mejor_score:
            mejor_score  = f1
            mejor_modelo = modelo
            mejor_nombre = nombre

    return mejor_modelo, mejor_nombre, metricas


def main():
    print("=" * 70)
    print("ENTRENAMIENTO DE MODELOS ML - ClinicalLens")
    print("=" * 70)

    resumen = []

    for enfermedad, archivo in DATASETS_CONFIG.items():
        print(f"\n>>> {enfermedad.upper()}")
        path = DATASETS / archivo
        df   = pd.read_csv(path)
        print(f"  Dataset: {archivo}  |  {len(df)} filas")

        X = df[FEATURES].values

        # ─── Modelo 1: has_disease (binario) ────────────────────────────────
        y_d = df["has_disease"].astype(int).values
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y_d, test_size=0.2, random_state=42, stratify=y_d
        )

        modelo_d, nombre_d, metricas_d = entrenar_modelo(
            X_tr, y_tr, X_te, y_te, multiclase=False
        )
        for n, m in metricas_d.items():
            print(f"  [has_disease] {n:18s}: acc={m['acc']:.3f} | f1={m['f1']:.3f} | P={m['precision']:.3f} | R={m['recall']:.3f}")
        print(f"  -> Seleccionado: {nombre_d}")

        # ─── Modelo 2: risk_level (multiclase) ─────────────────────────────
        y_r = df["risk_level"].astype(int).values
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y_r, test_size=0.2, random_state=42, stratify=y_r
        )

        modelo_r, nombre_r, metricas_r = entrenar_modelo(
            X_tr, y_tr, X_te, y_te, multiclase=True
        )
        for n, m in metricas_r.items():
            print(f"  [risk_level]  {n:18s}: acc={m['acc']:.3f} | f1={m['f1']:.3f} | P={m['precision']:.3f} | R={m['recall']:.3f}")
        print(f"  -> Seleccionado: {nombre_r}")

        # ─── Guardar ────────────────────────────────────────────────────────
        out_disease = MODELS_DIR / f"{enfermedad}_disease.pkl"
        out_risk    = MODELS_DIR / f"{enfermedad}_risk.pkl"

        joblib.dump(
            {"model": modelo_d, "features": FEATURES, "algo": nombre_d, "metrics": metricas_d[nombre_d]},
            out_disease
        )
        joblib.dump(
            {"model": modelo_r, "features": FEATURES, "algo": nombre_r, "metrics": metricas_r[nombre_r]},
            out_risk
        )
        print(f"  Guardado: {out_disease.name}")
        print(f"  Guardado: {out_risk.name}")

        resumen.append({
            "enfermedad": enfermedad,
            "disease_algo": nombre_d, "disease_f1": metricas_d[nombre_d]["f1"], "disease_acc": metricas_d[nombre_d]["acc"],
            "risk_algo":    nombre_r, "risk_f1":    metricas_r[nombre_r]["f1"], "risk_acc":    metricas_r[nombre_r]["acc"],
        })

    # ─── Resumen final ───────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("RESUMEN DE METRICAS")
    print("=" * 70)
    print(f"{'Enfermedad':25s} | {'Disease F1':>10s} | {'Disease Acc':>11s} | {'Risk F1':>8s} | {'Risk Acc':>9s}")
    print("-" * 75)
    for r in resumen:
        print(
            f"{r['enfermedad']:25s} | "
            f"{r['disease_f1']:>10.3f} | {r['disease_acc']:>11.3f} | "
            f"{r['risk_f1']:>8.3f} | {r['risk_acc']:>9.3f}"
        )

    print(f"\nTodos los modelos guardados en: {MODELS_DIR}")
    print("Listo. Reinicia el servidor Django para que use los modelos.")


if __name__ == "__main__":
    main()
