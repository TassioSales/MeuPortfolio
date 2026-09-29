# edge-audit

Aponte para um arquivo TypeScript e receba a lista de funções que quebram em casos-limite.
Você não escreve teste nenhum, não escreve propriedade nenhuma, não configura nada.

```bash
npx edge-audit "src/**/*.ts"
```

Saída real rodando contra `packages/lib` do [cal.com](https://github.com/calcom/cal.com):

```
ARQUIVO                   FUNÇÃO                   ENTRADA                       REGRA  O QUE ACONTECEU
-------------------------------------------------------------------------------------------------------
extract-base-email.ts     extractBaseEmail         ("")                          c      devolveu "@undefined" contendo "undefined"
random.ts                 randomString             (Infinity)                    d      não retornou em 15s ou passou de 512 MB
LinkBuilder.ts            buildCancelLink          ({ uid, bookerUrl })          a      TypeError: Invalid URL
piiFreeData.ts            getPiiFreeCredential     (undefined)                   a      TypeError: Cannot read properties of undefined
currencyConversions.ts    formatPrice              (0, undefined, "")            a      RangeError: Incorrect locale information provided
array.ts                  uniqueBy                 ([undefined], [undefined])    a      TypeError: Cannot read properties of undefined

18 falhas em 63 funções auditadas (906 chamadas).
```

## Como funciona

1. Lê a assinatura de cada função exportada com [ts-morph](https://ts-morph.com): nome, tipo de
   cada parâmetro, tipo de retorno.
2. Para cada parâmetro, monta as entradas hostis que aquele tipo admite:

   | Tipo declarado | Entradas geradas |
   |---|---|
   | `string` | `""`, `" "`, `"0"`, `"a\nb"`, string de 10.000 caracteres |
   | `number` | `0`, `-0`, `NaN`, `Infinity`, `-Infinity`, `MAX_SAFE_INTEGER` |
   | `boolean` | `true`, `false` |
   | `T[]` | `[]`, `[undefined]`, array de 1.000 posições |
   | `object`, `Record`, tudo opcional | `{}`, objeto com referência circular, objeto com chave `__proto__` |
   | objeto com propriedade obrigatória | objeto com essas propriedades preenchidas |
   | `Date` | `new Date("invalido")`, `new Date(0)` |
   | união | um valor por membro |
   | opcional ou anulável | `undefined`, `null`, mais o acima |

3. Chama a função com o produto cartesiano dessas entradas, no máximo 200 combinações por função.
4. Reporta quando uma destas três regras é violada:

   | Regra | O que é |
   |---|---|
   | **a** | a função lançou exceção, e o tipo de retorno declarado não é `never` |
   | **b** | o `typeof` do retorno contradiz o tipo de retorno declarado |
   | **c** | o retorno é uma string contendo `undefined` ou `NaN` que nenhuma entrada de texto continha |
   | **d** | a chamada não retornou em 15 segundos, ou passou de 512 MB |

A regra **d** existe porque a ferramenta morria junto com o bug que encontrava. `randomString(Infinity)`
entra em loop concatenando string até o processo ser morto pelo sistema. Cada arquivo é auditado em
processo filho próprio, com orçamento de tempo e de memória, e a função que não volta é reportada em
vez de derrubar a execução.

A regra **c** é a que pega mais bug de verdade. Ela nasceu de um padrão repetido: a função
interpola um valor ausente na string e devolve algo como `"@undefined"` ou `"R$ NaN"`, que passa
pelo compilador porque o tipo continua sendo `string`.

## O que ele NÃO faz

Esta seção é a mais importante do README. Leia antes de usar.

**Só audita módulo puro.** Um arquivo só é auditado se todos os seus imports forem de tipo
(`import type`, ou named imports todos `type`). Qualquer arquivo que importe algo em tempo de
execução é pulado, e o motivo aparece no relatório.

Isso não é preguiça, é o que torna a abordagem possível: com todos os imports apagados na
compilação, o arquivo transpilado não tem dependência nenhuma para resolver, então pode ser
carregado e ter suas funções chamadas sem tocar banco, rede ou disco. Auditar um módulo que
importa dependência viva significaria **executar essa dependência com argumentos hostis** — não
faço isso.

**Pula função assíncrona.** Precisaria de `await`, e o que roda dentro de uma Promise costuma ter
efeito colateral.

**Pula o que não sei sintetizar:** parâmetro `rest`, parâmetro que é função, genérico que não se
resolve estaticamente. O relatório diz qual e por quê, em vez de chutar um valor e produzir uma
falha em que você não pode agir.

**Não pega bug semântico com tipo correto.** Esta função tem bug real e o edge-audit não acha:

```ts
export function emailFromPhone(phoneNumber: string): string {
  return `${phoneNumber.replace(/\+/g, "")}@sms.cal.com`;
}
```

Com telefone vazio ela devolve `"@sms.cal.com"` — o mesmo endereço para toda chamada, fundindo
pessoas diferentes numa identidade só. Mas é string válida, do tipo declarado, sem `undefined` e
sem `NaN`. Nenhuma das três regras se aplica. Detectar isso exigiria saber que o resultado precisa
identificar alguém, e esse conhecimento não está na assinatura.

Essa limitação está fixada em teste (`src/cli.test.ts`), para aparecer se alguém tentar escondê-la.

**Não reporta função que só roda no navegador.** Um `ReferenceError: window is not defined` significa
que a função precisa de DOM, não que está quebrada. Os globais `window`, `document`, `navigator`,
`localStorage`, `sessionStorage` e `location` são tratados assim, e a função aparece como pulada com o
motivo. Sem isso, a pasta de utilitários de qualquer aplicação web acenderia inteira.

## `--untrusted-input`

Por padrão o edge-audit respeita os tipos: não passa `null` a um parâmetro declarado `string`,
porque o compilador já impede essa chamada dentro de um projeto TypeScript.

Com `--untrusted-input` ele passa. Use quando a biblioteca é publicada e pode ser chamada de
JavaScript, onde o tipo declarado não é garantia de nada:

```bash
npx edge-audit "src/**/*.ts" --untrusted-input
```

## Opções

| Opção | Efeito |
|---|---|
| `--json` | saída em JSON, incluindo a lista completa de alvos pulados e o motivo de cada |
| `--untrusted-input` | passa `null` e `undefined` mesmo a parâmetros cujo tipo proíbe |
| `--help` | uso |

Exit code `1` quando acha alguma falha, `0` quando não acha. Serve para usar em CI.

## Prova

O teste que importa não é o suite, é o resultado contra código real. Rodando contra o `packages/lib`
do cal.com, na revisão anterior às correções que eu mesmo enviei para lá:

- **63 funções auditadas, 906 chamadas, 18 falhas**, em menos de dois minutos
- **86 alvos pulados**, cada um com o motivo registrado

Entre as 18, a ferramenta reencontrou sozinha o `extractBaseEmail("")` devolvendo `"@undefined"` —
o mesmo defeito que eu havia achado à mão lendo o arquivo, e que virou o
[PR #30186](https://github.com/calcom/cal.diy/pull/30186). Achar de novo, sem que ninguém dissesse
onde olhar, é o que a ferramenta precisava demonstrar.

A regra **d** também nasceu dessa execução: `randomString(Infinity)` derrubava a própria ferramenta.

Reproduza:

```bash
git clone --depth 1 https://github.com/calcom/cal.com /tmp/alvo
node dist/main.js "/tmp/alvo/packages/lib/*.ts"
```

## Desenvolvimento

```bash
npm install --legacy-peer-deps   # ver a nota abaixo
npm run typecheck                # tsc --noEmit
npm test                         # vitest
npm run build                    # gera dist/
node dist/cli.js "fixtures/*.ts" # roda contra os fixtures
```

`--legacy-peer-deps` é necessário no npm 10.9.7: o resolvedor de peer dependencies do vitest
dispara `TypeError: Cannot read properties of null (reading 'edgesOut')` dentro do arborist. Não é
problema deste projeto. Em npm 12 ou superior não é preciso.

A pasta `fixtures/` tem funções propositalmente quebradas, cada uma reproduzindo um bug real de
biblioteca de utilitários em produção, e um arquivo com o bug que a ferramenta **não** pega.

## Licença

MIT
