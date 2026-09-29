# Guia — Memória da conversa

O que o agente lembra do que já foi dito, e por quê isto é mais simples do que
já foi.

---

## 1. O que existe

`backend/app/services/memory_service.py` tem um método:

```python
await memory_service.get_conversation_history(conversation_id, db, limit=60)
```

Devolve as últimas `limit` mensagens da conversa, **da mais antiga para a mais
recente**, no formato que a API espera:

```python
[
    {"role": "user",      "content": "fui demitido por justa causa"},
    {"role": "assistant", "content": "Em que mês foi a demissão?"},
]
```

Lê do banco toda vez. Sem cache.

**Papéis:** cliente é `user`; todo o resto — a IA (`assistant`) e o operador
que digita pelo painel (`operador`) — é o escritório falando, e entra como
`assistant`. Para o modelo, "o escritório disse" é uma coisa só; para quem lê a
transcrição depois, a diferença fica no banco, na coluna `remetente`.

---

## 2. Quem chama

Um caminho só, por dois lugares:

| Chamador | Janela | Para quê |
|---|---|---|
| `message_orchestrator` | `MENSAGENS_DE_CONTEXTO` (60) | O atendimento no WhatsApp |
| `routers/chat.py` | 5 | O chat de teste do painel |

A janela do atendimento está em `services/atendimento_context.py`, junto com a
**nota de atendimento anterior** — o resumo do que o banco já sabe do número,
que entra na frente do histórico quando o contato volta depois de a conversa
antiga ter saído da janela.

---

## 3. Por que não tem cache

Tinha. Um read-through no Redis, chave `conv_history:{id}`, TTL de uma hora, e
**nenhum caminho de escrita o invalidava**.

O efeito: a primeira mensagem da conversa lia o banco vazio, gravava `[]`, e
pela hora seguinte todo turno chegava ao modelo com esse histórico congelado. O
agente respondia bem à frase que acabara de chegar e, no turno seguinte, não
sabia que a tinha recebido. Numa triagem trabalhista real ele perguntou a data
de admissão quatro vezes, a função três, e se a saída fora demissão ou justa
causa outras três — até o cliente escrever "cara que volta absurda vc ta dando
volta nas perguntas".

O `invalidate_cache` existia, tinha teste, e ninguém o chamava em produção. O
teste invalidava o cache com as próprias mãos antes de reler: provava que o
método funcionava, não que alguém o usava. Este guia, na versão anterior, tinha
uma seção de troubleshooting chamada *"Cache não invalida após nova mensagem"*
com a linha exata que faltava em `message_orchestrator.py`. Estava escrito.
Nunca foi ligado.

E nenhum teste podia ter pego: `redis_client.connect()` só roda no lifespan, que
o `TestClient` não dispara, então `self.redis` era `None` na suíte inteira,
cada operação de cache estourava `AttributeError` e o `except` de cada método
engolia. O cache estava desligado nos testes — CI incluída — e ligado em
produção. A única configuração em que o defeito aparecia era a única que
ninguém exercitava.

Dava para consertar espalhando `invalidate_cache` pelos quatro pontos que
gravam mensagem (webhook, webhook em pausa, playground, resposta do operador) e
torcer para o quinto lembrar. O cache saiu, em vez disso: a consulta é um
índice e algumas dezenas de linhas, uns poucos milissegundos ao lado dos dois
segundos da chamada ao modelo que vem logo em seguida. Ele economizava 0,05% da
latência do turno e custava a memória do atendimento inteiro.

`REDIS_CACHE_TTL` continua declarada em `config.py` sem uso: está nos `.env` já
existentes, e o pydantic-settings recusa variável que não conheça — tirar do
código impediria o backend de subir na máquina de quem tem o arquivo.

O Redis continua em uso para o limite de chamadas (`rate_limiter.py`) e para o
cache de métricas (`metrics_service.py`), que agrega números históricos e
tolera estar quinze minutos atrasado.

---

## 4. Testes

| Onde | O que garante |
|---|---|
| `tests/test_webhook.py::test_segunda_mensagem_enxerga_a_primeira` | Dois turnos pelo orquestrador: o segundo enxerga o primeiro |
| `tests/test_memory_service.py` | Ordem cronológica, conversa vazia, papéis, falha do banco |
| `tests/test_human_pause.py::test_a_fala_do_operador_nao_vira_pergunta_do_cliente` | O operador entra como escritório, não como cliente |

O primeiro é o que importa: olha o que **chega ao modelo**, não o que o serviço
de memória faz quando alguém pede educadamente.

---

## 5. Ajustar a janela

`MENSAGENS_DE_CONTEXTO`, em `services/atendimento_context.py`.

Foi 5, foi 20, hoje é 60. As duas primeiras pareciam suficientes na mesa e não
eram: no WhatsApp o cliente responde uma ideia por mensagem — "mandaod", "1",
"analista" —, e uma triagem passa fácil de cinquenta mensagens. São mensagens
curtas: sessenta delas dão umas poucas centenas de tokens, contra os 6,4 mil
caracteres do system prompt que vão em toda chamada de qualquer jeito.

Se aumentar, meça o custo por conversa antes de fixar. Se diminuir, saiba que o
sintoma não é erro nenhum: é o agente reperguntando, e o cliente indo embora.
