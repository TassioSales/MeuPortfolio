"""
O compose entrega ao backend o que o `.env.example` promete.

Esta é a terceira vez que a mesma falha aparece no projeto, e as três foram
silenciosas: a variável existe no `.env`, o `Settings` a declara, e o
`docker-compose.yml` simplesmente não a repassa. O container então cai no
default do `config.py` — sem erro, sem aviso, com a configuração de quem
escreveu o código valendo em vez da de quem opera.

- `WEBHOOK_STATIC_TOKEN` faltando deixou o webhook **aberto** enquanto o log
  dizia "aceitando qualquer origem" e o `.env` dizia o contrário;
- as variáveis do parecer faltando fizeram o modelo do parecer ser o do
  atendimento;
- antes disso, uma chave ausente deixou o webhook em 503.

O contrato aqui é: **o que está documentado no `.env.example` e o `Settings`
conhece, o compose entrega.** Variável que o `Settings` não declara é de outro
serviço (Postgres, frontend) e não entra na conta.
"""

import re
from pathlib import Path

import pytest

from app.config import Settings

RAIZ = Path(__file__).resolve().parents[2]
COMPOSE = RAIZ / "docker-compose.yml"
ENV_EXEMPLO = RAIZ / ".env.example"


def _variaveis_do_env_exemplo() -> set:
    texto = ENV_EXEMPLO.read_text(encoding="utf-8", errors="replace")
    return {
        linha.split("=", 1)[0].strip()
        for linha in texto.splitlines()
        if "=" in linha and not linha.strip().startswith("#")
    }


def _ambiente_do_backend() -> set:
    """Os nomes de variável no bloco `environment:` do serviço `backend`."""
    texto = COMPOSE.read_text(encoding="utf-8", errors="replace")

    # Do "backend:" até o próximo serviço na mesma indentação.
    bloco = re.search(r"\n  backend:\n(.*?)(?=\n  \w+:\n)", texto, re.S)
    assert bloco, "não achei o serviço `backend` no docker-compose.yml"

    ambiente = re.search(r"\n    environment:\n(.*?)(?=\n    \w+:)", bloco.group(1), re.S)
    assert ambiente, "o serviço `backend` não tem bloco `environment`"

    return set(re.findall(r"^\s{6}([A-Z0-9_]+):", ambiente.group(1), re.M))


def _campos_do_settings() -> set:
    return {nome.upper() for nome in Settings.model_fields}


# Variáveis que o `Settings` declara e que **não** precisam ir ao container.
#
# Cada exceção carrega o motivo: se alguém acrescentar uma sem justificar, a
# próxima pessoa não tem como saber se é decisão ou esquecimento — que é
# exatamente como esta falha nasceu.
EXCECOES = {
    "API_PORT": (
        "é o mapeamento de porta do host (`${API_PORT:-8000}:8000`); dentro do "
        "container o uvicorn escuta sempre na 8000, e `settings.api_port` só é "
        "lido no bloco `__main__`, que o Docker não usa"
    ),
}


def test_o_compose_entrega_o_que_o_env_exemplo_promete():
    documentadas = _variaveis_do_env_exemplo() & _campos_do_settings()
    entregues = _ambiente_do_backend() | set(EXCECOES)

    faltando = sorted(documentadas - entregues)

    assert not faltando, (
        "variáveis documentadas no .env.example que o compose não repassa ao "
        f"backend: {faltando}.\n"
        "O container vai cair no default do config.py — sem erro e sem aviso."
    )


def test_o_compose_nao_repassa_variavel_que_o_settings_ignora():
    """
    O caminho inverso, e ele também já mordeu: o pydantic-settings recusa
    variável que não conhece, e o backend **não sobe**. Dez variáveis do
    `.env.example` faziam isso — hoje o `Settings` usa `extra="ignore"`, mas
    passar o que ninguém lê continua sendo ruído que engana quem for
    configurar.
    """
    desconhecidas = sorted(_ambiente_do_backend() - _campos_do_settings())

    assert not desconhecidas, (
        f"o compose passa ao backend variáveis que o Settings não declara: "
        f"{desconhecidas}"
    )


def test_a_excecao_precisa_aparecer_em_algum_lugar_do_compose():
    """
    Exceção quer dizer "vai por outro caminho", não "não existe". Se a
    variável não aparece nem no `environment` nem em nenhum outro lugar do
    compose, ela é documentação morta.
    """
    texto = COMPOSE.read_text(encoding="utf-8", errors="replace")

    orfas = sorted(nome for nome in EXCECOES if f"${{{nome}" not in texto)

    assert not orfas, (
        f"variáveis na lista de exceção que o compose nem menciona: {orfas}"
    )
