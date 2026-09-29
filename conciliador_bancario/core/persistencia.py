"""Guarda o que um humano decidiu, para a próxima execução não perguntar de novo.

O aprendizado aqui é deliberadamente burro: nenhum modelo, nenhum treino. Quando alguém aceita um
casamento cujo histórico não trazia o nome do cliente, guarda-se o par histórico→sacado e ele vira
regra. É o que resolve o caso mais chato da conciliação — o banco que manda "CRED TEF 0002" e
espera que você adivinhe de quem é.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from core.modelos import Conciliacao
from core.normalizacao import normalizar, similaridade_nome

ESQUEMA = """
CREATE TABLE IF NOT EXISTS decisao (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    lancamentos   TEXT    NOT NULL,
    titulos       TEXT    NOT NULL,
    estrategia    TEXT    NOT NULL,
    aceita        INTEGER NOT NULL,
    registrada_em TEXT    NOT NULL
);
CREATE TABLE IF NOT EXISTS apelido (
    historico  TEXT PRIMARY KEY,
    sacado     TEXT NOT NULL,
    vezes      INTEGER NOT NULL DEFAULT 1,
    atualizado TEXT NOT NULL
);
"""


class Repositorio:
    def __init__(self, caminho: str | Path = "conciliacao.db") -> None:
        self.caminho = str(caminho)
        with closing(self._conectar()) as conexao:
            conexao.executescript(ESQUEMA)
            conexao.commit()

    def _conectar(self) -> sqlite3.Connection:
        conexao = sqlite3.connect(self.caminho)
        conexao.row_factory = sqlite3.Row
        return conexao

    def registrar(self, conciliacao: Conciliacao, aceita: bool, historico: str = "", sacado: str = "") -> None:
        """Grava a decisão e, se couber, aprende o apelido.

        O apelido só é gravado quando o nome do sacado **não** aparecia no histórico: se aparecia,
        a próxima execução casa sozinha pela similaridade e a regra seria peso morto.
        """
        agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with closing(self._conectar()) as conexao:
            conexao.execute(
                "INSERT INTO decisao (lancamentos, titulos, estrategia, aceita, registrada_em)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    ",".join(conciliacao.lancamentos),
                    ",".join(conciliacao.titulos),
                    conciliacao.estrategia.value,
                    int(aceita),
                    agora,
                ),
            )
            if aceita and historico and sacado and similaridade_nome(historico, sacado) == 0.0:
                conexao.execute(
                    "INSERT INTO apelido (historico, sacado, vezes, atualizado) VALUES (?, ?, 1, ?)"
                    " ON CONFLICT(historico) DO UPDATE SET"
                    " sacado = excluded.sacado, vezes = apelido.vezes + 1, atualizado = excluded.atualizado",
                    (normalizar(historico), normalizar(sacado), agora),
                )
            conexao.commit()

    def apelidos(self) -> dict[str, str]:
        with closing(self._conectar()) as conexao:
            return {linha["historico"]: linha["sacado"] for linha in conexao.execute("SELECT historico, sacado FROM apelido")}

    def esquecer(self, historico: str) -> bool:
        """Remove um apelido aprendido errado. Sem isso, um engano vira permanente."""
        with closing(self._conectar()) as conexao:
            cursor = conexao.execute("DELETE FROM apelido WHERE historico = ?", (normalizar(historico),))
            conexao.commit()
            return cursor.rowcount > 0

    def historico_de_decisoes(self, limite: int = 100) -> list[dict[str, object]]:
        with closing(self._conectar()) as conexao:
            return [
                dict(linha)
                for linha in conexao.execute(
                    "SELECT * FROM decisao ORDER BY id DESC LIMIT ?", (limite,)
                )
            ]
