"""Plotly chart builders — modern dark-friendly theme."""
from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

TEMPLATE = "plotly_white"
PALETTE = px.colors.qualitative.Bold

SUBJECT_NAMES = {
    "NU_NOTA_CN": "Ciências Natureza",
    "NU_NOTA_CH": "Ciências Humanas",
    "NU_NOTA_LC": "Linguagens",
    "NU_NOTA_MT": "Matemática",
    "NU_NOTA_REDACAO": "Redação",
}

_LAYOUT = dict(
    template=TEMPLATE,
    font=dict(family="Inter, sans-serif", size=13),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=50, b=40, l=40, r=20),
)


def _apply(fig: go.Figure, **extra) -> go.Figure:
    fig.update_layout(**_LAYOUT, **extra)
    return fig


# ── Overview ─────────────────────────────────────────────────────────────────

def bar_regional(df_summary: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df_summary, x="regiao", y="media_geral",
        color="regiao", color_discrete_sequence=PALETTE,
        labels={"regiao": "Região", "media_geral": "Média Geral"},
        title="Média Geral por Região",
        text_auto=".1f",
    )
    fig.update_traces(textfont_size=12, marker_line_width=0)
    return _apply(fig, showlegend=False)


def line_yearly_trend(trend_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    colors = px.colors.qualitative.Vivid
    for i, (col, name) in enumerate(SUBJECT_NAMES.items()):
        if col not in trend_df.columns:
            continue
        fig.add_trace(go.Scatter(
            x=trend_df["NU_ANO"], y=trend_df[col],
            mode="lines+markers",
            name=name,
            line=dict(width=2.5, color=colors[i % len(colors)]),
            marker=dict(size=7),
        ))
    return _apply(fig, title="Evolução das Médias por Ano",
                  xaxis_title="Ano", yaxis_title="Nota Média",
                  legend=dict(orientation="h", y=-0.2))


def histogram_score(centers: list, counts: list, subject_name: str) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=centers, y=counts,
        marker=dict(color=counts, colorscale="Blues", showscale=False),
        opacity=0.85,
    ))
    return _apply(fig,
                  title=f"Distribuição — {subject_name}",
                  xaxis_title="Nota", yaxis_title="Candidatos")


# ── Map ───────────────────────────────────────────────────────────────────────

def choropleth_brazil(state_df: pd.DataFrame, value_col: str = "media_geral",
                      title: str = "Média Geral por Estado") -> go.Figure:
    """Choropleth using Plotly's built-in ISO-3166-2 support."""
    geojson_url = (
        "https://raw.githubusercontent.com/codeforamerica/click_that_hood/"
        "master/public/data/brazil-states.geojson"
    )
    try:
        import requests as _req
        resp = _req.get(geojson_url, timeout=5)
        geojson = resp.json()
        # Map feature id to UF code
        for feat in geojson.get("features", []):
            props = feat.get("properties", {})
            sigla = props.get("sigla") or props.get("UF_05") or props.get("id", "")
            feat["id"] = sigla

        fig = px.choropleth(
            state_df,
            geojson=geojson,
            locations="SG_UF_RESIDENCIA",
            color=value_col,
            color_continuous_scale="RdYlGn",
            range_color=[state_df[value_col].min() - 5, state_df[value_col].max() + 5],
            labels={value_col: "Média"},
            title=title,
            hover_data={"SG_UF_RESIDENCIA": True, value_col: ":.1f", "participantes": True},
        )
        fig.update_geos(fitbounds="locations", visible=False)
        return _apply(fig, height=500)
    except Exception:
        # Fallback: horizontal bar sorted by state
        sorted_df = state_df.sort_values(value_col)
        fig = px.bar(
            sorted_df, x=value_col, y="SG_UF_RESIDENCIA",
            orientation="h", color=value_col,
            color_continuous_scale="RdYlGn",
            title=title,
            labels={value_col: "Média", "SG_UF_RESIDENCIA": "Estado"},
        )
        return _apply(fig, height=700)


# ── Equity ───────────────────────────────────────────────────────────────────

def bar_school_gap(school_df: pd.DataFrame) -> go.Figure:
    subjects = [c.replace("_mean", "") for c in school_df.columns if c.endswith("_mean")]
    labels = [SUBJECT_NAMES.get(s, s) for s in subjects]
    colors = {"Pública": "#3498db", "Privada": "#e67e22"}

    fig = go.Figure()
    for _, row in school_df.iterrows():
        escola = row["escola_label"]
        means = [row.get(f"{s}_mean", 0) for s in subjects]
        fig.add_trace(go.Bar(
            name=escola, x=labels, y=means,
            marker_color=colors.get(escola, PALETTE[0]),
        ))
    return _apply(fig, barmode="group",
                  title="Pública vs Privada — Média por Disciplina",
                  yaxis_title="Nota Média", yaxis_range=[350, 750])


def radar_subjects(df_summary: pd.DataFrame, group_col: str) -> go.Figure:
    categories = list(SUBJECT_NAMES.values())
    cols = list(SUBJECT_NAMES.keys())
    colors = px.colors.qualitative.Bold

    fig = go.Figure()
    for i, (_, row) in enumerate(df_summary.iterrows()):
        values = [row.get(c, 0) for c in cols]
        values += values[:1]
        fig.add_trace(go.Scatterpolar(
            r=values, theta=categories + [categories[0]],
            fill="toself", name=str(row[group_col]),
            opacity=0.65, line=dict(color=colors[i % len(colors)], width=2),
        ))
    return _apply(fig,
                  title=f"Perfil por {group_col}",
                  polar=dict(radialaxis=dict(visible=True, range=[300, 750])))


# ── Socioeconomic ─────────────────────────────────────────────────────────────

def scatter_income_score(income_df: pd.DataFrame) -> go.Figure:
    fig = px.scatter(
        income_df, x="renda_label", y="media_geral",
        size="participantes", color="media_geral",
        color_continuous_scale="RdYlGn",
        labels={"renda_label": "Faixa de Renda", "media_geral": "Média Geral",
                "participantes": "Candidatos"},
        title="Renda Familiar × Nota Média (tamanho = nº de candidatos)",
    )
    fig.update_layout(xaxis_tickangle=-45)
    return _apply(fig)


def heatmap_correlation(corr_df: pd.DataFrame) -> go.Figure:
    labels = [SUBJECT_NAMES.get(c, c) for c in corr_df.columns]
    z = corr_df.values
    text = [[f"{v:.2f}" for v in row] for row in z]
    fig = go.Figure(go.Heatmap(
        z=z, x=labels, y=labels,
        colorscale="RdBu", zmin=-1, zmax=1,
        text=text, texttemplate="%{text}",
        colorbar=dict(title="r"),
    ))
    return _apply(fig, title="Correlação entre Disciplinas")


def bar_race(race_df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        race_df.sort_values("media_geral"),
        x="media_geral", y="raca_label",
        orientation="h", color="media_geral",
        color_continuous_scale="RdYlGn",
        labels={"raca_label": "Raça / Etnia", "media_geral": "Média Geral"},
        title="Média Geral por Raça / Etnia",
        text_auto=".1f",
    )
    return _apply(fig, showlegend=False)


# ── ML / Predictor ────────────────────────────────────────────────────────────

def gauge_predicted_score(score: float) -> go.Figure:
    color = "#e74c3c" if score < 450 else "#f39c12" if score < 600 else "#27ae60"
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        delta={"reference": 500, "valueformat": ".0f"},
        number={"valueformat": ".0f"},
        title={"text": "Nota Prevista (Média Geral)", "font": {"size": 16}},
        gauge={
            "axis": {"range": [0, 1000], "tickwidth": 1},
            "bar": {"color": color, "thickness": 0.3},
            "bgcolor": "white",
            "bordercolor": "#ccc",
            "steps": [
                {"range": [0, 450], "color": "#fadbd8"},
                {"range": [450, 650], "color": "#fef9e7"},
                {"range": [650, 1000], "color": "#eafaf1"},
            ],
            "threshold": {
                "line": {"color": "#2c3e50", "width": 3},
                "thickness": 0.8,
                "value": score,
            },
        },
    ))
    return _apply(fig, height=350)


def percentile_band_chart(score: float, percentile: float) -> go.Figure:
    """Horizontal band showing where the candidate stands."""
    x = list(range(0, 1001, 10))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=[1] * len(x),
        mode="markers",
        marker=dict(
            color=x,
            colorscale="RdYlGn",
            size=12,
            symbol="square",
            cmin=0, cmax=1000,
        ),
        showlegend=False,
        hoverinfo="skip",
    ))
    fig.add_vline(x=score, line_color="#2c3e50", line_width=3, annotation_text=f"Você: {score:.0f}")
    return _apply(fig,
                  title=f"Sua nota está no {percentile:.0f}º percentil",
                  xaxis_title="Nota Média",
                  yaxis=dict(visible=False),
                  height=160)


def feature_importance_chart(fi_series: "pd.Series") -> go.Figure:  # noqa: F821
    labels = {
        "school_private": "Escola Privada",
        "income_rank": "Nível de Renda",
        "regiao_encoded": "Região",
        "gender_male": "Gênero",
        "race_encoded": "Raça / Etnia",
    }
    df = fi_series.reset_index()
    df.columns = ["feature", "importance"]
    df["feature"] = df["feature"].map(labels).fillna(df["feature"])
    df = df.sort_values("importance")

    fig = px.bar(
        df, x="importance", y="feature", orientation="h",
        color="importance", color_continuous_scale="Blues",
        labels={"importance": "Importância", "feature": "Variável"},
        title="Importância das Variáveis no Modelo",
        text_auto=".3f",
    )
    return _apply(fig, showlegend=False)


# ── SISU ─────────────────────────────────────────────────────────────────────

def sisu_waterfall(eligible_df: pd.DataFrame, score: float) -> go.Figure:
    top = eligible_df.head(20)
    colors = ["#27ae60" if s == "✅ Aprovado" else "#f39c12"
              for s in top["situacao"]]
    fig = go.Figure(go.Bar(
        x=top["nota_corte"],
        y=top["curso"] + " — " + top["universidade"],
        orientation="h",
        marker_color=colors,
        text=top["nota_corte"].round(1),
        textposition="outside",
    ))
    fig.add_vline(x=score, line_dash="dash", line_color="#e74c3c",
                  annotation_text=f"Sua nota: {score:.0f}",
                  annotation_position="top right")
    return _apply(fig,
                  title="Cursos Elegíveis — Nota de Corte SISU 2023",
                  xaxis_title="Nota de Corte",
                  height=max(400, len(top) * 28))
