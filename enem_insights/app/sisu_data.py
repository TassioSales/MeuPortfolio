"""Approximate SISU 2023/2024 cutoff scores — public data from MEC/INEP."""
from __future__ import annotations

import pandas as pd

COURSES: list[dict] = [
    # ── Medicina ───────────────────────────────────────────────────────────────
    {"curso": "Medicina", "universidade": "UNIFESP", "uf": "SP", "nota_corte": 895.06, "modalidade": "Ampla"},
    {"curso": "Medicina", "universidade": "UFMG", "uf": "MG", "nota_corte": 882.34, "modalidade": "Ampla"},
    {"curso": "Medicina", "universidade": "UFRGS", "uf": "RS", "nota_corte": 878.12, "modalidade": "Ampla"},
    {"curso": "Medicina", "universidade": "UFPR", "uf": "PR", "nota_corte": 862.45, "modalidade": "Ampla"},
    {"curso": "Medicina", "universidade": "UFSC", "uf": "SC", "nota_corte": 858.92, "modalidade": "Ampla"},
    {"curso": "Medicina", "universidade": "UFC", "uf": "CE", "nota_corte": 847.61, "modalidade": "Ampla"},
    {"curso": "Medicina", "universidade": "UFPE", "uf": "PE", "nota_corte": 841.23, "modalidade": "Ampla"},
    {"curso": "Medicina", "universidade": "UFBA", "uf": "BA", "nota_corte": 836.77, "modalidade": "Ampla"},
    {"curso": "Medicina", "universidade": "UFG", "uf": "GO", "nota_corte": 831.44, "modalidade": "Ampla"},
    {"curso": "Medicina", "universidade": "UFPA", "uf": "PA", "nota_corte": 818.55, "modalidade": "Ampla"},
    {"curso": "Medicina", "universidade": "UFRN", "uf": "RN", "nota_corte": 825.38, "modalidade": "Ampla"},
    {"curso": "Medicina", "universidade": "UFAM", "uf": "AM", "nota_corte": 802.19, "modalidade": "Ampla"},
    # ── Direito ────────────────────────────────────────────────────────────────
    {"curso": "Direito", "universidade": "UFMG", "uf": "MG", "nota_corte": 741.32, "modalidade": "Ampla"},
    {"curso": "Direito", "universidade": "UFRGS", "uf": "RS", "nota_corte": 735.88, "modalidade": "Ampla"},
    {"curso": "Direito", "universidade": "UnB", "uf": "DF", "nota_corte": 752.61, "modalidade": "Ampla"},
    {"curso": "Direito", "universidade": "UFSC", "uf": "SC", "nota_corte": 721.45, "modalidade": "Ampla"},
    {"curso": "Direito", "universidade": "UFC", "uf": "CE", "nota_corte": 703.12, "modalidade": "Ampla"},
    {"curso": "Direito", "universidade": "UFPE", "uf": "PE", "nota_corte": 698.74, "modalidade": "Ampla"},
    {"curso": "Direito", "universidade": "UFBA", "uf": "BA", "nota_corte": 692.33, "modalidade": "Ampla"},
    # ── Engenharia ────────────────────────────────────────────────────────────
    {"curso": "Eng. de Computação", "universidade": "UFMG", "uf": "MG", "nota_corte": 728.44, "modalidade": "Ampla"},
    {"curso": "Eng. de Computação", "universidade": "UFRGS", "uf": "RS", "nota_corte": 715.22, "modalidade": "Ampla"},
    {"curso": "Eng. de Computação", "universidade": "UnB", "uf": "DF", "nota_corte": 721.38, "modalidade": "Ampla"},
    {"curso": "Eng. Elétrica", "universidade": "UFMG", "uf": "MG", "nota_corte": 714.56, "modalidade": "Ampla"},
    {"curso": "Eng. Elétrica", "universidade": "UFRGS", "uf": "RS", "nota_corte": 708.91, "modalidade": "Ampla"},
    {"curso": "Eng. Elétrica", "universidade": "UFPR", "uf": "PR", "nota_corte": 698.34, "modalidade": "Ampla"},
    {"curso": "Eng. Civil", "universidade": "UFMG", "uf": "MG", "nota_corte": 705.12, "modalidade": "Ampla"},
    {"curso": "Eng. Civil", "universidade": "UFRGS", "uf": "RS", "nota_corte": 698.45, "modalidade": "Ampla"},
    {"curso": "Eng. Civil", "universidade": "UFSC", "uf": "SC", "nota_corte": 689.77, "modalidade": "Ampla"},
    {"curso": "Eng. Mecânica", "universidade": "UFMG", "uf": "MG", "nota_corte": 695.33, "modalidade": "Ampla"},
    {"curso": "Eng. Mecânica", "universidade": "UFRGS", "uf": "RS", "nota_corte": 687.12, "modalidade": "Ampla"},
    # ── Ciência da Computação ─────────────────────────────────────────────────
    {"curso": "Ciência da Computação", "universidade": "UnB", "uf": "DF", "nota_corte": 712.44, "modalidade": "Ampla"},
    {"curso": "Ciência da Computação", "universidade": "UFMG", "uf": "MG", "nota_corte": 706.81, "modalidade": "Ampla"},
    {"curso": "Ciência da Computação", "universidade": "UFRGS", "uf": "RS", "nota_corte": 698.55, "modalidade": "Ampla"},
    {"curso": "Ciência da Computação", "universidade": "UFSC", "uf": "SC", "nota_corte": 691.23, "modalidade": "Ampla"},
    {"curso": "Ciência da Computação", "universidade": "UFC", "uf": "CE", "nota_corte": 676.44, "modalidade": "Ampla"},
    {"curso": "Sistemas de Informação", "universidade": "UFBA", "uf": "BA", "nota_corte": 638.22, "modalidade": "Ampla"},
    {"curso": "Sistemas de Informação", "universidade": "UFPE", "uf": "PE", "nota_corte": 645.77, "modalidade": "Ampla"},
    # ── Administração ─────────────────────────────────────────────────────────
    {"curso": "Administração", "universidade": "UnB", "uf": "DF", "nota_corte": 678.91, "modalidade": "Ampla"},
    {"curso": "Administração", "universidade": "UFRGS", "uf": "RS", "nota_corte": 662.34, "modalidade": "Ampla"},
    {"curso": "Administração", "universidade": "UFMG", "uf": "MG", "nota_corte": 655.12, "modalidade": "Ampla"},
    {"curso": "Administração", "universidade": "UFC", "uf": "CE", "nota_corte": 631.44, "modalidade": "Ampla"},
    {"curso": "Administração", "universidade": "UFBA", "uf": "BA", "nota_corte": 624.88, "modalidade": "Ampla"},
    # ── Economia ─────────────────────────────────────────────────────────────
    {"curso": "Ciências Econômicas", "universidade": "UnB", "uf": "DF", "nota_corte": 698.44, "modalidade": "Ampla"},
    {"curso": "Ciências Econômicas", "universidade": "UFRGS", "uf": "RS", "nota_corte": 679.12, "modalidade": "Ampla"},
    {"curso": "Ciências Econômicas", "universidade": "UFMG", "uf": "MG", "nota_corte": 671.55, "modalidade": "Ampla"},
    {"curso": "Ciências Econômicas", "universidade": "UFPE", "uf": "PE", "nota_corte": 641.33, "modalidade": "Ampla"},
    # ── Psicologia ───────────────────────────────────────────────────────────
    {"curso": "Psicologia", "universidade": "UFMG", "uf": "MG", "nota_corte": 714.22, "modalidade": "Ampla"},
    {"curso": "Psicologia", "universidade": "UFRGS", "uf": "RS", "nota_corte": 705.88, "modalidade": "Ampla"},
    {"curso": "Psicologia", "universidade": "UnB", "uf": "DF", "nota_corte": 721.11, "modalidade": "Ampla"},
    {"curso": "Psicologia", "universidade": "UFC", "uf": "CE", "nota_corte": 678.44, "modalidade": "Ampla"},
    {"curso": "Psicologia", "universidade": "UFBA", "uf": "BA", "nota_corte": 665.33, "modalidade": "Ampla"},
    # ── Pedagogia / Licenciaturas ────────────────────────────────────────────
    {"curso": "Pedagogia", "universidade": "UFRGS", "uf": "RS", "nota_corte": 558.22, "modalidade": "Ampla"},
    {"curso": "Pedagogia", "universidade": "UFBA", "uf": "BA", "nota_corte": 511.44, "modalidade": "Ampla"},
    {"curso": "Pedagogia", "universidade": "UFC", "uf": "CE", "nota_corte": 524.77, "modalidade": "Ampla"},
    {"curso": "Licenciatura em Matemática", "universidade": "UFPA", "uf": "PA", "nota_corte": 498.33, "modalidade": "Ampla"},
    {"curso": "Licenciatura em Letras", "universidade": "UFAM", "uf": "AM", "nota_corte": 482.11, "modalidade": "Ampla"},
    # ── Arquitetura ──────────────────────────────────────────────────────────
    {"curso": "Arquitetura e Urbanismo", "universidade": "UnB", "uf": "DF", "nota_corte": 741.88, "modalidade": "Ampla"},
    {"curso": "Arquitetura e Urbanismo", "universidade": "UFRGS", "uf": "RS", "nota_corte": 728.44, "modalidade": "Ampla"},
    {"curso": "Arquitetura e Urbanismo", "universidade": "UFBA", "uf": "BA", "nota_corte": 691.22, "modalidade": "Ampla"},
    # ── Nutrição / Saúde ─────────────────────────────────────────────────────
    {"curso": "Nutrição", "universidade": "UFBA", "uf": "BA", "nota_corte": 631.44, "modalidade": "Ampla"},
    {"curso": "Enfermagem", "universidade": "UFBA", "uf": "BA", "nota_corte": 618.88, "modalidade": "Ampla"},
    {"curso": "Enfermagem", "universidade": "UFMG", "uf": "MG", "nota_corte": 638.22, "modalidade": "Ampla"},
    {"curso": "Farmácia", "universidade": "UFMG", "uf": "MG", "nota_corte": 695.11, "modalidade": "Ampla"},
    {"curso": "Odontologia", "universidade": "UFMG", "uf": "MG", "nota_corte": 748.33, "modalidade": "Ampla"},
    {"curso": "Odontologia", "universidade": "UFRGS", "uf": "RS", "nota_corte": 738.77, "modalidade": "Ampla"},
    # ── Cursos de acesso mais amplo ───────────────────────────────────────────
    {"curso": "Agronomia", "universidade": "UFLA", "uf": "MG", "nota_corte": 584.22, "modalidade": "Ampla"},
    {"curso": "Agronomia", "universidade": "UFV", "uf": "MG", "nota_corte": 601.44, "modalidade": "Ampla"},
    {"curso": "Jornalismo", "universidade": "UnB", "uf": "DF", "nota_corte": 671.55, "modalidade": "Ampla"},
    {"curso": "Jornalismo", "universidade": "UFRGS", "uf": "RS", "nota_corte": 651.22, "modalidade": "Ampla"},
    {"curso": "Serviço Social", "universidade": "UFBA", "uf": "BA", "nota_corte": 498.77, "modalidade": "Ampla"},
    {"curso": "Serviço Social", "universidade": "UFPE", "uf": "PE", "nota_corte": 511.33, "modalidade": "Ampla"},
]


def get_dataframe() -> pd.DataFrame:
    return pd.DataFrame(COURSES).sort_values("nota_corte", ascending=False).reset_index(drop=True)


def find_eligible(score: float, margin: float = 30.0) -> pd.DataFrame:
    df = get_dataframe()
    eligible = df[df["nota_corte"] <= score + margin].copy()
    eligible["situacao"] = eligible["nota_corte"].apply(
        lambda c: "✅ Aprovado" if c <= score else "⚠️ Margem"
    )
    eligible["diferenca"] = (score - eligible["nota_corte"]).round(2)
    return eligible.sort_values("nota_corte", ascending=False)


def unique_courses() -> list[str]:
    return sorted(get_dataframe()["curso"].unique().tolist())
