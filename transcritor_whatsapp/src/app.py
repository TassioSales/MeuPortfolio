# -*- coding: utf-8 -*-
"""
Visualizador Streamlit das transcricoes.
Rode:  streamlit run src/app.py
"""
import os, re, json
import streamlit as st

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDAS = os.path.normpath(os.path.join(AQUI, "..", "dados", "saidas"))
CONVERSA = os.path.normpath(os.path.join(AQUI, "..", "dados", "conversa_whatsapp.txt"))
JSON_TRANSC = os.path.join(SAIDAS, "transcricoes.json")

RE_LINHA_AUDIO = re.compile(
    r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})\s*-\s*(.+?):\s*.*?((?:AUD|PTT)-\d+-WA\d+\.opus)"
)


@st.cache_data
def carregar():
    transc = json.load(open(JSON_TRANSC, encoding="utf-8")) if os.path.exists(JSON_TRANSC) else []
    remet = {}
    if os.path.exists(CONVERSA):
        for linha in open(CONVERSA, encoding="utf-8", errors="ignore"):
            m = RE_LINHA_AUDIO.search(linha)
            if m:
                d, h, quem, arq = m.groups()
                remet[arq] = (d, h, quem.strip())
    return transc, remet


st.set_page_config(page_title="Transcritor WhatsApp", page_icon="🎧", layout="wide")
st.title("🎧 Transcricoes de audios do WhatsApp")

transc, remet = carregar()
if not transc:
    st.warning("Nenhuma transcricao encontrada. Rode `python src/transcrever.py` antes.")
    st.stop()

# une metadados
for r in transc:
    d, h, quem = remet.get(r["file"], ("?", "?", "desconhecido"))
    r["data"], r["hora"], r["quem"] = d, h, quem

autores = sorted({r["quem"] for r in transc})
col1, col2 = st.columns([1, 2])
autor_sel = col1.selectbox("Remetente", ["(todos)"] + autores)
busca = col2.text_input("Buscar no texto", "")

filtrados = [
    r for r in transc
    if (autor_sel == "(todos)" or r["quem"] == autor_sel)
    and (not busca or busca.lower() in r["text"].lower())
]

st.caption(f"{len(filtrados)} de {len(transc)} audios")

for r in filtrados:
    texto = r["text"] or "*(sem fala detectada)*"
    if busca:
        texto = re.sub(f"({re.escape(busca)})", r"**\1**", texto, flags=re.I)
    with st.expander(f"[{r['data']} {r['hora']}] {r['quem']} — {r['file']} ({r['duration']}s)"):
        st.write(texto)
