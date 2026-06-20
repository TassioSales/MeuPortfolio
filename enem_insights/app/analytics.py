"""Statistical analyses on ENEM data."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data_loader import INCOME_MAP, SUBJECT_COLS

SUBJECTS = {
    "NU_NOTA_CN": "Ciências da Natureza",
    "NU_NOTA_CH": "Ciências Humanas",
    "NU_NOTA_LC": "Linguagens e Códigos",
    "NU_NOTA_MT": "Matemática",
    "NU_NOTA_REDACAO": "Redação",
}


def regional_summary(df: pd.DataFrame) -> pd.DataFrame:
    cols = SUBJECT_COLS + ["media_geral"]
    agg = {c: "mean" for c in cols}
    agg["SG_UF_RESIDENCIA"] = "count"
    result = (
        df.groupby("regiao")
        .agg(agg)
        .rename(columns={"SG_UF_RESIDENCIA": "participantes"})
        .reset_index()
    )
    for col in cols:
        result[col] = result[col].round(1)
    return result.sort_values("media_geral", ascending=False)


def state_summary(df: pd.DataFrame) -> pd.DataFrame:
    cols = SUBJECT_COLS + ["media_geral"]
    result = (
        df.groupby(["SG_UF_RESIDENCIA", "iso_code", "regiao"])
        .agg({c: "mean" for c in cols} | {"NU_ANO": "count"})
        .rename(columns={"NU_ANO": "participantes"})
        .reset_index()
    )
    for col in cols:
        result[col] = result[col].round(1)
    return result.sort_values("media_geral", ascending=False)


def school_type_summary(df: pd.DataFrame) -> pd.DataFrame:
    cols = SUBJECT_COLS + ["media_geral"]
    result = (
        df[df["escola_label"].isin(["Pública", "Privada"])]
        .groupby("escola_label")[cols]
        .agg(["mean", "std", "count"])
    )
    result.columns = ["_".join(c) for c in result.columns]
    return result.reset_index()


def gender_summary(df: pd.DataFrame) -> pd.DataFrame:
    cols = SUBJECT_COLS + ["media_geral"]
    return (
        df[df["genero_label"].isin(["Masculino", "Feminino"])]
        .groupby("genero_label")[cols]
        .mean()
        .round(1)
        .reset_index()
    )


def income_summary(df: pd.DataFrame) -> pd.DataFrame:
    order = {v: i for i, v in enumerate(INCOME_MAP.values())}
    result = (
        df.groupby("renda_label")["media_geral"]
        .agg(["mean", "count"])
        .reset_index()
        .rename(columns={"mean": "media_geral", "count": "participantes"})
    )
    result["order"] = result["renda_label"].map(order).fillna(99)
    return result.sort_values("order").drop(columns="order").reset_index(drop=True)


def race_summary(df: pd.DataFrame) -> pd.DataFrame:
    cols = SUBJECT_COLS + ["media_geral"]
    return (
        df[df["raca_label"] != "Não declarado"]
        .groupby("raca_label")[cols]
        .mean()
        .round(1)
        .reset_index()
        .sort_values("media_geral", ascending=False)
    )


def yearly_trend(df: pd.DataFrame) -> pd.DataFrame:
    cols = SUBJECT_COLS + ["media_geral"]
    return (
        df.groupby("NU_ANO")[cols]
        .mean()
        .round(1)
        .reset_index()
        .sort_values("NU_ANO")
    )


def score_distribution(df: pd.DataFrame, subject: str, bins: int = 40) -> tuple[list, list]:
    values = df[subject].dropna()
    counts, edges = np.histogram(values, bins=bins, range=(0, 1000))
    centers = ((edges[:-1] + edges[1:]) / 2).round(0)
    return centers.tolist(), counts.tolist()


def subject_correlations(df: pd.DataFrame) -> pd.DataFrame:
    return df[SUBJECT_COLS].corr().round(3)


def top_states(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    result = (
        df.groupby("SG_UF_RESIDENCIA")["media_geral"]
        .agg(["mean", "count"])
        .rename(columns={"mean": "Média", "count": "Participantes"})
        .reset_index()
        .rename(columns={"SG_UF_RESIDENCIA": "Estado"})
        .sort_values("Média", ascending=False)
        .head(n)
    )
    result["Média"] = result["Média"].round(1)
    return result.reset_index(drop=True)


def inequality_index(df: pd.DataFrame) -> dict:
    """Compute a composite inequality index (0–100) from school and income gaps."""
    pub = df[df["escola_label"] == "Pública"]["media_geral"]
    prv = df[df["escola_label"] == "Privada"]["media_geral"]
    school_gap = prv.mean() - pub.mean()

    income_df = income_summary(df)
    income_gap = income_df["media_geral"].max() - income_df["media_geral"].min()

    race_df = race_summary(df)
    race_gap = race_df["media_geral"].max() - race_df["media_geral"].min()

    # Normalize to 0-100 (higher = more inequality)
    index = min(100, (school_gap * 0.4 + income_gap * 0.4 + race_gap * 0.2) / 2)
    return {
        "school_gap": round(school_gap, 1),
        "income_gap": round(income_gap, 1),
        "race_gap": round(race_gap, 1),
        "index": round(index, 1),
    }


def percentile_distribution(df: pd.DataFrame, bins: int = 20) -> pd.DataFrame:
    """Score cutoff per percentile bucket (useful for percentile band chart)."""
    quantiles = np.linspace(0, 1, bins + 1)
    cuts = df["media_geral"].quantile(quantiles).round(1)
    return pd.DataFrame({
        "percentil": (quantiles * 100).round(0).astype(int),
        "nota": cuts.values,
    })
