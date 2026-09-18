---
tags: [projeto/whatsapp-suporte, bug, postmortem, banco]
projeto: whatsapp-suporte
atualizado: 2026-08-27
descoberto: 2026-08-17
reincidiu: 2026-08-18
---

# WA Fuso horário sem timezone

Volta para [[WhatsApp Suporte]] · contexto em [[WA Outbox e entrega]] e
[[WA Banco de dados]].

> [!important] Esta nota é histórico — o banco hoje é SQLite
> As duas causas descritas aqui eram **do Postgres** e não existem mais: em
> 2026-08-27 o banco passou a ser um arquivo SQLite, onde não há fuso de sessão
> para herdar e a data é gravada como texto ISO-8601 com offset explícito, sempre
> em UTC.
>
> O que **não** mudou é o lugar: a comparação de data em SQL crua na reserva da
> outbox. A armadilha equivalente no SQLite está em
> [[#E depois da troca para SQLite: a terceira forma do mesmo erro]], no fim
> desta nota. Leia essa seção antes de mexer em qualquer `WHERE` com data — o
> resto do documento explica **por que** essa parte do código merece
> desconfiança, e vale por isso.

O bug mais interessante do projeto até agora: **pré-existente, silencioso, e
invisível para os testes em memória**. Apareceu no primeiro teste ao vivo contra
um Postgres de verdade, em 2026-08-17.

E **voltou em 2026-08-18**, por um caminho completamente diferente, na subida
para o Prisma 7 — ver [[#Reincidência: o Prisma 7 trouxe o mesmo sintoma de volta]]
no fim desta nota. A mesma classe de bug, duas causas distintas, o mesmo
sintoma. Vale ler as duas.

## Sintoma

O varredor da outbox **não reenviava nada**. O README prometia "reenvia a cada
minuto"; na prática a mensagem só ficava elegível depois de completar
**~3 horas** de idade.

## Causa

Duas convenções de data se cruzando:

- as colunas `DateTime` do Prisma são `TIMESTAMP(3)` — **sem fuso** — e o Prisma
  grava **UTC** nelas;
- `now()` no Postgres é `timestamptz` — **com fuso**.

Comparar os dois em SQL cru faz o Postgres reinterpretar o valor sem fuso como
hora **local**. Em UTC−3, toda linha pendente parecia estar três horas **no
futuro**:

```
diff_seg_contra_now : -10799.98     <- 2h59m59s "no futuro"
menor_que_now       : false
menor_que_now_utc   : true
```

Como o filtro do varredor é
`coalesce("ultimaTentativaEm", "timestamp") < now() - espera`, nada era elegível
antes de a linha envelhecer o suficiente para compensar as 3 horas.

> [!note] Dependia do fuso da máquina
> A oeste de Greenwich (Brasil), o varredor ficava **inerte**. A leste, falharia
> ao contrário: disparando cedo demais e ignorando o intervalo de 30s entre
> tentativas. Um bug que muda de sintoma conforme o servidor onde roda.

## Por que a suíte não pegou

O dublê em memória ([test/fake-prisma.ts](../test/fake-prisma.ts)) **reimplementa
em JavaScript** a regra de elegibilidade da reserva. Comparação de `Date` em JS
não tem o problema que a comparação em SQL tem — então o teste passava
confirmando a orquestração em volta da query, não a query.

É exatamente a lacuna nº 4 registrada em [[WA Testes e verificação]], e o motivo
de `npm run dev:verificar-banco` existir.

## Primeira correção: no ponto de uso (hoje já substituída)

[whatsapp/outbox.ts](../src/whatsapp/outbox.ts) passou a comparar contra
`now() AT TIME ZONE 'UTC'`, trazendo o `now()` para a convenção das colunas. Foi
o suficiente para o varredor voltar a funcionar, mas deixava a armadilha viva: o
**próximo** `WHERE` com data em SQL cru repetiria o erro, e o `AT TIME ZONE`
parecia ruído removível para quem lesse depois. Substituída pela correção
definitiva abaixo.

Prova de que a recuperação passou a funcionar sem nenhuma ajuda (Graph derrubada
de propósito e depois restaurada; nada feito à mão depois disso):

```
3) resposta gravada: enviadaEm=null tentativas=1
   proxima tentativa so depois de 30s x 2^1 = 60s
4) Graph de volta. A partir daqui NADA e feito manualmente:
   +20s  ainda pendente      +60s  ainda pendente
   +65s  ENTREGUE pelo varredor (tentativas=2)
```

Antes da correção, esse mesmo cenário levaria 3 horas.

## Correção definitiva — feita em 2026-08-17

Migração
[`20260817190000_datas_com_fuso`](../prisma/migrations/20260817190000_datas_com_fuso/migration.sql):
as **7** colunas de data passaram de `TIMESTAMP(3)` para `TIMESTAMPTZ(3)`, e o
schema declara `@db.Timestamptz(3)` em todas. Isso torna a classe de bug
impossível, em vez de corrigida em um ponto de uso.

Três detalhes que a migração precisou tratar:

- **`USING <coluna> AT TIME ZONE 'UTC'` é obrigatório.** Sem isso o Postgres
  converte assumindo o fuso da *sessão* e **desloca todos os valores já
  gravados** (em UTC−3, três horas para trás). Com isso, o instante é preservado:
  o valor naive é lido como UTC, que é a convenção do Prisma.
- **A view teve de ser derrubada e recriada.** O Postgres recusa `ALTER TYPE` em
  coluna referenciada por view, e `chamados_para_cards` seleciona
  `Chamado.dataAbertura`. **`DROP`/`CREATE` não preserva `GRANT`** — reaplicar o
  `GRANT SELECT` do usuário de leitura é passo obrigatório de deploy. Ver
  [[WA Pendências]].
- **O código teve de mudar junto**, no mesmo commit: com coluna `timestamptz`, o
  `now() AT TIME ZONE 'UTC'` que *corrigia* o bug passa a **causá-lo ao
  contrário**.

Verificação: 85 testes + 20 checagens de banco passando, sem drift entre schema e
banco (`prisma migrate diff` → *No difference detected*), instantes preservados
nas 19 mensagens e 2 chamados que já existiam, e a recuperação real medida de
novo, idêntica a antes:

```
resposta gravada: enviadaEm=null tentativas=1
   proxima tentativa so depois de 30s x 2^1 = 60s
Graph de volta. Daqui em diante NADA e feito manualmente:
   +20s / +40s / +60s  ainda pendente
   +65s  ENTREGUE pelo varredor (tentativas=2)
```

## Regra que valia no Postgres

> [!danger] Em SQL cru, compare com `now()` **puro**
> E **não acrescente** `AT TIME ZONE 'UTC'` "por segurança": sobre coluna
> `timestamptz` isso produz um valor sem fuso e traz o bug de volta invertido —
> disparando cedo demais e ignorando a espera entre tentativas.

Isto valia enquanto o banco era Postgres. A regra de hoje está em
[[#E depois da troca para SQLite: a terceira forma do mesmo erro]].

Código via Prisma (`where: { campo: { lt: data } }`) nunca sofreu disso, nos dois
bancos: a data vai como parâmetro.

## Reincidência: o Prisma 7 trouxe o mesmo sintoma de volta

Data: 2026-08-18, durante a subida de dependências. **A migração de
`timestamptz` continua certa e não foi desfeita** — o que mudou foi quem abre a
conexão.

### O que aconteceu

Até o Prisma 5, quem falava com o Postgres era o motor em Rust, e ele **fixava a
sessão em UTC** por conta própria. O Prisma 7 troca esse motor por um *driver
adapter* (`@prisma/adapter-pg`, o `pg` puro), e o adaptador **não fixa nada**: a
sessão herda o fuso do servidor.

Com o Postgres local em `America/Sao_Paulo`, uma data enviada como
`2026-08-18 13:47:55` — os dígitos **UTC**, sem offset — passou a ser lida pelo
Postgres como hora **local** e gravada como `16:47:55` UTC. Três horas **no
futuro**. De novo.

```
JS escreveu (UTC real):  2026-08-18T13:47:55.644Z
guardado no Postgres  :  2026-08-18 13:47:55.644-03   <- 16:47:55 UTC
now()                 :  2026-08-18 10:49:55.860-03   <- 13:49:55 UTC
esta_no_futuro        :  true
```

### Por que passou despercebido

> [!danger] Isso não é teórico
> O varredor da outbox voltou a ficar inerte, e o
> `npm run dev:verificar-banco` acusou **5 falhas** nas seções 4 e 5 — reserva
> de pendentes e recuperação de ponta a ponta.

O que torna essa classe de bug traiçoeira é que **o round-trip pelo Prisma
esconde tudo**: ele converte de volta na leitura, então `findMany` devolvia a
data certa e os 111 testes em memória seguiram verdes. Só a SQL crua que compara
com `now()` enxerga a diferença.

### A correção

Uma linha, no pool, em [client.ts](../src/db/client.ts):

```ts
const adaptador = new PrismaPg({
  connectionString: config.databaseUrl,
  options: '-c timezone=UTC', // NÃO REMOVA
  // ...
});
```

> [!danger] Não remova o `options: '-c timezone=UTC'`
> É ele que segura de pé a migração `20260817190000_datas_com_fuso`. Sem ele,
> **toda** data escrita pelo sistema nasce deslocada pelo fuso do servidor — e
> nenhum teste em memória avisa.

### O que ficou de guarda

O `dev:verificar-banco` ganhou a **checagem 0**: confere o `TimeZone` da sessão
e prova que uma data recém-gravada não aparece no futuro para o `now()` do
banco. Foi verificada nos dois sentidos — sabotando a correção de propósito, ela
acusa `diferença=10800s`; com a correção, `0s`.

E, principalmente: essa checagem **agora roda no CI**, no job `banco`, contra um
Postgres de verdade (ver [[WA Testes e verificação]]). Da primeira vez o bug
esperou um teste manual para aparecer. Da segunda, apareceu sozinho.

## E depois da troca para SQLite: a terceira forma do mesmo erro

Data: 2026-08-27. O banco passou a ser um arquivo SQLite (ver
[[WA Banco de dados]]), e com isso as duas causas acima **deixaram de existir**:

- não há `timestamptz` nem `TIMESTAMP` — o SQLite não tem tipo de data, e o Prisma
  grava texto ISO-8601 com o offset explícito: `2026-08-27T19:57:00.604+00:00`,
  sempre UTC;
- não há fuso de **sessão** para herdar, então não há `-c timezone=UTC` para
  esquecer. A migração `20260817190000_datas_com_fuso` e o `options` do adaptador
  saíram junto, os dois sem substituto porque nada os substitui.

O que sobrou é a terceira versão do mesmo erro, e ela é mais fácil de cometer que
as duas anteriores porque parece certa ao ler:

```sql
-- ERRADO: comparação de TEXTO
WHERE coalesce("ultimaTentativaEm", "timestamp") < datetime('now')
```

`datetime('now')` devolve `2026-08-27 19:57:00`: **espaço** em vez de `T`, sem
milissegundo, sem offset. Comparado como texto com o valor da coluna, o `T` (0x54)
é maior que o espaço (0x20) — então a coluna é sempre "maior que agora" e **toda**
pendente parece estar no futuro. O sintoma é idêntico ao de 2026-08-17: varredor
inerte, sem erro nenhum no log.

> [!danger] A regra de hoje: converta as duas pontas para número
> ```sql
> WHERE unixepoch(coalesce("ultimaTentativaEm", "timestamp"), 'subsec')
>     < unixepoch('now', 'subsec') - (30 * pow(2, tentativas))
> ```
> `unixepoch()` entende o offset do texto gravado, então a conta é sempre correta.
>
> E ao **gravar** data em SQL crua, passe um `Date` como parâmetro
> (`${new Date()}`) em vez de deixar o SQLite escrever com `datetime('now')` — o
> Prisma serializa no formato dele, e um valor sem offset na coluna faria a
> varredura seguinte ler errado.

### O que ficou de guarda

A **checagem 0** do `dev:verificar-banco` mudou de assunto junto com o banco: em
vez do `TimeZone` da sessão, ela agora confere o **formato gravado** (a coluna
guarda texto? o texto casa com `ISO-8601 + 00:00`?) e, como antes, que uma data
recém-gravada não aparece no futuro para o `now()` do banco.

A primeira metade dessa checagem existe por um motivo específico: o adaptador do
SQLite tem uma opção `timestampFormat` que pode gravar epoch em milissegundos em
vez de texto. Se ela mudar — por padrão novo, ou por alguém "otimizando" — a SQL
de reserva quebra silenciosamente. É a checagem 0 que acusa.

## Como pegar esse tipo de coisa antes

1. `npm run dev:verificar-banco` antes de qualquer deploy que mexa em transação
   ou SQL cru — e ele roda sozinho no CI a cada push desde 2026-08-18. Trocar
   **quem abre a conexão** (driver, ORM, banco) conta como mexer nisso: foi assim
   que o bug voltou a segunda vez, e é o que valida a terceira.
2. Desconfiar de comportamento **baseado em tempo** que "nunca acontece" em vez
   de acontecer errado — silêncio é o sintoma mais fácil de ignorar.
3. Onde o dublê de teste **reimplementa** regra que o banco deveria aplicar,
   assumir que a regra não está testada.
