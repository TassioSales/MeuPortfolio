---
tags: [projeto/whatsapp-suporte, banco, painel, classificacao]
projeto: whatsapp-suporte
atualizado: 2026-08-31
---

# WA Classificação de chamados

Os campos que separam e classificam um chamado: setor, tipo (interno x franquia),
prioridade, prazo, canal, avaliação pós-fechamento, etiquetas livres, comentários,
anexos e dependência entre chamados.

Entrou em **2026-08-31**, na migração `20260831135505_classificacao_de_chamados`.
Antes disto, um chamado tinha sete campos úteis (nome, telefone, assunto, resumo,
descrição, situação, origem) e o quadro só sabia mover cartão entre quatro colunas.

> [!info] Onde está o quê
> Schema em `prisma/schema.prisma` · declaração única dos campos em
> `src/internal/camposDeChamado.ts` · rotas em `src/internal/chamados.ts`,
> `setores.ts` e `detalhes.ts` · tela em `activity-dashboard/` ·
> testes em `test/classificacao.test.ts`. A documentação de **uso** está no
> [README](../README.md#classificação-de-chamados).

## A pergunta que o desenho responde

O pedido trouxe quatro listas de campos: comuns, específicos de chamado interno,
específicos de chamado de franquia, e três obrigatórios (canal, avaliação, tags).
Isso dá 24 colunas novas em `Chamado` mais cinco tabelas.

A decisão que organiza todas as outras foi **como separar os dois blocos**. Três
caminhos eram possíveis:

| caminho | por que não |
| --- | --- |
| duas tabelas (`ChamadoInterno`, `ChamadoFranquia`) | toda leitura do painel viraria duas junções, e a listagem de 500 cartões é a consulta mais frequente do sistema |
| um JSON com os campos específicos | perde índice, perde tipo e perde a validação por JSON Schema que o resto do servidor tem |
| **colunas nuláveis + um discriminador `tipo`** | escolhido |

São 17 colunas escalares que ficam nulas em metade das linhas. Num banco de um
arquivo, com o volume deste bot, isso custa quase nada — e a junção obrigatória
em toda leitura custaria muito. É o mesmo raciocínio que já valia para `telefone`
ser nulável em vez de existir uma tabela de titular.

## `tipo`: por que nasce nulo

`tipo` é `interno`, `franquia` ou **nulo**, e o nulo é um estado de trabalho, não
um esquecimento.

A alternativa era o bot perguntar. Foi considerada e recusada por um custo
concreto: o fluxo da conversa tem cinco etapas e cada etapa é **uma mensagem a
mais** por atendimento. Perguntar "você é franqueado ou do time interno?" antes do
assunto custaria isso em todo chamado, para uma informação que quem atende
descobre em dois segundos olhando o resumo.

A outra alternativa — deduzir do assunto escolhido — exigiria um mapa
assunto → tipo mantido à mão, que quebra silenciosamente a cada assunto novo
criado no painel.

Então: chamado do WhatsApp nasce sem tipo, e o painel mostra isso como um estado a
resolver (o detalhe exibe um convite a classificar em vez de esconder os campos).

## Assunto ≠ setor

Este é o ponto em que o pedido e o código já existente quase colidiram. O pedido
chamava de "categoria" a lista TI/financeiro/operações/marketing/manutenção/RH.
O projeto **já tinha** uma tabela `Categoria` — com outro significado: os seis
grupos de atendimento que o cliente lê no menu numerado do WhatsApp
(`CADASTRO NO IFOOD`, `SUPORTE AO SISTEMA VETOR`…).

São eixos diferentes do mesmo chamado:

|  | `Categoria` (assunto) | `Setor` |
| --- | --- | --- |
| o que é | o que o cliente escolhe no menu | a área da empresa que atende |
| escrito para | o cliente ler | quem trabalha aqui |
| aparece na conversa | **sim** | nunca |
| mexer nela muda | o menu do WhatsApp na conversa seguinte | só o painel e os relatórios |

Juntar as duas numa lista teria dois efeitos ruins ao mesmo tempo: "TI" e
"Financeiro" passariam a aparecer como opção no menu que o cliente lê, e o
relatório por área perderia a distinção entre "sobre o que nos procuram" e "quem
resolveu".

`Setor` é **tabela** e não `enum`, pela mesma razão que `Categoria` deixou de ser
enum: organograma muda por decisão de negócio, e enum do Prisma só muda com
migração e deploy. A migração semeia os 11 iniciais e daí para frente a lista é
mantida na tela *Setores*.

### Duas FKs para a mesma tabela

`Chamado` aponta para `Setor` duas vezes:

- `setorId` — quem **resolve**;
- `setorOrigemId` — quem **pediu** (só faz sentido em chamado interno).

Um pedido do Financeiro para o TI tem origem Financeiro e responsável TI. Com uma
coluna só, os relatórios "quem mais nos demanda" e "quem mais atende" viram o
mesmo número — e são as duas perguntas que uma área de TI interna faz.

É por isso que a listagem de setores devolve `chamados` **e** `origens`, e que o
DELETE conta as duas pontas: um setor que nunca atendeu nada mas abriu 40 chamados
ainda tem histórico a perder.

## As três escalas que não podem ser uma

O pedido foi explícito num ponto: *"urgência comercial (separado da prioridade
técnica — loja parada é diferente de dúvida sobre material)"*. O desenho tem três
escalas, e cada uma mede algo que as outras não medem:

- **`prioridade`** (`baixa`/`media`/`alta`/`urgente`) — em que ordem a equipe puxa
  o chamado da fila. Default `media`, o único valor que não afirma nada: chamado
  vindo do WhatsApp não passa por ninguém que decida isso, e nascer `alta` seria o
  bot opinando sobre a fila.
- **`impacto`** (`sem_impacto` … `bloqueia_operacao`) — a resposta a "está travando
  algo?", no bloco interno. É escala e não booleano porque a pergunta que o painel
  precisa responder não é "trava ou não trava", é "trava mais que aquele outro".
- **`urgenciaComercial`** (`rotina` … `loja_parada`) — quanto a loja está perdendo
  enquanto espera, no bloco de franquia.

Um chamado pode ser tecnicamente trivial e comercialmente crítico ao mesmo tempo.
Com um campo só, uma das duas leituras mente.

## Canal ≠ origem

Duas colunas que parecem redundantes e não são:

- **`origem`** (`whatsapp`/`painel`) é técnica: por qual **porta** a linha do banco
  nasceu. É ela que diz se existe telefone, sessão e log de conversa — e é por
  isso que ela é fixada no servidor e nunca vem do corpo.
- **`canal`** (`whatsapp`/`email`/`telefone`/`presencial`) é de negócio: por onde o
  pedido chegou.

Um chamado digitado no painel por quem atendeu o telefone tem `origem = painel` e
`canal = telefone`. Juntar as duas faria **todo** chamado registrado à mão contar
como "presencial" no relatório, o que é falso na maioria dos casos.

Detalhe que vale registrar: a rota de criação sobrescreve o default do banco.
`canal` tem `@default(whatsapp)` — o que é certo para as linhas que já existiam,
todas vindas da conversa — mas whatsapp é justamente o que uma tarefa digitada
**não** é. `POST /internal/tarefas` usa `presencial` quando o corpo não diz nada.

## As duas situações novas

`Situacao` ganhou `aguardando_resposta` e `fechado`. As duas cobriam estados que
antes eram indistinguíveis de outra coisa:

- **`aguardando_resposta`** — chamado parado por falta de resposta de **quem
  pediu**. Antes essa espera ficava em `em_andamento`, e o tempo entrava na conta
  de SLA da equipe. É exatamente o número que o SLA não deve punir: a equipe não
  está devendo nada.
- **`fechado`** — encerramento **administrativo** depois de resolvido (avaliado,
  contabilizado). Sem ele, `resolvido` significava duas coisas, e a avaliação
  pós-fechamento não tinha momento próprio para existir.

### O que isso fez com `resolvidoEm`

A regra deixou de ser "entrou em `resolvido`" e passou a ser "entrou no conjunto
`{resolvido, fechado}`":

```
resolvido -> fechado   marco NÃO se move (as duas já são conclusão)
aberto    -> fechado   marco é gravado
fechado   -> aberto    marco é ZERADO (chamado reaberto não está concluído)
```

Se só `resolvido` marcasse o instante, mover de `resolvido` para `fechado`
apagaria a data de conclusão do próprio chamado que estava sendo dado por
concluído. A regra vive em `CONCLUIDAS`, em `chamados.ts`, e é lida em três
lugares — o marco de SLA, a recusa da avaliação e o relatório.

## Comentário ≠ mensagem

`Comentario` e `Mensagem` guardam texto de conversa sobre o mesmo chamado, e são
tabelas separadas por uma razão que não é organizacional:

- `Mensagem` é a conversa **com o solicitante**. Tudo que entra ali é enviado para
  uma pessoa de fora — a tabela carrega outbox, `wamid` e contador de tentativas.
- `Comentario` é a nota **interna**. Nunca sai deste banco.

Escrever um comentário na tabela de mensagens teria despachado a nota interna para
o cliente na primeira varredura da outbox. Há um teste de regressão exatamente
para isso (`comentário NÃO vira mensagem de WhatsApp`), e ele verifica as duas
pontas: nenhuma linha em `Mensagem` e nenhum envio capturado.

As duas listas chegam ao painel **separadas** dentro de `/detalhe`, e não numa
timeline única. Juntá-las obrigaria a tela a decidir, a cada linha, se aquilo pode
ser lido pelo cliente — uma decisão que se erra uma vez e não se desfaz.

### E `Mensagem` passou a ser legível (2026-08-31)

A conversa do WhatsApp entrou em `/detalhe` depois da classificação, e valeu por
si: era a maior lacuna do painel. O que ela expõe está no
[README](../README.md#classificação-de-chamados); a decisão que merece registro é
o que ficou **fora**.

`payload` é o corpo exato postado na Evolution — e **carrega o telefone**. Era o
campo mais fácil de deixar passar num `select` largo, e devolvê-lo teria anulado
pela porta de trás a minimização que a listagem, a view de cards e o histórico
aplicam há três meses. O teste `a conversa NÃO devolve telefone, payload nem wamid`
existe para essa linha nunca voltar — e ele confere também que o que sobra está
completo, senão passaria com a rota devolvendo objetos vazios.

`enviadaEm` é o único campo de entrega que sobrou, e não é enfeite: nulo numa
mensagem de saída significa "ainda na fila". Sem ele, quem atende não distingue
"a equipe não respondeu" de "a resposta existe e não saiu daqui" — e reenviaria à
mão uma mensagem que já ia sair.

Não existe rota para editar nem para apagar comentário. O pedido dizia *"pra time
trocar info sem perder o rastro"*, e rastro que se reescreve não é rastro — é o
mesmo desenho de `MudancaSituacao`.

## Anexo: o binário mora no SQLite

`Anexo.conteudo` é um `BLOB`. A alternativa era uma pasta ao lado do banco com o
caminho gravado na linha.

A escolha foi consciente e a contrapartida é conhecida. O que pesou:

- o banco deste projeto é **um arquivo** que o `run.bat` copia e o backup leva
  inteiro. Uma pasta ao lado seria uma segunda coisa para sincronizar, com a
  chance permanente de existir linha sem arquivo e arquivo sem linha;
- `ON DELETE CASCADE` passa a apagar o anexo de verdade quando a retenção (LGPD)
  apaga o chamado. Com arquivo em disco, apagar a linha deixaria o arquivo lá.

O preço é o `.db` crescer com as imagens, e é o que `ANEXO_MAX_BYTES` (padrão
5 MB) limita. **Baixar esse número é seguro; subir exige olhar o disco e o tamanho
do backup.**

Três detalhes do desenho da rota:

- **Upload em base64 dentro do JSON**, e não `multipart/form-data`. Evita a
  dependência `@fastify/multipart` para uma rota só e mantém o servidor com um
  formato de corpo em todas as rotas — o token, a validação por JSON Schema e o
  tratamento de erro já existentes valem aqui sem exceção. O custo é a inflação de
  4/3, e o `bodyLimit` da rota é calculado a partir do teto por causa disso.
- **Lista fechada de MIME.** O conteúdo volta pelo `GET` com o `Content-Type`
  declarado no upload; um `text/html` guardado aqui seria uma página servida pela
  mesma origem do painel, com acesso ao que aquela origem tem. O
  `Content-Disposition: attachment` é a segunda tranca, não a primeira — depender
  só dele é depender de o navegador respeitá-lo.
- **A ida e volta do base64 é conferida.** `Buffer.from(x, 'base64')` nunca
  estoura: ignora todo caractere inválido e devolve o que sobrou. Sem a
  conferência, mandar "isto não é base64" gravaria um anexo de lixo, e o erro só
  apareceria quando alguém tentasse abrir o arquivo semanas depois.

## Dependência: ligação entre chamados, não texto

*"Dependência de outra área (bloqueado por / bloqueia)"* virou uma tabela ligando
dois chamados, e não um campo de texto dizendo "esperando o Financeiro".

A diferença aparece na hora que importa: quando o chamado que travava é resolvido,
quem estava travado por ele é localizável por consulta, em vez de depender de
alguém lembrar.

Uma linha significa: `bloqueado` está parado esperando `bloqueador`. As duas
pontas caem na mesma tabela, e os nomes de relação em `Chamado`
(`ChamadoBloqueado` / `ChamadoBloqueador`) são o que separa "quem me trava" de
"quem eu travo".

Duas recusas, e a segunda é a interessante:

- chamado bloqueado por si mesmo é 400 — um deadlock desenhado à mão;
- A travar B com B já travando A é 409. É o **ciclo de dois**, e nenhum dos dois
  poderia jamais sair da fila.

Ciclos mais longos (A→B→C→A) **não** são recusados. Detectá-los exigiria percorrer
o grafo a cada inserção, e o estrago de um ciclo longo é uma leitura confusa, não
um travamento — diferente do caso de dois, que é o erro que se comete sem perceber.

## Etiquetas: por que tabela, e por que normalizadas no servidor

Classificação fechada sempre chega tarde. Quando aparece um assunto que ninguém
previu ("black friday", "troca de maquininha"), criar setor ou categoria para ele
suja a lista que todo mundo vê. A tag é barata, some do caminho de quem não usa, e
ainda agrupa o relatório depois.

`Tag.nome` é único e **normalizado no servidor** (minúsculas, sem espaço nas
pontas, sem repetidas). Fazer isso só na tela não bastaria: a garantia tem de
valer para quem chama a API sem passar pelo painel, e sem ela "PDV", "Pdv" e "pdv"
virariam três linhas e o relatório contaria o mesmo assunto três vezes.

A relação é muitos-para-muitos **implícita** — o Prisma mantém a tabela de junção
sozinho. Não há nada a guardar sobre a ligação em si (nem quem etiquetou, nem
quando), e uma tabela explícita seria um modelo a manter para carregar duas chaves.

O `PUT` substitui o conjunto inteiro, e não há rota de delta. É o que a tela sabe
dizer: o campo é uma caixa de texto separada por vírgula, e o que ela produz é "no
fim, são estas".

## Uma armadilha do Fastify que este trabalho revelou

`additionalProperties: false` no JSON Schema **não recusa** o campo desconhecido:
o Fastify roda o AJV com `removeAdditional`, então o campo é **removido** e a
requisição segue. E `minProperties: 1` não salva, porque o AJV conta as
propriedades **antes** de remover.

O efeito prático: `PATCH { "prioridadeee": "alta" }` passava pelas duas regras,
chegava ao handler com o corpo vazio, e respondia **200 com o chamado inteiro** —
fazendo quem chamou acreditar que gravou.

A correção é uma conferência no handler: se não sobrou campo conhecido, é 400. Ela
está em `PATCH /internal/chamados/:id` e em `PATCH /internal/setores/:id` (onde o
caso concreto é tentar renomear o `codigo`, que o schema não aceita justamente
porque é a chave estável de integração).

> [!warning] Vale para as outras rotas de PATCH
> `categorias.ts` e `pessoas.ts` têm a mesma forma de schema e a mesma brecha. Não
> foram alteradas neste trabalho porque os campos delas são poucos e conhecidos,
> mas a observação vale se alguém acrescentar campo lá.

## Onde a duplicação foi evitada

Dois caminhos escrevem exatamente os mesmos 24 campos: criar chamado no painel
(`POST /internal/tarefas`) e corrigir a classificação depois
(`PATCH /internal/chamados/:id`).

`src/internal/camposDeChamado.ts` existe para eles não terem duas listas de
campos, dois conjuntos de limites e duas validações de faixa. Ele guarda três
coisas e só elas: `PROPRIEDADES` (o JSON Schema), `Corpo` (o tipo) e `montarDados`
(a tradução para o Prisma, com o que o JSON Schema não alcança — `trim`, data ISO
válida, FK que existe de verdade).

O que **não** mora lá: `situacao` e `categoriaId`. As duas têm rota própria porque
a consequência da escrita é diferente — mudar situação é evento de atendimento
(histórico, marco de SLA, mensagem para o cliente); classificar é organização
interna. Juntá-las faria uma correção de digitação disparar WhatsApp.

O mesmo raciocínio vale no painel: `agrupar()` em `chamados.ts` é escrita uma vez
e usada três (assunto, setor, tipo), e `tabelaMetricas()` no `app.js` desenha as
três tabelas do resumo.

## O que mudou de contrato

Uma quebra, e vale saber dela:

**A linha de métrica passou a se chamar `id` no lugar de `categoriaId`.** A mesma
linha agora descreve grupo de assunto, de setor e de tipo, e um campo chamado
`categoriaId` dentro de um agrupamento por setor seria mentira. É nulo no grupo
"sem classificação" e nos grupos por `tipo` (cuja chave é o valor do enum, não uma
linha de tabela).

O único consumidor era o próprio painel, que não lia esse campo.

## O que ficou de fora

- **Pergunta de tipo na conversa** — decidido não fazer (ver acima). Se o volume
  de chamados sem tipo incomodar, o caminho é medir primeiro: o resumo por tipo já
  mostra quantos estão sem.
- **Tabela `Franquia`** — código e nome da unidade são texto livre. A rede é
  cadastrada em outro sistema, e uma tabela local seria uma segunda verdade sobre
  quais lojas existem. Quando houver integração, isto vira FK numa migração
  própria.
- **Lista de sistemas** — `sistemaAfetado` é texto pelo mesmo motivo: a lista não
  existe em lugar nenhum deste banco, e inventar uma tabela vazia seria pedir
  cadastro antes de o campo poder ser usado.
- **Eliminação por campo de contato** — `contato` e `franqueadoContato` são dado
  pessoal em chamados que podem não ter telefone, então `--esquecer <telefone>`
  não os alcança. Ver [[WA Segurança e LGPD]].
- **Detecção de ciclo longo** em dependências (ver acima).
- **Responder pelo painel.** Ler a conversa é rota de leitura; escrever é outra
  coisa: manda mensagem para pessoa real, precisa de rate limit e histórico
  próprios, e tem de entrar pela outbox para não perder envio numa queda da
  Evolution. A tela diz isso em vez de oferecer um campo de texto que não
  funcionaria.

## Ligações

- [[WA Banco de dados]] — o schema inteiro, índices e SQL cru
- [[WA Painel de chamados]] — como o quadro fala com a API
- [[WA Segurança e LGPD]] — o que a retenção alcança e o que não
- [[WA Testes e verificação]] — o que `test/classificacao.test.ts` cobre
- [[WA Pendências]] — o que este trabalho fechou e o que abriu
