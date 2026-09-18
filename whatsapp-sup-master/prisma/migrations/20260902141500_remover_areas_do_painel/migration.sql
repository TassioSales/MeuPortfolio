-- Tira a coluna `areas` de ConfiguracaoPainel.
--
-- AREA e SETOR eram o mesmo conceito (TI, Financeiro, Operacoes...), e `Setor`
-- ja e tabela, com FK nos chamados e filtro no quadro. A secao "Areas" do
-- painel guardava rotulos livres que nao classificavam nada - duas taxonomias
-- para a mesma coisa divergem, e "esse chamado e da area ou do setor de TI?"
-- nao tem resposta boa.
--
-- Escrita a mao porque o `prisma migrate dev` recusa rodar sem terminal
-- interativo quando a coluna a remover tem valor: aqui o unico valor era o
-- `'[]'` do default, ou seja, lista vazia.
--
-- Reconstrucao da tabela em vez de `ALTER TABLE ... DROP COLUMN` pelo mesmo
-- motivo das outras migracoes deste projeto: e o que o Prisma gera para SQLite,
-- e mantem o arquivo consistente com o que ele espera encontrar depois.
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;

CREATE TABLE "new_ConfiguracaoPainel" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "nome" TEXT NOT NULL DEFAULT 'Chamados',
    "sigla" TEXT NOT NULL DEFAULT 'CH',
    "periodoRotulo" TEXT NOT NULL DEFAULT '',
    "periodoTexto" TEXT NOT NULL DEFAULT '',
    "diasRestantes" INTEGER NOT NULL DEFAULT 0,
    "atualizadoEm" DATETIME NOT NULL
);

INSERT INTO "new_ConfiguracaoPainel" ("id", "nome", "sigla", "periodoRotulo", "periodoTexto", "diasRestantes", "atualizadoEm")
SELECT "id", "nome", "sigla", "periodoRotulo", "periodoTexto", "diasRestantes", "atualizadoEm" FROM "ConfiguracaoPainel";

DROP TABLE "ConfiguracaoPainel";
ALTER TABLE "new_ConfiguracaoPainel" RENAME TO "ConfiguracaoPainel";

PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;
