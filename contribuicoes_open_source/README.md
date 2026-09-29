# Contribuições em Open Source — cal.com

[cal.com](https://github.com/calcom/cal.diy) é uma infraestrutura de agendamento de código
aberto escrita em TypeScript, distribuída como monorepo Yarn/Turbo com Next.js, tRPC e Prisma.
Na consulta feita em 29/09/2026 o repositório tinha 48.727 estrelas, 15.240 forks e 1.451
issues abertas.

Abri 16 Pull Requests nesse repositório entre 17 e 22/09/2026, corrigindo falhas em
utilitários de `packages/lib`, em integrações do `app-store` e no fluxo de cobrança de
reservas. Além dos PRs públicos, enviei um relatório de segurança por canal privado e
mantenho quatro correções em branches do fork sem PR aberto.

---

## Tabela de contribuições

| PR | O que estava errado | Arquivos | Linhas | Testes | Estado |
|---|---|---|---|---|---|
| [#30176](https://github.com/calcom/cal.diy/pull/30176) | Assinatura HMAC do webhook HitPay comparada com `!==`, vazando o resultado byte a byte | 3 | +189 −16 | 13 | Aberto |
| [#30186](https://github.com/calcom/cal.diy/pull/30186) | `extractBaseEmail("")` retornava `"@undefined"`, fazendo e-mails malformados diferentes comparar como iguais | 2 | +112 −3 | 9 | Aberto (draft) |
| [#30187](https://github.com/calcom/cal.diy/pull/30187) | Telefone vazio gerava o e-mail `"@sms.cal.com"` para toda reserva, fundindo participantes distintos numa identidade só | 3 | +108 −7 | 5 | Aberto (draft) |
| [#30218](https://github.com/calcom/cal.diy/pull/30218) | `safeStringify` lançava exceção em referência circular e em `BigInt`, e devolvia o objeto cru em vez de string | 2 | +223 −8 | 14 | Aberto (draft) |
| [#30222](https://github.com/calcom/cal.diy/pull/30222) | Qualquer código de erro começando com `P` era tratado como erro do Prisma, e o log usava `JSON.stringify` sem proteção | 2 | +168 −5 | 8 | Aberto (draft) |
| [#30216](https://github.com/calcom/cal.diy/pull/30216) | `fromEntriesWithDuplicateKeys` duplicada em dois pacotes, com `hasOwnProperty` acessado pela instância e sem proteção de `__proto__` | 4 | +208 −51 | 12 | Aberto (draft) |
| [#30175](https://github.com/calcom/cal.diy/pull/30175) | Taxa de no-show dividida por 100 mesmo em moedas sem centavos, exibindo ¥500 como ¥5 | 5 | +71 −9 | 5 | Aberto |
| [#30174](https://github.com/calcom/cal.diy/pull/30174) | Regex do link de WhatsApp aceitava `wa.me/send?phone=` e URLs não ancoradas ([issue #30118](https://github.com/calcom/cal.diy/issues/30118)) | 2 | +40 −2 | 1 | Aberto |
| [#30183](https://github.com/calcom/cal.diy/pull/30183) | Patch do link do Google Meet reenviava "Updated invitation" a todos os convidados ([issue #30112](https://github.com/calcom/cal.diy/issues/30112)) | 2 | +5 | 20 | Aberto (draft) |
| [#30217](https://github.com/calcom/cal.diy/pull/30217) | `isKeyInObject` lançava `TypeError` com `null` e respondia `true` para chaves herdadas de `Object.prototype` | 2 | +139 −1 | 12 | Aberto (draft) |
| [#30189](https://github.com/calcom/cal.diy/pull/30189) | `getSafe` lançava exceção quando o caminho recebido não era um array | 2 | +81 −3 | 6 | Aberto (draft) |
| [#30185](https://github.com/calcom/cal.diy/pull/30185) | `stripMarkdown` lançava exceção com `null` ou `undefined` | 2 | +59 −1 | 4 | Aberto (draft) |
| [#30188](https://github.com/calcom/cal.diy/pull/30188) | Lista de 40 fusos recriada a cada chamada e varrida com busca linear | 2 | +75 −42 | 3 | Aberto (draft) |
| [#30215](https://github.com/calcom/cal.diy/pull/30215) | `isEqual` dava `true` para datas diferentes, `false` para `NaN === NaN` e igualava `[1]` a `{0:1}` | 2 | +307 −14 | 29 | Aberto (draft) |
| [#30184](https://github.com/calcom/cal.diy/pull/30184) | `formatPhoneNumber` propagava a exceção de `parsePhoneNumberWithError` em vez de devolver a entrada | 2 | +38 −2 | 4 | Aberto (draft) |
| [#30219](https://github.com/calcom/cal.diy/pull/30219) | `fetchWithTimeout` ignorava o `AbortSignal` do chamador e deixava o timer segurando o event loop | 2 | +207 −5 | 8 | Aberto (draft) |

Total: 16 PRs, 2.030 linhas adicionadas, 169 removidas, 153 casos de teste.

---

## Falha de segurança

### Comparação de HMAC sujeita a ataque de tempo — webhook HitPay

[PR #30176](https://github.com/calcom/cal.diy/pull/30176) · `packages/app-store/hitpay/`

O handler do webhook de pagamento do HitPay comparava a assinatura recebida com a calculada
usando `!==` sobre strings hexadecimais. `!==` retorna no primeiro byte diferente, e o tempo
gasto até o retorno revela quantos bytes iniciais do palpite estavam corretos. Isso permite
recuperar uma assinatura válida byte a byte e forjar notificações de pagamento.

```ts
// antes
const signed = generateSignatureArray(saltKey, excluded);
if (signed !== obj.hmac) { /* rejeita */ }

// depois
if (!isValidWebhookSignature(saltKey, excluded, obj.hmac)) { /* rejeita */ }
```

A verificação foi extraída para `lib/verifyWebhookSignature.ts` e passou a usar
`timingSafeEqual` do `node:crypto`. Como `timingSafeEqual` exige buffers de tamanho igual, o
tamanho é checado antes — o comprimento de um digest SHA-256 em hexadecimal é fixo e público,
então essa checagem não vaza nada.

### Relatório privado

Encontrei também uma falha de autorização no roteador tRPC de webhooks. Ela foi reportada
pelo canal privado de segurança do projeto e está em triagem. Esta página não descreve o
problema nem a correção, porque o relatório ainda não é público — a correção está na branch
`fix/webhook-team-authorization` do fork, com 557 linhas e 24 casos de teste, e será
detalhada aqui quando o advisory for publicado.

---

## Bugs com chamador real

Em cada caso abaixo eu contei, por busca no código do repositório, quantos arquivos importam
o módulo corrigido. Esse número é o alcance real da mudança.

### `safeStringify` quebrava exatamente no caso para o qual foi escrita

[PR #30218](https://github.com/calcom/cal.diy/pull/30218) · `packages/lib/safeStringify.ts` · **78 arquivos importam este módulo**

A função existe para garantir que o sistema de log receba sempre uma string. Ela não fazia
isso: `JSON.stringify` sem replacer lança `TypeError` em referência circular e em `BigInt`, e
o `catch` devolvia `obj` — o próprio objeto, não uma string. O tipo de retorno era inferido
como `string | unknown`.

A primeira versão que escrevi usava um `WeakSet` de tudo já visto. Os testes mostraram que
isso marca como `[Circular]` um objeto referenciado duas vezes como irmão, que é um grafo
acíclico, não um ciclo. A versão final compara contra a cadeia de ancestrais atual,
desempilhada via `this` que o `JSON.stringify` passa ao replacer:

```ts
while (ancestors.length > 0 && ancestors[ancestors.length - 1] !== this) {
  ancestors.pop();
}
if (ancestors.indexOf(value) !== -1) return "[Circular]";
ancestors.push(value);
```

### `extractBaseEmail` fabricava o domínio `undefined`

[PR #30186](https://github.com/calcom/cal.diy/pull/30186) · `packages/lib/extract-base-email.ts` · **5 arquivos importam este módulo**

A função remove o sufixo `+tag` do e-mail para que `a+x@b.com` e `a@b.com` sejam reconhecidos
como a mesma pessoa. Ela fazia `email.split("@")` e interpolava o resultado sem verificar se
havia `@`. Com entrada `""` o retorno era `"@undefined"`; com `"notanemail"`, era
`"notanemail@undefined"`.

Um dos chamadores é `BookingAttendeesRemoveService`, que usa o retorno para casar participantes
a remover. Duas entradas malformadas diferentes viravam a mesma string e passavam a casar entre
si.

```ts
// antes
const [localPart, domain] = email.split("@");
return `${baseLocalPart}@${domain}`;

// depois
if (!email.includes("@")) return email;
const [localPart, ...domainParts] = email.split("@");
return `${baseLocalPart}@${domainParts.join("@")}`;
```

O `...domainParts` também corrige o caso de e-mail com mais de um `@`, em que o domínio era
truncado silenciosamente.

### Telefone vazio dava a todos os participantes a mesma identidade

[PR #30187](https://github.com/calcom/cal.diy/pull/30187) · `packages/lib/contructEmailFromPhoneNumber.ts`

Reservas por SMS derivam um e-mail sintético do telefone. A função removia só o `+` e
concatenava o resto com `@sms.cal.com`. Um campo de telefone opcional não preenchido chega
como `""`, e o retorno era `"@sms.cal.com"` — o mesmo para toda reserva nessa situação.

Havia um segundo problema: `isValidPhoneNumber("+55 11 99999-8888")` retorna `true` na
biblioteca usada pelo projeto, ou seja, números com espaço e hífen passam pela validação e
geravam endereços com espaço no meio. A correção troca `replace(/\+/g, "")` por
`replace(/\D/g, "")` e retorna `""` quando não sobra dígito algum. O chamador
`getCalEventResponses` passou a lançar o erro 400 que já existia ali para o caso de campo
ausente.

### Erros não-Prisma tratados como erros de banco

[PR #30222](https://github.com/calcom/cal.diy/pull/30222) · `packages/lib/redactError.ts` · **4 arquivos importam este módulo**

`redactError` substitui a mensagem de erros do Prisma por um texto genérico, para não vazar
detalhes do schema. A detecção olhava se `error.code` começava com `"P"`, o que também captura
`PARSE_ERROR`, `PERMISSION_DENIED` e qualquer outro código com essa inicial — esses erros
chegavam ao chamador mascarados como falha de banco. Códigos do Prisma têm formato fixo:

```ts
const PRISMA_ERROR_CODE = /^P\d{4}$/;
```

No mesmo arquivo, o log usava `JSON.stringify(error)` direto, que lança em erro com referência
circular. Passou a usar `safeStringify`.

### Função duplicada em dois pacotes, com duas falhas

[PR #30216](https://github.com/calcom/cal.diy/pull/30216) · `packages/lib/`, `packages/embeds/embed-core/`

`fromEntriesWithDuplicateKeys` converte query params repetidos em array. Existiam duas copias
independentes: uma em `packages/lib` sem nenhum chamador, outra privada dentro de
`useRouterQuery.ts`. Uma terceira cópia vive no `embed-core` e precisa continuar lá, porque
esse pacote é publicado no npm e não pode depender de pacote privado — o próprio código
documenta isso.

Duas falhas nas três cópias:

```ts
// antes: quebra quando um param se chama "hasOwnProperty"
if (result.hasOwnProperty(key)) { ... }

// depois
if (Object.prototype.hasOwnProperty.call(result, key)) { ... }
```

E atribuir a chave `__proto__` num objeto literal invoca o setter de `Object.prototype` e pode
trocar o protótipo do resultado, então essa chave é descartada. Só ela: `constructor` e as
outras apenas sombreiam um membro herdado e seguem como dado comum.

A cópia de `packages/lib` passou a ser a usada por `useRouterQuery.ts`, e a privada foi
removida. O `Array.from(entries)` foi necessário porque `for...of` sobre um `Iterable` puro
exige `downlevelIteration`, que o repositório não habilita com `target: es5`.

### Taxa de no-show errada em moedas sem centavos

[PR #30175](https://github.com/calcom/cal.diy/pull/30175) · 5 arquivos · **`currencyConversions` é importado por 10 arquivos**

Quatro pontos do código dividiam o valor da cobrança por 100 para exibir. Isso vale para USD e
BRL, mas não para JPY, KRW, VND e as outras moedas sem subunidade, em que o valor armazenado
já está na unidade apresentável. Uma taxa de ¥500 aparecia como ¥5 na tela de cancelamento, no
diálogo de cobrança e em dois templates de e-mail.

```ts
// antes
amount: booking.payment.amount / 100,

// depois
amount: convertFromSmallestToPresentableCurrencyUnit(
  booking.payment.amount,
  booking.payment.currency
),
```

A função de conversão já existia no repositório e já era usada em outros 10 arquivos. O bug
era esses quatro pontos não a usarem.

### Regex de link do WhatsApp aceitava o formato errado

[PR #30174](https://github.com/calcom/cal.diy/pull/30174) · [issue #30118](https://github.com/calcom/cal.diy/issues/30118)

A issue relata que o campo de localização do WhatsApp gera URL inválida. O regex de validação
no `config.json` era `^http(s)?:\/\/(www\.)?wa.me\/[a-zA-Z0-9]*`: sem `$` no fim, com o ponto
de `wa.me` não escapado (casando `waXme`) e com `[a-zA-Z0-9]*` aceitando string vazia. O
placeholder mostrado ao usuário sugeria justamente o formato quebrado, `wa.me/send?phone=`.

```
^https?:\/\/(www\.)?wa\.me\/(?:[0-9]{7,15}|(?:message|qr)\/[A-Za-z0-9]+)(?:\?[^\s]*)?$
```

### Google Calendar reenviava convite a cada patch do link do Meet

[PR #30183](https://github.com/calcom/cal.diy/pull/30183) · [issue #30112](https://github.com/calcom/cal.diy/issues/30112)

Ao anexar o link do Meet a um evento já criado, o código chamava `events.patch` sem o
parâmetro `sendUpdates`. O padrão da API do Google nesse caso dispara e-mail de "Updated
invitation" para todos os convidados, que recebiam dois e-mails por reserva. A correção passa
`sendUpdates: "none"` nas três chamadas de patch que só escrevem a conferência.

### Utilitários que lançavam exceção com entrada nula

Três correções do mesmo tipo, em funções cuja assinatura prometia aceitar a entrada que
quebrava:

- [PR #30217](https://github.com/calcom/cal.diy/pull/30217) — `isKeyInObject` fazia `k in o`
  direto: `TypeError` com `null`, e `true` para `"toString"`, herdado de `Object.prototype`.
  Passou a usar `Object.hasOwn`.
- [PR #30189](https://github.com/calcom/cal.diy/pull/30189) — `getSafe` chamava `path.reduce`
  sem checar se `path` era array.
- [PR #30185](https://github.com/calcom/cal.diy/pull/30185) — `stripMarkdown` operava sobre a
  string sem checar `null`.

---

## Performance

### Lista de fusos recriada a cada chamada

[PR #30188](https://github.com/calcom/cal.diy/pull/30188) · `packages/lib/isProblematicTimezone.ts`

A função declarava um array literal de 40 fusos horários dentro do próprio corpo e fazia
`includes` nele. Cada chamada alocava o array de novo e varria até 40 strings. O array virou
um `Set` no escopo do módulo, criado uma vez, com consulta por hash.

### Duas buscas quadráticas no round-robin

Branch `fix/lucky-user-quadratic-lookups` · `packages/features/bookings/lib/getLuckyUser.ts` ·
sem PR aberto

`getLuckyUser` escolhe o anfitrião de uma reserva round-robin. Dentro do laço sobre os
anfitriões disponíveis havia um `attributeWeights.find` e um
`bookingsOfAvailableUsersOfInterval.filter` com um `attendees.some` aninhado — O(n²) e O(n·m)
sobre dados que crescem com o tamanho do time e o volume de reservas do intervalo.

As duas buscas foram substituídas por `Map` construídos uma vez antes do laço. O agrupamento
de reservas por participante usa `Set` na união, porque uma mesma reserva pode casar pelo
`userId` e pelo e-mail do participante ao mesmo tempo, e o `filter` original a contava uma vez
só. Verifiquei a equivalência com 20.000 entradas geradas aleatoriamente comparando a saída
antiga e a nova.

---

## Limpeza

- Branch `fix/json-utils-safe-parsing-and-tests` — `validJson` imprimia o erro de parse com
  `console.log` a cada string inválida, em produção. Um JSON inválido é um resultado negativo
  normal dessa função, já comunicado pelo `false` de retorno. O retorno também passou a ser
  genérico (`<T>`), evitando `any` nos chamadores. Sem PR aberto.
- Branch `fix/bookings-procedure-drops-unused-credentials` — a procedure de reservas do tRPC
  buscava `credentials: true` do usuário e nunca lia o resultado. Credencial de app é dado
  sensível; o projeto tem regra explícita de nunca retornar `credential.key`. As três linhas
  foram removidas. Sem PR aberto.

---

## Três PRs que corrigem código sem chamador

Ao contar os importadores de cada módulo, três deram zero:

| Módulo | PR | Importadores |
|---|---|---|
| `packages/lib/isEqual.ts` | [#30215](https://github.com/calcom/cal.diy/pull/30215) | 0 |
| `packages/lib/formatPhoneNumber.ts` | [#30184](https://github.com/calcom/cal.diy/pull/30184) | 0 |
| `packages/lib/fetchWithTimeout.ts` | [#30219](https://github.com/calcom/cal.diy/pull/30219) | 0 |

Os bugs são reais — `isEqual(new Date("2020-01-01"), new Date("2026-12-31"))` retornava `true`,
porque a comparação caía no ramo de objeto e as duas datas têm zero chaves próprias. Mas
nenhum arquivo do repositório importa esses três módulos, então nenhum usuário é afetado hoje.
Registro isso aqui porque é o tipo de informação que decide se um PR vale a atenção de um
mantenedor, e omiti-la tornaria o resto desta página menos confiável.

---

## Status atual

Verificado em 29/09/2026 pela API do GitHub:

- **16 PRs abertos, nenhum fechado ou mergeado.**
- **Nenhum recebeu revisão humana.** A busca `is:pr author:TassioSales repo:calcom/cal.diy
  review:none` retorna todos os 16.
- 13 estão em draft; 3 não (#30174, #30175, #30176).
- Nenhum tem a label que libera a execução dos jobs de CI para PR externo, então os testes do
  projeto não rodaram em nenhum deles. Os testes que escrevi foram executados localmente.
- 4 branches estão no fork sem PR aberto: `fix/webhook-team-authorization` (retido por ser
  segurança, reportada em canal privado), `fix/lucky-user-quadratic-lookups`,
  `fix/json-utils-safe-parsing-and-tests` e
  `fix/bookings-procedure-drops-unused-credentials`.
- 1 relatório de segurança em triagem pelo canal privado do projeto.

O cal.com tem 1.451 issues abertas e 15.240 forks. A ausência de revisão diz respeito ao
volume de contribuição externa que o projeto recebe, não ao conteúdo dos PRs.

---

## Como eu encontrei esses bugs

Não foi leitura de código à procura de algo estranho. Foi um procedimento repetido arquivo por
arquivo, sempre na mesma ordem:

**1. Escolher o alvo por alcance, não por curiosidade.** `packages/lib` concentra utilitários
puros, sem dependência de banco nem de rede. São as funções mais chamadas do monorepo e as
mais fáceis de testar em isolamento. Contei os importadores de cada uma antes de decidir onde
gastar tempo:

```bash
grep -rl "lib/safeStringify\"" --include='*.ts' --include='*.tsx' . | grep -v node_modules | wc -l
```

**2. Escrever o teste antes de olhar o bug.** Para cada função, escrevi os casos que a
assinatura promete suportar: `null`, `undefined`, string vazia, entrada do tipo errado, valor
duplicado, referência circular, `NaN`, data inválida. Rodando com o Vitest do próprio
repositório:

```bash
TZ=UTC yarn vitest run packages/lib/safeStringify.test.ts
```

Foi esse passo que achou a maior parte das falhas. O caso `extractBaseEmail("")` retornando
`"@undefined"` apareceu como teste vermelho, não como suspeita.

**3. Reproduzir antes de afirmar.** Nenhuma correção foi enviada com base em leitura. Cada bug
tem um script que demonstra o comportamento errado na versão original. No caso do
`safeStringify`, foi esse passo que mostrou que a minha primeira correção, com `WeakSet`,
estava errada: ela marcava como `[Circular]` um objeto irmão repetido.

**4. Procurar o chamador para decidir se importa.** Um bug numa função sem chamador não afeta
ninguém. Foi assim que descobri que três dos meus PRs mexem em código morto, e foi assim que
descobri que o `extractBaseEmail` é usado justamente para casar participantes a remover — o
que transformou um retorno esquisito num problema de identidade.

**5. Rodar a ferramenta real do projeto, não a que eu supunha.** Aqui eu errei primeiro. Rodei
`biome check` e concluí que sete branches tinham erro de lint. O CI do projeto roda
`biome lint`, que é um subconjunto: nenhuma branch tinha erro. Também usei o `tsconfig.json`
de `packages/lib` como referência de target, quando esse pacote não tem script de type-check —
a checagem acontece transitivamente por `apps/web`, com configuração diferente. Conferir qual
comando o CI executa de fato vem antes de confiar no resultado local.

**Convenção do pacote antes da preferência pessoal.** Nos testes que escrevi, eu havia
removido a linha em branco entre os imports de pacote e os relativos. Todos os testes
existentes de `packages/lib` têm essa linha. Reescrevi e refiz o push.
