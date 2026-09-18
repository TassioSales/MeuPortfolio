---
tags: [projeto/whatsapp-suporte, pendencias, backlog]
projeto: whatsapp-suporte
atualizado: 2026-08-27
---

# WA Pendências

Volta para [[WhatsApp Suporte]].

O que **ainda falta**, em ordem de quem bloqueia o quê. Cada item diz de quem é a
decisão: `[negócio]` depende de você definir, `[técnico]` é trabalho de código,
`[operação]` é ambiente/infra.

As seções não são todas iguais, e a diferença importa mais que a ordem dentro de
cada uma:

| seção | o que significa |
| --- | --- |
| Bloqueiam ir para produção | tem marco esperando em [[WA Lançamento]] |
| Janela que fecha em 28/08 | não bloqueia nada, mas **encarece** depois da data |
| O painel: o que ainda falta nele | ele entrou neste repositório; o que resta é funcionalidade, não versionamento |
| Dívida técnica conhecida | sem data; entra quando alguma condição virar |
| Higiene | real, mas nenhum marco espera |
| Melhorias de produto | ideias, sem compromisso |

## Bloqueiam ir para produção

- [ ] **Definir o prazo de retenção dos CHAMADOS** `[negócio]` — *metade deste
      item foi resolvida em 2026-08-26.* O `.env` passou a trazer
      `RETENCAO_MENSAGENS_DIAS=1827` (5 anos), mas
      `RETENCAO_CHAMADOS_DIAS` continua **0**: chamado nenhum é descartado, e
      o chamado é justamente onde moram nome e texto livre. Ver
      [[WA Segurança e LGPD]] e [[WA Configuração]].

      > [!note] O que essa mudança alterou de verdade
      > `npm run retencao` deixou de ser um no-op. Que nada seja apagado hoje
      > é consequência de não existir dado com 5 anos — é calendário, não
      > mecanismo desligado. A diferença aparece sozinha daqui a cinco anos, ou
      > no dia em que alguém baixar esse número.
- [ ] **Ligar a instância da Evolution** `[operação]` — *substituiu o item do
      app na Meta em 2026-09-17, quando o projeto trocou de provedor.* O código
      está migrado e testado (357 testes, conversa ponta a ponta), mas contra a
      **Evolution de mentira**. O que **não** dá para confirmar lendo o disco:
      - a instância conectada a um número
        (`GET /instance/connectionState/<instancia>` tem de dizer `open`);
      - a URL do webhook cadastrada como `https://DOMINIO/webhook/<segredo>`,
        com o segredo igual ao `WEBHOOK_SEGREDO` que o processo carregou;
      - o evento `MESSAGES_UPSERT` marcado — é o erro mais comum e o mais
        silencioso, porque **não existe handshake**: a Evolution não valida a
        URL ao salvar, ela só começa (ou não) a postar;
      - se alguma mensagem real já foi e voltou.

      `node diagnostico.mjs` fecha os três primeiros; só a conversa ponta a ponta
      fecha o quarto. Passo a passo em [GOLIVE.md](../GOLIVE.md); o caminho sem
      instância continua em [[WA Ambiente local]].
- [ ] **Redeploy do `servidor-painel.mjs` no servidor** `[operação]` — *aberto em
      2026-09-17.* A versão no ar casa `/webhook` **exato**, e o segredo agora vai
      no caminho: ela manda `/webhook/<segredo>` para a tela de login do Entra
      (302). Confirmado pelo `diagnostico.mjs` contra o domínio de produção.
      Enquanto não subir a versão nova, **nenhuma mensagem chega**, e sem erro em
      lugar nenhum. Ver [[WA Implantação]].
- [ ] **Limpar as credenciais da Meta do `.env`** `[operação]` — *aberto em
      2026-09-17.* `META_APP_SECRET`, `WHATSAPP_TOKEN` e
      `WHATSAPP_PHONE_NUMBER_ID` continuam no arquivo com valor real, e o código
      não lê mais nenhuma delas. Segredo que ninguém usa é só risco parado:
      apagar as três linhas e, já que estiveram em disco, revogar o token no
      painel da Meta.
- [ ] **Configurar `ALERTA_WEBHOOK_URL`** `[operação]` — o mecanismo entrou em
      2026-08-19 e está testado, mas **desligado**: a variável não está definida
      em lugar nenhum, então hoje desistir de uma mensagem continua só virando
      linha de log. Precisa de um webhook de Slack ou Discord criado e a
      variável no ambiente. É a mesma forma do item de retenção — mecanismo
      pronto, decisão de operação faltando. **M2 (31/08) exige isto no ar.**
      Ver [[WA Outbox e entrega]].
- [ ] **Agendar `npm run retencao`** `[operação]` — falta só o cron. O
      argumento que segurava este item ("agendar antes de decidir os prazos é
      agendar um no-op") **enfraqueceu em 2026-08-26**: com
      `RETENCAO_MENSAGENS_DIAS=1827` o script já tem o que apagar em tese, e o
      que o mantém inócuo hoje é só a idade do dado. Continua fazendo sentido
      esperar o prazo dos chamados antes de agendar — mas agora por economia de
      um passo, não porque o script seja inofensivo. As sessões abandonadas
      seguem sendo varridas dentro do processo por `iniciarLimpezaDeSessoes`, no
      boot e a cada `LIMPEZA_SESSOES_MINUTOS`, independentemente do cron. A view
      saiu desta lista: `npm run db:view` a aplica e já roda no
      `preDeployCommand`. **Entrou um vizinho**: com SQLite, apagar linha não
      devolve espaço ao disco, então o cron da retenção pede um `VACUUM`
      periódico junto. Ver [[WA Banco de dados]].

## Janela que fecha em 28/08 — migrações que só são baratas com tabela vazia

> [!warning] Isto tem data, e a data é a de M1
> Estas duas mudanças foram avaliadas em 2026-08-18 e adiadas conscientemente,
> **sob uma condição explícita: fazer enquanto as tabelas estiverem vazias.**
> Em 2026-08-19 a condição ainda vale — `Chamado` 2, `Mensagem` 23,
> `SessaoConversa` 0, `MudancaSituacao` 0, tudo dado de teste, e o provedor de
> WhatsApp ainda não configurado.
>
> **M1 ("primeira mensagem real") é 28/08.** Depois disso a condição deixa de
> valer e o custo das duas passa de trabalho mecânico contra volume zero para
> uma janela de manutenção com dado de gente de verdade dentro. Ver
> [[WA Lançamento]].

Nenhuma das duas resolve um problema que exista hoje — o que decide não é
urgência, é o preço, que só sobe. Se a janela passar sem elas, o certo é mover
as duas de volta para dívida técnica e parar de olhar até haver manutenção
programada.

- [ ] **Identificadores em `snake_case`** `[técnico]` — o schema usa o padrão do
      Prisma, `"Mensagem"`, `"enviadaEm"`, e identificador com maiúscula exige
      aspas em SQL crua **para sempre**. O custo é pago em toda query crua e em
      toda sessão de `sqlite3`. Resolve-se com `@@map`/`@map`, sem tocar o
      código TypeScript — mas a migração renomeia todas as tabelas e colunas, e
      obriga a reescrever a SQL de [outbox.ts](../src/whatsapp/outbox.ts) e a
      view de cards. (A de [chamados.ts](../src/internal/chamados.ts) saiu de
      cena na troca para SQLite: virou um `findUnique`.)
      **No SQLite o preço subiu:** renomear coluna é recriar a tabela, copiar e
      apagar a antiga — o que com tabela vazia é trivial e com dado dentro é uma
      janela de manutenção de verdade.
- [ ] **`bigint generated always as identity` nas PKs** `[técnico]` — hoje as
      PKs são `SERIAL`, que é `int` e para em 2,1 bilhões. Irrelevante no volume
      atual, e `Chamado` nunca chegará perto. A tabela onde o teto é ao menos
      concebível é `Mensagem`: ela cresce a **cada** mensagem recebida e a cada
      resposta enviada, incluindo as retentativas de outbox.

> [!note] Se for fazer, faça as duas juntas
> Numa migração só, e antes de 28/08. As duas mexem nas mesmas tabelas e a
> segunda pega carona no downtime da primeira; separá-las paga o custo duas
> vezes. Depois: `npm run dev:verificar-banco` obrigatório — as duas reescrevem
> SQL cru, que é exatamente a classe de mudança que os testes em memória não
> pegam.

## O painel: o que ainda falta nele

O quadro de cards **entrou neste repositório** em 2026-08-25, em
`activity-dashboard/`, e é essa cópia que o `run.bat` sobe. Versionamento e
cópias soltas deixaram de ser problema em 2026-08-26 — ver
[[#Fechados em 2026-08-26]]. O que sobrou aqui é funcionalidade.

- [ ] **O painel não manda `autor`** `[técnico]` — `moverChamado` em
      [api.js](../activity-dashboard/api.js) posta só `situacao` e
      `notificarUsuario`. O `PATCH` aceita `autor` desde 2026-08-19, então toda
      mudança feita **pelo painel** nasce com `autor: null` — a auditoria
      registra o quê e o quando, mas nunca o quem. (Conferido em 27/08/2026: a
      única linha de `MudancaSituacao` no banco local TEM autor — foi escrita à
      mão, por um `PATCH` que mandou o campo. Nenhuma veio do painel ainda, e é
      por isso que a frase anterior, "toda linha está nascendo com autor null",
      era contrariada pelo próprio banco.) Falta o painel ter uma noção
      de quem está atendendo: hoje ele só tem token, não tem identidade. O
      caminho mais curto é pedir o nome uma vez e guardar junto das prefs (o
      `api.js` já faz isso para a preferência de aviso).
- [ ] **O painel não lê `/internal/chamados/:id/historico`** `[técnico]` — a rota
      existe e devolve de/para/autor/quando; nada na tela mostra isso ainda.
      Depende do item acima para valer alguma coisa. Ver
      [[WA Painel de chamados]].

## Dívida técnica conhecida

- [ ] **`removeAdditional` nas rotas de PATCH antigas** — `categorias.ts` e
      `pessoas.ts` declaram `additionalProperties: false` + `minProperties: 1` e
      têm a mesma brecha que as rotas novas tiveram: campo desconhecido é removido
      pelo AJV, o corpo chega vazio ao handler e a resposta é 200 sem ter gravado
      nada. Não foi corrigido porque os campos daquelas duas são poucos e
      conhecidos, mas passa a valer se alguém acrescentar campo lá. A correção é a
      mesma: conferir se sobrou campo antes de escrever. Ver
      [[WA Classificação de chamados#Uma armadilha do Fastify que este trabalho revelou]].

- [ ] **Sem detecção de ciclo longo em dependências** — A→B→C→A é aceito. O ciclo
      de dois é recusado (409) porque é o erro que se comete sem perceber;
      percorrer o grafo a cada inserção para pegar os longos não se pagou, já que o
      estrago deles é uma leitura confusa e não um travamento.

- [ ] **Eliminação (LGPD) não alcança os campos de contato digitados** — `contato`
      e `franqueadoContato` são dado pessoal e vivem em chamados que podem não ter
      telefone, então `npm run retencao -- --esquecer <telefone>` não os encontra.
      Hoje só o prazo de retenção de chamados os remove. Se passar a ser
      necessário, é uma rota de eliminação nova, não um ajuste no script.

- [ ] **ESLint continua bloqueado pelo TypeScript 7** `[técnico]` — o Prettier
      entrou (`npm run format`, checado no CI), mas o ESLint não: o
      `typescript-eslint` 8.68 declara `typescript >=4.8.4 <6.1.0` e o projeto
      está no **7.0.2** (faixa reconferida em 27/08/2026: não mudou). Instalar exigiria `--legacy-peer-deps`, o que deixaria o
      `npm ci` do CI dependendo de um lockfile inconsistente. Reavaliar quando o
      `typescript-eslint` anunciar suporte a TS 7.
- [ ] **Índice parcial para o varredor** `[técnico]` —
      `Mensagem(remetente, enviadaEm, timestamp)` serve bem, mas
      `WHERE remetente = 'sistema' AND "enviadaEm" IS NULL` cobriria uma fração
      das linhas. Prisma não declara índice parcial: teria de viver numa migração
      à mão, e o `migrate dev` tentaria removê-lo. Só vale quando `Mensagem`
      ficar grande. Ver [[WA Banco de dados]].

## Higiene (não bloqueia o lançamento)

Coisas reais, mas que nenhum marco espera para **ir ao ar**. Ficam separadas
para não competirem com o que tem data — o M0 de [[WA Lançamento]] lista a senha
como pré-requisito de ambiente, e é correto: o que ela destrava é compartilhar a
máquina, não subir para produção.

- [x] **~~Rotacionar a senha do Postgres local~~** — **sem objeto desde
      2026-08-27**: o banco passou a ser SQLite e não tem senha nenhuma. A senha
      antiga, que estava em texto claro no `.env` e apareceu em transcrição de
      chat, deixou de dar acesso a este projeto (rotacioná-la ainda vale se
      aquele Postgres for usado por outra coisa).
- [ ] **Backup do arquivo do banco** `[operação]` — **entrou em 2026-08-27, junto
      com o SQLite.** O Postgres gerenciado do Render fazia backup automático;
      disco não faz. O banco é um arquivo com dado pessoal de gente real, e hoje
      não existe cópia de segurança nenhuma. O caminho é
      `sqlite3 <banco> "VACUUM INTO 'backup.db'"` num cron (nunca `cp`, que perde
      o `-wal`), com o backup tratado como dado pessoal também. **Bloqueia uso com
      dado real tanto quanto a retenção bloqueia.** Ver
      [[WA Banco de dados#Backup]].
- [ ] **O `run.bat` não sobrevive a um reboot** `[operação]` — ele não se
      registra como serviço do Windows. Se a máquina reiniciar, bot e painel
      ficam fora do ar até alguém rodá-lo de novo — e ninguém é avisado, porque
      o alerta da outbox depende do processo estar vivo. O caminho barato é o
      Agendador de Tarefas com gatilho "ao iniciar o sistema". Vira urgente no
      dia em que a Evolution estiver apontada para a máquina. Ver
      [[WA Implantação#O caminho do go-live no Windows]].
- [x] **~~O usuário de leitura da view nunca foi criado~~** — **deixou de ser
      possível em 2026-08-27**: SQLite não tem usuário nem `GRANT`, então não há
      papel a criar. A defesa em profundidade que estava descrita — plataforma de
      cards lendo `chamados_para_cards` com um papel restrito a `SELECT` — não é
      mais alcançável por esse caminho, e a documentação foi corrigida para não
      prometê-la.
- [ ] **Definir como um segundo consumidor lerá os cards** `[técnico]` — sucessor
      do item acima, e ainda aberto. Com o controle de acesso reduzido à permissão
      do arquivo, sobram dois caminhos: a rota `/internal/chamados` (mesma
      minimização de campos, com token — é o que o painel já usa) ou entregar uma
      **cópia** do arquivo aberta em modo `readonly`. Só passa a valer quando
      existir de fato um segundo consumidor. Ver [[WA Segurança e LGPD]].

## Melhorias de produto (sem bloqueio)

- [ ] **Descrição em várias mensagens** — hoje a descrição é uma mensagem só;
      permitir concatenar até o usuário dizer que terminou.
- [ ] **Reaproveitar o nome do último chamado** do mesmo telefone, em vez de
      perguntar de novo a cada abertura.
- [ ] **Anexo vindo da CONVERSA** — o chamado já aceita anexo pelo painel
      (`POST /internal/chamados/:id/anexos`, binário em `Anexo.conteudo`), mas a
      imagem que o usuário manda no WhatsApp continua recebendo só a resposta
      explicando a limitação. Ligar as duas pontas é baixar a mídia pela Evolution
      dentro do fluxo da conversa e gravá-la na tabela que já existe. Áudio
      exigiria transcrição, o que traria IA para um projeto que hoje não tem
      nenhuma.
- [ ] **Teste de carga** — os limites (rate limit, `ENVIO_SINCRONO_MS`) foram
      raciocinados a partir do comportamento do provedor, nunca medidos. Ver
      [[WA Testes e verificação]].

## Fechados em 2026-08-31

- [x] **Campos de separação e classificação de chamado** — o pedido trouxe quatro
      listas (comuns, interno, franquia, e três obrigatórios) e todas entraram.
      Migração `20260831135505_classificacao_de_chamados`: 24 colunas em `Chamado`
      e cinco tabelas (`Setor`, `Comentario`, `Anexo`, `Tag`, `Dependencia`).

      As decisões que valem ser lembradas, todas em
      [[WA Classificação de chamados]]:

      - **Assunto e setor são eixos diferentes** e ficaram em tabelas diferentes.
        `Categoria` continua sendo o menu que o cliente lê no WhatsApp; `Setor` é a
        área interna que atende, e nunca aparece na conversa. Juntar as duas faria
        "TI" e "Financeiro" aparecerem como opção para o cliente.
      - **`tipo` nasce nulo** e um atendente classifica no painel. O fluxo da
        conversa NÃO ganhou pergunta nova — cada etapa custa uma mensagem por
        atendimento, e quem atende descobre o tipo em dois segundos lendo o resumo.
      - **Três escalas separadas** (prioridade técnica, impacto no negócio,
        urgência comercial), porque o pedido nomeou a razão: loja parada é
        diferente de dúvida sobre material.
      - **`canal` e `origem` coexistem**: um é por onde o pedido chegou, o outro é
        por qual porta a linha do banco nasceu.
      - **Comentário interno não mora em `Mensagem`.** Se morasse, a varredura da
        outbox despacharia a nota interna para o cliente. Há teste de regressão.
      - **Anexo em BLOB no SQLite**, e não em pasta ao lado: o banco é um arquivo
        que o backup leva inteiro, e o `CASCADE` da retenção passa a apagar o
        anexo de verdade. O preço é o `.db` crescer — limitado por
        `ANEXO_MAX_BYTES`.

- [x] **Chamado passou a ter responsável** — `Chamado.responsavelId` aponta para
      `Pessoa`, com `onDelete: SetNull`. O comentário no schema dizia o contrário
      ("chamado não tem responsável, só solicitante. Criar a chave estrangeira
      agora seria desenhar para uma regra que ainda não existe") e era verdade
      enquanto a regra não existia; ela passou a existir. As bolhas de perfil da
      barra de filtros, que estavam ocultas por não terem coluna atrás, voltaram
      a filtrar.

- [x] **O resumo ganhou dois cortes** — `GET /internal/metricas` devolve
      `porCategoria`, `porSetor` e `porTipo`. **Quebra de contrato:** a linha de
      métrica passou a se chamar `id` no lugar de `categoriaId`, porque a mesma
      linha agora descreve grupo de assunto, de setor e de tipo. O único consumidor
      era o painel, que não lia o campo.

- [x] **`additionalProperties: false` não recusava campo desconhecido** — o
      Fastify roda o AJV com `removeAdditional`, então o campo era removido e a
      requisição seguia; `minProperties` não salvava porque o AJV conta as
      propriedades antes de remover. Um `PATCH` com nome de campo digitado errado
      respondia 200 com o chamado inteiro. Corrigido nas duas rotas novas com uma
      conferência de corpo vazio no handler. **`categorias.ts` e `pessoas.ts` têm a
      mesma forma** — ver o item em *Dívida técnica conhecida*.

## Fechados em 2026-08-27

- [x] **O banco passou de Postgres para SQLite** — um arquivo em
      `dados/whatsapp-suporte.db`, pelo adaptador
      `@prisma/adapter-better-sqlite3`. Sai um serviço para instalar, subir,
      autenticar e manter; sai o `services: postgres` do CI; saem `DB_POOL_*`,
      `VIEW_ROLES_LEITURA` e a senha de banco. Ver [[WA Banco de dados]].

      Três locks explícitos foram embora **sem substituto**, porque o SQLite
      aceita um escritor por banco e o adaptador serializa as transações do
      processo num mutex: o `pg_advisory_xact_lock` do handler, o
      `SELECT ... FOR UPDATE` do endpoint interno (virou `findUnique` dentro da
      mesma transação) e o `FOR UPDATE SKIP LOCKED` da reserva da outbox. As 29
      checagens do `dev:verificar-banco` provam que o efeito observável não mudou.

      **O que a troca custou, e vale ter na frente dos olhos:** uma instância
      deixou de ser escolha e virou limite do desenho; o deploy no Render passa a
      ter janela de indisponibilidade (disco não faz deploy sem downtime); backup
      deixou de ser automático (item aberto em *Higiene*); e a view de cards
      deixou de ser fronteira de permissão, virando só contrato de leitura.

      As quatro migrações do Postgres foram substituídas por uma baseline SQLite
      única — o SQL antigo não roda aqui. **Dados não são migrados
      automaticamente.**

## Fechados em 2026-08-17

- [x] **Bug de fuso no varredor da outbox** — corrigido e provado ao vivo:
      [[WA Fuso horário sem timezone]].
- [x] **Colunas `DateTime` migradas para `timestamptz`** — as 7 colunas de data
      convertidas preservando o instante gravado (migração
      `20260817190000_datas_com_fuso`), schema com `@db.Timestamptz(3)`, SQL da
      outbox voltando a comparar com `now()` puro. A classe de bug deixou de ser
      possível em vez de corrigida em um ponto. Verificado: 85 testes + 20
      checagens de banco, sem drift, recuperação real medida de novo em +65s.
      **Deixa uma pendência de operação:** o `GRANT` da view, acima.
- [x] **Dublê do Prisma ignorava o `LIMIT` da reserva** — recebia a base do
      backoff (30) no lugar do limite pedido. Sem efeito nos testes atuais
      (nenhum chega a 20 pendentes), mas faria um teste de limite passar em falso.
- [x] **As quatro garantias que "precisavam de teste manual"** — automatizadas em
      `npm run dev:verificar-banco`, 20 checagens. Ver [[WA Testes e verificação]].
- [x] **Simulador frágil** — um comando que falhava encerrava a conversa inteira;
      agora cada comando pré-checa só o que precisa e erra com mensagem
      acionável.
- [x] **Banco local de verdade** — Postgres 18, banco `whatsapp_suporte`,
      baseline aplicada, fluxo completo exercitado ponta a ponta.

## Fechados em 2026-08-18

- [x] **Projeto em git** — repositório iniciado, histórico com um commit por
      assunto. Falta só o remoto (acima).
- [x] **Dependências e runtime uma major atrás** — Node 20 (fora do LTS desde
      abril/2026) → 24; Fastify 4 → 5; Prisma 5 → 7; TypeScript 5.9 → 7;
      `@fastify/rate-limit` 9 → 11; dotenv 16 → 17. `ts-node-dev` saiu de cena
      (depende da API antiga do compilador) e entrou `tsx`.
- [x] **`GRAPH_API_VERSION` apontando para uma versão quase expirada** — a
      `v20.0` expira em **24/09/2026**. Padrão agora é `v25.0` (expira
      29/07/2028), com as datas registradas no código e na documentação.
- [x] **Pool de conexões sem teto** — era `new PrismaClient()` puro. Agora
      `DB_POOL_MAX`/`DB_POOL_TIMEOUT_MS`/`DB_POOL_IDLE_MS`, pelo driver adapter
      do Prisma 7. Ver [[WA Configuração]].
- [x] **`retencao.ts` sem nenhum teste** — 14 casos novos, incluindo a trava de
      que a simulação não apaga nada e a de que eliminar um titular não toca em
      outro. **Encontrou um bug:** a simulação contava menos do que o
      `--confirmar` apagava (não contava as mensagens que somem junto com o
      chamado). Ver [[WA Segurança e LGPD]].
- [x] **Regressão de fuso trazida pelo Prisma 7** — o driver adapter não fixa a
      sessão em UTC como o motor antigo fazia. Corrigido no pool e com checagem
      de guarda no CI: [[WA Fuso horário sem timezone]].
- [x] **Nada para implantar** — Dockerfile, `.dockerignore`, `.nvmrc` e
      `render.yaml`. Ver [[WA Implantação]].
- [x] **CI que não rodava as checagens de banco** — job novo com
      `services: postgres`, aplicando as migrações de verdade. A afirmação de
      que "não dá para colocar no CI sem um Postgres" estava errada. Ver
      [[WA Testes e verificação]].
- [x] **Rotas sem schema** — o endpoint interno valida por JSON Schema em vez de
      dois `if` no handler, e a autenticação passou para `onRequest` (validação
      roda **depois** do `preHandler`, então quem não tinha token recebia 400 com
      a lista de situações aceitas antes do 401).
- [x] **Sem `setErrorHandler`/`setNotFoundHandler` e sem helmet** — exceção
      inesperada saía no formato padrão do Fastify, com a mensagem do erro; erro
      do Prisma carrega os parâmetros da query, ou seja telefone e texto.
- [x] **429 ignorava o `Retry-After`** — agora obedece o que a Meta pede (em
      segundos ou data HTTP), com teto de 60s para não segurar a execução.
- [x] **Reentrega consumia cota do telefone** — a mensagem descartada como
      duplicata devolve a cota. Uma rajada de reentregas comia o limite de um
      usuário legítimo.

## Fechados em 2026-08-19

- [x] **`GRANT` da view virou passo automático** — `npm run db:view` aplica
      `sql/view_chamados_para_cards.sql` e REAPLICA o `GRANT` para os papéis de
      `VIEW_ROLES_LEITURA` (papel inexistente é ignorado, então roda igual em
      produção e na máquina do desenvolvedor). Entrou no `preDeployCommand` do
      Render junto do `prisma:deploy` e num passo do CI. Deixa de ser "lembrar
      de rodar à mão depois da migração" — que era como o painel perdia acesso
      em silêncio. Ver [[WA Banco de dados]].
- [x] **Histórico de mudanças de situação** — tabela `MudancaSituacao` (de,
      para, autor, criadoEm), gravada DENTRO da mesma transação e do mesmo
      `FOR UPDATE` do PATCH: ou a situação muda e fica registrada, ou nada
      acontece. PATCH que repete a situação atual não vira linha. Leitura em
      `GET /internal/chamados/:id/historico`, sem telefone (mesma minimização da
      listagem). `ON DELETE CASCADE` de propósito, para a retenção (LGPD)
      continuar apagando chamado antigo sem esbarrar na FK — provado contra
      Postgres de verdade. Ver [[WA Painel de chamados]].
- [x] **O menu de edição saiu do teto de 3 botões** — `corpoEscolha` escolhe o
      formato pelo número de opções: até 3 continuam botões, de 4 a 10 viram
      **lista**. Acrescentar um campo em `CAMPOS` passou a ser só acrescentar um
      campo. O webhook agora lê `list_reply` além de `button_reply` — sem isso o
      bot responderia "só consigo ler texto" a quem usou o menu que ele mesmo
      mandou. Ver [[WA Fluxo da conversa]].
- [x] **Alerta no descarte de mensagem** — `ALERTA_WEBHOOK_URL` (Slack, Discord
      ou qualquer coletor de JSON) é avisado quando a outbox desiste, que é o
      único evento do sistema em que uma pessoa real ficou sem resposta. Com
      janela de coalescência, porque numa queda longa da Evolution todas as
      pendentes desistem juntas e um canal com centenas de avisos iguais é um
      canal que ninguém lê. **Não leva telefone nem texto**: o destino é um
      canal de equipe, fora da retenção deste sistema. Desligado por padrão.
      Ver [[WA Outbox e entrega]].
- [x] **Prettier** — `npm run format`, `npm run format:check` no CI. Escopo só
      de código: a documentação fica de fora (é Markdown escrito à mão, e
      reflowar tabela de Obsidian é churn puro). O ESLint não veio junto —
      continua bloqueado pelo TS 7, acima.
- [x] **`SESSAO_TTL_HORAS` aceitava só inteiro** — `SESSAO_TTL_HORAS=0.5` (meia
      hora, o valor natural para exercitar a expiração sem esperar) não era
      arredondado: derrubava o processo no boot com "precisa ser inteiro >= 1".
      Agora aceita fração.
- [x] **`.env.example` com valores de experimento** — o arquivo é o modelo que
      todo mundo copia, e tinha `SESSAO_TTL_HORAS=0.5` (que não subia),
      `RETENCAO_MENSAGENS_DIAS=3680` e `RATE_LIMIT_POR_MINUTO=300` gravados como
      se fossem padrão. Voltaram a ser exemplos comentados.

## Fechados em 2026-08-20

- [x] **Publicar o repositório num remoto** `[operação]` — feito: remoto privado
      `BioMundo/whatsapp-sup`. Era o item que travava o valor de todos os
      outros — enquanto ele estava aberto, o `ci.yml` era um arquivo de texto e
      esta nota afirmava cobertura automática que não existia.
- [x] **O CI estava vermelho desde a primeira execução** — o job `verificar`
      morria no `prisma:generate` com
      `PrismaConfigEnvError: Cannot resolve environment variable: DATABASE_URL`.
      Passava na máquina porque o `.env` supre a variável, e o `.env` não vai
      para o repositório. Efeito real: **`typecheck`, `build` e os 137 testes
      nunca executaram no CI** — o job morria três passos antes deles. O job
      `banco` não sofria, porque define `DATABASE_URL` no nível do job. Corrigido
      com `env` no passo (valor de fachada; `prisma generate` não abre conexão),
      deixando o `prisma.config.ts` intacto para não trocar o diagnóstico de
      produção pelo conforto do CI. História completa em
      [[WA Testes e verificação#Quando o CI passou a rodar de verdade]].
- [x] **Actions no runtime de Node depreciado** — `actions/checkout` e
      `actions/setup-node` subiram de `@v4` para `@v7`. As `v4` declaram
      `using: node20`; em **16/09/2026** o Node 20 sai do runner e elas param de
      rodar. Não era a causa da falha acima, e não tem relação com a versão de
      Node do projeto (essa vem do `.nvmrc` e estava certa).
- [x] **A primeira mensagem do usuário virava o nome** — encontrado no ensaio da
      apresentação (ver [[WA Demonstração]]): no primeiro contato a sessão nascia
      na etapa `nome` e o texto que chegou era gravado como nome, então quem
      abria com "oi" ficava com `nome="oi"` e todo o formulário deslizava um
      campo. No ensaio isso gerou um chamado com `nome="Bom dia, preciso de
      ajuda"` e `resumo="Natan Ferreira"`. A pergunta
      `Olá! Para abrir seu chamado, qual é o seu nome?` existia em `flows.ts` e
      só era alcançável por expiração, mídia ou edição — ou seja, nunca no
      caminho que todo usuário novo percorre. Agora `carregarSessao` distingue
      sessão **nova** de **reiniciada**, e a primeira mensagem recebe a pergunta
      sem ser consumida. Custa uma mensagem a mais por chamado e não exige
      adivinhar nada sobre o conteúdo. Dois testes novos cobrem o primeiro
      contato (a suíte passava porque o teste do fluxo feliz começava mandando
      `'Natan'`, que é um nome válido), e as checagens 1, 2 e 5 de
      `dev:verificar-banco` ganharam uma mensagem de aquecimento, porque mediam
      etapas contando a primeira mensagem como resposta.
      Ver [[WA Fluxo da conversa]].

## Fechados em 2026-08-24

- [x] **Estado em memória trocado por Redis** `[técnico]` — `throttle.ts` e
      `indisponibilidade.ts` deixaram de ter estado próprio e passaram a usar
      `src/estado/janelas.ts`, que tem duas implementações escolhidas no boot por
      `REDIS_URL`: memória (padrão, e o certo com uma instância) ou Redis. Era o
      que impedia escalar horizontalmente — com N instâncias cada limite virava
      **N × o configurado**, sem nada quebrar e sem nada avisar.
      Três decisões que valem mais que o código:
      **(1) opt-in.** Sem `REDIS_URL` nada muda e nenhuma dependência entra no
      caminho da requisição. Ligar Redis antes de haver segunda instância seria
      acrescentar um modo de falha a um sistema que ainda não mandou a primeira
      mensagem real.
      **(2) falha do Redis não desliga o limite** — ela cai para memória, ou
      seja, o limite volta a valer por instância. Fechar descartaria mensagem de
      gente real em silêncio; abrir removeria o único controle de abuso que
      existe depois da validação de assinatura.
      **(3) as operações são atômicas em Lua**, numa ida só. `INCR` seguido de
      `PEXPIRE` em dois comandos deixa a chave SEM prazo se o processo morrer
      entre eles, e aquele telefone ficaria bloqueado para sempre.
      O boot passou a registrar em qual dos dois modos subiu, porque essa é
      exatamente a classe de erro que não aparece sozinha. 15 testes novos
      (`test/janelas.test.ts`, com o dublê em `test/fake-redis.ts`), incluindo os
      dois caminhos de falha e uma prova de que as duas implementações concordam
      no mesmo roteiro. **O que o dublê não cobre está escrito nele**: a
      atomicidade real do Lua e a expiração pelo relógio do Redis precisam de um
      Redis de pé. Ver [[WA Arquitetura#Estado compartilhado entre instâncias]].

## Fechados em 2026-08-25

- [x] **Não havia como subir isto numa máquina** `[operação]` — existiam
      Dockerfile e `render.yaml`, ou seja um destino; não existia o caminho
      para o servidor que a Bio Mundo tem hoje. Entraram `run.bat`,
      `parar.bat`, `servidor-painel.mjs` e `GOLIVE.md`. O script não é um
      atalho: ele **recusa subir** com Node velho, `.env` por preencher, porta
      ocupada, migração reprovada ou build quebrado, e não deixa meio serviço no
      ar. Ver [[WA Implantação#O caminho do go-live no Windows]].
- [x] **O painel não estava em git** `[operação]` — era o item que dizia "um
      `rm` distraído leva 2.400 linhas". O quadro entrou neste repositório em
      `activity-dashboard/` e passou a ter histórico, remoto e CI junto com o
      bot. Ficou uma ponta solta — a cópia antiga seguia no vault e já havia
      divergido — resolvida no dia seguinte: ver [[#Fechados em 2026-08-26]].
- [x] **O painel dependia de `PAINEL_ORIGENS` acertar todo endereço**
      `[técnico]` — o `servidor-painel.mjs` repassa `/internal/*` para o
      bot, então painel e API ficam na mesma origem e o CORS sai do caminho. O
      quadro passou a funcionar por `localhost`, por IP da rede e por domínio
      sem reconfigurar nada. Ver [[WA Painel de chamados#Como o painel é servido]].

## Fechados em 2026-08-26

- [x] **Três cópias do projeto convivendo dentro do vault** `[operação]` —
      apagadas `Code/golive/` (pacote autocontido com bot, painel,
      `node_modules` e `.env` próprio, sem git e já defasado) e
      `Code/activity-dashboard/` (a cópia antiga do painel). Antes de apagar foi
      conferido que **nenhuma das duas tinha arquivo exclusivo**: todo caminho
      já existia na versão versionada, e o único texto próprio — o
      `golive/LEIA-ME.md` — havia sido substituído por inteiro pelo
      [GOLIVE.md](../GOLIVE.md).

      > [!info] O que isso corrigiu no Obsidian, e não só no disco
      > `golive/whatsapp-suporte/docs/` carregava uma cópia **congelada** das 16
      > notas `WA …`, e `Painel de Chamados` existia em **três** lugares. Nome
      > de nota duplicado deixa todo link interno ambíguo, e abrir a cópia velha
      > achando que é a viva não dá nenhum sinal de erro — 6 das 16 já
      > divergiam. Agora cada nota tem nome único no vault.

- [x] **O `GOLIVE.md` afirmava que a retenção estava desligada** — dizia
      "`RETENCAO_*_DIAS=0`: nada é apagado", enquanto o `.env` já trazia
      `RETENCAO_MENSAGENS_DIAS=1827`. Texto corrigido. A decisão que falta
      continua sendo a dos chamados, no topo desta nota.
- [x] **Dois wikilinks quebrados nas notas** — em
      [[WA Fuso horário sem timezone]], a âncora para a seção de reincidência
      estava escrita **sem os dois-pontos** que o heading real tem; e em
      [[WA Implantação]] um link estava partido em duas linhas dentro de um
      callout (o Obsidian não resolve link que atravessa quebra de linha).
      Os links do vault inteiro foram verificados depois: todos resolvem.

## Como retomar isto

O caminho crítico continua sendo o provedor de WhatsApp, e em 2026-09-17 ele
**mudou de dono**: saiu a Meta, entrou a Evolution API. O código está migrado e
testado; o que sobrou ali é a parte que depende do mundo — instância conectada,
webhook cadastrado com o segredo certo, `MESSAGES_UPSERT` marcado, o painel
novo no ar e uma conversa real que vá e volte. Em paralelo, na ordem:

1. **prazo de retenção dos chamados** `[negócio]` — a metade que falta do item
   mais antigo em aberto; destrava o cron do item 3;
2. **`ALERTA_WEBHOOK_URL`** `[operação]` — M2 (31/08) espera por isto, e é o
   único jeito de ficar sabendo que alguém escreveu e não foi respondido;
3. **cron da retenção** `[operação]` — depois do item 1.

O remoto do git saiu desta fila em 2026-08-20, e o do painel em 2026-08-25 —
ele passou a viver dentro deste repositório. As cópias soltas do projeto dentro
do vault saíram em 2026-08-26, apagadas.

Fora dessa fila, com relógio próprio: as duas migrações da **janela de 28/08**,
acima. Elas não bloqueiam nada e não resolvem nenhum problema de hoje — o que decide é
que o preço delas só sobe, e passa de mecânico para janela de manutenção assim
que chegar a primeira mensagem real.

Redis deixou de ser trabalho e virou configuração: o mecanismo está pronto e
testado, e `REDIS_URL` vazia mantém o comportamento de antes. Hoje o
`render.yaml` não declara `numInstances`, então é uma instância e memória é o
certo. Quem subir esse número precisa definir `REDIS_URL` no mesmo movimento —
senão os dois limites por telefone passam a valer por processo, sem nenhum aviso.
O `render.yaml` traz o bloco comentado e o aviso ao lado de onde a tentação mora.
Ver [[WA Arquitetura#Estado compartilhado entre instâncias]].

Depois de **toda** migração, rode `npm run db:view`. Em produção isso já está no
`preDeployCommand`; num banco que você migrou à mão, não está.

Antes de qualquer deploy que toque em transação ou SQL cru:
`npm run dev:verificar-banco` com o servidor de pé. Não é opcional — foi assim
que o bug de fuso apareceu, das duas vezes. Trocar driver, ORM ou **banco** conta
como tocar em SQL cru: foi por aí que ele voltou em 2026-08-18, e foi este comando
que validou a troca para SQLite em 2026-08-27. Desde 2026-08-18 o CI roda essa
verificação sozinho a cada push.
