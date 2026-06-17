"""Score prediction model using socioeconomic features."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler

from .data_loader import INCOME_MAP, REGIONS

INCOME_ORDER = {v: i for i, v in enumerate(INCOME_MAP.values())}

FEATURE_LABELS = {
    "school_private": "Escola Privada",
    "income_rank": "Nível de Renda",
    "regiao_encoded": "Região do Brasil",
    "gender_male": "Gênero Masculino",
    "race_encoded": "Raça/Etnia",
}


def _build_features(df: pd.DataFrame) -> pd.DataFrame:
    feat = pd.DataFrame()
    feat["school_private"] = (df["escola_label"] == "Privada").astype(int)
    feat["income_rank"] = df["renda_label"].map(INCOME_ORDER).fillna(0)

    region_order = {r: i for i, r in enumerate(sorted(set(REGIONS.values())))}
    feat["regiao_encoded"] = df["regiao"].map(region_order).fillna(0)

    feat["gender_male"] = (df["genero_label"] == "Masculino").astype(int)

    race_enc = LabelEncoder()
    feat["race_encoded"] = race_enc.fit_transform(df["raca_label"].fillna("Não declarado"))
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
            n_estimators=200,
            max_depth=4,
            learning_rate=0.1,
            subsample=0.8,
            random_state=42,
        )),
    ])
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    metrics = {
        "mae": mean_absolute_error(y_test, y_pred),
        "r2": r2_score(y_test, y_pred),
        "rmse": float(np.sqrt(np.mean((y_test - y_pred) ** 2))),
    }

    importances = model.named_steps["gbr"].feature_importances_
    feat_importance = pd.Series(importances, index=feat.columns).sort_values(ascending=False)

    return model, metrics, feat_importance


def predict_score(
    model,
    school_private: bool,
    income_label: str,
    region: str,
    gender_male: bool,
    race_label: str,
) -> float:
    region_order = {r: i for i, r in enumerate(sorted(set(REGIONS.values())))}
    race_enc = LabelEncoder()
    known_races = [
        "Não declarado", "Branco", "Preto", "Pardo", "Amarelo", "Indígena", "Outro"
    ]
    race_enc.fit(known_races)

    row = pd.DataFrame([{
        "school_private": int(school_private),
        "income_rank": INCOME_ORDER.get(income_label, 0),
        "regiao_encoded": region_order.get(region, 0),
        "gender_male": int(gender_male),
        "race_encoded": (
            race_enc.transform([race_label])[0]
            if race_label in known_races
            else 0
        ),
    }])
    return float(np.clip(model.predict(row)[0], 0, 1000))
