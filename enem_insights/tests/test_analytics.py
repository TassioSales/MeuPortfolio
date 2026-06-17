"""Unit tests for analytics module."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import pytest

from app.data_loader import _generate_synthetic_data, load_data
from app.analytics import (
    gender_summary,
    income_summary,
    race_summary,
    regional_summary,
    school_type_summary,
    score_distribution,
    subject_correlations,
    yearly_trend,
    top_states,
)


@pytest.fixture(scope="module")
def sample_df():
    return _generate_synthetic_data(n=5_000, seed=0)


def test_synthetic_data_shape(sample_df):
    assert len(sample_df) == 5_000
    assert "media_geral" in sample_df.columns
    assert "regiao" in sample_df.columns


def test_scores_in_range(sample_df):
    for col in ["NU_NOTA_CN", "NU_NOTA_CH", "NU_NOTA_LC", "NU_NOTA_MT", "NU_NOTA_REDACAO"]:
        assert sample_df[col].between(0, 1000).all(), f"{col} out of range"


def test_regional_summary_has_all_regions(sample_df):
    result = regional_summary(sample_df)
    assert "media_geral" in result.columns
    assert len(result) >= 4


def test_school_type_summary_columns(sample_df):
    result = school_type_summary(sample_df)
    assert "escola_label" in result.columns
    assert any("media_geral" in c for c in result.columns)


def test_gender_summary(sample_df):
    result = gender_summary(sample_df)
    assert set(result["genero_label"]) == {"Masculino", "Feminino"}


def test_income_summary_ordered(sample_df):
    result = income_summary(sample_df)
    assert "media_geral" in result.columns
    assert len(result) > 1


def test_race_summary(sample_df):
    result = race_summary(sample_df)
    assert len(result) >= 1


def test_yearly_trend(sample_df):
    result = yearly_trend(sample_df)
    assert "NU_ANO" in result.columns
    assert len(result) >= 1


def test_score_distribution(sample_df):
    centers, counts = score_distribution(sample_df, "NU_NOTA_MT")
    assert len(centers) == len(counts)
    assert sum(counts) == sample_df["NU_NOTA_MT"].notna().sum()


def test_subject_correlations(sample_df):
    corr = subject_correlations(sample_df)
    assert corr.shape == (5, 5)
    assert (corr.diagonal() == 1.0).all()


def test_top_states(sample_df):
    result = top_states(sample_df, n=5)
    assert len(result) <= 5
    assert "media_geral" in result.columns


def test_private_school_advantage(sample_df):
    pub = sample_df[sample_df["escola_label"] == "Pública"]["media_geral"].mean()
    priv = sample_df[sample_df["escola_label"] == "Privada"]["media_geral"].mean()
    assert priv > pub, "Private schools should outperform public in synthetic data"
