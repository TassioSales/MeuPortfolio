-- View de leitura para a plataforma de cards consultar.
--
-- NÃO precisa ser aplicada à mão: `npm run db:view` derruba a view e executa
-- este arquivo (ver src/scripts/aplicar-view.ts). Rode depois de toda migração -
-- migração que mexe em coluna usada pela view precisa derrubá-la e recriá-la.
--
-- UMA INSTRUÇÃO SÓ NESTE ARQUIVO. O driver do SQLite prepara uma instrução por
-- chamada, então um `DROP` aqui junto com o `CREATE` estouraria; o `DROP` mora no
-- aplicar-view.ts. Também não existe `CREATE OR REPLACE VIEW` no SQLite.
--
-- O QUE ESTA VIEW É E O QUE ELA NÃO É: ela é o contrato de leitura - define
-- quais colunas o consumidor vê, e `telefone` deliberadamente não é uma delas.
-- Ela NÃO é uma fronteira de permissão. No Postgres dava para criar um usuário
-- somente-leitura e conceder SELECT apenas nesta view; no SQLite não há usuário
-- nem GRANT, e quem tem o arquivo tem tudo. Para expor os cards sem entregar o
-- banco, use a rota `/internal/chamados` (mesma minimização, com token) ou
-- entregue uma cópia do arquivo aberta em modo `readonly`.

-- ESTA DEFINIÇÃO TEM UMA CÓPIA em
-- `prisma/migrations/20260831135505_classificacao_de_chamados/migration.sql`. A cópia
-- existe porque migração que reconstrói a tabela `Chamado` (o jeito do SQLite de
-- mudar coluna) precisa derrubar a view antes e recriá-la depois, sem depender
-- de alguém rodar `npm run db:view` no servidor. Mexeu aqui, mexa lá - ou
-- acrescente uma migração nova que recrie a view.

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
