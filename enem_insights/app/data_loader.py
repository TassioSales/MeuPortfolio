"""Load ENEM microdata or generate synthetic sample data."""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
import streamlit as st
from loguru import logger

REGIONS: dict[str, str] = {
    "AC": "Norte", "AM": "Norte", "AP": "Norte", "PA": "Norte",
    "RO": "Norte", "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste",
    "PB": "Nordeste", "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste",
    "SE": "Nordeste",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MS": "Centro-Oeste", "MT": "Centro-Oeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}

STATE_ISO: dict[str, str] = {uf: f"BR-{uf}" for uf in REGIONS}

SCHOOL_TYPE_MAP = {1: "Não respondeu", 2: "Pública", 3: "Privada", 4: "Exterior"}
GENDER_MAP = {"M": "Masculino", "F": "Feminino"}
RACE_MAP = {0: "Não declarado", 1: "Branco", 2: "Preto", 3: "Pardo", 4: "Amarelo", 5: "Indígena"}
INCOME_MAP = {
    "A": "Nenhuma renda",
    "B": "Até R$ 1.320",
    "C": "R$ 1.320 – R$ 1.980",
    "D": "R$ 1.980 – R$ 2.640",
    "E": "R$ 2.640 – R$ 3.960",
    "F": "R$ 3.960 – R$ 5.280",
    "G": "R$ 5.280 – R$ 6.600",
    "H": "R$ 6.600 – R$ 7.920",
    "I": "R$ 7.920 – R$ 9.240",
    "J": "R$ 9.240 – R$ 10.560",
    "K": "R$ 10.560 – R$ 11.880",
    "L": "R$ 11.880 – R$ 13.200",
    "M": "R$ 13.200 – R$ 15.840",
    "N": "R$ 15.840 – R$ 19.800",
    "O": "R$ 19.800 – R$ 26.400",
    "P": "Acima de R$ 26.400",
    "Q": "Acima de R$ 39.600",
}

SUBJECT_COLS = ["NU_NOTA_CN", "NU_NOTA_CH", "NU_NOTA_LC", "NU_NOTA_MT", "NU_NOTA_REDACAO"]
SUBJECT_NAMES = {
    "NU_NOTA_CN": "Ciências da Natureza",
    "NU_NOTA_CH": "Ciências Humanas",
    "NU_NOTA_LC": "Linguagens e Códigos",
    "NU_NOTA_MT": "Matemática",
    "NU_NOTA_REDACAO": "Redação",
}


# ── Synthetic data generation ────────────────────────────────────────────────

def _state_weights(states: list[str]) -> np.ndarray:
    pop = {
        "SP": 45.9, "MG": 21.3, "RJ": 17.5, "BA": 14.9, "PR": 11.4,
        "RS": 11.4, "PE": 9.6, "CE": 9.2, "PA": 8.7, "MA": 7.1,
        "SC": 7.6, "GO": 7.2, "AM": 4.1, "ES": 4.1, "PB": 4.0,
        "RN": 3.5, "MT": 3.6, "MS": 2.8, "PI": 3.3, "AL": 3.3,
        "SE": 2.3, "RO": 1.8, "TO": 1.6, "DF": 3.0, "AC": 0.9,
        "AP": 0.8, "RR": 0.6,
    }
    arr = np.array([pop.get(s, 1.0) for s in states], dtype=float)
    return arr / arr.sum()


def _income_weights(n_buckets: int) -> np.ndarray:
    raw = [2, 12, 14, 12, 11, 9, 7, 6, 5, 4, 3, 3, 3, 2, 2, 1, 1]
    arr = np.array(raw[:n_buckets], dtype=float)
    return arr / arr.sum()


def _generate_synthetic_data(n: int = 60_000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    states = list(REGIONS.keys())
    income_letters = list(INCOME_MAP.keys())

    ufs = rng.choice(states, size=n, p=_state_weights(states))
    school_types = rng.choice([2, 3], size=n, p=[0.76, 0.24])
    genders = rng.choice(["F", "M"], size=n, p=[0.56, 0.44])
    races = rng.choice(
        list(RACE_MAP.keys()), size=n,
        p=[0.04, 0.32, 0.10, 0.45, 0.04, 0.05]
    )
    incomes = rng.choice(income_letters, size=n, p=_income_weights(len(income_letters)))

    # income index 0-16 maps linearly to bonus score
    income_index = np.array([income_letters.index(i) for i in incomes], dtype=float)
    school_bonus = np.where(school_types == 3, 70.0, 0.0)
    income_bonus = income_index * 8.5

    # small regional effect
    region_bonus = np.array(
        [{"Sul": 15, "Sudeste": 10, "Centro-Oeste": 5, "Nordeste": -5, "Norte": -10}
         .get(REGIONS.get(uf, ""), 0) for uf in ufs],
        dtype=float,
    )

    base = 450 + school_bonus + income_bonus + region_bonus + rng.normal(0, 28, n)

    def subj(shift=0, noise=80):
        return np.clip(base + shift + rng.normal(0, noise, n), 0, 1000).round(1)

    redacao = np.clip(base + rng.normal(0, 120, n), 0, 1000)
    redacao = (redacao / 40).round() * 40  # ENEM grades in 40-pt steps

    df = pd.DataFrame({
        "NU_ANO": rng.choice([2019, 2020, 2021, 2022, 2023], size=n,
                             p=[0.18, 0.16, 0.18, 0.24, 0.24]),
        "SG_UF_RESIDENCIA": ufs,
        "TP_ESCOLA": school_types,
        "TP_SEXO": genders,
        "TP_COR_RACA": races,
        "Q006": incomes,
        "NU_NOTA_CN": subj(shift=0, noise=85),
        "NU_NOTA_CH": subj(shift=10, noise=75),
        "NU_NOTA_LC": subj(shift=15, noise=70),
        "NU_NOTA_MT": subj(shift=-10, noise=100),
        "NU_NOTA_REDACAO": redacao,
    })
    return df


# ── Public loader ────────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Carregando dados do ENEM...")
def load_data() -> pd.DataFrame:
    path = os.getenv("ENEM_DATA_PATH", "")
    sample_size = int(os.getenv("ENEM_SAMPLE_SIZE", "0"))

    if path and os.path.exists(path):
        logger.info(f"Loading microdata from {path}")
        df = pd.read_csv(
            path, sep=";", encoding="latin-1",
            usecols=["NU_ANO", "SG_UF_RESIDENCIA", "TP_ESCOLA", "TP_SEXO",
                     "TP_COR_RACA", "Q006"] + SUBJECT_COLS,
            nrows=sample_size or None,
        )
        df = df.dropna(subset=["NU_NOTA_MT", "NU_NOTA_REDACAO"])
    else:
        logger.info("No data path — using synthetic sample.")
        df = _generate_synthetic_data()

    df["regiao"] = df["SG_UF_RESIDENCIA"].map(REGIONS).fillna("Desconhecida")
    df["iso_code"] = df["SG_UF_RESIDENCIA"].map(STATE_ISO)
    df["escola_label"] = df["TP_ESCOLA"].map(SCHOOL_TYPE_MAP).fillna("Outro")
    df["genero_label"] = df["TP_SEXO"].map(GENDER_MAP).fillna("Outro")
    df["raca_label"] = df["TP_COR_RACA"].map(RACE_MAP).fillna("Não declarado")
    df["renda_label"] = df["Q006"].map(INCOME_MAP).fillna("Não informado")

    df["media_objetivas"] = df[["NU_NOTA_CN", "NU_NOTA_CH", "NU_NOTA_LC", "NU_NOTA_MT"]].mean(axis=1).round(1)
    df["media_geral"] = df[SUBJECT_COLS].mean(axis=1).round(1)

    return df


def calc_percentile(df: pd.DataFrame, score: float) -> float:
    """Return percentile rank of *score* within the dataset (0–100)."""
    return float((df["media_geral"] < score).mean() * 100)
