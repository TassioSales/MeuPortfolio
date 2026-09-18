---
tags: [projeto/whatsapp-suporte, configuracao]
projeto: whatsapp-suporte
atualizado: 2026-08-26
---

# WA Configuração

Volta para [[WhatsApp Suporte]].

Tudo é lido e validado **uma vez, no boot**, em [config.ts](../src/config.ts).
Referência comentada para copiar: [.env.example](../.env.example).

## Um arquivo só, e um bloco que o inverte

Existe **um** `.env`, e ele serve os dois mundos. O `npm run dev` e o
[[WA Implantação#O caminho do go-live no Windows|run.bat]] leem o mesmo arquivo;
não há `.env.producao` nem nada paralelo.

Os valores de cima são os de **produção**. No fim do arquivo há um bloco
**MODO DE TESTE LOCAL**, comentado, com cinco linhas que devolvem o
comportamento de desenvolvimento — `PORT=3000`, credenciais de mentira e
`EVOLUTION_URL` apontando para a [[WA Ambiente local|Evolution de mentira]].

> [!info] Por que funciona, e por que a ordem importa
> O dotenv fica com a **última** ocorrência de cada chave. As linhas de teste
> vêm depois das de produção de propósito: descomentadas, elas vencem. Inverter
> a ordem tornaria o bloco inofensivo e silenciosamente inútil.

O `run.bat` **não** aceita esse bloco: ele exige os valores reais da Evolution.
E deve mesmo — um go-live apontado para a Evolution de mentira sobe sem erro
nenhum e não entrega uma única mensagem, porque ela responde 201 para tudo.

> [!danger] O `.env` desta máquina tem segredo de verdade
> `EVOLUTION_API_KEY`, `WEBHOOK_SEGREDO`, `INTERNAL_API_TOKEN` e `PAINEL_TOKEN`
> estão preenchidos, em texto claro no disco. O `.gitignore` cobre `.env` e
> `.env.*` (com `!.env.example`), então nada disso está versionado — mas
> "não commitado" não é o mesmo que "protegido". Ver [[WA Segurança e LGPD]].

> [!warning] Sobrou credencial da Meta no `.env` desta máquina
> `META_APP_SECRET`, `WHATSAPP_TOKEN` e `WHATSAPP_PHONE_NUMBER_ID` continuam
> lá com valor real, e o código **não lê mais nenhuma delas**. Segredo que
> ninguém usa é só risco parado: apague as três linhas e, já que estiveram em
> disco, revogue o token no painel da Meta.

## Falhar alto e cedo

Faltando qualquer variável obrigatória — ou com número inválido em qualquer
opcional — o processo **imprime todas as pendências de uma vez e morre**:

```
Configuração inválida. Corrija no .env antes de subir o servidor:
  - WEBHOOK_SEGREDO
  - RATE_LIMIT_POR_MINUTO (precisa ser inteiro >= 1, veio "abc")
```

A alternativa (subir com valor vazio) significaria rodar com a **autenticação do
webhook desligada** — exatamente o cenário em que qualquer um que descobrisse a
URL poderia abrir chamados falsos e fazer o bot mandar mensagem para qualquer
número.

Também não existe `parseInt` solto pelo código: `numeroOpcional` exige inteiro e
recusa `"abc"`, `"1.5"` e negativo em vez de virar `NaN` no meio de uma conta.

A exceção é `SESSAO_TTL_HORAS`, que passa por `fracaoOpcional` e aceita qualquer
número > 0. O motivo é concreto: `0.5` (meia hora) é o valor natural para
exercitar a expiração de sessão sem esperar uma hora, e a validação de inteiro
não o arredondava — **derrubava o processo no boot** com "precisa ser inteiro
>= 1", que não é o que quem escreveu `0.5` esperava ler.

## Obrigatórias

| variável | onde achar / o que é |
| --- | --- |
| `WEBHOOK_SEGREDO` | string secreta que você escolhe. Vira o final da URL cadastrada na Evolution (`/webhook/<segredo>`) e autentica **cada** webhook |
| `EVOLUTION_URL` | endereço da sua Evolution, com esquema e sem barra no fim |
| `EVOLUTION_API_KEY` | `AUTHENTICATION_API_KEY` da instalação, ou o token da instância. Vai no cabeçalho `apikey` |
| `EVOLUTION_INSTANCIA` | nome da instância conectada — `GET /instance/fetchInstances` lista |
| `INTERNAL_API_TOKEN` | você escolhe; quem tem esse token pode alterar chamados. Use valor longo e aleatório |
| `DATABASE_URL` | caminho do arquivo SQLite, no formato `file:...`. Não é servidor: não há host, senha nem banco a criar. Ver [[WA Banco de dados]] |

## Opcionais (têm padrão)

| variável | padrão | efeito |
| --- | --- | --- |
| `PORT` | 3000 | porta do servidor. **No go-live vale 8511** — e é dela que o `run.bat` e o `parar.bat` leem a porta, ver [[WA Implantação#O caminho do go-live no Windows]] |
| `TRUST_PROXY` | `false` | confiar no `X-Forwarded-For`. Aceita `true`/`false`, número de hops ou lista de IPs/CIDRs |
| `BODY_LIMIT_BYTES` | 262144 (256 KB) | corpo máximo da requisição |
| `MAX_CARACTERES_MENSAGEM` | 4096 | corte duro por mensagem recebida |
| `RATE_LIMIT_POR_MINUTO` | 300 | teto de requisições/min no endpoint (por IP) |
| `MSGS_POR_MINUTO_POR_TELEFONE` | 20 | teto por telefone — o controle de abuso que importa |
| `SESSAO_TTL_HORAS` | 24 | inatividade até a coleta em andamento ser descartada. **Aceita fração** (`0.5` = 30min) |
| `LIMPEZA_SESSOES_MINUTOS` | 60 | frequência da varredura de sessões abandonadas |
| `ENVIOS_TENTATIVAS` | 3 | tentativas HTTP imediatas por rodada |
| `ENVIOS_MAX_TENTATIVAS` | 6 | teto de rodadas (imediatas + varredor) |
| `VARREDOR_INTERVALO_SEGUNDOS` | 60 | frequência do varredor da outbox |
| `ENVIO_SINCRONO_MS` | 10000 | orçamento de envio **do lote** dentro da requisição |
| `DB_BUSY_TIMEOUT_MS` | 10000 | espera pelo lock de escrita do arquivo antes de devolver `SQLITE_BUSY` — ver o aviso abaixo |
| `PAINEL_ORIGENS` | (vazio) | origens autorizadas a chamar a API pelo navegador; vazio desliga o CORS. Ver [[WA Painel de chamados]] |
| `PAINEL_TOKEN` | (vazio) | token só do painel; sem ele o painel usa o `INTERNAL_API_TOKEN` |
| `ALERTA_WEBHOOK_URL` | (vazio) | canal avisado quando a outbox **desiste** de uma mensagem; vazio = só log. Ver [[WA Outbox e entrega]] |
| `ALERTA_INTERVALO_SEGUNDOS` | 300 | janela de coalescência dos alertas |
| `RETENCAO_MENSAGENS_DIAS` | 0 (desligado) | LGPD — decisão do negócio, ver [[WA Segurança e LGPD]]. **No `.env` atual: 1827** (5 anos) |
| `RETENCAO_CHAMADOS_DIAS` | 0 (desligado) | idem. **No `.env` atual: 0** — chamado nenhum é descartado |

> [!warning] A retenção deixou de estar "desligada", e só metade dela foi decidida
> O `.env` traz `RETENCAO_MENSAGENS_DIAS=1827` e
> `RETENCAO_CHAMADOS_DIAS=0`. Ou seja: mensagem tem prazo (5 anos), chamado
> não tem nenhum. Isso muda o `npm run retencao` de *no-op* para um script que
> de fato apaga — hoje sem efeito prático só porque não há dado com 5 anos, o
> que não é uma garantia, é uma coincidência de calendário.
>
> O [GOLIVE.md](../GOLIVE.md) ainda afirmava "Retenção está desligada
> (`RETENCAO_*_DIAS=0`): nada é apagado"; corrigido em 2026-08-26. Ver
> [[WA Pendências#Bloqueiam ir para produção]].

## Painel: login (Entra ID) e HTTPS

Estas **não** são lidas pelo `config.ts` do bot — quem as lê é o processo do
painel ([servidor-painel.mjs](../servidor-painel.mjs) e
[painel-entra.mjs](../painel-entra.mjs)). Detalhe de segurança em
[[WA Segurança e LGPD]] e no [.env.example](../.env.example).

| variável | padrão | efeito |
| --- | --- | --- |
| `PAINEL_PORT` | 8511 | porta do painel no navegador |
| `PAINEL_HOST` | `0.0.0.0` | interface de escuta; `127.0.0.1` restringe à própria máquina |
| `BOT_PORT` | `PORT`/9511 | porta do bot para onde o painel repassa `/internal/*` e o `/webhook` |
| `PAINEL_TOKEN_NO_SERVIDOR` | (desligado) | injeta o token da API no servidor; o painel abre sem pedir token — **só com a porta restrita** |
| `PAINEL_EXPOSICAO_SEM_LOGIN` | (desligado) | libera subir **sem login e exposto fora do loopback**; sem isso, essa combinação recusa subir |
| `PAINEL_TLS_CERT` · `PAINEL_TLS_KEY` | (vazio) | caminhos do certificado/chave; sem os dois, o painel serve em HTTP (só serve para `localhost`) |
| `ENTRA_TENANT_ID` · `ENTRA_CLIENT_ID` · `ENTRA_CLIENT_SECRET` · `PAINEL_URL_BASE` | (vazio) | as **quatro** que ligam o login pelo Entra ID. Todas vazias = sem login; preencher só algumas é erro fatal |
| `PAINEL_SESSAO_SEGREDO` | (vazio) | segredo que assina o cookie de sessão; obrigatório quando o login está ligado |
| `PAINEL_SESSAO_HORAS` | 8 | validade da sessão do painel |

## Três variáveis que enganam

> [!danger] `DB_BUSY_TIMEOUT_MS` não é pool — e o limite real não é ele
> SQLite não tem pool: tem **um escritor por banco**. Este valor só diz quanto
> esperar quando **outro processo** está com o lock — o `npm run retencao` do
> agendador, o `npm run db:view` do deploy, um `sqlite3` aberto.
>
> O limite que importa é anterior a qualquer variável: **uma instância**. Duas
> instâncias apontadas para o mesmo arquivo brigam pelo lock, e subir a segunda
> não é ajuste de configuração, é troca de banco. Ver [[WA Banco de dados]] e
> [[WA Implantação]].

> [!warning] `TRUST_PROXY`
> **Ligue** se houver ngrok / Render / nginx / load balancer na frente: sem isso
> todo request aparece com o IP do proxy e o rate limit por IP vira um contador
> global do endpoint. **Não ligue** com o processo exposto direto na internet —
> aí qualquer um forja o header e escapa do limite.

> [!warning] `EVOLUTION_URL`
> Apontada para a [[WA Ambiente local|Evolution de mentira]], ela faz o bot
> postar as respostas em `127.0.0.1` e **nenhuma mensagem chega ao usuário** —
> sem erro nenhum, porque a Evolution de mentira responde 201. Diferente das
> antigas `GRAPH_API_*`, esta é obrigatória: não dá para "esquecer definida",
> mas dá para deixar apontando para o lugar errado.

## Ajustes úteis em desenvolvimento

```env
EVOLUTION_URL=http://127.0.0.1:4000        # Evolution de mentira
VARREDOR_INTERVALO_SEGUNDOS=15             # ver o varredor agir sem esperar 1min
SESSAO_TTL_HORAS=1                         # testar expiração de sessão
RETENCAO_MENSAGENS_DIAS=30                 # exercitar o script de retenção
```

## Onde cada limite é aplicado

| limite | módulo |
| --- | --- |
| corpo da requisição | Fastify (`bodyLimit`) em [app.ts](../src/app.ts) |
| requisições por minuto | `@fastify/rate-limit` em [app.ts](../src/app.ts) — `/health` e `/ready` ficam fora |
| mensagens por telefone | [whatsapp/throttle.ts](../src/whatsapp/throttle.ts), janela fixa de 60s, em [estado/janelas.ts](../src/estado/janelas.ts) — memória ou Redis, conforme `REDIS_URL` |
| caracteres por mensagem | [whatsapp/webhook.ts](../src/whatsapp/webhook.ts) |
| caracteres por campo | [conversation/flows.ts](../src/conversation/flows.ts) — ver [[WA Fluxo da conversa]] |
| tempo de envio na requisição | [whatsapp/client.ts](../src/whatsapp/client.ts) via `ateMs` |
