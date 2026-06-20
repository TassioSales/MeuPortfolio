"""Score prediction model — Gradient Boosting with uncertainty estimate."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler

from .data_loader import INCOME_MAP, REGIONS

INCOME_ORDER = {v: i for i, v in enumerate(INCOME_MAP.values())}
_RACE_CLASSES = ["Não declarado", "Branco", "Preto", "Pardo", "Amarelo", "Indígena", "Outro"]
_REGION_ORDER = {r: i for i, r in enumerate(sorted(set(REGIONS.values())))}


def _build_features(df: pd.DataFrame) -> pd.DataFrame:
    race_enc = LabelEncoder().fit(_RACE_CLASSES)
    feat = pd.DataFrame({
        "school_private": (df["escola_label"] == "Privada").astype(int),
        "income_rank": df["renda_label"].map(INCOME_ORDER).fillna(0),
        "regiao_encoded": df["regiao"].map(_REGION_ORDER).fillna(0),
        "gender_male": (df["genero_label"] == "Masculino").astype(int),
        "race_encoded": race_enc.transform(
            df["raca_label"].fillna("Não declarado").where(
                df["raca_label"].isin(_RACE_CLASSES), "Outro"
            )
        ),
    })
    return feat


@st.cache_resource(show_spinner="Treinando modelo preditivo...")
def train_model(df: pd.DataFrame):
    feat = _build_features(df)
    target = df["media_geral"].dropna()
    feat = feat.loc[target.index]

    X_train, X_test, y_train, y_test = train_test_split(
        feat, target, test_size=0.2, random_state=42
    )

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("gbr", GradientBoostingRegressor(
            n_estimators=300, max_depth=4,
            learning_rate=0.08, subsample=0.8,
            min_samples_leaf=20, random_state=42,
        )),
    ])
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    residuals = y_test.values - y_pred
    metrics = {
        "mae": round(mean_absolute_error(y_test, y_pred), 1),
        "r2": round(r2_score(y_test, y_pred), 3),
        "rmse": round(float(np.sqrt(np.mean(residuals ** 2))), 1),
        "std_residual": round(float(residuals.std()), 1),
    }

    importances = model.named_steps["gbr"].feature_importances_
    feat_importance = pd.Series(importances, index=feat.columns).sort_values(ascending=False)

    return model, metrics, feat_importance


def predict_score(
    model,
    std_residual: float,
    school_private: bool,
    income_label: str,
    region: str,
    gender_male: bool,
    race_label: str,
) -> tuple[float, float, float]:
    """Return (predicted, lower_95, upper_95)."""
    race_enc = LabelEncoder().fit(_RACE_CLASSES)
    safe_race = race_label if race_label in _RACE_CLASSES else "Outro"

    row = pd.DataFrame([{
        "school_private": int(school_private),
        "income_rank": INCOME_ORDER.get(income_label, 0),
        "regiao_encoded": _REGION_ORDER.get(region, 0),
        "gender_male": int(gender_male),
        "race_encoded": race_enc.transform([safe_race])[0],
    }])
    pred = float(np.clip(model.predict(row)[0], 0, 1000))
    margin = 1.96 * std_residual
    lo = float(np.clip(pred - margin, 0, 1000))
    hi = float(np.clip(pred + margin, 0, 1000))
    return pred, lo, hi
