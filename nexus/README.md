# Nexus ◈ AI Agent Terminal

Terminal de IA com interface TUI que executa ferramentas reais de forma autônoma. Baseado no loop ReAct (Reason → Act → Observe) com múltiplas sessões persistentes.

## Arquitetura

```
nexus/
├── core/
│   ├── agent.py       loop ReAct async (máx 8 iterações)
│   ├── events.py      eventos tipados (TOKEN, TOOL_*, DONE, ERROR)
│   ├── llm.py         cliente Mistral AI
│   ├── memory.py      SQLite multi-sessão (~/.nexus/memory.db)
│   └── tools/
│       ├── web_search.py     DuckDuckGo (sem API key)
│       ├── python_repl.py    subprocess isolado, timeout 15s
│       ├── file_ops.py       read/write/list em ~/nexus_workspace/
│       └── web_fetch.py      httpx + BeautifulSoup
└── ui/
    ├── app.py         Textual TUI (sidebar + chat + input)
    └── styles.tcss    dark theme, acento verde #00e676
```

## Instalação

```bash
cd nexus
pip install -r requirements.txt
export MISTRAL_API_KEY='sua-chave'
python main.py
```

### Docker

```bash
docker build -t nexus .
docker run -it -e MISTRAL_API_KEY='sua-chave' nexus
```

## Atalhos

| Atalho | Ação |
|--------|------|
| `Enter` | Enviar mensagem |
| `Ctrl+N` | Nova sessão |
| `Ctrl+L` | Limpar chat |
| `Ctrl+Q` | Sair |

## Ferramentas disponíveis

| Ferramenta | Descrição |
|------------|-----------|
| `web_search` | Busca no DuckDuckGo sem API key |
| `python_repl` | Executa Python em subprocess isolado (timeout 15s) |
| `read_file` | Lê arquivos do workspace |
| `write_file` | Escreve arquivos no workspace |
| `list_directory` | Lista diretórios em formato árvore |
| `fetch_url` | Faz fetch de URLs com extração de texto |

## Stack

- **Python 3.12**
- **Textual** — TUI framework
- **Mistral AI** — LLM com function calling
- **DuckDuckGo Search** — busca sem API key
- **httpx + BeautifulSoup** — web fetch
- **SQLite** — memória persistente
