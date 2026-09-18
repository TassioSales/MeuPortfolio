# Painel de chamados

Quadro que lê os chamados abertos pelo bot de suporte do WhatsApp
(`../whatsapp-suporte`) direto do banco, e devolve a mudança de situação.

Sem IA em ponto nenhum: o painel só mostra o que está no banco e escreve de
volta pela API que já existia.

## Como as peças se encaixam

```
navegador                servidor do bot              SQLite (arquivo)
┌──────────────┐   GET /internal/chamados   ┌──────────┐          ┌──────────┐
│   painel     │ ─────────────────────────► │ Fastify  │ ───────► │ Chamado  │
│ (estático)   │ ◄───────────────────────── │ + Prisma │ ◄─────── │          │
│              │   PATCH .../situacao       └──────────┘          └──────────┘
└──────────────┘                                  │
                                                  └─► Graph API (avisa o usuário)
```

O navegador **não** fala com o banco — não existe driver de SQLite no browser, e o arquivo está no disco do servidor.
Quem lê o banco é o servidor do bot, que já tem o pool, o token e os schemas. O
painel continua sendo quatro arquivos estáticos, sem build e sem dependências.

## Colunas = situações do banco

Os ids das colunas em `data.js` são exatamente os valores do enum `Situacao`:

| coluna | `situacao` |
| --- | --- |
| A FAZER | `aberto` |
| EM ANDAMENTO | `em_andamento` |
| RESOLVIDO | `resolvido` |
| CANCELADO | `cancelado` |

Não existe tabela de conversão em lugar nenhum: arrastar um cartão para
"RESOLVIDO" manda literalmente `situacao: "resolvido"`. Se entrar uma situação
nova no schema do Prisma, ela entra aqui com o mesmo id e mais nada muda.

## Subir

### 1. No servidor do bot (`../whatsapp-suporte/.env`)

```bash
# A origem do PAINEL, não a do bot. Sem isto o navegador recusa a resposta.
PAINEL_ORIGENS=http://127.0.0.1:5500

# Opcional, e recomendado: token só do painel, revogável sem derrubar outras
# integrações. Sem ele, o painel usa o INTERNAL_API_TOKEN.
PAINEL_TOKEN=um_token_longo_e_aleatorio
```

E suba o servidor: `npm run dev`.

### 2. Aqui

`apiBaseUrl` em `data.js` precisa apontar para o servidor do bot
(padrão `http://127.0.0.1:3000`). Depois sirva esta pasta por HTTP:

```bash
python -m http.server 5500 --bind 127.0.0.1
# ou
npx serve -l 5500 .
```

> **Abrir o `index.html` direto do disco não funciona.** Em `file://` a origem
> vira `null` e nenhum CORS sensato a libera. Precisa ser servido por HTTP, na
> mesma porta que você listou em `PAINEL_ORIGENS`.

### 3. Conectar

Na primeira abertura o painel pede o token. Ele fica em `sessionStorage` e some
ao fechar a aba, a não ser que você marque **Lembrar neste navegador**.

O padrão é não lembrar de propósito: esse token altera chamado e dispara
mensagem de WhatsApp para uma pessoa real.

## O que o painel faz e o que não faz

**Faz**

- Lista os chamados, um cartão por chamado, com resumo, número, idade
  ("3 h", "2 d") e as iniciais do solicitante.
- Recarrega sozinho a cada 30 s (`atualizarASegundos` em `data.js`).
- Muda a situação ao arrastar o cartão ou pelo campo no detalhe. A tela atualiza
  na hora e **desfaz sozinha** se a API recusar.
- Busca por número, resumo, solicitante ou texto da descrição.

**Não faz, e é de propósito**

- **Criar chamado.** Chamado nasce na conversa do WhatsApp. Um cartão criado
  aqui não existiria no banco e sumiria na atualização seguinte.
- **Editar resumo, descrição ou solicitante.** Foram escritos pela pessoa na
  conversa, e a API não expõe rota para alterá-los. Campo editável que não
  persiste é pior que campo travado.
- **Excluir chamado.** Sumiria do quadro sem apagar nada no banco. Apagar dado
  de titular é obrigação de LGPD e tem caminho próprio e auditável:
  `npm run retencao -- --esquecer <telefone> --confirmar`.
- **Arquivar/fechar semana.** O histórico fica no banco e sai de lá pelo
  prazo de retenção, não por um botão de quadro.

## O aviso ao usuário

Mover um chamado envia mensagem de WhatsApp para quem abriu — o cabeçalho tem
uma chave **"Avisar usuário ao mover"**, ligada por padrão. O aviso que aparece
depois de cada movimento diz se a mensagem saiu:

```
#12 → RESOLVIDO · usuário avisado no WhatsApp
```

Mensagem enviada não volta atrás. Dois casos **não** disparam nada:

- mover de volta para **A FAZER** (não existe texto para `aberto`);
- soltar o cartão na mesma coluna onde ele já estava.

Para uma limpeza em lote, desligue a chave antes.

## Dado pessoal

A API não devolve `telefone` — mesma minimização da view
`chamados_para_cards`. Mas `nome`, `resumo` e `descricao` **são** dado pessoal e
aparecem na tela, então o painel exige token e não deve ficar aberto numa
máquina sem supervisão.

## Arquivos

| arquivo | o que é |
| --- | --- |
| `index.html` | estrutura da página |
| `data.js` | endereço da API, colunas e identidade do quadro |
| `api.js` | token, chamadas HTTP e a tradução chamado → cartão |
| `app.js` | render, filtros, arrastar-e-soltar, detalhe |
| `styles.css` | estilos |
