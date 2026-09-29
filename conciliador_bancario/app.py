"""Interface da conciliação bancária."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.importacao import CsvInvalido, ler_titulos_csv
from core.matching import conciliar
from core.modelos import Situacao
from core.ofx import OfxInvalido, ler_ofx
from core.persistencia import Repositorio
from core.regras import Regras
from core.relatorio import para_tabela, pendencias, resumir
from dados_exemplo.gerar import gerar, para_csv, para_ofx

st.set_page_config(page_title="Conciliação Bancária", page_icon="◫", layout="wide")


@st.cache_resource
def repositorio() -> Repositorio:
    return Repositorio(Path(__file__).parent / "conciliacao.db")


def moeda(valor: Decimal | float) -> str:
    return f"R$ {float(valor):,.2f}".replace(",", "~").replace(".", ",").replace("~", ".")


st.title("Conciliação bancária")
st.caption(
    "Cruza o extrato do banco com o contas a receber e explica cada casamento. "
    "O que não tiver evidência suficiente fica para revisão, em vez de ser adivinhado."
)

with st.sidebar:
    st.header("Regras")
    janela = st.slider("Janela de data (dias)", 0, 15, 5, help="Boleto cai em D+1, PIX de sexta aparece na segunda.")
    tolerancia_centavos = st.number_input("Tolerância em centavos", 0, 100, 2)
    tolerancia_percentual = st.slider("Tolerância percentual", 0.0, 5.0, 1.0, 0.1, format="%.1f%%")
    max_combinados = st.slider("Máximo de títulos por depósito", 2, 6, 4)
    min_nome = st.slider("Similaridade mínima de nome", 0.0, 1.0, 0.5, 0.05)

    regras = Regras(
        janela_dias=janela,
        tolerancia_centavos=int(tolerancia_centavos),
        tolerancia_percentual=Decimal(str(tolerancia_percentual / 100)),
        max_titulos_combinados=max_combinados,
        min_similaridade_nome=min_nome,
    )

    st.divider()
    aprendidos = repositorio().apelidos()
    st.metric("Apelidos aprendidos", len(aprendidos))
    if aprendidos:
        with st.expander("Ver e remover"):
            for historico, sacado in sorted(aprendidos.items()):
                coluna_texto, coluna_botao = st.columns([4, 1])
                coluna_texto.write(f"`{historico}` → **{sacado}**")
                if coluna_botao.button("✕", key=f"del-{historico}", help="Esquecer"):
                    repositorio().esquecer(historico)
                    st.rerun()

aba_conciliar, aba_exemplo = st.tabs(["Conciliar", "Dados de exemplo"])

with aba_exemplo:
    st.write(
        "Gera um extrato e um contas a receber sintéticos com os casos que dão trabalho no "
        "fechamento: tarifa descontada, um depósito quitando vários boletos, pagamento dividido, "
        "histórico sem o nome do cliente e créditos que não são pagamento de título."
    )
    quantidade = st.number_input("Quantidade de títulos", 20, 1000, 200, step=20)
    semente = st.number_input("Semente", 0, 9999, 42)
    if st.button("Gerar arquivos"):
        cenario = gerar(int(quantidade), int(semente))
        coluna_ofx, coluna_csv = st.columns(2)
        coluna_ofx.download_button("Baixar extrato.ofx", para_ofx(cenario.lancamentos), "extrato.ofx")
        coluna_csv.download_button("Baixar titulos.csv", para_csv(cenario.titulos), "titulos.csv")
        st.success(f"{len(cenario.lancamentos)} lançamentos e {len(cenario.titulos)} títulos gerados.")

with aba_conciliar:
    coluna_extrato, coluna_titulos = st.columns(2)
    arquivo_ofx = coluna_extrato.file_uploader("Extrato do banco (.ofx)", type=["ofx", "txt"])
    arquivo_csv = coluna_titulos.file_uploader("Contas a receber (.csv)", type=["csv"])

    if not (arquivo_ofx and arquivo_csv):
        st.info("Envie os dois arquivos. Não tem os seus? A aba ao lado gera um par de exemplo.")
        st.stop()

    try:
        lancamentos = ler_ofx(arquivo_ofx.getvalue().decode("utf-8", errors="replace"))
    except OfxInvalido as erro:
        st.error(f"Extrato: {erro}")
        st.stop()

    try:
        titulos = ler_titulos_csv(arquivo_csv.getvalue().decode("utf-8", errors="replace"))
    except CsvInvalido as erro:
        st.error(f"Contas a receber: {erro}")
        st.stop()

    resultado = conciliar(lancamentos, titulos, regras, repositorio().apelidos())
    resumo = resumir(resultado, lancamentos, titulos)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Conciliados", resumo.conciliados, f"{resumo.cobertura:.0%} do extrato")
    c2.metric("Divergentes", resumo.divergentes, moeda(resumo.diferenca_total) if resumo.divergentes else None)
    c3.metric("Para revisão", resumo.lancamentos_sem_par)
    c4.metric("Em aberto", moeda(resumo.valor_em_aberto), f"{resumo.titulos_sem_par} títulos")

    st.subheader("Casamentos")
    tabela = para_tabela(resultado, lancamentos, titulos)
    st.dataframe(tabela, use_container_width=True, hide_index=True)
    st.download_button("Exportar CSV", tabela.write_csv(), "conciliacao.csv", type="primary")

    if resultado.lancamentos_sem_par:
        st.subheader("Pendentes de revisão")
        st.caption("Ordenados por valor: o que mais pesa no fechamento aparece primeiro.")
        st.dataframe(pendencias(resultado, lancamentos, titulos), use_container_width=True, hide_index=True)

        st.subheader("Ensinar a ferramenta")
        st.caption(
            "Quando o histórico do banco não traz o nome do cliente, diga de quem é uma vez. "
            "A associação fica gravada e vale para as próximas conciliações."
        )
        por_id = {l.id: l for l in lancamentos}
        escolhido = st.selectbox(
            "Lançamento", resultado.lancamentos_sem_par,
            format_func=lambda i: f"{i} · {moeda(por_id[i].valor)} · {por_id[i].descricao[:60]}",
        )
        sacados = sorted({t.sacado for t in titulos})
        sacado = st.selectbox("É pagamento de qual cliente?", sacados)
        if st.button("Gravar associação"):
            from core.modelos import Conciliacao, Estrategia

            repositorio().registrar(
                Conciliacao((escolhido,), (titulos[0].id,), Estrategia.APELIDO, 1.0, Situacao.CONCILIADO, Decimal("0"), "manual"),
                aceita=True,
                historico=por_id[escolhido].descricao,
                sacado=sacado,
            )
            st.success(f"Gravado: esse histórico passa a apontar para {sacado}.")
            st.rerun()
