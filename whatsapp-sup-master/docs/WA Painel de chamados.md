---
tags: [projeto/whatsapp-suporte, integracao, painel]
projeto: whatsapp-suporte
atualizado: 2026-08-31
---

# WA Painel de chamados

Volta para [[WhatsApp Suporte]] · o projeto do quadro tem nota própria: [[Painel de Chamados]] · configuração em [[WA Configuração]] ·
minimização de dado em [[WA Segurança e LGPD]].

O quadro mostra os chamados do banco e devolve a mudança de situação. Ele é a
"plataforma de cards" que a `sql/view_chamados_para_cards.sql` e o README
sempre citaram — só que agora existe de fato.

## O quadro em uso

![[painel-quadro.jpg]]
*As colunas espelham a `situacao` do chamado; arrastar um cartão manda a nova
situação para a API. As etiquetas coloridas são assunto, setor e tipo; o chip de
prioridade e o de prazo ficam no rodapé; as bolhas à direita são o solicitante e
o responsável. (Dados de demonstração.)*

### Um chamado aberto

![[painel-chamado-detalhe.jpg]]
*O modal de um chamado: a classificação (situação, tipo, assunto, setor,
prioridade, responsável, canal) e, abaixo, descrição, comentários internos e
anexos. É a mesma tela que edita qualquer um dos campos.*

### Visão gerencial

![[painel-dashboard.jpg]]
*O Dashboard: fila aberta, aguardando 1º atendimento, prazo vencido, tempo até o
primeiro atendimento (mediana) e a série de abertos × resolvidos no período.*

> [!info] Onde ele mora mudou em 2026-08-25
> O painel era `../activity-dashboard`, fora deste repositório e fora de
> qualquer git. Agora ele vive **versionado aqui dentro**, em
> `activity-dashboard/`, e é essa cópia que o `run.bat` sobe. A pasta antiga
> chegou a coexistir e a divergir; foi apagada em 2026-08-26 — ver
> [[WA Pendências#Fechados em 2026-08-26]]. **Hoje existe uma cópia só.**

## O buraco que precisava ser preenchido

O painel é uma página estática: quatro arquivos, sem build e sem servidor. E
**navegador não abre banco** — não existe driver de SQLite no browser, e nem
faria sentido: o arquivo está no disco do servidor. Alguma coisa tinha que ficar
no meio.

Essa coisa é o servidor do bot, que já tem o banco aberto, o token, os schemas, o
helmet e o handler de erro. Subir um segundo serviço só para ler `Chamado` seria
pior agora do que era com Postgres: dois processos escrevendo no mesmo arquivo
SQLite brigam pelo lock (ver [[WA Banco de dados#Um escritor por banco]]).

```
navegador                servidor do bot              SQLite (arquivo)
┌──────────────┐   GET /internal/chamados   ┌──────────┐          ┌──────────┐
│   painel     │ ─────────────────────────► │ Fastify  │ ───────► │ Chamado  │
│ (estático)   │ ◄───────────────────────── │ + Prisma │ ◄─────── │          │
└──────────────┘   PATCH .../situacao       └──────────┘          └──────────┘
                                                  │
                                                  └─► Evolution  (avisa o usuário)
```

## As colunas SÃO o enum

Os ids das colunas do quadro são exatamente os valores de `Situacao`:
`aberto`, `em_andamento`, `resolvido`, `cancelado`.

> [!important] Não crie uma tabela de conversão
> Arrastar para "RESOLVIDO" manda literalmente `situacao: "resolvido"`. Um mapa
> `todo → aberto` no meio seria mais um lugar para divergir do schema, e o
> primeiro sintoma de divergência seria um cartão que some da tela sem erro.
> Situação nova no Prisma entra no `data.js` com o mesmo id e nada mais muda.

## As rotas

| rota | para quê |
| --- | --- |
| `GET /internal/chamados` | lista para o quadro. Aceita `situacao` e `limite` (1–500, padrão 200) |
| `GET /internal/chamados/:id/historico` | auditoria: quem mudou o quê, quando. Mais novo primeiro |
| `PATCH /internal/chamados/:id/situacao` | move o cartão; é aí que os marcos de SLA são gravados |
| `PATCH /internal/chamados/:id/categoria` | troca o **assunto** do chamado |
| `POST /internal/tarefas` | cria tarefa (nasce no painel, sem conversa por trás) |
| `GET /internal/metricas` | números agregados por assunto + médias de SLA |
| `GET /internal/categorias` | a árvore de assuntos inteira, **inclusive as inativas** |
| `POST /internal/categorias` | cria assunto |
| `PATCH /internal/categorias/:id` | renomeia, reordena, ativa/desativa, troca o pai |
| `DELETE /internal/categorias/:id` | exclui — e recusa (409) se houver chamado ou sub-assunto |

> [!important] Assunto tem rota própria, e não entrou no `PATCH` de situação
> As duas mudanças não têm nada em comum além do alvo. Mudar situação é evento
> de atendimento: vai para o histórico, pode notificar o usuário no WhatsApp e
> move marco de SLA. Mudar assunto é correção de classificação.
>
> Num `PATCH` genérico, corrigir uma classificação errada dispararia mensagem
> para uma pessoa real.

Nenhuma delas devolve `telefone`, e isso não é esquecimento: é a mesma
minimização da view `chamados_para_cards`. O painel roda no navegador de quem
atende e não precisa do telefone para nada. Há teste em
[test/rotas.test.ts](../test/rotas.test.ts) fixando isso — se ele falhar, vazou
dado do titular.

A consulta é pelo Prisma, e não pela view, de propósito: a view é aplicada por
`npm run db:view` e pode não existir num banco recém-migrado. Ela continua
servindo o caso para o qual foi feita — um usuário de banco separado, com
`SELECT` só nela.

### Histórico de atendimento

O `PATCH` aceita um campo opcional `autor` (o nome de quem está mexendo, até 120
caracteres). Toda mudança REAL de situação vira uma linha em `MudancaSituacao`,
gravada **dentro da mesma transação** que leu a situação anterior: ou a situação
muda e fica registrada, ou nada acontece. (No Postgres essa transação carregava um
`SELECT ... FOR UPDATE`; no SQLite a transação basta, porque duas nunca se
sobrepõem.) Um `PATCH` que repete a
situação atual não vira linha — não é evento de atendimento, é ruído (é a mesma
regra que decide se o usuário é notificado).

```
PATCH /internal/chamados/12/situacao   {"situacao":"resolvido","autor":"Ana"}
GET   /internal/chamados/12/historico
  -> { "chamadoId": 12,
       "mudancas": [ { "de": "em_andamento", "para": "resolvido",
                       "autor": "Ana", "criadoEm": "2026-08-19T18:04:11.000Z" } ] }
```

Chamado que não existe responde **404**, e não lista vazia: `mudancas: []`
deixaria "não existe" indistinguível de "existe e nunca mudou de situação".

Antes disso, "quem mudou o quê" existia só na linha de log da aplicação — que
rotaciona, não é consultável por chamado e some junto com o contêiner. O
`atualizadoEm` do chamado diz QUANDO mudou pela última vez, mas não de onde para
onde nem por quem: um chamado que foi `resolvido` e voltou para `aberto` era
indistinguível de um que nunca saiu de `aberto`.

## Dois tokens

`PAINEL_TOKEN` é opcional; sem ele, o painel usa o `INTERNAL_API_TOKEN`.

> [!warning] Por que vale a pena separar
> O token interno vive em servidor. O do painel vive no **navegador de cada
> atendente** — máquina compartilhada, extensão instalada, print de tela. Ter os
> dois permite revogar o do painel sem derrubar nenhuma outra integração.

No painel ele fica em `sessionStorage` e some ao fechar a aba, a menos que a
pessoa marque "Lembrar neste navegador". O padrão é não lembrar.

## Como o painel é servido

Uma página estática não pode ser aberta do disco: em `file://` a origem vira
`null` e nenhum CORS sensato a libera. Quem a serve é o
[servidor-painel.mjs](../servidor-painel.mjs), na porta 8511 — biblioteca padrão
do Node, sem dependência nenhuma.

Ele faz **duas** coisas, e a segunda é a que importa:

```
navegador ──► :8511  servidor-painel.mjs ──► arquivos estáticos do painel
                          │
                          └── /internal/*  ──► 127.0.0.1:9511  (o bot)
```

Repassar `/internal/*` põe painel e API na **mesma origem**. Isso tira o CORS
inteiro do caminho, e é o que faz o quadro funcionar por `localhost`, pelo IP
da máquina na rede ou por um domínio **sem reconfigurar nada** a cada endereço
novo. Por isso `apiBaseUrl` está vazio em `activity-dashboard/data.js` e
`PAINEL_ORIGENS` está comentado no `.env`.

Dois detalhes do proxy que não são acidente: o `Authorization` é repassado
(é ele que carrega o `PAINEL_TOKEN`; sem ele a API responde 401 a tudo), e o
caminho em disco passa por `normalize` **antes** da checagem de raiz — sem
isso, `/../../.env` sairia da pasta do painel e serviria os segredos do bot.

## CORS

`PAINEL_ORIGENS` lista as origens autorizadas. Vazio desliga o CORS por
completo, e aí a API só é consumível fora do navegador.

> [!note] Com o proxy, isto virou o caminho de exceção
> Enquanto o painel for servido pelo `servidor-painel.mjs`, não há requisição
> entre origens e `PAINEL_ORIGENS` pode ficar vazio. Ele volta a ser
> necessário no dia em que o painel passar a falar com um bot em **outro** host.

> [!danger] Nunca `origin: true` nem `*`
> Refletir qualquer origem deixaria qualquer site que o atendente abrisse fazer
> requisição autenticada em nome dele — e estas rotas leem e alteram chamado.
> A lista é explícita por isso.

E `file://` não funciona: a origem vira `null`. O painel precisa ser servido
por HTTP — hoje pelo `servidor-painel.mjs`, via `run.bat`.

## O aviso ao usuário

Mover um chamado dispara mensagem de WhatsApp para quem abriu. É opção do
painel (chave "Avisar usuário ao mover", ligada por padrão), e o aviso na tela
diz se a mensagem saiu.

Dois casos **não** disparam nada, e os dois vêm de `alterarSituacao`, não do
painel:

- soltar o cartão na mesma coluna — a situação não mudou;
- mover de volta para **A FAZER** — não existe texto em `AVISOS` para `aberto`.

> [!warning] Mensagem enviada não volta atrás
> Para limpeza em lote, desligue a chave antes de começar a arrastar.

## Assuntos e resumo

Duas telas entraram em 2026-08-27, junto com a árvore de `Categoria`:

- **Assuntos** (barra lateral) edita a árvore que o menu do WhatsApp oferece.
  Renomear, reordenar, aninhar e ativar/desativar valem no **próximo menu**, sem
  migração e sem deploy. O botão de excluir já sabe, pela contagem que vem na
  listagem, que a categoria está em uso — e oferece **desativar** em vez de
  mostrar o 409 e deixar a pessoa sem saída.
- **Resumo** (antigo "Fechar semana") mostra os números de `/internal/metricas`:
  totais por situação, média até o primeiro atendimento e média até resolver,
  quebrados por assunto, com janela de 7/30/90 dias ou histórico inteiro.

O botão antes contava os cartões **da tela** — dois vieses (o que estava
carregado e o que estava filtrado) que ninguém enxerga olhando o número. Agora a
conta é feita no banco.

> [!note] A média vem com o tamanho da amostra
> "12 min" sobre um chamado é lido igual a "12 min" sobre duzentos. Por isso cada
> média mostra entre parênteses quantos chamados entraram nela — e uma média sem
> ninguém que tenha atingido o marco sai como `—`, e não como zero.

No cartão, o assunto aparece como etiqueta e é **editável** no detalhe: quem abre
pelo WhatsApp escolhe pelo menu, e às vezes escolhe errado. Um assunto inativo
continua aparecendo no seletor **se for o que o chamado já usa** — senão o campo
mostraria "Sem assunto" e o primeiro salvamento apagaria a classificação.

### Assunto de uso interno

Cada linha da tela **Assuntos** tem dois interruptores, e eles **não** são a
mesma pergunta:

| interruptor | desmarcado significa | o assunto ainda aparece… |
| --- | --- | --- |
| **No WhatsApp** | assunto de **uso interno** | …no seletor de assunto do chamado, aqui no painel |
| **Ativo** | assunto **fora de circulação** | …em lugar nenhum; sobrevive nos chamados que já o usam |

O de uso interno é o assunto que a TI precisa para classificar e que o cliente
não deve ver na lista da conversa. Antes ele não tinha como existir: esconder um
assunto do menu exigia desativá-lo, e aí ele sumia **também** daqui — que é
justamente onde ele tinha de estar. No seletor do chamado eles aparecem com o
sufixo `(interno)`, para quem classifica saber que aquele assunto nunca foi
oferecido a quem abriu o chamado.

Marcar um assunto **guarda-chuva** como interno leva os sub-assuntos junto — a
conversa desce um nível por vez, e ninguém alcança o que está embaixo de uma
opção que não é oferecida. Nesses sub-assuntos o interruptor aparece **travado**,
com a marca *"interno (o assunto acima está fora do menu)"*: a coluna deles não
foi tocada, e religar o pai devolve o ramo inteiro exatamente como estava.

Um assunto interno continua somando no **Resumo**: a métrica conta pelo id
gravado no chamado, e não pergunta por qual caminho ele foi classificado.

> [!note] Isto vale só para o WhatsApp
> O nome da coluna (`visivelNoWhatsapp`) diz o canal de propósito. Um portal de
> abertura, se houver, decide por conta própria o que mostra.

## As rotas de classificação (2026-08-31)

Além das que já existiam, o painel passou a falar com estas — e a divisão entre
elas é a parte que vale entender, porque não é arbitrária:

| rota | o que é | notifica o cliente? |
| --- | --- | --- |
| `PATCH /internal/chamados/:id/situacao` | **evento de atendimento**: vai para `MudancaSituacao`, move marco de SLA | sim, se pedirem |
| `PATCH /internal/chamados/:id/categoria` | correção de **menu** (o assunto que o cliente escolheu) | nunca |
| `PATCH /internal/chamados/:id` | **classificação**: setor, tipo, prioridade, prazo, responsável, canal, e os dois blocos específicos | nunca |
| `PUT /internal/chamados/:id/avaliacao` | nota pós-fechamento (só em `resolvido`/`fechado`) | nunca |
| `PUT /internal/chamados/:id/tags` | substitui o conjunto de etiquetas | nunca |
| `GET /internal/chamados/:id/detalhe` | **a conversa do WhatsApp**, comentários, anexos e dependências do chamado aberto | — |
| `POST /internal/chamados/:id/comentarios` | nota **interna** da equipe | nunca |
| `POST /internal/chamados/:id/anexos` · `GET`/`DELETE /internal/anexos/:id` | arquivo (BLOB no próprio banco) | nunca |
| `POST`/`DELETE /internal/chamados/:id/dependencias[/:bloqueadorId]` | "este chamado está travado esperando aquele" | nunca |
| `GET`/`POST`/`PATCH`/`DELETE /internal/setores` | as áreas que atendem | nunca |

**Só a primeira dispara WhatsApp.** É a razão de a classificação não viajar no
mesmo PATCH da situação: se viajasse, corrigir o setor de um chamado mandaria "seu
chamado está sendo analisado" para o solicitante. O raciocínio inteiro está em
[[WA Classificação de chamados]].

Duas convenções que valem para todas as de `PATCH`:

- campo **ausente** é "não mexa"; **`null`** é "limpe este campo". Sem a
  distinção, desfazer uma classificação errada seria impossível pela API.
- corpo que chega sem nenhum campo conhecido é **400**. Isto não é zelo: o Fastify
  **remove** o campo desconhecido em vez de recusar a requisição, então sem essa
  conferência um `PATCH` com nome de campo digitado errado respondia 200 com o
  chamado inteiro. Ver
  [[WA Classificação de chamados#Uma armadilha do Fastify que este trabalho revelou]].

### O que a listagem traz e o que não traz

`GET /internal/chamados` devolve as 31 colunas do chamado **mais as etiquetas** —
e não os comentários, anexos e dependências. A divisão é por cardinalidade: coluna
é uma por linha, aquelas três são listas que crescem sem teto. Trazê-las na
listagem seria 500 cartões x N comentários x M anexos para desenhar quatro campos
por cartão.

Etiqueta é a exceção porque aparece **no** cartão. As outras vêm de
`GET /internal/chamados/:id/detalhe`, numa requisição só, quando um chamado é
aberto na tela — inclusive a **conversa do WhatsApp**, que entrou ali em
2026-08-31 pelo mesmo critério de cardinalidade.

> [!warning] O painel e o bot são atualizados em momentos diferentes
> O painel é servido como **arquivo estático do disco**: um `F5` já traz o
> `app.js` novo. O bot roda `dist/` **compilado**, e só muda depois de
> `parar.bat` + `run.bat`. Entre os dois momentos, o painel novo pode falar com um
> bot antigo que não tem a rota nova — e uma lista ausente na resposta viraria
> `TypeError` no render.
>
> Por isso `normalizarDetalhe`, no `app.js`, garante que as cinco listas existam
> antes de qualquer render. Vale lembrar disso ao acrescentar uma sexta.

## O que o painel deliberadamente não faz

Criar chamado pela conversa, editar resumo/descrição/solicitante, excluir e
arquivar. Todos pelo mesmo motivo: seriam ações sem efeito no banco, e o cartão
voltaria ao estado anterior na atualização seguinte. Situação e assunto são
editáveis justamente porque têm rota para persistir. Chamado nasce na conversa do WhatsApp e
é apagado pelo caminho auditável da retenção
(`npm run retencao -- --esquecer <telefone> --confirmar`).

## Uma armadilha que já existia no painel

O `app.js` fazia `loadState() || padrão`: uma vez que o `localStorage` tivesse
uma foto do quadro, ela vencia para sempre. Ligado ao banco, isso significaria
um painel que **nunca mostra chamado novo** — e sem erro nenhum na tela.

Agora o padrão vem primeiro, o salvo escreve por cima só o que é configuração, e
`issues` recomeça vazio a cada carga. A chave do `localStorage` também mudou,
porque o formato antigo tinha outras colunas.

## Verificado ao vivo

Contra o banco de verdade, com cinco chamados semeados, em 2026-08-18 (então ainda em Postgres; o comportamento não mudou com o SQLite):

- o quadro carregou 2/1/1/1 nas quatro colunas, com resumo, número, idade e
  iniciais do solicitante;
- arrastar `#2` para RESOLVIDO gravou no banco e enviou a mensagem
  ("Seu chamado #2 foi marcado como resolvido...");
- arrastar de volta para A FAZER gravou e **não** enviou nada;
- soltar na mesma coluna não gerou requisição;
- com a chave de aviso desligada, o movimento gravou com **zero** mensagens;
- com token inválido, o `PATCH` levou 401, o cartão **voltou sozinho** para a
  coluna de origem, o banco ficou intacto e o cabeçalho passou a exibir
  "token recusado".
