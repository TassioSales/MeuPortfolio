-- CreateTable
CREATE TABLE "ConfiguracaoPainel" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "nome" TEXT NOT NULL DEFAULT 'Chamados',
    "sigla" TEXT NOT NULL DEFAULT 'CH',
    "periodoRotulo" TEXT NOT NULL DEFAULT '',
    "periodoTexto" TEXT NOT NULL DEFAULT '',
    "diasRestantes" INTEGER NOT NULL DEFAULT 0,
    "areas" TEXT NOT NULL DEFAULT '[]',
    "atualizadoEm" DATETIME NOT NULL
);
