-- CreateTable
CREATE TABLE "SessaoConversa" (
    "telefone" TEXT NOT NULL PRIMARY KEY,
    "etapa" TEXT NOT NULL DEFAULT 'nome',
    "editando" BOOLEAN NOT NULL DEFAULT false,
    "nome" TEXT,
    "resumo" TEXT,
    "descricao" TEXT,
    "criadoEm" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "atualizadoEm" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "Chamado" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "nome" TEXT NOT NULL,
    "telefone" TEXT,
    "origem" TEXT NOT NULL DEFAULT 'whatsapp',
    "dataAbertura" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "resumo" TEXT NOT NULL,
    "descricao" TEXT NOT NULL,
    "situacao" TEXT NOT NULL DEFAULT 'aberto',
    "atualizadoEm" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "Mensagem" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "chamadoId" INTEGER,
    "telefone" TEXT NOT NULL,
    "remetente" TEXT NOT NULL,
    "texto" TEXT NOT NULL,
    "whatsappMessageId" TEXT,
    "timestamp" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "payload" JSONB,
    "enviadaEm" DATETIME,
    "tentativas" INTEGER NOT NULL DEFAULT 0,
    "ultimaTentativaEm" DATETIME,
    CONSTRAINT "Mensagem_chamadoId_fkey" FOREIGN KEY ("chamadoId") REFERENCES "Chamado" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "MudancaSituacao" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "chamadoId" INTEGER NOT NULL,
    "de" TEXT NOT NULL,
    "para" TEXT NOT NULL,
    "autor" TEXT,
    "criadoEm" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "MudancaSituacao_chamadoId_fkey" FOREIGN KEY ("chamadoId") REFERENCES "Chamado" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateIndex
CREATE INDEX "SessaoConversa_atualizadoEm_idx" ON "SessaoConversa"("atualizadoEm");

-- CreateIndex
CREATE INDEX "Chamado_situacao_idx" ON "Chamado"("situacao");

-- CreateIndex
CREATE INDEX "Chamado_telefone_idx" ON "Chamado"("telefone");

-- CreateIndex
CREATE INDEX "Chamado_dataAbertura_idx" ON "Chamado"("dataAbertura");

-- CreateIndex
CREATE UNIQUE INDEX "Mensagem_whatsappMessageId_key" ON "Mensagem"("whatsappMessageId");

-- CreateIndex
CREATE INDEX "Mensagem_telefone_idx" ON "Mensagem"("telefone");

-- CreateIndex
CREATE INDEX "Mensagem_chamadoId_idx" ON "Mensagem"("chamadoId");

-- CreateIndex
CREATE INDEX "Mensagem_telefone_timestamp_idx" ON "Mensagem"("telefone", "timestamp");

-- CreateIndex
CREATE INDEX "Mensagem_remetente_enviadaEm_timestamp_idx" ON "Mensagem"("remetente", "enviadaEm", "timestamp");

-- CreateIndex
CREATE INDEX "MudancaSituacao_chamadoId_criadoEm_idx" ON "MudancaSituacao"("chamadoId", "criadoEm");
