---
tags: [projeto/whatsapp-suporte, testes]
projeto: whatsapp-suporte
atualizado: 2026-08-28
---

# WA Testes e verificação

Volta para [[WhatsApp Suporte]] · como rodar: [[WA Ambiente local]].

Duas camadas, com fronteira explícita:

| camada | comando | precisa de | cobre |
| --- | --- | --- | --- |
| unitária / de rota | `npm test` | nada (sem banco, sem rede) | regra de conversa, envio, rotas, segurança, retenção |
| garantias de banco | `npm run dev:verificar-banco` | banco migrado + servidor de pé | formato e comparação de data, serialização de transações, índice único, SQL da outbox, cascade |

**As duas estão no CI** desde 2026-08-18 — inclusive a segunda. Ela nasceu num job
com `services: postgres`; com o banco em SQLite esse serviço deixou de existir, e o
job só precisa rodar a migração. Mas *rodar* é outra coisa: o repositório só ganhou
remoto em 2026-08-20, e a primeira execução de verdade falhou. Ver [[#CI]] e
[[#Quando o CI passou a rodar de verdade]].

## Suíte em memória — 357 testes, todos passando (2026-09-17)

```bash
npm test         # tsc -p tsconfig.test.json && node --test dist-test/test/*.test.js
npm run typecheck
npm run format:check   # Prettier, só sobre código (a documentação fica de fora)
```

Test runner **nativo do Node** — nenhuma dependência de teste no projeto (o
único devDep de qualidade é o Prettier, que não roda teste nenhum). Prisma,
`fetch` e Redis são substituídos por dublês ([test/fake-prisma.ts](../test/fake-prisma.ts),
[test/env.ts](../test/env.ts), [test/fake-redis.ts](../test/fake-redis.ts)) e o código
real é exercitado.

> [!warning] Todo dublê aqui declara o que ele NÃO simula
> É a única coisa que impede um teste verde de virar promessa falsa. O do
> Prisma não prova a serialização de transações concorrentes, o índice único, a
> comparação de data em SQL crua nem o `ON DELETE SET NULL` de `Categoria`; o do Redis não prova a atomicidade do Lua (aqui
> não existe concorrência) nem a expiração pelo relógio do servidor. Nos dois casos
> a lista está no topo do arquivo, e nos dois casos o que falta só se prova com o
> banco de verdade — foi assim que o bug de fuso apareceu duas vezes.
>
> A classificação de chamados acrescentou itens a essa lista: o dublê **não** prova
> o `ON DELETE CASCADE` que leva comentários e anexos junto com o chamado, nem o
> `ON DELETE SET NULL` que devolve o chamado para "sem responsável" quando a pessoa
> sai do cadastro. Os dois são do banco, e saem em `npm run dev:verificar-banco`.

### `test/classificacao.test.ts` (2026-08-31)

Arquivo próprio para as rotas de classificação — 60 testes. Vale saber o que ele
cobre porque três desses casos existem para impedir uma regressão específica:

- **`comentário NÃO vira mensagem de WhatsApp`** — o mais importante do arquivo.
  Se `Comentario` e `Mensagem` fossem a mesma tabela, a varredura da outbox
  despacharia a nota interna da equipe para o cliente. O teste confere as duas
  pontas: nenhuma linha em `Mensagem` e nenhum envio capturado.
- **`resolvido -> fechado NÃO remarca a data de conclusão`** — só a ENTRADA no
  conjunto `{resolvido, fechado}` move o marco. Remarcar apagaria a data real de
  conclusão do chamado que estava sendo dado por concluído.
- **`campo desconhecido no corpo é recusado`** — foi ele que revelou que
  `additionalProperties: false` **não** recusa nada no Fastify (ver
  [[WA Classificação de chamados#Uma armadilha do Fastify que este trabalho revelou]]).
  O teste falhou com 200, e a correção foi no servidor, não no teste.

Também exercitados: a faixa da avaliação (só em chamado concluído), base64
inválido, MIME fora da lista, o teto de tamanho do anexo (`ANEXO_MAX_BYTES` é
posto em 3 KB no `test/env.ts` para o caso não exigir um corpo de megabytes), o
ciclo de dois em dependências, e o fechamento das três tabelas de métricas com o
total geral.

| arquivo | cobre |
| --- | --- |
| [test/categorias.test.ts](../test/categorias.test.ts) | **menu numerado de assuntos** (numeração entre as ativas, escolha por número/linha/rótulo, descida na árvore, "0" para voltar, botão de menu antigo recusado, etapa pulada sem assunto cadastrado), **CRUD da árvore** (código repetido, ciclo, exclusão recusada), **marcos de SLA** e **métricas** |
| [test/conversa.test.ts](../test/conversa.test.ts) | máquina de etapas, limites por campo, cancelar, expiração, mídia, edição, botão x texto, **escolha em lista (`list_reply`)** |
| [test/envio.test.ts](../test/envio.test.ts) | retry, classificação transitório/permanente, orçamento `ateMs`, varredor, desistência, **escolha botões x lista**, **alerta de descarte** (coalescência, sem dado pessoal, alerta que falha não derruba o envio) |
| [test/rotas.test.ts](../test/rotas.test.ts) | `/health`, `/ready`, handshake, lote com falha parcial, endpoint interno, notificação que falha não desfaz a situação, **histórico de situação** (de/para, autor, ordem, 404, sem telefone) |
| [test/seguranca.test.ts](../test/seguranca.test.ts) | segredo do webhook (`segredoValido`), segredo vazio dos dois lados, tamanho diferente, `comparacaoSegura`, throttle, máscara de telefone no log |
| [test/retencao.test.ts](../test/retencao.test.ts) | **LGPD**: a simulação não apaga nada, sem política nada sai, corte por data, lotes até o fim, eliminação do titular sem tocar em outro titular, leitura do `--confirmar` |
| [test/janelas.test.ts](../test/janelas.test.ts) | **estado compartilhado entre instâncias**: virada de janela, devolução de cota, reserva (`SET NX`), prefixo de chave, e os dois caminhos de falha — Redis fora do ar cai para memória sem desligar o limite, e as duas implementações concordam no mesmo roteiro |

As rotas são exercitadas com `app.inject()` — sem abrir porta. É o que
`criarApp()` separado de `server.ts` permite (ver [[WA Arquitetura]]).

## O que a suíte em memória NÃO prova

Estes comportamentos dependem do banco real:

1. o **formato da data e a comparação dela em SQL crua**: em memória não existe
   serialização de data nenhuma, então um erro de formato é literalmente invisível;
2. a serialização de fato de duas transações concorrentes (que no SQLite vem do
   mutex do adaptador, e não de uma instrução que dê para espionar);
3. o índice único rejeitando de fato um `whatsappMessageId` repetido;
4. a SQL de reserva da outbox — a regra de elegibilidade dela está
   **reimplementada em JS** no dublê, então o teste cobre a orquestração em
   volta, **não a query**;
5. o `ON DELETE CASCADE`, que no SQLite depende ainda de `PRAGMA foreign_keys`
   estar ligado na conexão.

> [!danger] Isso não é teórico — aconteceu duas vezes
> Essa lacuna já escondeu o **mesmo sintoma por duas causas diferentes**: em
> 2026-08-17 por tipo de coluna, em 2026-08-18 por fuso da sessão, na subida
> para o Prisma 7. Nas duas, o dublê passou — a comparação em JS não tem o
> problema que a comparação em SQL tem — e nas duas o varredor da outbox ficou
> inerte por 3 horas. Ver [[WA Fuso horário sem timezone]].
>
> A troca para SQLite fechou aquelas duas causas e abriu uma terceira, no mesmo
> lugar: comparar a coluna de data com `datetime('now')` **como texto**. O dublê
> continuaria passando. É por isso que a checagem 0 do `verificar-banco` hoje
> confere o formato gravado, e não mais o fuso da sessão.
>
> Foi essa reincidência que levou o `dev:verificar-banco` para dentro do CI.

## `npm run dev:verificar-banco` — 38 checagens

[src/dev/verificar-banco.ts](../src/dev/verificar-banco.ts). Exige `npm run dev`
(ele checa `/health` primeiro e para com mensagem clara se não responder) e, para
os dois últimos blocos, a Evolution de mentira. Usa **telefone novo por execução**,
então uma rodada nunca herda estado da anterior, e limpa o que criou.

| bloco | prova |
| --- | --- |
| 0. data | a coluna guarda **texto** ISO-8601 com offset `+00:00`, e uma data recém-gravada **não** aparece no futuro para o `now()` do banco — a guarda contra a reincidência descrita acima |
| 1. serialização por telefone | duas mensagens simultâneas do mesmo telefone: as duas gravadas, o fluxo avançou **duas** etapas, nome e resumo preenchidos — nenhuma se sobrescreveu |
| 2. índice único | mesmo `key.id` duas vezes: entrada não duplicada, etapa não avançou de novo, bot não respondeu duas vezes |
| 3. dois `PATCH` simultâneos | **um só** viu a situação anterior como `aberto` e o usuário foi notificado **uma** vez |
| 4. reserva da outbox | cinco linhas plantadas cobrindo a regra de elegibilidade: nunca tentada e antiga (reserva), com menos de 30s (não), espera de 60s não vencida (não), vencida (reserva), no teto de tentativas (não) — e `ultimaTentativaEm` marcado pela reserva |
| 5. recuperação ponta a ponta | Evolution fora → resposta gravada e pendente, **estado da conversa avança de qualquer forma** → Evolution de volta → varredor entrega e marca `enviadaEm` |
| 6. histórico de situação | só as mudanças reais viram linha (um `PATCH` que repete a situação não), o `autor` é gravado (e fica nulo sem ele) e apagar o chamado **leva o histórico junto** — o `ON DELETE CASCADE` de que a retenção depende |
| 7. árvore de assuntos | `_count` sobre relação, `orderBy` em lista, `paiId: null` virando `IS NULL`, o índice único do `codigo` derrubando repetido (P2002), os marcos de SLA voltando como `Date` — e o `ON DELETE SET NULL` que faz apagar categoria **zerar a coluna do chamado** em vez de apagar o chamado |

Saída: uma linha `OK`/`FALHOU` por checagem e exit code 1 se qualquer uma falhar.
No `finally`, sempre devolve a Evolution de mentira ao normal — nunca deixa o
ambiente em modo falha.

> [!important] Quando rodar
> Antes de **qualquer** deploy que mexa em transação, índice ou SQL cru — e
> **trocar quem abre a conexão** (driver, ORM, banco) conta como mexer nisso. Foi
> este comando que validou a troca do Postgres pelo SQLite.
> Desde 2026-08-18 isso também roda sozinho no CI, então na prática você só roda
> à mão enquanto desenvolve.

## CI

[.github/workflows/ci.yml](../.github/workflows/ci.yml), em push para
`main`/`master` e em pull request. **Dois jobs.**

### `verificar` — sem banco, sem rede

```
checkout → node (do .nvmrc, cache npm) → npm ci → prisma:generate
        → format:check → typecheck → build → npm test
```

`prisma:generate` antes do build porque o client é gerado, não versionado.
`format:check` antes do typecheck porque é a checagem mais barata e a que dá o
retorno mais objetivo ("rode `npm run format`").

### `banco` — com um banco de verdade

```
checkout → npm ci → prisma:generate → prisma:deploy → build → db:view
        → sobe a Evolution de mentira → sobe o servidor → espera o /health
        → dev:verificar-banco
```

Sem `services:` nenhum, e isso é o resumo da troca do Postgres pelo SQLite: não há
servidor para subir, nem health check para esperar, nem corrida entre "o banco
aceitou conexão" e "a migração rodou". `DATABASE_URL: file:./dados/ci.db` e o
`prisma:deploy` cria o arquivo.

`db:view` está aí porque `prisma migrate` **não gerencia view**: sem esse passo,
um erro na SQL da view de cards só apareceria em produção, depois de a migração
já ter passado. É exatamente o que o `preDeployCommand` do `render.yaml` faz.

Esta nota afirmava, até 2026-08-18, que "não dá para colocar no CI sem um
Postgres". Dava: `services: postgres` — e depois da troca para SQLite nem isso é
preciso. O job aplica as **migrações de verdade** (uma migração quebrada derruba o
CI aqui, não na implantação) e roda as 38 checagens contra elas.

> [!important] Isso não é zelo excessivo
> Na primeira execução, esse job encontrou um bug real: a regressão de fuso do
> Prisma 7. As checagens que pegam a classe de bug mais difícil do projeto
> dependiam de alguém **lembrar** de rodar um comando na própria máquina.

## Quando o CI passou a rodar de verdade

O arquivo do CI existia desde o começo do projeto. O que não existia era um
**remoto**: sem `origin`, um workflow do GitHub Actions é um arquivo de texto.
O remoto privado (`BioMundo/whatsapp-sup`) entrou em **2026-08-20**, e a primeira
execução de verdade **falhou** — no job `verificar`, no passo `prisma:generate`:

```
Failed to load config file "/home/runner/work/whatsapp-sup/whatsapp-sup"
  as a TypeScript/JavaScript module.
  Error: PrismaConfigEnvError: Cannot resolve environment variable: DATABASE_URL.
```

### Por que passava na máquina e falhava no runner

[prisma.config.ts](../prisma.config.ts) resolve `env('DATABASE_URL')` no momento
em que é **carregado** — antes de o CLI saber qual comando foi pedido. O
`prisma generate` não abre conexão nenhuma (só lê o schema), mas paga o pedágio
igual e morre se a variável não existir.

Na máquina isso passa batido porque a primeira linha do arquivo é
`import 'dotenv/config'`, e o `.env` supre a variável. **O `.env` está no
`.gitignore`** — então nunca chega ao runner.

> [!important] A assimetria que esconde a falha
> O job `banco` **não** sofria: ele define `DATABASE_URL` no nível do job, para
> falar com o banco. Só o `verificar` ficava sem. Ou seja: as checagens contra o
> banco real rodavam, e o `typecheck`, o `build` e os 137 testes **não rodavam
> nenhuma vez** — o job morria três passos antes deles.

Era invisível de outra forma também: o passo existe desde o commit inicial, mas
só virou fatal em 2026-08-18, quando a subida para o **Prisma 7** trouxe o
`prisma.config.ts` com o `env()` estrito. Até o Prisma 5 a URL vinha do
`schema.prisma` e o `generate` não precisava de ambiente.

### A correção

`env` **no passo**, não no job — só o `prisma:generate` precisava da variável, e
o valor era uma fachada declarada:

```yaml
- run: npm run prisma:generate
  env:
    DATABASE_URL: postgresql://nao:usado@127.0.0.1:5432/generate_nao_conecta
```

O `prisma.config.ts` ficou **intacto de propósito**: `env()` era a forma idiomática
do Prisma 7 e era ela que dava a mensagem precisa quando faltava `DATABASE_URL` no
`prisma migrate deploy` de produção. Trocar diagnóstico de produção para acomodar o
CI seria o negócio errado.

> [!note] A troca para SQLite tornou essa fachada desnecessária
> O `prisma.config.ts` não usa mais `env()`: ele passa o `DATABASE_URL` por
> [db/caminho.ts](../src/db/caminho.ts), que **cai no caminho padrão** quando a
> variável não existe. Um `prisma generate` sem ambiente nenhum funciona, que é o
> comportamento correto para um comando que só lê o schema — e o passo do CI
> perdeu o `env:` de fachada.
>
> O diagnóstico de produção não piorou: quem falha alto por `DATABASE_URL` ausente
> continua sendo o [config.ts](../src/config.ts), no boot do servidor.

Verificado reproduzindo o estado do runner na máquina — sem `.env` e sem
variável de ambiente, apontando o dotenv para um caminho inexistente
(`DOTENV_CONFIG_PATH=/naoexiste/.env`). Antes: a mesma mensagem do log, palavra
por palavra. Depois: `prisma:generate` → `format:check` → `typecheck` → `build`
→ 137 testes, tudo verde.

> [!note] Os testes nunca estavam em risco
> [test/env.ts](../test/env.ts) injeta o ambiente da suíte
> (`Object.assign(process.env, {...})`) antes de qualquer import de
> [src/config.ts](../src/config.ts). `npm test` não depende de `.env` nem de
> variável do runner — foi por isso que o problema apareceu no
> `prisma:generate` e não no `npm test`.

### E as actions estavam no runtime errado

No mesmo dia, `actions/checkout` e `actions/setup-node` subiram de `@v4` para
`@v7`. Não era a causa da falha — o log prova que o job chegou até o quarto
passo. Mas as `v4` declaram `using: node20`, e isso tem prazo: desde 16/06/2026
o runner as executa no Node 24 com aviso de depreciação, e em **16/09/2026** o
Node 20 sai do runner e elas param de rodar.

Atenção: isso é a versão de Node **da action**, não a do projeto — a do projeto
vem do `.nvmrc` e sempre esteve certa. O [[Estúdio]] tem o mesmo defeito no CI
dele, ainda não corrigido.

> [!tip] A lição, que não é sobre Prisma
> Uma checagem automática que nunca executou não é uma checagem — é uma
> intenção. Entre "o CI existe" e "o CI roda" havia uma pendência de operação
> (publicar o remoto), e enquanto ela estava aberta as notas deste vault
> afirmavam cobertura que não existia. Ver [[WA Pendências]].

## Build

```bash
npm run build     # tsc → dist/
npm start         # node dist/server.js
```

`tsconfig.json` **exclui `src/dev`**: Evolution de mentira e simulador não vão para o
build de produção. Eles continuam sendo checados pelo `npm run typecheck`, que
usa `tsconfig.test.json`.

## Lacunas de teste conhecidas

- **Sem lint/formatter** — só `typecheck`. Ver [[WA Pendências]].
- **A FK `Mensagem → Chamado` não é simulada** — no dublê nada reclama se o
  chamado for apagado antes das mensagens dele. A ordem correta em
  `apagarChamadosAntigos` está fixada por teste, mas quem a **obriga** é o banco —
  e no SQLite, só com `PRAGMA foreign_keys` ligado (conferido no boot por
  `prepararBanco`, ver [[WA Banco de dados]]).
- **Sem teste de carga** — os limites (rate limit, `ENVIO_SINCRONO_MS`) foram
  escolhidos por raciocínio sobre o comportamento de quem entrega o webhook,
  não medidos.
- **Sem teste com a Evolution de verdade** — todo o caminho de saída foi
  exercitado contra a Evolution de mentira; o contrato real (formato de erro,
  limites de
  template, banimento de número) nunca foi tocado.
- **A view de cards não tem teste de conteúdo** — mas `npm run db:view` roda no
  CI, então pelo menos um erro de SQL na view derruba o build em vez de aparecer
  em produção.
