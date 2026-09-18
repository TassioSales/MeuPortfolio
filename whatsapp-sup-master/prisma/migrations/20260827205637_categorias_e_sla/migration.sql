-- A view de leitura precisa SAIR ANTES e VOLTAR DEPOIS.
--
-- Não é zelo: sem isto esta migração falha no meio, e foi o que aconteceu na
-- primeira tentativa. Trocar o tipo de uma coluna no SQLite significa criar a
-- tabela nova, copiar, DROPAR A ANTIGA e renomear - e o `DROP TABLE "Chamado"`
-- estoura com `error in view chamados_para_cards: no such table: main.Chamado`
-- porque a view passa a apontar para uma tabela que deixou de existir. A
-- migração para no meio, o banco fica com `new_Chamado` e sem `Chamado`, e o
-- deploy morre com o serviço fora do ar.
--
-- A definição recriada no fim deste arquivo tem de ser a MESMA de
-- `sql/view_chamados_para_cards.sql` (que `npm run db:view` aplica). As duas
-- cópias existem porque a migração precisa ser auto-suficiente - ela roda em
-- banco de produção sem ninguém por perto para rodar o script depois.
DROP VIEW IF EXISTS "chamados_para_cards";

-- CreateTable
CREATE TABLE "Categoria" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "codigo" TEXT NOT NULL,
    "nome" TEXT NOT NULL,
    "rotulo" TEXT NOT NULL,
    "ordem" INTEGER NOT NULL,
    "ativa" BOOLEAN NOT NULL DEFAULT true,
    "paiId" INTEGER,
    "criadoEm" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "atualizadoEm" DATETIME NOT NULL,
    CONSTRAINT "Categoria_paiId_fkey" FOREIGN KEY ("paiId") REFERENCES "Categoria" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);

-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_Chamado" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "nome" TEXT NOT NULL,
    "telefone" TEXT,
    "origem" TEXT NOT NULL DEFAULT 'whatsapp',
    "categoriaId" INTEGER,
    "dataAbertura" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "primeiroAtendimentoEm" DATETIME,
    "resolvidoEm" DATETIME,
    "resumo" TEXT NOT NULL,
    "descricao" TEXT NOT NULL,
    "situacao" TEXT NOT NULL DEFAULT 'aberto',
    "atualizadoEm" DATETIME NOT NULL,
    CONSTRAINT "Chamado_categoriaId_fkey" FOREIGN KEY ("categoriaId") REFERENCES "Categoria" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);
INSERT INTO "new_Chamado" ("atualizadoEm", "dataAbertura", "descricao", "id", "nome", "origem", "resumo", "situacao", "telefone") SELECT "atualizadoEm", "dataAbertura", "descricao", "id", "nome", "origem", "resumo", "situacao", "telefone" FROM "Chamado";
DROP TABLE "Chamado";
ALTER TABLE "new_Chamado" RENAME TO "Chamado";
CREATE INDEX "Chamado_situacao_idx" ON "Chamado"("situacao");
CREATE INDEX "Chamado_telefone_idx" ON "Chamado"("telefone");
CREATE INDEX "Chamado_dataAbertura_idx" ON "Chamado"("dataAbertura");
CREATE INDEX "Chamado_categoriaId_idx" ON "Chamado"("categoriaId");
CREATE INDEX "Chamado_resolvidoEm_idx" ON "Chamado"("resolvidoEm");
CREATE TABLE "new_SessaoConversa" (
    "telefone" TEXT NOT NULL PRIMARY KEY,
    "etapa" TEXT NOT NULL DEFAULT 'categoria',
    "editando" BOOLEAN NOT NULL DEFAULT false,
    "categoriaId" INTEGER,
    "nome" TEXT,
    "resumo" TEXT,
    "descricao" TEXT,
    "criadoEm" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "atualizadoEm" DATETIME NOT NULL,
    CONSTRAINT "SessaoConversa_categoriaId_fkey" FOREIGN KEY ("categoriaId") REFERENCES "Categoria" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);
INSERT INTO "new_SessaoConversa" ("atualizadoEm", "criadoEm", "descricao", "editando", "etapa", "nome", "resumo", "telefone") SELECT "atualizadoEm", "criadoEm", "descricao", "editando", "etapa", "nome", "resumo", "telefone" FROM "SessaoConversa";
DROP TABLE "SessaoConversa";
ALTER TABLE "new_SessaoConversa" RENAME TO "SessaoConversa";
CREATE INDEX "SessaoConversa_atualizadoEm_idx" ON "SessaoConversa"("atualizadoEm");
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;

-- CreateIndex
CREATE UNIQUE INDEX "Categoria_codigo_key" ON "Categoria"("codigo");

-- CreateIndex
CREATE INDEX "Categoria_ativa_ordem_idx" ON "Categoria"("ativa", "ordem");

-- CreateIndex
CREATE INDEX "Categoria_paiId_idx" ON "Categoria"("paiId");

-- ---------------------------------------------------------------------------
-- Carga inicial das categorias
-- ---------------------------------------------------------------------------
-- As seis vieram dos grupos de atendimento da empresa (a tela "Grupos de chat").
-- Ficam AQUI, e não num script de seed à parte, por um motivo operacional: sem
-- categoria ativa o menu da conversa não tem o que oferecer e o bot pula direto
-- para o nome. Um seed opcional transformaria "alguém esqueceu de rodar" numa
-- mudança silenciosa de comportamento; dentro da migração, subir o banco já
-- deixa o menu de pé.
--
-- Migração roda UMA VEZ: renomear, reordenar ou desativar qualquer uma delas no
-- painel depois disto não é desfeito por deploy nenhum.
--
-- `ordem` é a posição no menu (a mesma ordem alfabética da tela de origem), e
-- NÃO o número que o usuário digita: o número é calculado sobre as ATIVAS na
-- hora de montar o menu, para desativar uma categoria não deixar buraco na
-- numeração. Todas nascem na raiz (`paiId` nulo); a árvore é montada no painel.
--
-- A data vai no formato ISO com deslocamento explícito
-- (`2026-08-27T20:00:00.000+00:00`), que é exatamente o que o Prisma grava. O
-- `CURRENT_TIMESTAMP` do SQLite gravaria `2026-08-27 20:00:00` (espaço, sem
-- milissegundo, sem fuso) - outro formato para a mesma coluna, que é a armadilha
-- descrita no comentário do model Mensagem.
INSERT INTO "Categoria" ("codigo", "nome", "rotulo", "ordem", "ativa", "paiId", "criadoEm", "atualizadoEm")
SELECT
  v."codigo", v."nome", v."rotulo", v."ordem", true, NULL,
  strftime('%Y-%m-%dT%H:%M:%f', 'now') || '+00:00',
  strftime('%Y-%m-%dT%H:%M:%f', 'now') || '+00:00'
FROM (
  SELECT 'cadastro_ifood'               AS "codigo", 'CADASTRO NO IFOOD'                       AS "nome", 'CADASTRO NO IFOOD'        AS "rotulo", 1 AS "ordem"
  UNION ALL SELECT 'demanda_interna_franqueadora', 'DEMANDA INTERNA FRANQUEADORA',            'SUPORTE A FRANQUEADORA',  2
  UNION ALL SELECT 'mudanca_cnpj',                 'MUDANÇA DE CNPJ',                          'MUDANÇA DE CNPJ',         3
  UNION ALL SELECT 'sistema_vetor',                'PROBLEMAS RELACIONADOS AO SISTEMA VETOR', 'SUPORTE AO SISTEMA VETOR',4
  UNION ALL SELECT 'suporte_franqueado',           'SUPORTE TÉCNICO AO FRANQUEADO',            'SUPORTE AO FRANQUEADO',   5
  UNION ALL SELECT 'suporte_loja_propria',         'SUPORTE TÉCNICO LOJA PRÓPRIA',             'SUPORTE LOJA PRÓPRIA',    6
) AS v
-- Idempotente de propósito: se este banco já tiver uma categoria com o mesmo
-- código (restaurado de um dump mais novo, por exemplo), o índice único faria a
-- migração inteira falhar e o deploy parar.
WHERE NOT EXISTS (SELECT 1 FROM "Categoria" c WHERE c."codigo" = v."codigo");

-- ---------------------------------------------------------------------------
-- Backfill dos marcos de SLA
-- ---------------------------------------------------------------------------
-- Chamado que já existia nasceria com os dois marcos nulos e ficaria fora de
-- toda métrica para sempre - mesmo tendo sido atendido e resolvido. O histórico
-- de `MudancaSituacao` guarda exatamente esses dois instantes desde que existe,
-- então o que faltava era colocá-los na coluna.
--
-- Chamado anterior ao próprio histórico continua nulo, e é o certo: o instante
-- não foi registrado em lugar nenhum, e inventar um a partir de `atualizadoEm`
-- produziria métrica plausível e falsa.
UPDATE "Chamado"
SET "primeiroAtendimentoEm" = (
  SELECT MIN(m."criadoEm") FROM "MudancaSituacao" m
  WHERE m."chamadoId" = "Chamado"."id" AND m."de" = 'aberto' AND m."para" <> 'aberto'
)
WHERE "primeiroAtendimentoEm" IS NULL;

-- MAX e não MIN: um chamado que foi resolvido, reaberto e resolvido de novo tem
-- como tempo de resolução o da última vez - a primeira resolução foi desfeita.
-- E só para quem está resolvido AGORA, pela mesma razão.
UPDATE "Chamado"
SET "resolvidoEm" = (
  SELECT MAX(m."criadoEm") FROM "MudancaSituacao" m
  WHERE m."chamadoId" = "Chamado"."id" AND m."para" = 'resolvido'
)
WHERE "situacao" = 'resolvido' AND "resolvidoEm" IS NULL;

-- ---------------------------------------------------------------------------
-- Volta a view, agora com as colunas novas
-- ---------------------------------------------------------------------------
-- `categoriaId` e não o nome da categoria: a view é contrato de leitura, e
-- juntar com `Categoria` aqui congelaria o rótulo de exibição (que é editável no
-- painel) dentro dela. Quem consome junta com `Categoria` se quiser o texto.
--
-- `telefone` continua de fora, pela mesma minimização de sempre.
CREATE VIEW chamados_para_cards AS
SELECT
  id,
  nome,
  "dataAbertura",
  "primeiroAtendimentoEm",
  "resolvidoEm",
  resumo,
  descricao,
  situacao,
  origem,
  "categoriaId"
FROM "Chamado"
ORDER BY "dataAbertura" DESC;
