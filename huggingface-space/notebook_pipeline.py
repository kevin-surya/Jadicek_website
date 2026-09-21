"""Feature transformation used by `satria_data - Copy.ipynb`."""
from __future__ import annotations

import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

BASE_FEATURES = [
    "smoking", "alcohol", "bmi", "exercise", "high_blood_pressure",
    "high_cholesterol", "sex", "age_group", "difficulty_walking",
    "general_health", "residence", "physical_activity",
]
CATEGORIES = {
    "smoking": [1.0, 2.0], "alcohol": [1.0, 2.0], "exercise": [1.0, 2.0],
    "sex": [1.0, 2.0], "age_group": [float(x) for x in range(1, 15)],
    "difficulty_walking": [1.0, 2.0],
    "general_health": [float(x) for x in range(1, 6)],
    "physical_activity": [float(x) for x in range(1, 5)],
}


class NotebookFeatureTransformer(BaseEstimator, TransformerMixin):
    """Reproduce cell 38, including raw BP/cholesterol/residence columns."""

    def __init__(self, include_diabetes=False):
        self.include_diabetes = include_diabetes

    def fit(self, X, y=None):
        transformed = self._transform(X)
        self.feature_names_in_order_ = transformed.columns.tolist()
        return self

    def transform(self, X):
        transformed = self._transform(X)
        return transformed.reindex(columns=self.feature_names_in_order_, fill_value=0)

    def _transform(self, X):
        data = pd.DataFrame(X).copy()
        leading = ["bmi", "high_blood_pressure", "high_cholesterol", "residence"]
        if self.include_diabetes:
            leading = ["diabetes"] + leading
        result = data[leading].astype(float).reset_index(drop=True)
        for column, categories in CATEGORIES.items():
            values = pd.Categorical(data[column].astype(float), categories=categories)
            dummies = pd.get_dummies(values, prefix=column, dtype=int)
            result = pd.concat([result, dummies.reset_index(drop=True)], axis=1)
        return result

    def get_feature_names_out(self, input_features=None):
        return self.feature_names_in_order_
