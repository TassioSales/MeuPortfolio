-- Classificacao e separacao de chamados: setores, prioridade, prazo, tipo
-- (interno x franquia), canal, avaliacao, tags, anexos, comentarios e
-- dependencia entre chamados.
--
-- A view de leitura precisa SAIR ANTES e VOLTAR DEPOIS.
--
-- Nao e zelo, e o que faz esta migracao terminar: acrescentar coluna no SQLite
-- significa criar a tabela nova, copiar, DROPAR A ANTIGA e renomear - e o
-- `DROP TABLE "Chamado"` estoura com `error in view chamados_para_cards: no such
-- table: main.Chamado` enquanto a view aponta para ela. Ja aconteceu na migracao
-- `20260827205637_categorias_e_sla`, que carrega o mesmo par DROP/CREATE pela
-- mesma razao.
--
-- A definicao recriada no fim deste arquivo tem de ser a MESMA de
-- `sql/view_chamados_para_cards.sql` (que `npm run db:view` aplica). As duas
-- copias existem porque a migracao precisa ser auto-suficiente: ela roda em
-- banco de producao sem ninguem por perto para rodar o script depois.
DROP VIEW IF EXISTS "chamados_para_cards";

-- CreateTable
CREATE TABLE "Setor" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "codigo" TEXT NOT NULL,
    "nome" TEXT NOT NULL,
    "ordem" INTEGER NOT NULL,
    "ativo" BOOLEAN NOT NULL DEFAULT true,
    "criadoEm" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "atualizadoEm" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "Comentario" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "chamadoId" INTEGER NOT NULL,
    "autor" TEXT,
    "texto" TEXT NOT NULL,
    "criadoEm" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "Comentario_chamadoId_fkey" FOREIGN KEY ("chamadoId") REFERENCES "Chamado" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Anexo" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "chamadoId" INTEGER NOT NULL,
    "nome" TEXT NOT NULL,
    "mime" TEXT NOT NULL,
    "bytes" INTEGER NOT NULL,
    "conteudo" BLOB NOT NULL,
    "enviadoPor" TEXT,
    "criadoEm" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "Anexo_chamadoId_fkey" FOREIGN KEY ("chamadoId") REFERENCES "Chamado" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Tag" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "nome" TEXT NOT NULL,
    "criadoEm" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "Dependencia" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "bloqueadoId" INTEGER NOT NULL,
    "bloqueadorId" INTEGER NOT NULL,
    "criadoEm" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "Dependencia_bloqueadoId_fkey" FOREIGN KEY ("bloqueadoId") REFERENCES "Chamado" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "Dependencia_bloqueadorId_fkey" FOREIGN KEY ("bloqueadorId") REFERENCES "Chamado" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "_ChamadoToTag" (
    "A" INTEGER NOT NULL,
    "B" INTEGER NOT NULL,
    CONSTRAINT "_ChamadoToTag_A_fkey" FOREIGN KEY ("A") REFERENCES "Chamado" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "_ChamadoToTag_B_fkey" FOREIGN KEY ("B") REFERENCES "Tag" ("id") ON DELETE CASCADE ON UPDATE CASCADE
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
    "tipo" TEXT,
    "setorId" INTEGER,
    "prioridade" TEXT NOT NULL DEFAULT 'media',
    "canal" TEXT NOT NULL DEFAULT 'whatsapp',
    "contato" TEXT,
    "responsavelId" INTEGER,
    "prazoEm" DATETIME,
    "setorOrigemId" INTEGER,
    "tipoSolicitacao" TEXT,
    "impacto" TEXT,
    "sistemaAfetado" TEXT,
    "tempoEstimadoMin" INTEGER,
    "tempoGastoMin" INTEGER,
    "franquiaCodigo" TEXT,
    "franquiaNome" TEXT,
    "franqueadoNome" TEXT,
    "franqueadoContato" TEXT,
    "localizacao" TEXT,
    "tipoFranquia" TEXT,
    "afetaAtendimento" BOOLEAN NOT NULL DEFAULT false,
    "envolveCusto" BOOLEAN NOT NULL DEFAULT false,
    "valorEstimadoCentavos" INTEGER,
    "precisaAprovacao" BOOLEAN NOT NULL DEFAULT false,
    "urgenciaComercial" TEXT,
    "avaliacaoNota" INTEGER,
    "avaliacaoComentario" TEXT,
    "avaliadoEm" DATETIME,
    CONSTRAINT "Chamado_categoriaId_fkey" FOREIGN KEY ("categoriaId") REFERENCES "Categoria" ("id") ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT "Chamado_setorId_fkey" FOREIGN KEY ("setorId") REFERENCES "Setor" ("id") ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT "Chamado_responsavelId_fkey" FOREIGN KEY ("responsavelId") REFERENCES "Pessoa" ("id") ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT "Chamado_setorOrigemId_fkey" FOREIGN KEY ("setorOrigemId") REFERENCES "Setor" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);
INSERT INTO "new_Chamado" ("atualizadoEm", "categoriaId", "dataAbertura", "descricao", "id", "nome", "origem", "primeiroAtendimentoEm", "resolvidoEm", "resumo", "situacao", "telefone") SELECT "atualizadoEm", "categoriaId", "dataAbertura", "descricao", "id", "nome", "origem", "primeiroAtendimentoEm", "resolvidoEm", "resumo", "situacao", "telefone" FROM "Chamado";
DROP TABLE "Chamado";
ALTER TABLE "new_Chamado" RENAME TO "Chamado";
CREATE INDEX "Chamado_situacao_idx" ON "Chamado"("situacao");
CREATE INDEX "Chamado_telefone_idx" ON "Chamado"("telefone");
CREATE INDEX "Chamado_dataAbertura_idx" ON "Chamado"("dataAbertura");
CREATE INDEX "Chamado_categoriaId_idx" ON "Chamado"("categoriaId");
CREATE INDEX "Chamado_resolvidoEm_idx" ON "Chamado"("resolvidoEm");
CREATE INDEX "Chamado_setorId_idx" ON "Chamado"("setorId");
CREATE INDEX "Chamado_setorOrigemId_idx" ON "Chamado"("setorOrigemId");
CREATE INDEX "Chamado_responsavelId_idx" ON "Chamado"("responsavelId");
CREATE INDEX "Chamado_prazoEm_idx" ON "Chamado"("prazoEm");
CREATE INDEX "Chamado_tipo_idx" ON "Chamado"("tipo");
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;

-- CreateIndex
CREATE UNIQUE INDEX "Setor_codigo_key" ON "Setor"("codigo");

-- CreateIndex
CREATE INDEX "Setor_ativo_ordem_idx" ON "Setor"("ativo", "ordem");

-- CreateIndex
CREATE INDEX "Comentario_chamadoId_criadoEm_idx" ON "Comentario"("chamadoId", "criadoEm");

-- CreateIndex
CREATE INDEX "Anexo_chamadoId_criadoEm_idx" ON "Anexo"("chamadoId", "criadoEm");

-- CreateIndex
CREATE UNIQUE INDEX "Tag_nome_key" ON "Tag"("nome");

-- CreateIndex
CREATE INDEX "Dependencia_bloqueadorId_idx" ON "Dependencia"("bloqueadorId");

-- CreateIndex
CREATE UNIQUE INDEX "Dependencia_bloqueadoId_bloqueadorId_key" ON "Dependencia"("bloqueadoId", "bloqueadorId");

-- CreateIndex
CREATE UNIQUE INDEX "_ChamadoToTag_AB_unique" ON "_ChamadoToTag"("A", "B");

-- CreateIndex
CREATE INDEX "_ChamadoToTag_B_index" ON "_ChamadoToTag"("B");

-- Setores iniciais.
--
-- A lista nasce semeada, e nao vazia, porque um seletor de setor sem opcao
-- nenhuma trava a classificacao no primeiro uso: quem abre o painel depois do
-- deploy nao tem como cadastrar 11 setores antes de mexer no primeiro chamado.
-- Daqui para frente ela e mantida no painel, por quem atende - e a razao de
-- `Setor` ser tabela e nao enum.
--
-- `INSERT OR IGNORE` e nao `INSERT`: o `codigo` e unico, e se alguem tiver
-- criado "ti" a mao antes desta migracao rodar, o certo e manter o que existe em
-- vez de a migracao inteira falhar. Repare que ignorar aqui e seguro justamente
-- porque estas linhas nao carregam dado de ninguem.
INSERT OR IGNORE INTO "Setor" ("codigo", "nome", "ordem", "ativo", "atualizadoEm") VALUES
  ('ti',          'TI',          1, true, CURRENT_TIMESTAMP),
  ('financeiro',  'Financeiro',  2, true, CURRENT_TIMESTAMP),
  ('operacoes',   'Operações',   3, true, CURRENT_TIMESTAMP),
  ('marketing',   'Marketing',   4, true, CURRENT_TIMESTAMP),
  ('manutencao',  'Manutenção',  5, true, CURRENT_TIMESTAMP),
  ('rh',          'RH',          6, true, CURRENT_TIMESTAMP),
  ('comercial',   'Comercial',   7, true, CURRENT_TIMESTAMP),
  ('juridico',    'Jurídico',    8, true, CURRENT_TIMESTAMP),
  ('suprimentos', 'Suprimentos', 9, true, CURRENT_TIMESTAMP),
  ('logistica',   'Logística',  10, true, CURRENT_TIMESTAMP),
  ('expansao',    'Expansão',   11, true, CURRENT_TIMESTAMP);

-- A view volta, agora com as colunas novas.
CREATE VIEW chamados_para_cards AS
SELECT
  id,
  nome,
  -- Os quatro instantes que fecham a conta de SLA. `prazoEm` entrou com a
  -- classificacao e e o unico que nao e um fato consumado: e o combinado, contra
  -- o qual os outros tres sao lidos.
  "dataAbertura",
  "prazoEm",
  "primeiroAtendimentoEm",
  "resolvidoEm",
  resumo,
  descricao,
  situacao,
  prioridade,
  -- 'whatsapp' ou 'painel': por qual PORTA a linha nasceu.
  origem,
  -- Por onde a pessoa CHEGOU (whatsapp/email/telefone/presencial). Outra
  -- pergunta que `origem` - ver o comentario do enum `Canal` no schema.
  canal,
  -- 'interno' ou 'franquia', nulo enquanto ninguem classificou. E o
  -- discriminador: e ele que diz qual dos dois blocos de colunas abaixo tem
  -- significado nesta linha.
  tipo,
  -- Os IDs, e nao os nomes. Juntar com `Categoria`/`Setor`/`Pessoa` aqui
  -- congelaria dentro da view rotulos que sao editaveis no painel; quem consome
  -- faz o JOIN se quiser o texto.
  "categoriaId",
  "setorId",
  "setorOrigemId",
  "responsavelId",
  -- Bloco interno.
  "tipoSolicitacao",
  impacto,
  "sistemaAfetado",
  "tempoEstimadoMin",
  "tempoGastoMin",
  -- Bloco franquia. `franqueadoContato` NAO esta aqui, pelo mesmo motivo de
  -- `telefone`: e canal de contato de uma pessoa, e a view minimiza isso.
  "franquiaCodigo",
  "franquiaNome",
  "franqueadoNome",
  localizacao,
  "tipoFranquia",
  "afetaAtendimento",
  "envolveCusto",
  "valorEstimadoCentavos",
  "precisaAprovacao",
  "urgenciaComercial",
  -- Avaliacao pos-fechamento.
  "avaliacaoNota",
  "avaliacaoComentario",
  "avaliadoEm"
FROM "Chamado"
ORDER BY "dataAbertura" DESC;
