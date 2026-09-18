---
tags: [projeto/whatsapp-suporte, referencia]
projeto: whatsapp-suporte
atualizado: 2026-08-28
---

# WA Mapa de arquivos

Volta para [[WhatsApp Suporte]] · agrupamento por camada em [[WA Arquitetura]].

## `src/` — produção

| arquivo | linhas ~ | o que faz | nota |
| --- | --- | --- | --- |
| [app.ts](../src/app.ts) | 288 | monta o Fastify: rotas + schemas, rate limit, helmet, handlers de erro/404, segredo do webhook no caminho, orçamento de envio do lote | [[WA Arquitetura]] |
| [server.ts](../src/server.ts) | 57 | boot: sobe porta, liga varredor e limpeza, trata `SIGTERM`/`SIGINT` | [[WA Arquitetura]] |
| [config.ts](../src/config.ts) | 244 | lê e valida **todo** o ambiente no boot; mata o processo se faltar segredo | [[WA Configuração]] |
| [log.ts](../src/log.ts) | 68 | logger único + `mascararTelefones` + `erroSeguro` | [[WA Segurança e LGPD]] |
| [db/client.ts](../src/db/client.ts) | 66 | o `PrismaClient` compartilhado: adaptador do SQLite, `busy_timeout`, WAL no boot e a checagem de `foreign_keys` | [[WA Banco de dados]] |
| [db/caminho.ts](../src/db/caminho.ts) | 111 | resolve o `DATABASE_URL` para um caminho absoluto ancorado na raiz do projeto — usado pelo runtime **e** pelo `prisma.config.ts` | [[WA Banco de dados]] |
| [conversation/handler.ts](../src/conversation/handler.ts) | 757 | **o coração**: transação (que é o que serializa), idempotência, decisão de etapa, enfileirar saída | [[WA Fluxo da conversa]] |
| [conversation/flows.ts](../src/conversation/flows.ts) | 152 | etapas, perguntas, textos, limites, palavras de comando | [[WA Fluxo da conversa]] |
| [conversation/categorias.ts](../src/conversation/categorias.ts) | 241 | o menu numerado de assuntos: monta, interpreta a escolha e navega na árvore de `Categoria`. O número do menu é calculado aqui e não é guardado em lugar nenhum. `filhasNoMenu` é a **única** porta pela qual um assunto entra na conversa — é lá que o de uso interno fica de fora | [[WA Fluxo da conversa]] |
| [conversation/sessoes.ts](../src/conversation/sessoes.ts) | 57 | TTL de sessão: corte, contagem, limpeza e varredura periódica | [[WA Segurança e LGPD]] |
| [whatsapp/webhook.ts](../src/whatsapp/webhook.ts) | 138 | traduz o envelope `messages.upsert` da Evolution em `Entrada`; descarta eco, grupo e evento que não é mensagem; isola falha por mensagem | [[WA Fluxo da conversa]] |
| [whatsapp/client.ts](../src/whatsapp/client.ts) | 277 | monta o corpo de texto (`menuNumerado` numera as opções) e posta em `/message/sendText/{instancia}` com retry, orçamento e `Retry-After` | [[WA Outbox e entrega]] |
| [whatsapp/outbox.ts](../src/whatsapp/outbox.ts) | 163 | `despachar`, SQL de reserva, `varrerPendentes`, varredor | [[WA Outbox e entrega]] |
| [whatsapp/signature.ts](../src/whatsapp/signature.ts) | 32 | segredo do webhook + comparação de tempo constante | [[WA Segurança e LGPD]] |
| [whatsapp/throttle.ts](../src/whatsapp/throttle.ts) | 45 | limite por telefone, janela fixa de 60s; devolve a cota gasta em reentrega | [[WA Segurança e LGPD]] |
| [estado/janelas.ts](../src/estado/janelas.ts) | 280 | contadores e reservas em janela: memória (padrão) ou Redis, escolhido no boot por `REDIS_URL`; falha do Redis cai para memória | [[WA Arquitetura]] |
| [whatsapp/telefone.ts](../src/whatsapp/telefone.ts) | 12 | `ehTelefoneValido` — regra única usada em três lugares | [[WA Segurança e LGPD]] |
| [whatsapp/indisponibilidade.ts](../src/whatsapp/indisponibilidade.ts) | 60 | aviso ao usuário quando o banco está fora (HTTP direto, 1 por telefone/10min) | [[WA Outbox e entrega]] |
| [alerta.ts](../src/alerta.ts) | 97 | alerta operacional quando a outbox desiste; coalescido e sem dado pessoal | [[WA Outbox e entrega]] |
| [internal/chamados.ts](../src/internal/chamados.ts) | 1178 | listagem, histórico e métricas (três cortes: assunto, setor, tipo); `PATCH` de situação, de assunto e de **classificação**; criação de chamado no painel; avaliação pós-fechamento | [[WA Painel de chamados]] |
| [internal/camposDeChamado.ts](../src/internal/camposDeChamado.ts) | 418 | os 24 campos de classificação declarados UMA vez: JSON Schema, tipo e a tradução para o Prisma (trim, data ISO, FK que existe). Criar e corrigir usam o mesmo módulo — é o que impede as duas validações de divergirem | [[WA Classificação de chamados]] |
| [internal/setores.ts](../src/internal/setores.ts) | 282 | CRUD dos setores (as áreas que atendem). Conta as duas pontas de uso — quem atende e quem abriu — antes de deixar excluir | [[WA Classificação de chamados]] |
| [internal/detalhes.ts](../src/internal/detalhes.ts) | 635 | o que pende de UM chamado: comentários internos, anexos (BLOB, upload em base64), etiquetas e dependência entre chamados. Separado de `chamados.ts` por CARDINALIDADE — são listas que não cabem na listagem do quadro | [[WA Classificação de chamados]] |
| [internal/auth.ts](../src/internal/auth.ts) | 43 | o guarda das rotas internas: aceita o token interno e o do painel, e a fábrica de hook `exigirToken` usada por todas elas | [[WA Segurança e LGPD]] |
| [internal/categorias.ts](../src/internal/categorias.ts) | 385 | CRUD da árvore de assuntos, com os guardas que a protegem: sem ciclo, sem apagar categoria em uso e sem apagar quem tem sub-assunto. Também o interruptor `visivelNoWhatsapp`, que não tem guarda nenhuma de propósito | [[WA Painel de chamados]] |
| [internal/pessoas.ts](../src/internal/pessoas.ts) | 157 | CRUD do cadastro de pessoas do painel — quem pode ser responsável de um chamado; e o `PUT /identidade`, que casa o `oid` do login Entra a uma pessoa | [[WA Painel de chamados]] |
| [internal/series.ts](../src/internal/series.ts) | 846 | os números do Dashboard: séries temporais (abertos × resolvidos, fila por situação, tempos de atendimento) e os KPIs, em baldes por dia/semana | [[WA Painel de chamados]] |
| [internal/configuracao.ts](../src/internal/configuracao.ts) | 138 | lê e grava a configuração do painel guardada no banco (o que a tela precisa saber e não vem do `.env`) | [[WA Painel de chamados]] |
| [scripts/retencao.ts](../src/scripts/retencao.ts) | 246 | LGPD: simulação, descarte em lotes, `--esquecer` | [[WA Segurança e LGPD]] |
| [scripts/aplicar-view.ts](../src/scripts/aplicar-view.ts) | 58 | derruba e recria a view de cards; roda no deploy e no CI | [[WA Banco de dados]] |

> [!note] As contagens são aproximadas, e por isso mesmo úteis
> Reconferidas em 2026-08-26 com `wc -l`. Elas não servem para auditar nada —
> servem para dizer "isto é um arquivo de 40 linhas" ou "isto é o de 450", que é
> a informação que decide por onde começar a ler.

## `src/dev/` — ferramentas locais (fora do build)

Excluídas do `tsconfig.json`, mas checadas pelo `npm run typecheck`.

| arquivo | o que faz |
| --- | --- |
| [dev/simular.ts](../src/dev/simular.ts) | simulador da Evolution: conversa interativa, cenários prontos, monta o envelope Baileys |
| [dev/evolution-fake.ts](../src/dev/evolution-fake.ts) | Evolution de mentira na 4000, com `/_controle` e `/_estado`; exige o cabeçalho `apikey` |
| [dev/verificar-banco.ts](../src/dev/verificar-banco.ts) | 38 checagens das garantias que só o arquivo SQLite de verdade prova; roda no CI |

Uso em [[WA Ambiente local]].

## `test/`

| arquivo | cobre |
| --- | --- |
| [test/conversa.test.ts](../test/conversa.test.ts) | máquina de etapas e regras da conversa |
| [test/categorias.test.ts](../test/categorias.test.ts) | menu de assuntos na conversa, CRUD da árvore, marcos de SLA e métricas |
| [test/envio.test.ts](../test/envio.test.ts) | retry, orçamento, varredor, desistência |
| [test/rotas.test.ts](../test/rotas.test.ts) | rotas via `app.inject()` |
| [test/seguranca.test.ts](../test/seguranca.test.ts) | assinatura, throttle, máscara de log |
| [test/retencao.test.ts](../test/retencao.test.ts) | LGPD: simulação que não apaga, cortes, lotes, eliminação do titular |
| [test/classificacao.test.ts](../test/classificacao.test.ts) | os campos de classificação: validação, montagem para o Prisma, FKs |
| [test/pessoas.test.ts](../test/pessoas.test.ts) | CRUD de pessoas e o casamento de identidade do login |
| [test/series.test.ts](../test/series.test.ts) | as séries e KPIs do Dashboard, incluindo os baldes de tempo |
| [test/entra.test.mjs](../test/entra.test.mjs) | login pelo Entra ID: PKCE, `state`, `nonce`, validação do `id_token` e do cookie de sessão |
| [test/fake-prisma.ts](../test/fake-prisma.ts) | dublê do Prisma em memória |
| [test/janelas.test.ts](../test/janelas.test.ts) | estado compartilhado: janela, devolução, reserva e os dois caminhos de falha do Redis |
| [test/fake-redis.ts](../test/fake-redis.ts) | dublê do Redis em memória (com a lista do que ele NÃO simula) |
| [test/env.ts](../test/env.ts) | ambiente mínimo para o `config.ts` não matar o processo |

Detalhe em [[WA Testes e verificação]].

## Banco e SQL

| arquivo | o que é |
| --- | --- |
| [prisma/schema.prisma](../prisma/schema.prisma) | modelos, enums, índices. `provider = "sqlite"` |
| [prisma.config.ts](../prisma.config.ts) | config do CLI do Prisma. Desde o Prisma 7 a URL do banco **não** fica mais no `schema.prisma`; aqui ela passa por `db/caminho.ts` para o CLI e o runtime abrirem o mesmo arquivo |
| [prisma/migrations/20260827200659_init/migration.sql](../prisma/migrations/20260827200659_init/migration.sql) | baseline SQLite (substituiu as quatro migrações do Postgres, que ficaram no histórico do git) |
| [sql/view_chamados_para_cards.sql](../sql/view_chamados_para_cards.sql) | view de leitura para a plataforma de cards; aplicada por `npm run db:view` |

## Configuração do projeto

| arquivo | o que é |
| --- | --- |
| [package.json](../package.json) | scripts e dependências |
| [tsconfig.json](../tsconfig.json) | build de produção; **exclui `src/dev`** |
| [tsconfig.test.json](../tsconfig.test.json) | typecheck e compilação dos testes (inclui tudo) |
| [.env.example](../.env.example) | referência comentada de todas as variáveis |
| [.github/workflows/ci.yml](../.github/workflows/ci.yml) | dois jobs: `format:check`/typecheck/build/test e as checagens contra um banco SQLite de verdade (com `db:view`); sem `services:`, porque não há servidor para subir |
| [README.md](../README.md) | documentação de uso |
| `docs/` | estas notas |

## Go-live no Windows — os dois processos

Entraram no repositório em 2026-08-25. Detalhe e as decisões por trás em
[[WA Implantação#O caminho do go-live no Windows]].

| arquivo | linhas ~ | o que faz |
| --- | --- | --- |
| [run.bat](../run.bat) | 461 | confere o ambiente (Node, `.env`, portas, migração, build) e sobe bot + painel; espera o `/health` |
| [iniciar.mjs](../iniciar.mjs) | 236 | sobe bot **e** painel num terminal só, cada um como filho deste processo; um Ctrl+C encerra os dois. É a EXECUÇÃO que o `run.bat` chama depois de conferir o ambiente |
| [parar.bat](../parar.bat) | 76 | derruba os dois **por porta**, nunca por `node.exe` |
| [servidor-painel.mjs](../servidor-painel.mjs) | 694 | serve o painel na 8511 e repassa `/internal/*` **e o `/webhook`** para o bot na 9511; faz o login pelo Entra ID e os cabeçalhos de segurança (CSP, anti-clickjacking, checagem de Origin). Ver [[WA Segurança e LGPD]] |
| [painel-entra.mjs](../painel-entra.mjs) | 561 | o login pelo Entra ID: authorization code + PKCE, `state`/`nonce`, validação do `id_token` contra as chaves do tenant, cookie de sessão assinado. Ver [[WA Segurança e LGPD]] |
| [diagnostico.mjs](../diagnostico.mjs) | 208 | diagnóstico do go-live de dentro para fora: `.env` → processos nas portas → webhook com o segredo certo e com o errado → o mesmo par pelo domínio |
| [GOLIVE.md](../GOLIVE.md) | — | o passo a passo operacional deste caminho |
| `activity-dashboard/` | ~6.000 | o painel de chamados, agora versionado aqui dentro. Ver [[WA Painel de chamados]] |

A porta do bot sai do **`.env`**, nunca de um número fixo — mas por dois
caminhos diferentes, e a diferença tem consequência:

- `run.bat` e `parar.bat` leem `PORT=` do arquivo direto (`findstr /B`);
- `servidor-painel.mjs` **não abre o `.env`**: ele lê `BOT_PORT` do
  ambiente, que o `run.bat` define antes de chamá-lo.

> [!warning] Subir o painel à mão fura essa corrente
> `node servidor-painel.mjs` fora do `run.bat` cai no padrão `9511`. Se o
> `.env` disser outra porta, o painel abre normalmente e todo
> `/internal/*` responde 502 — o quadro fica vazio sem dizer por quê. Nesse
> caso, defina `BOT_PORT` na mão. Ver
> [[WA Configuração#Um arquivo só, e um bloco que o inverte]].

## Implantação

| arquivo | o que é |
| --- | --- |
| [Dockerfile](../Dockerfile) | imagem em duas etapas; a final não leva compilador nem código-fonte. **Não inclui o painel nem os `.bat`** |
| [.dockerignore](../.dockerignore) | o que **não** entra na imagem (a começar pelo `.env`) |
| [.nvmrc](../.nvmrc) | versão do Node; o CI lê deste arquivo |
| [render.yaml](../render.yaml) | serviço + banco no Render, migração no `preDeploy` |
| [cloudflared.exemplo.yml](../cloudflared.exemplo.yml) | exemplo de config do Cloudflare Tunnel — a URL pública HTTPS que o webhook exige; avisa que túnel **local × remoto** muda tudo |
| [GOLIVE.md](../GOLIVE.md) | o outro caminho: dois processos numa máquina Windows |

Detalhe em [[WA Implantação]].

## Diretórios gerados (não versionar, não editar)

`dist/` (build), `dist-test/` (testes compilados), `node_modules/` e
`src/generated/` — o cliente do Prisma, que desde a versão 7 é gerado num
caminho do projeto em vez de dentro do `node_modules`. Quem o cria é
`npm run prisma:generate`.

## Por onde entrar, dependendo do que você quer mexer

| mudança | comece em |
| --- | --- |
| texto que o bot fala | [flows.ts](../src/conversation/flows.ts) |
| nova etapa ou campo | [flows.ts](../src/conversation/flows.ts) + [handler.ts](../src/conversation/handler.ts) — do 4º campo em diante o menu vira lista sozinho, ver [[WA Fluxo da conversa]] |
| comportamento de reenvio | [outbox.ts](../src/whatsapp/outbox.ts) + [client.ts](../src/whatsapp/client.ts) |
| novo tipo de mídia | `FORMATOS_CONHECIDOS` em [webhook.ts](../src/whatsapp/webhook.ts) |
| nova variável de ambiente | [config.ts](../src/config.ts) **e** [.env.example](../.env.example) |
| nova rota interna | [internal/chamados.ts](../src/internal/chamados.ts) — ou [setores.ts](../src/internal/setores.ts) / [detalhes.ts](../src/internal/detalhes.ts), se for de setor ou do que pende de um chamado |
| novo campo de classificação de chamado | [camposDeChamado.ts](../src/internal/camposDeChamado.ts) (schema + tipo + montagem, num lugar) + migração, ver [[WA Classificação de chamados]] |
| tabela, coluna ou índice | [schema.prisma](../prisma/schema.prisma) + migração, ver [[WA Banco de dados]] |
| qualquer coisa de implantação | [Dockerfile](../Dockerfile) / [render.yaml](../render.yaml), ver [[WA Implantação]] |
| onde o arquivo do banco fica | `DATABASE_URL` no `.env` → [db/caminho.ts](../src/db/caminho.ts) → [db/client.ts](../src/db/client.ts) |
