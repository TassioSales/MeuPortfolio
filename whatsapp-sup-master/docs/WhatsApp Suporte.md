---
tags: [projeto/whatsapp-suporte, indice]
projeto: whatsapp-suporte
atualizado: 2026-09-04
---

# WhatsApp Suporte

Bot de suporte no WhatsApp que coleta um chamado por um fluxo guiado
(**assunto → nome → resumo → descrição → confirmação**) e grava tudo em SQLite.
**Sem IA em nenhum ponto do caminho**: cada resposta do usuário vai direto para o
campo correspondente, sem interpretação de conteúdo.

> [!info] Onde fica o quê
> Código em `whatsapp-suporte/` · estas notas em `whatsapp-suporte/docs/` ·
> os outros projetos do vault em [[Projetos]] ·
> a documentação de uso para quem vai rodar continua no
> [README](../README.md). Estas notas são a leitura de *consulta*: explicam
> **por quê** cada coisa é assim e o que ainda falta.

## Por onde começar

| Quero… | Nota |
| --- | --- |
| entender o desenho geral | [[WA Arquitetura]] |
| saber o que o bot responde e quando | [[WA Fluxo da conversa]] |
| entender como a mensagem sai (e volta a sair) | [[WA Outbox e entrega]] |
| mexer em tabela, índice ou SQL cru | [[WA Banco de dados]] |
| **entender os campos de um chamado** (setor, tipo, prazo, anexo…) | [[WA Classificação de chamados]] |
| configurar `.env` | [[WA Configuração]] |
| revisar segurança / LGPD | [[WA Segurança e LGPD]] |
| rodar sem instância da Evolution | [[WA Ambiente local]] |
| **implantar** (Docker, Render, CI) | [[WA Implantação]] |
| ligar o quadro de chamados ao banco | [[WA Painel de chamados]] |
| saber o que os testes cobrem (e o que não) | [[WA Testes e verificação]] |
| achar um arquivo | [[WA Mapa de arquivos]] |
| **saber o que ainda falta** | [[WA Pendências]] |
| **apresentar o projeto e combinar prazo** | [[WA Lançamento]] |
| **subir num servidor Windows** (bot + painel) | [[WA Implantação#O caminho do go-live no Windows]] |
| **rodar a demonstração ao vivo** | [[WA Demonstração]] |
| **ver métricas e monitoramento** | [[WA Métricas]] · [[Monitor Bio]] |

## Estado em 2026-08-31

- **Um chamado deixou de ter sete campos e passou a ter trinta e um.** Entraram
  setor (a área que atende, e a que pediu), tipo (interno x franquia, que decide
  qual bloco de campos vale), prioridade técnica separada da urgência comercial,
  prazo de SLA, canal de origem, avaliação pós-fechamento, etiquetas livres,
  comentários internos, anexos e dependência entre chamados. `Situacao` ganhou
  `aguardando_resposta` e `fechado`.

  São 24 colunas em `Chamado` e cinco tabelas novas (`Setor`, `Comentario`,
  `Anexo`, `Tag`, `Dependencia`), na migração
  `20260831135505_classificacao_de_chamados` — que também semeia os 11 setores
  iniciais. **Todo o estado é do servidor**: nada disso vive no navegador, então
  todos os atendentes veem os mesmos chamados e os mesmos campos.

  O raciocínio de cada decisão está em [[WA Classificação de chamados]] — em
  especial por que assunto e setor são coisas diferentes, por que `tipo` nasce
  nulo, e por que comentário interno **não** pode morar na tabela `Mensagem`.

- **297 testes** passando (eram 237), com `test/classificacao.test.ts` novo.
- Uma armadilha do Fastify apareceu no caminho e valeu correção:
  `additionalProperties: false` **remove** o campo desconhecido em vez de recusar
  a requisição, e `minProperties` não salva. Ver
  [[WA Classificação de chamados#Uma armadilha do Fastify que este trabalho revelou]].

## Estado em 2026-08-26

- Fluxo completo funcionando, exercitado **contra o banco de verdade** (arquivo
  SQLite em `dados/`), não só com dublê em memória.
- **152 testes** + `npm run dev:verificar-banco` (28 checagens contra o banco
  real) passando; sem drift entre schema e banco. A suíte foi rodada de novo em
  2026-08-26: **152/152**, nenhuma falha.
- **O projeto deixou de ser só implantável e passou a estar configurado para
  subir.** Entraram no repositório `run.bat`, `parar.bat`,
  `servidor-painel.mjs` e `GOLIVE.md`, e o painel veio junto, em
  `activity-dashboard/`. Ver [[WA Implantação#O caminho do go-live no Windows]].
- **O repositório foi publicado** em 2026-08-20 (remoto privado
  `BioMundo/whatsapp-sup`) — era a pendência que travava tudo abaixo dela.
- **E o CI, na primeira execução de verdade, falhou.** O job `verificar` morria
  no `prisma:generate` por falta de `DATABASE_URL`; corrigido no mesmo dia. Vale
  ler o que isso ensina em [[WA Testes e verificação#Quando o CI passou a rodar de verdade]].
- **Existe o que implantar**: Dockerfile, `.dockerignore`, `.nvmrc` e
  `render.yaml`. Ver [[WA Implantação]].
- Dois bugs reais de fuso encontrados em teste ao vivo — o mesmo sintoma por
  causas diferentes, um deles trazido pela subida para o Prisma 7. Os dois em
  [[WA Fuso horário sem timezone]]; o segundo deixou uma checagem de guarda no
  CI.
- Um bug na simulação da retenção, encontrado ao escrever os testes que
  faltavam: ela contava **menos** do que o `--confirmar` apagava. Ver
  [[WA Segurança e LGPD]].
- **Troca da Meta pela Evolution API** (2026-09-17). O projeto deixou de falar
  com a WhatsApp Cloud API. Mudou a autenticação do webhook (HMAC sobre o corpo
  → segredo no caminho), o formato do payload (`entry/changes/messages` →
  envelope Baileys `messages.upsert`), o endpoint de saída
  (`/message/sendText/{instancia}`) e a forma dos menus (botão e lista
  interativa → **lista numerada em texto**). Ver [[WA Segurança e LGPD]] e
  [[WA Fluxo da conversa]].
  > [!warning] O que isso ainda **não** prova
  > Os 357 testes e a conversa ponta a ponta rodaram contra a **Evolution de
  > mentira**. Que a instância esteja conectada, que a URL do webhook esteja
  > cadastrada com o segredo certo e que uma mensagem real tenha ido e voltado
  > **não dá para verificar daqui** — só a conversa de ponta a ponta com um
  > número real prova isso. Ver [[WA Pendências#Bloqueiam ir para produção]].

## Pilha

Node 24 (LTS) · TypeScript 7 (strict) · Fastify 5 · Prisma 7 · SQLite ·
`node --test` (test runner nativo, sem framework de teste).

Dependências de produção enxutas, de propósito: `fastify`,
`@fastify/rate-limit`, `@fastify/helmet`, `@fastify/cors`,
`@prisma/client`, `@prisma/adapter-pg`, `pg`, `prisma`, `ioredis` e
`dotenv`.

> [!note] As duas que entraram depois
> `@fastify/cors` serve o `PAINEL_ORIGENS` (ver [[WA Painel de chamados]]) e
> `ioredis` só é carregada quando `REDIS_URL` existe — sem ela, nada de Redis
> entra no caminho da requisição. Ver
> [[WA Arquitetura#Estado compartilhado entre instâncias]].

> [!note] Por que o `@prisma/adapter-better-sqlite3` aparece aqui
> A partir do Prisma 7 o cliente não abre conexão sozinho: quem fala com o banco
> é um *driver adapter*. Aqui ele é o do SQLite, e é onde ficam o `busy_timeout`
> e a serialização das transações — o mutex que substituiu os locks explícitos do
> Postgres. Ver [[WA Banco de dados]].

## Os quatro comandos que importam

```bash
npm run dev                  # servidor (webhook + varredor + limpeza de sessões)
npm test                     # suíte em memória: sem banco, sem rede
npm run dev:verificar-banco  # garantias que só o banco de verdade prova
npm run retencao             # LGPD: simula o descarte; --confirmar apaga
```

O resto está em [[WA Ambiente local]].

## As cinco ideias que explicam o código

1. **Nada de IA, nada de adivinhação.** Texto digitado vai para o campo da etapa
   atual. Comando só vale por igualdade exata do texto normalizado — "preciso
   cancelar meu pedido no site" é descrição, não comando. Ver
   [[WA Fluxo da conversa]].
2. **Id de botão é protocolo interno.** `editar_descricao` só vale vindo de um
   clique de verdade; digitado, não é comando. As *palavras* humanas ("sim",
   "editar") são aceitas digitadas porque botão interativo não renderiza em todo
   cliente.
3. **Estado e resposta commitam juntos.** A resposta do bot é gravada em
   `Mensagem` **dentro da mesma transação** que muda a etapa, e só depois é
   enviada. Se a Evolution estiver fora, a linha fica pendente e o varredor
   reenvia. Ver [[WA Outbox e entrega]].
4. **Uma mensagem é processada por vez.** A transação é a serialização: o SQLite
   aceita um escritor e o adaptador segura um mutex do `BEGIN` ao commit, então
   duas mensagens quase simultâneas não leem a mesma etapa. No Postgres isso era
   um `pg_advisory_xact_lock` por telefone. O preço é o desenho: **uma
   instância**. Ver [[WA Banco de dados]].
5. **Falhar alto e cedo.** Sem qualquer segredo no `.env`, o processo morre no
   boot listando tudo que falta, em vez de subir com a validação de assinatura
   desligada. Ver [[WA Configuração]].
