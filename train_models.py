"""Faithful, reproducible run of `satria_data - Copy.ipynb`."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from sklearn.ensemble import AdaBoostClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, average_precision_score, confusion_matrix, f1_score,
    precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from notebook_pipeline import BASE_FEATURES, NotebookFeatureTransformer

RAW_COLUMNS = {
    "CVDINFR4": "heart_target", "DIABETE4": "diabetes_target",
    "SMOKE100": "smoking", "DRNKANY6": "alcohol", "_BMI5": "bmi",
    "EXERANY2": "exercise", "_RFHYPE6": "high_blood_pressure",
    "TOLDHI3": "high_cholesterol", "SEXVAR": "sex",
    "_AGEG5YR": "age_group", "DIFFWALK": "difficulty_walking",
    "GENHLTH": "general_health", "_URBSTAT": "residence",
    "_PACAT3": "physical_activity",
}
FILTER_79 = [
    "smoking", "alcohol", "exercise", "high_blood_pressure",
    "high_cholesterol", "difficulty_walking", "diabetes_target",
    "heart_target", "general_health", "physical_activity",
]


def reproduce_notebook_cleaning(path: Path):
    df = pd.read_csv(path, usecols=list(RAW_COLUMNS)).rename(columns=RAW_COLUMNS)
    df = df.dropna().drop_duplicates()
    df["bmi"] = df["bmi"] / 100
    for column in FILTER_79:
        df = df[~df[column].isin([7, 9])]
    df = df.reset_index(drop=True)
    df["diabetes_target"] = df["diabetes_target"].replace({1: 0, 2: 1, 3: 2, 4: 3})
    df["heart_target"] = df["heart_target"].replace({1: 0, 2: 1})
    df["diabetes_target"] = df["diabetes_target"].replace({0: 0, 1: 0, 2: 1, 3: 1}).astype(int)
    df["heart_target"] = df["heart_target"].astype(int)
    return df


def candidates():
    return {
        "XGBoost": XGBClassifier(eval_metric="logloss"),
        "AdaBoost": AdaBoostClassifier(),
        "LightGBM": LGBMClassifier(verbosity=-1),
        "CatBoost": CatBoostClassifier(verbose=0),
        "Logistic Regression": LogisticRegression(max_iter=1000),
    }


def evaluate(y_true, predicted, disease_score):
    notebook = {
        "accuracy": float(accuracy_score(y_true, predicted)),
        "precision_weighted": float(precision_score(y_true, predicted, average="weighted", zero_division=0)),
        "recall_weighted": float(recall_score(y_true, predicted, average="weighted", zero_division=0)),
        "f1_weighted": float(f1_score(y_true, predicted, average="weighted", zero_division=0)),
    }
    disease_true = (np.asarray(y_true) == 0).astype(int)
    disease_pred = (np.asarray(predicted) == 0).astype(int)
    disease = {
        "precision": float(precision_score(disease_true, disease_pred, zero_division=0)),
        "recall": float(recall_score(disease_true, disease_pred, zero_division=0)),
        "f1": float(f1_score(disease_true, disease_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(disease_true, disease_score)),
        "average_precision": float(average_precision_score(disease_true, disease_score)),
        "confusion_matrix": confusion_matrix(disease_true, disease_pred).tolist(),
    }
    return {"notebook_weighted": notebook, "disease_class": disease}


def run_models(X, y, include_diabetes):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    results, fitted = {}, {}
    for name, estimator in candidates().items():
        pipeline = Pipeline([
            ("features", NotebookFeatureTransformer(include_diabetes=include_diabetes)),
            ("model", estimator),
        ])
        pipeline.fit(X_train, y_train)
        prediction = pipeline.predict(X_test)
        probabilities = pipeline.predict_proba(X_test)
        class_zero_index = list(pipeline.named_steps["model"].classes_).index(0)
        results[name] = evaluate(y_test, prediction, probabilities[:, class_zero_index])
        fitted[name] = pipeline
        print(name, json.dumps(results[name]["notebook_weighted"]), flush=True)
    return results, fitted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "models")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    df = reproduce_notebook_cleaning(args.data)

    diabetes = df.drop(columns="heart_target").drop_duplicates()
    diabetes_results, diabetes_models = run_models(
        diabetes[BASE_FEATURES], diabetes["diabetes_target"], include_diabetes=False,
    )

    heart = df.copy()
    heart["diabetes"] = heart["diabetes_target"].replace({0: 0, 1: 0, 2: 1, 3: 1})
    heart_features = ["diabetes"] + BASE_FEATURES
    heart_results, heart_models = run_models(
        heart[heart_features], heart["heart_target"], include_diabetes=True,
    )

    joblib.dump(diabetes_models["LightGBM"], args.output / "diabetes_pipeline.joblib", compress=3)
    joblib.dump(heart_models["LightGBM"], args.output / "heart_pipeline.joblib", compress=3)
    report = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "notebook": str((Path(__file__).parent.parent / "satria_data - Copy.ipynb").resolve()),
        "source": str(args.data.resolve()),
        "clean_rows_before_task_dedup": len(df),
        "diabetes_rows": len(diabetes), "heart_rows": len(heart),
        "label_semantics": {"0": "condition present/history", "1": "condition absent/borderline"},
        "selected_model": {"diabetes": "LightGBM", "heart": "LightGBM"},
        "diabetes": diabetes_results, "heart": heart_results,
        "faithful_notebook_notes": [
            "Unknown/refused values 7 and 9 and null rows are removed exactly as in the notebook.",
            "The notebook maps gestational diabetes to disease and borderline/prediabetes to no disease.",
            "The notebook's heart feature `diabetes` becomes constant 0 in cell 69; this is reproduced.",
            "The 80s/90s figures are overall/weighted metrics on imbalanced targets, not disease-class recall.",
        ],
    }
    (args.output / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "selected_diabetes": report["diabetes"]["LightGBM"],
        "selected_heart": report["heart"]["LightGBM"],
    }, indent=2))


if __name__ == "__main__":
    main()
