# WhatsApp Suporte

Bot de suporte via WhatsApp que coleta dados de um chamado através de um fluxo
guiado (nome → resumo → descrição → confirmação) e salva tudo em um banco
SQLite, sem usar nenhum modelo de IA no caminho — cada resposta do usuário
vai direto para o campo correspondente, sem interpretação de conteúdo.

> Este README é a documentação de **uso**. Para consulta — por que cada decisão é
> assim, onde fica cada coisa e o que ainda falta — há um cofre de notas em
> [`docs/`](docs/WhatsApp%20Suporte.md) (feito para abrir no Obsidian, mas são
> arquivos Markdown comuns). O que está em aberto vive em
> [`docs/WA Pendências.md`](docs/WA%20Pend%C3%AAncias.md).

## Como funciona

1. O usuário manda uma mensagem no WhatsApp.
2. O webhook confere o segredo do caminho e identifica em qual etapa a conversa
   está (por telefone).
3. Dependendo da etapa, a resposta é salva no campo certo e a próxima pergunta
   é enviada.
4. Na etapa final, o bot mostra o que entendeu e o usuário confirma respondendo
   com o número da opção (confirmar, corrigir um campo, cancelar).
5. Ao confirmar, o chamado é criado na tabela `Chamado` com `situacao = aberto`.
6. Toda mensagem trocada (nos dois sentidos) fica registrada na tabela
   `Mensagem`, vinculada ao chamado.

### Regras da conversa

- **Primeiro contato só recebe a pergunta.** A mensagem que abre a conversa
  (tipicamente "oi") **não** é gravada como nome: a sessão nasce na etapa `nome`
  e o bot responde a pergunta. Custa uma mensagem a mais por chamado, e é o que
  impede o formulário inteiro de deslizar um campo quando a pessoa cumprimenta
  antes de responder.
- **Menu numerado.** Toda escolha é oferecida como lista numerada, e a resposta
  esperada é o número. A Evolution envia texto puro — não há botão nem lista
  interativa como havia na API da Meta, e por isso o número virou o caminho
  principal, não o alternativo.

  O que ainda é aceito, e de propósito: as *palavras* humanas ("confirmar",
  "sim", "cancelar") e os **ids de botão antigos** (`confirmar`,
  `editar_descricao`, ...). Os ids só valem vindos de um clique de verdade —
  digitá-los não faz nada. Eles continuam sendo lidos porque uma conversa que
  estava no meio do fluxo quando a migração aconteceu recebeu botões antes e
  responderia com eles depois; sem isso, ela ficaria sem resposta.
- **Entrega duplicada.** Webhook é entregue "pelo menos uma vez": uma repetição
  por retentativa da Evolution, ou por um 200 que se perdeu no caminho. O id da
  mensagem (`key.id`) é gravado com índice único, então a repetição é descartada
  em vez de avançar o fluxo duas vezes.
- **Mensagens simultâneas.** O processamento acontece dentro de uma transação, e
  o SQLite aceita um escritor por banco — então duas mensagens quase simultâneas
  não leem a mesma etapa e uma sobrescreve a outra. O preço é que o sistema roda
  em **uma instância** (ver *Limites conhecidos*).
- **Limites por campo.** Nome 120, resumo 200, descrição 2000 caracteres, com
  aviso amigável quando passa. No resumo da confirmação a descrição aparece
  encurtada — não mais por limite de API, e sim porque um bloco de 2000
  caracteres no meio da confirmação esconde as opções abaixo dele. O texto
  completo continua salvo no banco.
- **Áudio, imagem e anexo** recebem uma resposta explicando a limitação e a
  pergunta atual é repetida. A ocorrência fica registrada no histórico.
- **Cancelar a qualquer momento** digitando `cancelar` / `reiniciar` / `sair`, ou
  pelo botão Cancelar na confirmação. Só vale como comando quando é a mensagem
  inteira: "preciso cancelar meu pedido no site" é tratado como texto normal. Sem
  nada em andamento, a resposta diz isso em vez de afirmar que cancelou algo.
- **Sessão expira** após 24h sem atividade (`SESSAO_TTL_HORAS`) e a conversa
  recomeça, avisando o usuário.

A tabela `SessaoConversa` existe só enquanto o chamado ainda está sendo
montado — assim que confirmado, ela é apagada.

## Pré-requisitos

- Node.js 24 ou superior (a versão exata está no `.nvmrc`; o Node 20 saiu do
  LTS em abril/2026)
- **Nada de banco a instalar** — o banco é um arquivo SQLite criado pela
  migração, em `dados/whatsapp-suporte.db`
- Uma instalação da [Evolution API](https://doc.evolution-api.com/) v2 com uma
  instância conectada a um número de WhatsApp
- [ngrok](https://ngrok.com/) (ou similar) para expor seu servidor local durante
  o desenvolvimento, já que a Evolution precisa alcançar seu webhook

## Setup

```bash
npm install
cp .env.example .env
```

Edite o `.env` com:
- `WEBHOOK_SEGREDO`: string longa e aleatória que você escolhe. Ela vira o final
  da URL que a Evolution vai chamar: `https://SEU_DOMINIO/webhook/<segredo>`
- `EVOLUTION_URL`: o endereço da sua Evolution, com esquema e sem barra no fim
- `EVOLUTION_API_KEY`: a `AUTHENTICATION_API_KEY` da instalação, ou o token da
  instância. Vai no cabeçalho `apikey` de cada envio
- `EVOLUTION_INSTANCIA`: o nome da instância conectada (o que aparece em
  `GET /instance/fetchInstances`)

`DATABASE_URL` já vem funcionando (`file:./dados/whatsapp-suporte.db`) e só
precisa de atenção em produção, onde deve apontar para um disco persistente.
O caminho relativo é resolvido contra a **raiz do projeto**, não contra o
diretório de onde você rodou o comando.

O servidor valida essas variáveis no boot e **se recusa a subir** se faltar
alguma, listando todas as pendências de uma vez.

Depois, gere o cliente e aplique as migrações:

```bash
npm run prisma:generate
npm run prisma:deploy    # produção: aplica as migrações versionadas
```

Em desenvolvimento, use `npm run prisma:migrate` (o `migrate dev`, que também
gera novas migrações quando você muda o schema). **Nunca em produção**: ele pode
resetar o banco.

Isso cria o arquivo do banco e as tabelas.

Migrações versionadas hoje:

| migração | o que faz |
| --- | --- |
| `20260827200659_init` | baseline SQLite: as quatro tabelas, índices e as FKs |
| `20260827205637_categorias_e_sla` | `Categoria` (assuntos do menu) e os marcos de SLA |
| `20260831124955_cadastro_de_pessoas` | `Pessoa`: o cadastro compartilhado do painel |
| `20260831135505_classificacao_de_chamados` | `Setor`, `Comentario`, `Anexo`, `Tag`, `Dependencia` e os 24 campos de classificação em `Chamado`; semeia os 11 setores |
| `20260917120000_assunto_de_uso_interno` | `Categoria.visivelNoWhatsapp`: o assunto que só existe no painel (ver *[Assunto de uso interno](#assunto-de-uso-interno)*) |

> **Vindo da versão em Postgres?** As quatro migrações antigas foram substituídas
> por esta baseline única — o SQL delas não roda no SQLite. Elas continuam no
> histórico do git.
>
> E **os dados não vêm automaticamente**: `migrate deploy` cria tabelas vazias, e
> um dump de `pg_dump` não é um arquivo SQLite. Se houver dado a preservar, é um
> script de exportação/importação de uma vez, respeitando a ordem das FKs. Ver
> [`docs/WA Banco de dados.md`](docs/WA%20Banco%20de%20dados.md).

Para recomeçar do zero, apague os arquivos do banco e migre outra vez:

```bash
rm -f dados/whatsapp-suporte.db dados/whatsapp-suporte.db-wal dados/whatsapp-suporte.db-shm
npm run prisma:deploy && npm run dev:view
```

### View para a plataforma de cards

```bash
npm run dev:view    # em desenvolvimento
npm run db:view     # depois do build; é o que o deploy roda
```

`prisma migrate` **não gerencia view**, então este passo é separado — e
idempotente, para rodar depois de toda migração. A view `chamados_para_cards`
expõe as colunas de leitura do chamado: identificação, os quatro instantes de SLA
(`dataAbertura`, `prazoEm`, `primeiroAtendimentoEm`, `resolvidoEm`), a
classificação inteira (situação, prioridade, canal, tipo, e os ids de assunto,
setor, setor de origem e responsável), os dois blocos específicos (interno e
franquia) e a avaliação pós-fechamento.

O que ela **não** expõe são os canais de contato de pessoas: `telefone`,
`contato` e `franqueadoContato` ficam de fora, pela mesma minimização de sempre.

> A migração `20260831135505_classificacao_de_chamados` **derruba e recria** esta
> view, porque adicionar coluna no SQLite significa reconstruir a tabela — e
> `DROP TABLE "Chamado"` estoura enquanto a view aponta para ela. Se você alterar
> `sql/view_chamados_para_cards.sql`, a cópia no fim daquela migração tem de
> acompanhar (ou entre uma migração nova que recrie a view).

> **A view é um contrato de leitura, não uma fronteira de permissão.** No
> Postgres dava para criar um usuário somente-leitura com `SELECT` apenas nela.
> SQLite não tem usuário nem `GRANT`: quem tem o arquivo tem tudo — incluindo os
> anexos, que moram como BLOB dentro dele.
> Para expor os cards sem entregar o banco, use a rota `/internal/chamados` (mesma
> minimização de campos, com token) ou entregue uma **cópia** do arquivo aberta em
> modo `readonly`.

## Rodando localmente SEM instância da Evolution

Dá para exercitar a conversa inteira — banco de verdade, transações de verdade,
outbox de verdade — sem instância conectada e sem número de WhatsApp. Só as duas
pontas da integração são substituídas:

| ponta | de verdade | no teste local |
| --- | --- | --- |
| entra | webhook POST da Evolution | `npm run dev:simular`, que monta o mesmo envelope `messages.upsert` |
| sai | `{EVOLUTION_URL}/message/sendText/{instancia}` | `npm run dev:evolution` (`EVOLUTION_URL` aponta para ela) |

Nada disso enfraquece o caminho testado: o simulador entra pelo
`/webhook/<segredo>` normal e passa pela mesma autenticação — segredo errado
continua levando 404.

**Três terminais:**

```bash
npm run dev:evolution  # 1) Evolution de mentira: mostra o que o bot enviaria
npm run dev            # 2) o servidor
npm run dev:simular    # 3) conversa interativa
```

No terminal 3 você digita como se fosse o usuário no WhatsApp. As respostas do bot
aparecem ali mesmo (lidas da tabela `Mensagem`, onde a saída é gravada antes de
ser enviada) e também no terminal 1, com o texto exatamente como sairia:

```
5511999990000> Natan
bot [entregue]:
  Obrigado! Agora resuma seu problema em uma frase curta.
```

Comandos dentro da conversa: `/botao confirmar`, `/botao editar_descricao`
(simulam o clique antigo, que o bot ainda lê), `/audio`, `/imagem`, `/estado`
(sessão + chamados + pendências do outbox), `/repetir` (reenvia com o mesmo id,
simulando entrega duplicada), `/sair`.

**Cenários prontos**, para conferir os comportamentos que mais importam:

```bash
npm run dev:simular -- assinatura   # payload forjado recebe 401; assinado, 200
npm run dev:simular -- duplicada    # mesma mensagem 2x não avança o fluxo
npm run dev:simular -- lote         # 3 mensagens em um webhook só
npm run dev:simular -- estado       # inspeciona sessão, chamados e outbox
```

**Conferir as garantias de banco** — com o servidor de pé:

```bash
npm run dev:verificar-banco
```

Exercita, contra o arquivo SQLite de verdade, as coisas que dublê em memória não
prova: o formato em que a data é gravada e comparada em SQL crua, a serialização
de duas requisições simultâneas do mesmo telefone, o índice único descartando
entrega repetida, dois `PATCH` simultâneos gerando uma notificação só, a SQL de
reserva da outbox com a espera crescente, e o `ON DELETE CASCADE` do histórico.
Vale rodar antes de qualquer deploy que mexa nessas partes — foi assim que o bug
de fuso horário abaixo apareceu.

**Testar a recuperação do outbox** (o comportamento mais difícil de observar em
produção) — derrube a Evolution, mande uma mensagem, veja ela ficar pendente e sair
sozinha depois:

```bash
curl -X POST http://127.0.0.1:4000/_controle -H "content-type: application/json" -d "{\"status\":503,\"vezes\":5}"
```

Agora o simulador mostra `bot [PENDENTE no outbox]`. A reentrega leva **cerca de
um minuto**, e baixar o `VARREDOR_INTERVALO_SEGUNDOS` não muda isso: a espera é
`30s x 2^tentativas`, e a falha dentro da requisição já gasta a primeira
tentativa — então a linha só fica elegível 60s depois, e o varredor a pega na
primeira passada seguinte (medido: 74s com `VARREDOR_INTERVALO_SEGUNDOS=15`). O
intervalo do varredor define a granularidade da espera, não o tamanho dela. Para
voltar ao normal, mande `{"status":0}` no mesmo endpoint.

**Testar o endpoint interno** (use o `INTERNAL_API_TOKEN` do seu `.env`):

```bash
curl -X PATCH http://127.0.0.1:3000/internal/chamados/1/situacao -H "authorization: Bearer SEU_INTERNAL_API_TOKEN" -H "content-type: application/json" -d "{\"situacao\":\"resolvido\",\"notificarUsuario\":true}"
```

Os exemplos com `curl` acima são de uma linha de propósito, e funcionam como
estão no **bash**. **No PowerShell 5.1 eles não funcionam**, por dois motivos
independentes:

- `curl` é alias de `Invoke-WebRequest`, que não entende `-X`. Use `curl.exe`.
- o corpo entre aspas duplas com `\"` chega quebrado no processo e o servidor
  responde `{"erro":"JSON inválido"}`. Use aspas simples com as internas
  escapadas.

A mesma chamada, no PowerShell:

```powershell
curl.exe -X PATCH http://127.0.0.1:3000/internal/chamados/1/situacao -H "authorization: Bearer SEU_INTERNAL_API_TOKEN" -H "content-type: application/json" -d '{\"situacao\":\"resolvido\",\"notificarUsuario\":true}'
```

## Rodando localmente com a Evolution de verdade

```bash
npm run dev
```

Aponte o `EVOLUTION_URL` do `.env` para a sua instalação (em vez da porta 4000
da Evolution de mentira). Em outro terminal, exponha a porta com o ngrok:

```bash
ngrok http 3000
```

No painel da Evolution, em **Webhook** da instância, configure a URL como
`https://SEU_DOMINIO_NGROK/webhook/SEU_WEBHOOK_SEGREDO` e marque o evento
`MESSAGES_UPSERT`. Não marque `SEND_MESSAGE`: as mensagens que o próprio bot
envia voltariam como evento, e ainda que ele as descarte pelo `key.fromMe`, é
tráfego que não serve para nada.

> **O webhook precisa ser HTTPS.** O segredo viaja no caminho da URL, não num
> cabeçalho: em HTTP ele passa legível pela rede.

Pronto — mande uma mensagem de teste para o número da instância.

## Build para produção

```bash
npm run build
npm start
```

### Implantar

Há três formas, e todas partem dos mesmos artefatos:

```bash
docker build -t whatsapp-suporte .
docker run --env-file .env -p 3000:3000 whatsapp-suporte
```

- **Docker** — o [`Dockerfile`](Dockerfile) compila numa etapa e leva só o que
  roda para a outra: a imagem final não tem compilador nem código-fonte, e roda
  como usuário `node`.
- **Render** — o [`render.yaml`](render.yaml) descreve o serviço e o banco. As
  migrações rodam no `preDeployCommand`, antes de a versão nova passar a
  atender; se falharem, a versão antiga continua no ar.
- **Direto no host** — `npm ci --omit=dev`, `npm run build`, `npm start` atrás de
  um nginx. Nesse caso, **ligue `TRUST_PROXY`**.

Em qualquer uma delas, rode as migrações antes de subir a versão nova — e a
view logo em seguida:

```bash
npm run prisma:deploy
npm run db:view          # derruba e recria a view de cards
```

Os dois são idempotentes e no Render já estão juntos no `preDeployCommand`. O
`db:view` não é opcional: `prisma migrate` não gerencia view, e migração que mexe
em coluna usada por ela precisa da view recriada — no SQLite isso é ainda mais
frequente, porque toda alteração de coluna é feita recriando a tabela.

> **Em produção, o banco tem de ficar num disco persistente.** Se o
> `DATABASE_URL` apontar para dentro da imagem, o banco vive na camada de escrita
> do contêiner e é **apagado no próximo deploy**, sem erro nenhum. O `render.yaml`
> declara um `disk` montado em `/app/dados` e aponta o `DATABASE_URL` para lá.
>
> E **backup deixou de ser automático**: banco gerenciado fazia, disco não faz.
> Agende `sqlite3 <banco> "VACUUM INTO 'backup.db'"`.

Detalhes, incluindo o que conferir antes da primeira implantação e o que quebra
ao subir uma segunda instância: `docs/WA Implantação.md`.

### Health checks

- `GET /health` — **liveness**. Responde 200 se o processo está vivo. Não toca o
  banco de propósito: a pergunta é sobre o processo, não sobre as dependências.
- `GET /ready` — **readiness**. Faz um `SELECT 1` e responde 503 se o banco está
  inacessível, para o balanceador tirar a instância de rotação em vez de mandar
  tráfego para um processo que vai falhar em toda mensagem. Com SQLite o modo de
  falha típico não é rede, é disco: volume não montado, cheio, ou com permissão
  errada.

Os dois ficam fora do rate limit — um health check de 10 em 10 segundos não pode
consumir a cota do webhook.

## Segurança

- **Segredo do webhook**: o `POST` só é aceito em `/webhook/<WEBHOOK_SEGREDO>`,
  comparado em tempo constante. Segredo errado recebe **404** — e não 401, de
  propósito: um 401 confirmaria que existe um webhook naquele caminho. Sem isso,
  qualquer um que descubra a URL poderia abrir chamados falsos e, pior, fazer o
  bot **enviar mensagem para qualquer número** — o que costuma terminar com o
  número banido.

  Vale saber o que se perdeu na saída da Meta: o HMAC dela era calculado sobre os
  bytes crus do corpo, então provava **duas** coisas — quem chamou e que o corpo
  chegou intacto. Um segredo no caminho prova só a primeira. Some-se a isso que
  caminho de URL aparece em log de proxy e em histórico, enquanto cabeçalho não.
  Daí o webhook ter de ser HTTPS, e o segredo ser longo e rotacionável.
- **Validação de configuração**: o processo morre no boot se faltar qualquer
  segredo, em vez de subir com a verificação desligada.
- **Limites**: corpo da requisição limitado a 256 KB, mensagem cortada em 4096
  caracteres, teto de requisições por minuto no endpoint e teto de mensagens por
  minuto por telefone.
- **Logs**: telefones são mascarados e erros são reduzidos a tipo/código/mensagem
  truncada, para não despejar dado pessoal no log. Todo o código fora de rota
  (outbox, varredor, limpeza de sessões) escreve no mesmo logger das requisições.
- **Atrás de proxy**: se houver ngrok / Render / nginx / load balancer na frente,
  defina `TRUST_PROXY`. Sem isso, todo request aparece com o IP do proxy e o rate
  limit por IP vira um contador global do endpoint. Com o processo exposto direto
  na internet, deixe desligado — aí o header seria forjável.

## Endpoint interno (mudar a situação)

O bot nunca muda `situacao` sozinho — isso é decisão de um atendente humano.

```
PATCH /internal/chamados/:id/situacao
Authorization: Bearer $INTERNAL_API_TOKEN
{ "situacao": "em_andamento", "notificarUsuario": false, "autor": "Ana" }
```

Situações aceitas: `aberto`, `em_andamento`, `aguardando_resposta`, `resolvido`,
`fechado`, `cancelado`.

As duas últimas a entrar cobrem estados que antes eram indistinguíveis de outra
coisa:

- **`aguardando_resposta`** é o chamado parado por falta de resposta de **quem
  pediu**, e não por falta de atendimento. Sem ele, essa espera ficava em
  `em_andamento` e entrava na conta de SLA da equipe — exatamente o número que o
  SLA não deve punir.
- **`fechado`** é o encerramento **administrativo** depois de resolvido (avaliado,
  contabilizado). `resolvido` continua significando "o problema acabou".

`resolvidoEm` (a data de conclusão) é preenchida ao **entrar** no conjunto
`{resolvido, fechado}` e zerada ao sair dele. Mover de `resolvido` para `fechado`
não remarca o instante — só a entrada conta —, e reabrir um chamado zera a data,
porque chamado reaberto não está concluído.

`notificarUsuario` é **opcional e desligado por padrão**. Quando `true`, o
usuário recebe um aviso no WhatsApp — como isso manda mensagem para uma pessoa
real, quem chama decide. A mudança de situação é persistida mesmo se a
notificação falhar; ela fica pendente na outbox e é reenviada depois.

A situação é lida e gravada dentro da **mesma transação**, então dois PATCH
simultâneos no mesmo chamado não conseguem os dois enxergar a mesma situação
anterior e notificar o usuário em duplicidade. (No Postgres isso exigia um
`SELECT ... FOR UPDATE`; no SQLite a transação basta, porque duas nunca se
sobrepõem.)

`autor` é opcional (até 120 caracteres) e vai para o histórico de atendimento:

```
GET /internal/chamados/:id/historico
Authorization: Bearer $INTERNAL_API_TOKEN
-> { "chamadoId": 12, "mudancas": [ { "de": "aberto", "para": "em_andamento",
                                     "autor": "Ana", "criadoEm": "2026-08-19T18:04:11.000Z" } ] }
```

Toda mudança real de situação vira uma linha, gravada **dentro da mesma**
**transação** do PATCH: ou a situação muda e fica
registrada, ou nada acontece. Um PATCH que repete a situação atual não vira linha
(não é evento de atendimento). Chamado inexistente responde 404, e não lista
vazia. Nenhuma das rotas devolve `telefone`.

## Classificação de chamados

Um chamado carrega três coisas: os campos **comuns** (todo chamado tem), os do
bloco **interno** e os do bloco **franquia**. Quem decide qual dos dois blocos
vale é `tipo`.

### `tipo`: o discriminador

`tipo` é `interno`, `franquia` ou **nulo**. Nulo é um estado legítimo: quem abre
pelo WhatsApp não responde isso — o fluxo da conversa **não** ganhou pergunta
nova, para não custar mais uma mensagem a todo atendimento —, então o chamado
nasce sem tipo e um atendente classifica no painel. O formulário do painel esconde
o bloco que não se aplica; a API aceita os dois preenchidos, porque o tipo
costuma ser descoberto **depois** dos dados.

### Assunto ≠ setor

São dois eixos, e as duas colunas existem de propósito:

| | o que é | onde vive | quem vê |
| --- | --- | --- | --- |
| **assunto** (`categoriaId` → `Categoria`) | o que o cliente escolhe no menu numerado do WhatsApp | tabela, editável em *Assuntos* | o cliente, na conversa |
| **setor** (`setorId` → `Setor`) | a área da empresa que atende | tabela, editável em *Setores* | só quem trabalha aqui |

O mesmo assunto pode cair em setores diferentes conforme o caso, e um setor
atende vários assuntos — com um campo só, uma das duas leituras se perde.

Chamado interno aponta para setor **duas vezes**: `setorId` (quem resolve) e
`setorOrigemId` (quem pediu). Um pedido do Financeiro para o TI tem origem
Financeiro e responsável TI; com uma coluna só, os relatórios "quem mais nos
demanda" e "quem mais atende" viram o mesmo número.

Os 11 setores iniciais (TI, Financeiro, Operações, Marketing, Manutenção, RH,
Comercial, Jurídico, Suprimentos, Logística, Expansão) são semeados pela migração.
Daí para frente a lista é mantida no painel — é por isso que `Setor` é tabela e
não um `enum` do Prisma: organograma muda por decisão de negócio, e enum só muda
com migração e deploy.

### Assunto de uso interno

Nem todo assunto deve ser oferecido ao cliente. Alguns existem só para a TI
classificar o que chega — e para eles a categoria tem um segundo interruptor,
`visivelNoWhatsapp`, ao lado de `ativa`:

| | `ativa` | `visivelNoWhatsapp` | onde aparece |
| --- | --- | --- | --- |
| assunto de atendimento | ✓ | ✓ | menu do WhatsApp **e** seletor do painel |
| **assunto de uso interno** | ✓ | — | só no seletor do painel |
| assunto fora de circulação | — | (indiferente) | em lugar nenhum; sobrevive nos chamados que já o usam |

São **dois eixos e não três estados de um campo só**, porque respondem perguntas
diferentes: `ativa` é *o assunto existe?*, `visivelNoWhatsapp` é *quem pode
escolhê-lo?*. Antes desta coluna, esconder um assunto do cliente exigia
desativá-lo — e aí ele sumia também do painel, que é justamente onde ele
precisava estar.

Marca-se pelo painel, em **Assuntos**, no interruptor *No WhatsApp* de cada
linha. O efeito é imediato, na conversa seguinte: quem filtra é `filhasNoMenu`
(`src/conversation/categorias.ts`), a única consulta que monta as opções — e a
mesma que interpreta a resposta. É o que garante que o assunto interno não seja
alcançável nem pelo número que ele "teria", nem pelo rótulo digitado por extenso,
nem por um toque num menu antigo que o WhatsApp mantém clicável no histórico.

Marcar um **assunto guarda-chuva** como interno leva junto os sub-assuntos dele:
a conversa desce um nível por vez, e ninguém chega ao que está embaixo de uma
opção que nunca é oferecida. A coluna das filhas **não** é reescrita — o painel
mostra a herança na linha —, e é isso que faz religar o pai devolver o ramo
inteiro sem ninguém ter de lembrar o que estava marcado antes.

Vale também para a conversa que **já estava dentro** do ramo quando a marcação
aconteceu: a etapa valida o nó onde a pessoa parou e, se ele saiu de circulação,
devolve o menu raiz com um aviso, descartando a resposta que veio — ela foi
escrita olhando uma lista que não existe mais. Ver
[`docs/WA Fluxo da conversa.md`](docs/WA%20Fluxo%20da%20conversa.md).

Um assunto interno continua somando no dashboard: `porCategoria` conta pelo id
gravado no chamado e não pergunta por onde ele foi classificado.

> **A coluna governa um canal só, e o nome dela diz qual.** É deliberado: um
> nome genérico (`publica`, `externa`) prometeria valer para qualquer canal de
> abertura que venha a existir, e nenhum outro a consulta. O portal de abertura,
> quando houver, decide por conta própria o que mostra.

### Prioridade ≠ urgência comercial

Duas escalas, porque medem coisas diferentes:

- **`prioridade`** (`baixa`/`media`/`alta`/`urgente`) é técnica: em que ordem a
  equipe puxa o chamado da fila. Default `media`, o único valor que não afirma
  nada — chamado vindo do WhatsApp não passa por ninguém que decida isso.
- **`urgenciaComercial`** (`rotina`/`atencao`/`loja_impactada`/`loja_parada`) é de
  franquia: quanto a loja está perdendo enquanto o chamado espera.

Um chamado pode ser tecnicamente simples e comercialmente crítico ao mesmo tempo.

### Canal ≠ origem

Também duas colunas, também por perguntas diferentes:

- **`origem`** (`whatsapp`/`painel`) é técnica: por qual **porta** a linha do banco
  nasceu. É ela que diz se existe telefone, sessão e log de conversa.
- **`canal`** (`whatsapp`/`email`/`telefone`/`presencial`) é de negócio: por onde o
  pedido chegou. Um chamado digitado no painel por quem atendeu o telefone tem
  `origem = painel` e `canal = telefone`.

Chamado criado pelo painel nasce com `canal = presencial` e não com o default
`whatsapp` do banco — whatsapp é justamente o que ele não é.

### Rotas

```
PATCH /internal/chamados/:id          # classificação (não notifica ninguém)
{ "tipo": "franquia", "setorId": 2, "prioridade": "urgente",
  "prazoEm": "2026-09-02T18:00:00Z", "franquiaCodigo": "BM-042" }
-> o chamado INTEIRO, no mesmo formato da listagem
```

Rota separada da de situação e da de assunto, e a separação não é estética: mudar
situação é **evento de atendimento** (vai para o histórico, move marco de SLA,
pode disparar mensagem de WhatsApp para o cliente); classificar é **organização
interna**. Se os campos viajassem no mesmo PATCH, corrigir o setor de um chamado
mandaria "seu chamado está sendo analisado" para o solicitante.

Campo **ausente** é "não mexa"; **`null`** é "limpe este campo". Sem essa
distinção, desfazer uma classificação errada seria impossível pela API — só daria
para trocar por outra. Corpo que chega sem nenhum campo conhecido é 400, e não um
200 que não gravou nada.

```
PUT  /internal/chamados/:id/avaliacao      { "nota": 4, "comentario": "rápido" }
PUT  /internal/chamados/:id/tags           { "tags": ["pdv", "black friday"] }
GET  /internal/chamados/:id/detalhe        # conversa, comentários, anexos, dependências
POST /internal/chamados/:id/comentarios    { "texto": "...", "autor": "Ana" }
POST /internal/chamados/:id/anexos         { "nome", "mime", "conteudoBase64" }
GET  /internal/anexos/:id                  # download
DELETE /internal/anexos/:id
POST /internal/chamados/:id/dependencias   { "bloqueadorId": 7 }
DELETE /internal/chamados/:id/dependencias/:bloqueadorId
GET/POST/PATCH/DELETE /internal/setores
```

A **avaliação** só é aceita em chamado concluído (`resolvido` ou `fechado`) — é
"pós-fechamento", e aceitá-la antes deixaria a nota ser dada antes do trabalho.
`avaliadoEm` é gravado pelo servidor e não vem do corpo.

**Etiquetas** são substituídas em conjunto (`PUT`), porque o campo da tela é uma
caixa de texto separada por vírgula: o que ela sabe dizer é "no fim, são estas".
O servidor normaliza para minúsculas e remove repetidas — sem isso "PDV", "Pdv" e
"pdv" virariam três linhas e o relatório contaria o mesmo assunto três vezes.

**A conversa do WhatsApp** é legível no painel desde 2026-08-31, dentro de
`/detalhe`. Ela vinha sendo gravada em `Mensagem` desde o início (é o log da
outbox), mas nenhuma rota a expunha — quem atendia via o resumo e a descrição, e
não o que a pessoa escreveu para chegar até eles.

O que a rota devolve de cada mensagem: `remetente` (`usuario`/`sistema`), `texto`,
`timestamp` e `enviadaEm`. O que ela **não** devolve, e é a parte que importa:
`telefone`, `whatsappMessageId`, `tentativas` e — principalmente — **`payload`**,
que é o corpo exato postado na Evolution e **contém o telefone**. Expor `payload`
teria devolvido pela porta de trás justamente o dado que todas as outras rotas
escondem. Há um teste de regressão para isso.

`enviadaEm` nulo numa mensagem de saída significa "ainda na fila da outbox", e o
painel mostra isso: é a diferença entre "a equipe não respondeu" e "a resposta
existe e não saiu daqui".

> **A conversa não continua.** Ela termina na abertura do chamado: uma nova
> mensagem do solicitante começa outra sessão e abre outro chamado (ver
> `SessaoConversa`). Depois disso, só entram na lista os avisos automáticos de
> mudança de situação. **Responder pelo painel não existe** — mandar mensagem
> escrita à mão precisa entrar pela outbox, com rate limit e histórico; é um
> trabalho próprio, não um campo de texto.

**Comentário** é nota **interna**: nunca vira mensagem de WhatsApp. É por isso que
ele mora em `Comentario` e não em `Mensagem` — escrevê-lo na tabela de mensagens
faria a varredura da outbox despachá-lo para o cliente. Não há rota para editar
nem para apagar: rastro que se reescreve não é rastro. (Há um teste de regressão
para isso.)

**Anexo** guarda o binário dentro do SQLite, em `Anexo.conteudo`. É uma escolha
com contrapartida conhecida: o banco deste projeto é um arquivo único que o backup
leva inteiro, e uma pasta de arquivos ao lado seria uma segunda coisa para
sincronizar, com a chance de existir linha sem arquivo e arquivo sem linha. O
preço é o `.db` crescer com as imagens — daí o teto por arquivo em
`ANEXO_MAX_BYTES` (padrão 5 MB). O upload é base64 dentro do JSON, e a rota tem
`bodyLimit` próprio calculado a partir desse teto. Só imagem, PDF, texto e
documentos do Office são aceitos, e o download sai sempre como
`Content-Disposition: attachment` — um `text/html` guardado aqui voltaria sendo
servido pela mesma origem do painel.

**Dependência** liga dois chamados: uma linha significa "`:id` está travado
esperando `bloqueadorId`". A direção está no nome da rota. Auto-dependência é 400,
e o ciclo de dois (A trava B e B trava A) é 409 — nenhum dos dois poderia sair da
fila. Ciclos mais longos não são detectados: o estrago deles é uma leitura confusa,
não um travamento, e verificá-los exigiria percorrer o grafo a cada inserção.

### Métricas

`GET /internal/metricas` agora devolve **três cortes** do mesmo período, além do
geral: `porCategoria`, `porSetor` e `porTipo`. São três perguntas diferentes —
"sobre o que nos procuram", "quem está atendendo", "quanto é interno e quanto é da
rede" — e o mesmo chamado aparece uma vez em cada. A soma de cada corte fecha com
o total geral, inclusive o grupo dos não classificados.

> **Mudança de contrato:** a linha de métrica passou a se chamar `id` no lugar de
> `categoriaId`. A mesma linha agora descreve grupo de assunto, de setor e de
> tipo, e um campo chamado `categoriaId` dentro de um agrupamento por setor seria
> mentira. É nulo no grupo "sem classificação" e nos grupos por `tipo` (cuja chave
> é o valor do enum, não uma linha de tabela).

## Entrega de mensagens (outbox)

A resposta é gravada em `Mensagem` **dentro da mesma transação** que muda o
estado da conversa, e só depois é enviada. Se a Evolution estiver fora, a linha
fica pendente (`enviadaEm IS NULL`) e um varredor reenvia a cada minuto.

Antes disso, uma falha de envio deixava o usuário esperando por uma pergunta que
nunca chegou, com o estado já avançado no banco.

Quatro consequências que valem saber:

- **Entrega é "pelo menos uma vez".** Se o processo morrer entre o POST aceito e
  a marcação de enviado, a mensagem sai de novo. Repetir uma pergunta é melhor do
  que deixar a pessoa no vácuo.
- **A espera entre tentativas cresce** (30s, 1min, 2min, 4min...), registrada em
  `ultimaTentativaEm`. Com o teto padrão de 6 tentativas, a mensagem sobrevive a
  mais de meia hora de Evolution fora. Quando o teto é atingido, isso vai para o
  log como `Mensagem descartada sem entrega` — antes a linha só parava de aparecer
  e ninguém ficava sabendo.
- **Desistir dispara alerta**, se `ALERTA_WEBHOOK_URL` estiver configurado (Slack,
  Discord ou qualquer coletor de JSON). É o único evento do sistema em que uma
  pessoa real mandou mensagem e nunca recebeu resposta, e o log sozinho só é visto
  por quem estiver olhando na hora. O alerta é coalescido
  (`ALERTA_INTERVALO_SEGUNDOS`, 300s) — numa queda longa da Evolution todas as
  pendentes desistem juntas — e **não leva telefone nem texto**, porque o destino
  é um canal de equipe, fora da retenção deste sistema. Desligado por padrão.
- **O envio feito dentro da requisição tem orçamento de tempo**
  (`ENVIO_SINCRONO_MS`, 10s para o lote inteiro). Quem entrega o webhook desiste
  de esperar o 200 em poucos segundos e reentrega; o que não couber no orçamento
  fica pendente e sai pelo varredor, que não tem ninguém esperando do outro lado.
- **Se o processamento de uma mensagem estourar** (tipicamente banco inacessível), as
  outras do mesmo lote continuam sendo processadas, e só quem falhou recebe o
  aviso de indisponibilidade — enviado direto pela HTTP, sem passar pelo banco, no
  máximo um a cada 10 minutos por telefone. Isso importa porque o webhook responde
  200 de qualquer forma: abortar o lote na primeira falha perdia em silêncio todas
  as mensagens seguintes, já que ninguém reentrega depois de um 200.

## Dados pessoais (LGPD)

O sistema armazena nome, telefone e texto livre descrevendo o problema — tudo
dado pessoal.

Para **mensagens e chamados**, o **mecanismo** de descarte existe e a **política**
(por quantos dias guardar) é uma decisão do negócio: nada é apagado enquanto
`RETENCAO_MENSAGENS_DIAS` / `RETENCAO_CHAMADOS_DIAS` não forem definidos — o
sistema não inventa prazo.

```bash
npm run retencao                    # simula: mostra o que seria apagado
npm run retencao -- --confirmar     # apaga de verdade
```

Roda em modo simulação por padrão, e apaga em lotes de mil linhas. Em produção,
agende com cron.

**Sessões abandonadas são a exceção e saem sempre.** `SessaoConversa` guarda nome,
resumo e descrição enquanto o chamado está sendo montado. O TTL era aplicado só
de forma preguiçosa — a sessão vencida era descartada quando *aquele* telefone
mandava outra mensagem — então quem abandonava a conversa na etapa da descrição e
nunca voltava deixava esses dados no banco para sempre. Agora a varredura roda
sozinha no processo a cada `LIMPEZA_SESSOES_MINUTOS`, e também no
`npm run retencao`. Aqui não há decisão de negócio a tomar: passado o
`SESSAO_TTL_HORAS`, a sessão já seria descartada no próximo contato de todo jeito.

**Pedido de exclusão do titular** (direito à eliminação):

```bash
npm run retencao -- --esquecer 5511998877665              # simula
npm run retencao -- --esquecer 5511998877665 --confirmar  # apaga
```

Remove chamados, mensagens e sessão daquele telefone. **Comentários e anexos
saem junto**, por `ON DELETE CASCADE`: são registros filhos do chamado, sem prazo
de retenção próprio, e um print de tela costuma ser dado pessoal.

Duas coisas que essa busca por telefone **não** alcança, e é bom saber:

- Chamado criado no painel não tem telefone (ver `origem`), então nunca casa —
  o que é o comportamento correto: ele não tem titular.
- Os campos de contato digitados pelo atendente (`contato`, `franqueadoContato`)
  vivem em chamados que podem não ter telefone. Não há hoje um caminho de
  eliminação por esses campos; se ele passar a ser necessário, é uma rota nova,
  não um ajuste neste script.

> A contagem da simulação segue somando **mensagens, chamados e sessões**, e não
> comentários e anexos — o mesmo tratamento que `MudancaSituacao` já recebia: são
> filhos que saem por cascade junto com o pai que a simulação já contou.

## Testes

```bash
npm test         # compila e roda
npm run typecheck
npm run format:check   # Prettier — só código; a documentação fica de fora
```

Roda com o test runner nativo do Node — sem dependência de teste no projeto. Os
testes substituem o Prisma e o `fetch` por dublês em memória e exercitam o código
real de conversa, webhook, envio, retenção e rotas (via `app.inject()`, sem abrir
porta).

Cinco coisas **não** são cobertas por esses testes, porque dependem do banco de
verdade:

- **o formato em que a data é gravada, e a comparação dela em SQL crua** — em
  memória não existe serialização de data nenhuma, então um erro de formato é
  literalmente invisível;
- a serialização de fato de duas transações concorrentes (que no SQLite vem do
  mutex do adaptador, e não de uma instrução que dê para espionar);
- o índice único rejeitando de fato um `whatsappMessageId` repetido;
- a SQL de reserva da outbox — a regra de elegibilidade dela está *reimplementada
  em JS* no dublê, então o teste cobre a orquestração em volta, não a query;
- o `ON DELETE CASCADE` do histórico de situação, de que a retenção depende para
  conseguir apagar chamado antigo sem esbarrar na FK — e que no SQLite ainda
  depende de `PRAGMA foreign_keys` estar ligado na conexão.

Para essas cinco existe o `npm run dev:verificar-banco`, que roda contra o banco
real (ver a seção de teste local).

O CI (`.github/workflows/ci.yml`) roda **os dois**: um job com typecheck, build e
testes, e outro que aplica as migrações de verdade e roda o `dev:verificar-banco`
contra elas. Esse segundo job nasceu com `services: postgres`; com o banco em
SQLite não há serviço nenhum para subir. Este README já afirmou que isso "não dava
para colocar no CI sem um Postgres" — dava, e na primeira execução o job encontrou
um bug real de fuso horário.

### Datas: texto ISO-8601 com offset, sempre UTC

O SQLite não tem tipo de data. O Prisma grava texto ISO-8601 com o deslocamento
explícito — `2026-08-27T19:57:00.604+00:00` — e sempre em UTC. Não há fuso de
sessão para herdar, e por isso o schema não tem mais o `@db.Timestamptz(3)` que
toda coluna de data carregava na versão em Postgres.

Isso fecha as duas causas do bug de fuso que este projeto já teve duas vezes (o
histórico está em `docs/WA Fuso horário sem timezone.md`), mas **não** fecha o
lugar onde ele mora:

> **Ao mexer em SQL cru com data:** converta as duas pontas para número com
> `unixepoch(coluna, 'subsec')`. **Nunca** compare a coluna com `datetime('now')`
> como texto — `datetime('now')` devolve `2026-08-27 19:57:00` (espaço em vez de
> `T`, sem milissegundo, sem offset), e em comparação de string o `T` é maior que
> o espaço: **toda** linha pareceria estar no futuro e o varredor não reenviaria
> nada, nunca. É o mesmo sintoma de antes, por outro motivo.
>
> E ao **gravar** data em SQL cru, passe um `Date` como parâmetro em vez de usar
> `datetime('now')`: só assim o valor fica no formato que o Prisma lê.

## Limitações conhecidas

- **Estado por telefone: memória ou Redis, conforme `REDIS_URL`.** O rate limit
  por telefone e o aviso de indisponibilidade vivem em `src/estado/janelas.ts`.
  Com `REDIS_URL` vazia (padrão) eles ficam na memória do processo — o certo com
  **uma** instância. Com mais de uma instância e sem `REDIS_URL`, o limite
  efetivo vira N x o configurado, sem nada quebrar e sem nada avisar: defina a
  variável no mesmo movimento em que subir o número de instâncias. Falha do Redis
  não desliga o limite, ela o faz voltar a valer por instância. A linha de boot
  diz em qual dos dois modos o processo subiu.
- **Uma instância, e isso não é configuração.** O banco é um arquivo SQLite, que
  aceita **um escritor**. Duas instâncias apontadas para o mesmo arquivo brigam
  pelo lock de escrita, e a serialização que faz o sistema ser correto vem de um
  mutex *dentro do processo*, que não atravessa instâncias. Escalar
  horizontalmente é trocar de banco, não mexer numa variável.
- **Backup é responsabilidade sua.** Banco gerenciado fazia backup automático;
  um arquivo em disco não. Use `VACUUM INTO` (não `cp`, que perde o `-wal`).
- **Apagar linha não devolve espaço ao disco.** Depois de uma limpeza grande de
  retenção, rode `VACUUM` — ele bloqueia escrita enquanto roda.
- **Identificadores em CamelCase com aspas.** `"Mensagem"`, `"enviadaEm"`: o
  padrão do Prisma obriga aspas em toda query crua e em toda sessão de `sqlite3`,
  para sempre. Corrigível com `@@map`/`@map`, mas é migração de tabela inteira.
- **Prazo de retenção de mensagens e chamados não definido.** O mecanismo existe,
  o número é seu. (Sessões abandonadas já saem sozinhas.)
- **`prisma migrate` não gerencia a view**: quem a aplica é `npm run db:view`, no
  `preDeployCommand` e no CI. E a view **não é mais uma fronteira de permissão** —
  SQLite não tem usuário nem `GRANT`.
- **Sem histórico de mudanças de situação.** Quem mudou o quê fica só no log da
  aplicação, não em tabela.
- **Sem lint/formatter.** Só typecheck. Adicionar ESLint + Prettier exige instalar
  dependências novas.
- **Índice do varredor é comum, não parcial.** `@@index([remetente, enviadaEm,
  timestamp])` serve bem a busca de pendentes, mas com a tabela `Mensagem` muito
  grande um índice parcial (`WHERE remetente = 'sistema' AND "enviadaEm" IS NULL`)
  seria menor e mais rápido. O Prisma não sabe declarar índice parcial, então ele
  teria de viver numa migração à mão — e aí o `migrate dev` tentaria removê-lo.

## Extensões sugeridas

- Permitir que o usuário envie a descrição em várias mensagens seguidas
  (concatenando) até confirmar explicitamente que terminou.
- Reaproveitar o nome do último chamado do mesmo telefone, para não perguntar de
  novo a cada abertura.
- Tabela de auditoria para mudanças de `situacao`.
