"""Statistical analyses on ENEM data."""
import numpy as np
import pandas as pd

SUBJECTS = {
    "NU_NOTA_CN": "Ciências da Natureza",
    "NU_NOTA_CH": "Ciências Humanas",
    "NU_NOTA_LC": "Linguagens e Códigos",
    "NU_NOTA_MT": "Matemática",
    "NU_NOTA_REDACAO": "Redação",
}


def regional_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Mean scores and participant count per region."""
    cols = list(SUBJECTS.keys()) + ["media_geral"]
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


def school_type_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Mean scores by school type (public vs private)."""
    cols = list(SUBJECTS.keys()) + ["media_geral"]
    result = (
        df[df["escola_label"].isin(["Pública", "Privada"])]
        .groupby("escola_label")[cols]
        .agg(["mean", "std", "count"])
    )
    result.columns = ["_".join(c) for c in result.columns]
    return result.reset_index()


def gender_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Mean scores by gender."""
    cols = list(SUBJECTS.keys()) + ["media_geral"]
    return (
        df[df["genero_label"].isin(["Masculino", "Feminino"])]
        .groupby("genero_label")[cols]
        .mean()
        .round(1)
        .reset_index()
    )


def income_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Mean overall score per income bracket (ordered by bracket)."""
    from .data_loader import INCOME_MAP

    order = {v: i for i, v in enumerate(INCOME_MAP.values())}
    result = (
        df.groupby("renda_label")["media_geral"]
        .agg(["mean", "count"])
        .reset_index()
        .rename(columns={"mean": "media_geral", "count": "participantes"})
    )
    result["order"] = result["renda_label"].map(order).fillna(99)
    return result.sort_values("order").drop(columns="order")


def race_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Mean score per race/ethnicity group."""
    cols = list(SUBJECTS.keys()) + ["media_geral"]
    return (
        df[df["raca_label"] != "Não declarado"]
        .groupby("raca_label")[cols]
        .mean()
        .round(1)
        .reset_index()
        .sort_values("media_geral", ascending=False)
    )


def yearly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Mean scores per year."""
    cols = list(SUBJECTS.keys()) + ["media_geral"]
    return (
        df.groupby("NU_ANO")[cols]
        .mean()
        .round(1)
        .reset_index()
        .sort_values("NU_ANO")
    )


def score_distribution(df: pd.DataFrame, subject: str, bins: int = 40) -> tuple:
    """Return histogram counts and bin edges for a given subject column."""
    values = df[subject].dropna()
    counts, edges = np.histogram(values, bins=bins, range=(0, 1000))
    centers = ((edges[:-1] + edges[1:]) / 2).round(0)
    return centers.tolist(), counts.tolist()


def subject_correlations(df: pd.DataFrame) -> pd.DataFrame:
    """Pearson correlation matrix for all five subject scores."""
    cols = list(SUBJECTS.keys())
    return df[cols].corr().round(3)


def top_states(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Top-N states by mean overall score."""
    result = (
        df.groupby("SG_UF_RESIDENCIA")["media_geral"]
        .agg(["mean", "count"])
        .rename(columns={"mean": "media_geral", "count": "participantes"})
        .reset_index()
        .sort_values("media_geral", ascending=False)
        .head(n)
    )
    result["media_geral"] = result["media_geral"].round(1)
    return result
