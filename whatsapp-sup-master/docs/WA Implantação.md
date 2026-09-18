---
tags: [projeto/whatsapp-suporte, operacao, deploy]
projeto: whatsapp-suporte
atualizado: 2026-08-26
---

# WA Implantação

Volta para [[WhatsApp Suporte]] · configuração em [[WA Configuração]] ·
o que roda no CI em [[WA Testes e verificação]].

> [!note] Duas versões de Node, não uma
> O `.nvmrc` diz em que Node o **projeto** roda. As *actions* do workflow têm uma
> versão de Node própria, declarada por elas (`using:`) — e é essa que estava
> vencida em 2026-08-20, com `@v4`. As duas não têm relação, e confundi-las é
> perder tempo procurando no lugar errado. Ver
> [[WA Testes e verificação#E as actions estavam no runtime errado]].

Até 2026-08-18 o projeto **falava** de implantação — o README citava nginx,
Render e `TRUST_PROXY` — mas não havia um único artefato para implantar.
Era a maior distância entre "documentado" e "existe". Agora existe:

| arquivo | para quê |
| --- | --- |
| [Dockerfile](../Dockerfile) | imagem de produção, em duas etapas |
| [.dockerignore](../.dockerignore) | o que **não** entra na imagem |
| [.nvmrc](../.nvmrc) | versão do Node do **projeto** (o CI lê deste arquivo) |
| [render.yaml](../render.yaml) | serviço + banco no Render |

E desde 2026-08-25 existe um **segundo** caminho, que não é o do contêiner —
ver [[#O caminho do go-live no Windows]] logo abaixo. Os dois convivem porque
respondem a perguntas diferentes: o de cima é "como isto roda numa PaaS", o de
baixo é "como isto sobe **hoje**, na máquina que a Bio Mundo tem".

## A imagem

Duas etapas. A primeira compila e precisa de tudo — TypeScript, CLI do Prisma,
dependências de desenvolvimento. A segunda leva só o que roda: **não vai
compilador nem código-fonte para produção**.

```
build   → npm ci → prisma generate → tsc → npm ci --omit=dev
runtime → node_modules + dist + prisma/ + prisma.config.ts
```

Três detalhes que não são acidente:

- **`prisma generate` antes do `tsc`.** O cliente do Prisma é gerado, não
  versionado (`src/generated/` está no `.gitignore`). Sem esse passo o `tsc` não
  acha os tipos.
- **`USER node`.** Não roda como root.
- **Sem `tini`/`--init`.** O [server.ts](../src/server.ts) já trata `SIGTERM`:
  para de aceitar conexão, deixa as requisições em voo terminarem e só então
  fecha o pool. Como o handler existe, o node como PID 1 encerra limpo.

> [!info] Por que o CLI do Prisma é dependência de produção
> `prisma` saiu de `devDependencies` para `dependencies` porque é ele que roda
> o `prisma migrate deploy` no `preDeployCommand` — a partir desta imagem. Sem
> isso, `npm ci --omit=dev` o removeria e a migração não teria como rodar.

## O caminho do go-live no Windows

Docker e Render descrevem um destino. O que foi efetivamente preparado para o
primeiro go-live é outra coisa: **dois processos Node numa máquina Windows**,
subidos por script. Os artefatos entraram no repositório em 2026-08-25.

| arquivo | o que faz |
| --- | --- |
| [run.bat](../run.bat) | confere o ambiente, prepara o banco e sobe os dois serviços |
| [parar.bat](../parar.bat) | derruba os dois, **por porta** |
| [servidor-painel.mjs](../servidor-painel.mjs) | serve o painel e repassa `/internal/*` para o bot |
| [GOLIVE.md](../GOLIVE.md) | o passo a passo operacional (é o README deste caminho) |
| `activity-dashboard/` | o painel, agora versionado **dentro deste repositório** |

| serviço | porta | quem precisa alcançar |
| --- | --- | --- |
| painel | **8511** | a Evolution e os atendentes, pelo túnel HTTPS |
| bot | 9511 | só o painel, por `127.0.0.1` |

Uma porta pública para os dois: o túnel entrega tudo na 8511 e o painel repassa
`/webhook/<segredo>` e `/internal/*` para o bot. A Evolution nunca fala com o bot diretamente,
e por isso a porta dele não precisa ser pública nem estável.

### As quatro decisões que valem mais que o script

**1. Um `.env` só.** Não existe `.env.producao` nem nada paralelo: o
`run.bat` e o `npm run dev` leem o mesmo arquivo. O que separa
desenvolvimento de produção é um bloco **MODO DE TESTE LOCAL** comentado no fim
dele — descomentar devolve porta 3000, credenciais de mentira e a
[[WA Ambiente local|Evolution de mentira]]. Funciona porque o dotenv fica com a
**última** ocorrência de cada chave. Ver [[WA Configuração#Um arquivo só, e um bloco que o inverte]].

**2. A porta sai do `.env`, não do script.** Tanto o `run.bat` quanto o
`parar.bat` leem `PORT=` do arquivo. Fixar 9511 no script criaria o pior
desencontro possível — o bot numa porta e o health check, o proxy do painel e a
Evolution olhando para outra — e ele apareceria só depois de a Evolution já estar
apontada para a máquina.

**3. `parar.bat` mata por porta, nunca por `node.exe`.** Um
`taskkill /IM node.exe` levaria junto o `npm run dev`, o editor e qualquer
outro Node aberto na máquina.

**4. O script falha antes de subir meio serviço.** Node ausente ou < 24, `.env`
com `PREENCHER_`, porta ocupada, `prisma migrate deploy` reprovado, build
quebrado — cada um interrompe tudo com a instrução do que fazer. Depois de subir
o bot ele **espera o `/health`** e só então consulta o `/ready`; o painel só
sobe se o bot respondeu, porque um painel sem bot só mostraria erro de conexão.

> [!important] O painel não fala com a porta 9511 direto
> O `servidor-painel.mjs` repassa `/internal/*` para `127.0.0.1:9511`, e é
> isso que tira o CORS do caminho: para o navegador, painel e API estão na
> **mesma origem**. Sem o proxy, `PAINEL_ORIGENS` teria de listar de antemão
> todo endereço pelo qual alguém fosse abrir o quadro — localhost, o IP da
> máquina na rede, o domínio — e qualquer um que faltasse quebraria a tela com
> um erro que o navegador se recusa a explicar. Ver [[WA Painel de chamados#CORS]].

> [!warning] Docker e Render **não** incluem o painel
> O [Dockerfile](../Dockerfile) copia arquivo por arquivo (`src`, `prisma`,
> `sql`) e não pega `activity-dashboard/` nem os `.bat`. A imagem continua
> sendo só o bot. Os dois caminhos não se atrapalham, mas também não são
> intercambiáveis: quem subir pelo contêiner **não** ganha o quadro de chamados
> junto.

> [!danger] O `run.bat` não é serviço do Windows
> Se a máquina reiniciar, alguém precisa rodá-lo de novo. Para sobreviver a um
> reboot, registrar no Agendador de Tarefas com gatilho "ao iniciar o sistema".
> Está em [[WA Pendências#Higiene (não bloqueia o lançamento)]].

## Health checks: dois, e não é redundância

| rota | quem pergunta | pergunta |
| --- | --- | --- |
| `/health` | o orquestrador (`HEALTHCHECK` do Docker) | o processo está vivo? |
| `/ready` | o balanceador (`healthCheckPath` do Render) | esta instância consegue atender? |

O `/health` **não toca o banco** de propósito. Reiniciar o contêiner porque o
banco está inacessível não conserta o disco — só tira mais uma instância do ar.
Quem reage a isso é o `/ready`, tirando a instância de rotação até o banco voltar.

Com SQLite o modo de falha típico não é rede, é **disco**: volume não montado,
cheio, ou com permissão errada. O processo sobe perfeitamente nesses casos e só a
escrita falha — que é exatamente o que o `/ready` pega.

## Render

O [render.yaml](../render.yaml) descreve o serviço e o **disco** onde o banco vive.
Não há mais bloco `databases:`: o banco é um arquivo SQLite dentro do disco
montado.

```yaml
disk:
  name: dados
  mountPath: /app/dados
  sizeGB: 1

envVars:
  - key: DATABASE_URL
    value: file:/app/dados/whatsapp-suporte.db

preDeployCommand: npm run prisma:deploy && npm run db:view
healthCheckPath: /ready
```

A migração roda **antes** de a versão nova passar a atender: se falhar, o Render
aborta e a versão antiga continua no ar.

> [!danger] O `DATABASE_URL` tem de apontar para DENTRO do disco montado
> Se apontar para fora, o banco vive na camada de escrita do contêiner e é
> **apagado no próximo deploy** — sem erro nenhum, sem aviso nenhum. O
> `mountPath` e o caminho do `DATABASE_URL` andam juntos: mexer em um sem o outro
> é a forma mais fácil de perder tudo.

> [!warning] Serviço com disco não faz deploy sem downtime
> O contêiner antigo precisa liberar o disco antes de o novo montá-lo. São alguns
> segundos de indisponibilidade em cada deploy. Nenhuma mensagem se perde — a
> entrega do webhook é "pelo menos uma vez" e o que cair no intervalo é
> reentregue — mas ela chega com atraso.

> [!danger] Backup deixou de ser automático
> O Postgres gerenciado fazia backup; **disco não faz**. O banco é um arquivo com
> dado pessoal de gente real. Agende `VACUUM INTO` — ver
> [[WA Banco de dados#Backup]].

> [!warning] `TRUST_PROXY=1` é obrigatório atrás do Render
> Sem isso **todo** request aparece com o IP do proxy e o rate limit por IP vira
> um contador global. E o contrário também é armadilha: não ligue `TRUST_PROXY`
> se o processo estiver exposto direto na internet, aí qualquer um forja o
> header e escapa do limite. Ver [[WA Configuração]].

Segredos usam `sync: false`: o Render pede o valor no painel na primeira
implantação e **nada disso passa pelo repositório**.

## Antes da primeira implantação

- [ ] Conferir que o `DATABASE_URL` aponta para dentro do `mountPath` do disco.
- [ ] Conferir que o `preDeployCommand` inclui `npm run db:view` — `prisma migrate`
      não gerencia view. Ver [[WA Banco de dados]].
- [ ] **Agendar backup** do arquivo (`VACUUM INTO`) — não existe mais backup
      automático de banco gerenciado. Ver [[WA Banco de dados#Backup]].
- [ ] Definir `RETENCAO_MENSAGENS_DIAS` e `RETENCAO_CHAMADOS_DIAS` — sem elas
      **nada é apagado**. Ver [[WA Segurança e LGPD]].
- [ ] Agendar `npm run retencao -- --confirmar` num cron, e um `VACUUM`
      periódico depois dele (apagar linha não devolve espaço ao disco).
- [ ] Conferir a data de expiração da `GRAPH_API_VERSION` em uso.

## Escalar para mais de uma instância

> [!danger] Com SQLite, não escala — e não é questão de configuração
> O banco é um arquivo que aceita **um escritor**. Duas instâncias montando o
> mesmo disco brigam pelo lock de escrita, e o mutex que serializa as transações
> vive dentro do processo, então não atravessa instâncias. Não declare
> `numInstances` maior que 1 e não ligue autoscaling.
>
> Subir a segunda instância é **trocar de banco** — voltar para um servidor
> (Postgres, MySQL) ou algo como o LiteFS/Turso, com tudo que a versão em Postgres
> tinha e que saiu junto: `pg_advisory_xact_lock` no handler,
> `SELECT ... FOR UPDATE` no endpoint interno e `FOR UPDATE SKIP LOCKED` na
> outbox. Ver [[WA Banco de dados#Um escritor por banco]].

O que **já está pronto** para o dia dessa troca:

- **os limites por telefone.** `throttle.ts` (mensagens/min por telefone) e
  `indisponibilidade.ts` (1 aviso por telefone a cada 10 min) leem de
  [[WA Arquitetura#Estado compartilhado entre instâncias|estado/janelas.ts]]:
  basta definir `REDIS_URL` e os dois valem para a frota. Sem ela o estado é do
  processo e cada limite vira **N × o configurado**, sem nada quebrar e sem nada
  avisar. A linha de boot diz em qual modo o processo está ("compartilhados no
  Redis" ou "em memória").
- **a reserva da outbox**, que já é uma instrução atômica e só precisaria do
  `SKIP LOCKED` de volta para não entregar a mesma linha a duas instâncias. Ver
  [[WA Outbox e entrega]].
