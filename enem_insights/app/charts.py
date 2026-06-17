"""Plotly chart builders."""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

PALETTE = px.colors.qualitative.Bold
SUBJECT_NAMES = {
    "NU_NOTA_CN": "Ciências Natureza",
    "NU_NOTA_CH": "Ciências Humanas",
    "NU_NOTA_LC": "Linguagens",
    "NU_NOTA_MT": "Matemática",
    "NU_NOTA_REDACAO": "Redação",
}


def bar_regional(df_summary: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df_summary,
        x="regiao",
        y="media_geral",
        color="regiao",
        color_discrete_sequence=PALETTE,
        labels={"regiao": "Região", "media_geral": "Média Geral"},
        title="Média Geral por Região",
        text_auto=".1f",
    )
    fig.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)")
    return fig


def radar_subjects(df_summary: pd.DataFrame, group_col: str) -> go.Figure:
    categories = list(SUBJECT_NAMES.values())
    cols = list(SUBJECT_NAMES.keys())

    fig = go.Figure()
    for _, row in df_summary.iterrows():
        values = [row.get(c, 0) for c in cols]
        values += values[:1]
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories + [categories[0]],
            fill="toself",
            name=str(row[group_col]),
            opacity=0.7,
        ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[300, 700])),
        title=f"Perfil de Desempenho por {group_col}",
    )
    return fig


def histogram_score(centers: list, counts: list, subject_name: str) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=centers,
        y=counts,
        marker_color=PALETTE[2],
        opacity=0.8,
    ))
    fig.update_layout(
        title=f"Distribuição de Notas — {subject_name}",
        xaxis_title="Nota",
        yaxis_title="Participantes",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def scatter_income_score(income_df: pd.DataFrame) -> go.Figure:
    fig = px.scatter(
        income_df,
        x="renda_label",
        y="media_geral",
        size="participantes",
        color="media_geral",
        color_continuous_scale="RdYlGn",
        labels={"renda_label": "Faixa de Renda", "media_geral": "Média Geral"},
        title="Impacto da Renda Familiar na Nota Média",
    )
    fig.update_layout(xaxis_tickangle=-45, plot_bgcolor="rgba(0,0,0,0)")
    return fig


def heatmap_correlation(corr_df: pd.DataFrame) -> go.Figure:
    labels = [SUBJECT_NAMES.get(c, c) for c in corr_df.columns]
    fig = go.Figure(go.Heatmap(
        z=corr_df.values,
        x=labels,
        y=labels,
        colorscale="RdBu",
        zmin=-1,
        zmax=1,
        text=corr_df.round(2).values,
        texttemplate="%{text}",
    ))
    fig.update_layout(title="Correlação entre Disciplinas")
    return fig


def line_yearly_trend(trend_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for col, name in SUBJECT_NAMES.items():
        if col in trend_df.columns:
            fig.add_trace(go.Scatter(
                x=trend_df["NU_ANO"],
                y=trend_df[col],
                mode="lines+markers",
                name=name,
            ))
    fig.update_layout(
        title="Evolução das Médias por Ano",
        xaxis_title="Ano",
        yaxis_title="Média",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def bar_school_gap(school_df: pd.DataFrame) -> go.Figure:
    rows = school_df.copy()
    subjects = [c.replace("_mean", "") for c in rows.columns if c.endswith("_mean")]
    labels = [SUBJECT_NAMES.get(s, s) for s in subjects]

    fig = go.Figure()
    for _, row in rows.iterrows():
        escola = row["escola_label"]
        means = [row.get(f"{s}_mean", 0) for s in subjects]
        fig.add_trace(go.Bar(name=escola, x=labels, y=means))

    fig.update_layout(
        barmode="group",
        title="Pública vs Privada — Média por Disciplina",
        yaxis_title="Nota Média",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def gauge_predicted_score(score: float) -> go.Figure:
    color = "#e74c3c" if score < 450 else "#f39c12" if score < 600 else "#27ae60"
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        delta={"reference": 500},
        title={"text": "Nota Prevista (Média Geral)"},
        gauge={
            "axis": {"range": [0, 1000]},
            "bar": {"color": color},
            "steps": [
                {"range": [0, 450], "color": "#fadbd8"},
                {"range": [450, 650], "color": "#fdebd0"},
                {"range": [650, 1000], "color": "#d5f5e3"},
            ],
        },
    ))
    return fig
