---
tags: [projeto/whatsapp-suporte, observabilidade, prometheus]
projeto: whatsapp-suporte
atualizado: 2026-09-04
---

# WA Métricas

Os **dois** processos expõem `GET /metrics` no formato Prometheus desde 04/09.
A pilha que consome isso é o [[Monitor Bio]]; esta nota é o lado de cá.

Volta para [[WhatsApp Suporte]].

## Quem mede o quê

A divisão segue quem é **dono do dado**, e é a mesma divisão que explica o resto
do projeto ([[WA Arquitetura]]):

| Processo | Arquivo | Prefixo | Mede |
| --- | --- | --- | --- |
| bot (9511) | `src/metricas.ts` | `painel_bot_` | o **trabalho**: chamados, prazos, conversas, mensagens |
| web (8511) | `painel-metricas.mjs` | `painel_web_` | **quem está conectado** |

O bot é dono do banco; o web é dono da sessão do Entra. Nenhum dos dois consegue
responder a pergunta do outro.

## As séries

```
painel_chamados{situacao}                    as seis situações, sempre presentes
painel_chamados_sem_responsavel              a fila que ninguém pegou
painel_chamado_mais_antigo_aberto_segundos   se a fila está sendo atendida
painel_chamados_prazo_vencido                SLA estourado
painel_conversas_em_andamento                gente no meio do formulário
painel_mensagens{remetente}                  usuario | sistema
painel_banco_ok                              o SELECT 1, como métrica
painel_bot_build_info{commit,versao}         o valor é 1; leia os rótulos
painel_web_usuarios_conectados               pessoas, não abas
painel_web_login_entra_ligado                0 em produção é incidente
```

> [!important] Os gauges com rótulo semeiam TODOS os valores possíveis
> `painel_chamados` e `painel_mensagens` escrevem zero para cada valor do enum
> antes de consultar o banco. Sem isso, uma situação sem nenhum chamado
> simplesmente **some da exposição** — e some do gráfico, o que na tela parece
> coleta quebrada, não "zero chamados nesse estado".
>
> Isso não é teoria: `painel_mensagens` foi escrito sem o preenchimento e
> desapareceu inteiro na primeira verificação contra o banco vazio. Corrigido
> no mesmo dia.

## Usuários conectados, sem tabela de sessão

O cookie é *stateless*, então não há lista de sessões para contar. Mas o quadro
**já se atualiza sozinho**: o `app.js` roda um `setInterval` que rebusca os
chamados, e cada uma dessas requisições passa pelo `servidor-painel.mjs` com o
cookie junto. Isso é um heartbeat que já existia — só não estava sendo usado.

A contagem é um `Map` em memória de `oid → instante da última requisição`,
alimentado no ponto em que `sessaoDe()` confirma o cookie. Janela de 3 minutos.

> [!note] Três consequências, todas aceitáveis
> 1. **Zera quando o processo reinicia.** Correto: ninguém está "conectado" a um
>    processo que acabou de subir.
> 2. **Não persiste nada** — diferente do [[Estúdio]], onde o mesmo problema foi
>    resolvido gravando `last_seen_at`, porque lá o heartbeat é raro (15 min) e o
>    dado já morava no banco. Aqui seria escrita em disco a cada atualização de
>    quadro.
> 3. **Conta abas únicas por pessoa**, não abas: duas janelas do mesmo usuário
>    contam uma vez. É o que "usuários conectados" deve significar.

O ponto que fez escolher assim: **não exigiu migração de banco** num sistema
praticamente lançado.

## Configuração

Uma variável, opcional, no `.env`:

```
METRICS_TOKEN=<32 bytes aleatórios em base64url>
```

Vale para os **dois** processos. É separada do `INTERNAL_API_TOKEN` de propósito:
são consumidores diferentes com ciclos de rotação diferentes — revogar o acesso
do Prometheus não pode derrubar o quadro, e vice-versa.

> [!danger] Sem o token, a rota não existe
> Falha fechada. No bot ela nem é registrada; no web, a requisição cai no portão
> de sessão e vira 302. Nos dois casos o Prometheus marca o alvo como fora do ar,
> que é o sinal desejado — melhor que servir métrica sem proteção por
> esquecimento.

Também há `GIT_COMMIT` e `APP_VERSION`, injetados no `docker build` — sem eles o
painel "versão no ar" mostra `desconhecido`.

## Cardinalidade

O rótulo de rota é o **molde** (`/internal/chamados/:id`), nunca a URL: com a
URL, cada id de chamado viraria uma série nova no Prometheus, para sempre.
Caminho que não casa rota nenhuma vira `desconhecida`, senão um scanner batendo
em caminhos aleatórios criaria uma série por caminho.

Medido em 04/09 com os três alvos no ar: **162 séries** no bot, **119** no web.
Um alvo destes não deveria passar de algumas centenas — milhares significariam
id virando rótulo.

## Fora do rate limit

`/metrics` é registrada com `config: { rateLimit: false }`, como `/health` e
`/ready`. Uma raspagem de 15 em 15 segundos não pode consumir a cota do webhook —
o mesmo raciocínio que já valia para as sondas (ver [[WA Segurança e LGPD]]).
