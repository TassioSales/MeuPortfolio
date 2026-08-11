# -*- coding: utf-8 -*-
"""
Analisador das transcricoes.

1) Cruza cada audio (transcricoes.json) com o arquivo de texto exportado do
   WhatsApp para descobrir QUEM enviou o audio e QUANDO.
2) Sinaliza trechos com termos que podem indicar assedio moral / abuso
   (xingamento, ameaca, humilhacao, cobranca hostil, exigencia fora do horario).

Gera um relatorio em dados/saidas/relatorio_analise.txt

Uso:
    python analisar.py
    python analisar.py --autor "+55 61 9657-4839"   # foca num remetente
"""
import os, re, json, argparse
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDAS = os.path.normpath(os.path.join(AQUI, "..", "dados", "saidas"))
CONVERSA = os.path.normpath(os.path.join(AQUI, "..", "dados", "conversa_whatsapp.txt"))
JSON_TRANSC = os.path.join(SAIDAS, "transcricoes.json")

# Termos agrupados por categoria (regex, minusculo). \b = limite de palavra,
# evita falsos positivos (ex.: "vai se" NAO deve casar dentro de "vai ser").
CATEGORIAS = {
    "Xingamento/ofensa direta": r"\bidiota\b|\bburro\b|imbecil|\binutil\b|\binútil\b|"
                         r"incompeten|otari|otári|palhac|palhaç|ridicul|ridícul|\blixo\b|"
                         r"vagabund|\bbesta\b|jumento|arrombad|desgrac|desgraç|filho da p|"
                         r"vai se f|vai tomar|escrot|cuz[aã]o",
    "Culpabilizacao/desqualificacao": r"culpa (é|e|exclusivamente|especificamente) (sua|tua)|"
                         r"culpa (é|e) (exclusivamente|especificamente)|a culpa (é|e) sua|"
                         r"n[aã]o deu conta|n[aã]o deu certo por|voc[eê] n[aã]o fez|"
                         r"tu n[aã]o fez|falha (sua|tua)|erro (é|e) (seu|teu)|"
                         r"vai (dar|ficar) (ruim|mal)|vai ficar mal pra",
    "Ameaca/desligamento": r"demiss|demitir|manda(r)? embora|justa causa|"
                         r"n[aã]o consigo segurar|n[aã]o consigo te segurar|"
                         r"pessoa com disponibilidade|acho que j[aá] sabe o que|"
                         r"faz parte do processo|se tu n[aã]o (é|e) esse cara|"
                         r"a gente vai chegar",
    "Pressao/faltas/saude": r"\bfalta[s]?\b|essas duas falta|dando (a )?saída|"
                         r"quest[aã]o de saúde|disponibilidade|desando tudo|desanda tudo|"
                         r"n[aã]o d[aá] pra ficar dessa forma|tá foda|tá complicado segurar",
    "Cobranca hostil/pressao": r"larga tudo|é pra ontem|e pra ontem|n[aã]o quero saber|"
                         r"imediat|cai pra dentro|sume a bronca|corre atr[aá]s",
    "Fora do horario/folga": r"final de semana|fim de semana|\bdomingo\b|s[aá]bado|"
                         r"feriado|de madrugada|dia de folga|toca as demandas",
}

RE_LINHA_AUDIO = re.compile(
    r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})\s*-\s*(.+?):\s*.*?((?:AUD|PTT)-\d+-WA\d+\.opus)"
)


def carregar_remetentes():
    """filename -> (data, hora, remetente) a partir do .txt do WhatsApp."""
    mapa = {}
    if not os.path.exists(CONVERSA):
        return mapa
    for linha in open(CONVERSA, encoding="utf-8", errors="ignore"):
        m = RE_LINHA_AUDIO.search(linha)
        if m:
            data, hora, remetente, arq = m.groups()
            mapa[arq] = (data, hora, remetente.strip())
    return mapa


def encontrar_termos(texto):
    achados = []
    low = texto.lower()
    for cat, padrao in CATEGORIAS.items():
        for m in re.finditer(padrao, low):
            achados.append((cat, m.group(0)))
    return achados


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--autor", default=None,
                    help="Filtra por remetente (ex: '+55 61 9657-4839')")
    args = ap.parse_args()

    if not os.path.exists(JSON_TRANSC):
        raise SystemExit(f"Rode transcrever.py primeiro. Nao achei {JSON_TRANSC}")

    transc = json.load(open(JSON_TRANSC, encoding="utf-8"))
    remetentes = carregar_remetentes()

    linhas = []
    resumo_cat = defaultdict(int)
    resumo_autor = defaultdict(int)
    sinalizados = []

    for r in transc:
        arq = r["file"]
        data, hora, quem = remetentes.get(arq, ("?", "?", "desconhecido"))
        resumo_autor[quem] += 1
        if args.autor and args.autor.lower() not in quem.lower():
            continue
        achados = encontrar_termos(r.get("text", ""))
        if achados:
            for cat, _ in achados:
                resumo_cat[cat] += 1
            sinalizados.append((data, hora, quem, arq, achados, r["text"]))

    # monta relatorio
    out = []
    out.append("=" * 70)
    out.append("RELATORIO DE ANALISE DAS TRANSCRICOES")
    out.append("=" * 70)
    out.append(f"\nTotal de audios transcritos: {len(transc)}")
    out.append("\nAudios por remetente:")
    for quem, n in sorted(resumo_autor.items(), key=lambda x: -x[1]):
        out.append(f"  {n:4d}  {quem}")

    out.append("\n" + "-" * 70)
    out.append("TRECHOS SINALIZADOS (possiveis indicios) por categoria:")
    if resumo_cat:
        for cat, n in sorted(resumo_cat.items(), key=lambda x: -x[1]):
            out.append(f"  {n:4d}  {cat}")
    else:
        out.append("  Nenhum termo das listas foi encontrado.")

    out.append("\n" + "=" * 70)
    out.append(f"DETALHAMENTO ({len(sinalizados)} audios sinalizados)")
    out.append("=" * 70)
    for data, hora, quem, arq, achados, texto in sinalizados:
        cats = ", ".join(sorted({c for c, _ in achados}))
        termos = ", ".join(sorted({t for _, t in achados}))
        out.append(f"\n[{data} {hora}] {quem}  ({arq})")
        out.append(f"  categorias: {cats}")
        out.append(f"  termos: {termos}")
        out.append(f"  texto: {texto}")

    out.append("\n" + "=" * 70)
    out.append("AVISO: esta e uma triagem automatica por palavras-chave. NAO e prova")
    out.append("juridica nem laudo. Falsos positivos/negativos sao esperados. Leia o")
    out.append("texto completo no contexto antes de qualquer conclusao. Para uso legal,")
    out.append("procure orientacao de um(a) advogado(a) trabalhista.")
    out.append("=" * 70)

    relatorio = "\n".join(out)
    dest = os.path.join(SAIDAS, "relatorio_analise.txt")
    open(dest, "w", encoding="utf-8").write(relatorio)
    print(relatorio)
    print(f"\n>> Relatorio salvo em: {dest}")


if __name__ == "__main__":
    main()
