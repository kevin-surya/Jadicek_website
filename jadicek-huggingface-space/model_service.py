"""Load saved pipelines and map the website contract to BRFSS model features."""
from __future__ import annotations

from pathlib import Path
import joblib
import pandas as pd

MODEL_DIR = Path(__file__).resolve().parent / "models"
BASE_FEATURES = [
    "smoking", "alcohol", "bmi", "exercise", "high_blood_pressure",
    "high_cholesterol", "sex", "age_group", "difficulty_walking",
    "general_health", "residence", "physical_activity",
]
YES_NO = {"ya": 1, "tidak": 2}
SEX = {"laki-laki": 1, "perempuan": 2}
HEALTH = {"sangat_baik": 1, "baik": 2, "cukup": 3, "kurang": 4}
ACTIVITY = {"sangat_aktif": 1, "aktif": 2, "cukup": 3, "kurang": 4}


class ModelService:
    def __init__(self, model_dir=MODEL_DIR):
        model_dir = Path(model_dir)
        self.diabetes = joblib.load(model_dir / "diabetes_pipeline.joblib")
        self.heart = joblib.load(model_dir / "heart_pipeline.joblib")

    @staticmethod
    def _choice(payload, field, mapping):
        value = payload.get(field)
        if value not in mapping:
            raise ValueError(f"Nilai {field} tidak valid.")
        return mapping[value]

    def prepare(self, payload):
        try:
            bmi = float(payload.get("bmi"))
            age = int(float(payload.get("umur")))
            residence = int(float(payload.get("domisili")))
        except (TypeError, ValueError):
            raise ValueError("BMI, umur, atau domisili tidak valid.") from None
        if not 10 <= bmi <= 100 or age not in range(1, 15) or residence not in (1, 2):
            raise ValueError("BMI, umur, atau domisili di luar rentang model.")
        row = {
            "smoking": self._choice(payload, "merokok", YES_NO),
            "alcohol": self._choice(payload, "alkohol", YES_NO),
            "bmi": bmi,
            "exercise": self._choice(payload, "olahraga", YES_NO),
            # BRFSS calculated _RFHYPE6 is reversed: 1=no, 2=yes.
            "high_blood_pressure": self._choice(payload, "tekanan_darah_tinggi", {"ya": 2, "tidak": 1}),
            "high_cholesterol": self._choice(payload, "kolesterol_tinggi", YES_NO),
            "sex": self._choice(payload, "jenis_klmn", SEX),
            "age_group": age,
            "difficulty_walking": self._choice(payload, "susah_jalan", YES_NO),
            "general_health": self._choice(payload, "kesehatan_umum", HEALTH),
            "residence": residence,
            "physical_activity": self._choice(payload, "aktivitas_fisik", ACTIVITY),
        }
        return pd.DataFrame([row], columns=BASE_FEATURES)

    @staticmethod
    def label(score):
        if score < 0.35:
            return "Indikasi model rendah"
        if score < 0.65:
            return "Indikasi model sedang"
        return "Indikasi model tinggi"

    def predict(self, payload):
        features = self.prepare(payload)
        # The notebook encodes condition present/history as class 0.
        diabetes_classes = list(self.diabetes.named_steps["model"].classes_)
        diabetes_score = float(self.diabetes.predict_proba(features)[0, diabetes_classes.index(0)])
        heart_features = features.copy()
        # Faithful to cell 69: the already-binary diabetes column is remapped to 0.
        heart_features.insert(0, "diabetes", 0)
        heart_classes = list(self.heart.named_steps["model"].classes_)
        heart_score = float(self.heart.predict_proba(heart_features)[0, heart_classes.index(0)])
        return {
            "diabetes_result": self.label(diabetes_score),
            "heart_result": self.label(heart_score),
            "diabetes_score": round(diabetes_score, 4),
            "heart_score": round(heart_score, 4),
            "model_status": "local-trained",
        }
