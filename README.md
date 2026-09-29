# Tássio Sales

Desenvolvedor focado em dados e automação. Construo pipelines, APIs e interfaces que resolvem um
problema específico de ponta a ponta — da coleta do dado à tela que alguém usa.

Python · Go · TypeScript · SQL

---

## Comece por aqui

Quatro trabalhos que carregam evidência verificável, não só descrição.

### Contribuições no cal.com

16 Pull Requests no [cal.com](https://github.com/calcom/cal.diy), monorepo TypeScript com 48,7 mil
estrelas: comparação de HMAC sujeita a ataque de tempo, bugs de identidade de participante em
reservas, serialização de log que quebrava em referência circular, formatação de moeda sem
subunidade e duas buscas quadráticas em código de round-robin. 2.030 linhas, 153 casos de teste.

Cada correção está documentada com o comportamento errado, o chamador afetado e a contagem de
arquivos que importam o módulo — incluindo os três PRs que mexem em código sem chamador, e o que
ainda não foi revisado.

**[Ler o detalhamento](./contribuicoes_open_source)**

### edge-audit

Ferramenta CLI que audita funções utilitárias TypeScript em casos-limite sem você escrever teste
nenhum: lê a assinatura com ts-morph, gera as entradas hostis que o tipo admite, chama a função e
reporta quatro tipos de falha.

Rodando contra o `packages/lib` do cal.com: **18 falhas em 63 funções, 906 chamadas**. Entre elas,
reencontrou sozinha um defeito que eu havia achado antes lendo o código à mão.

`TypeScript · ts-morph · Vitest` — 49 testes, tsc estrito, sem `any`

**[Ver projeto](./edge_audit)**

### CRM Conversacional

Atendimento no WhatsApp com agentes de IA, qualificação automática de leads, CRM em Kanban e
dashboards de desempenho. Integração via Evolution API, autenticação JWT, WebSocket para o painel.

`FastAPI · Next.js 14 · PostgreSQL 16 · Redis 7 · Claude · Docker Compose`
— 79 arquivos de teste, único projeto do repositório com CI rodando contra banco real

**[Ver projeto](./crm_conversacional)**

### ERP Pessoal

Controle financeiro, investimentos, PDV, estoque e emissão de nota fiscal. Distribuído também como
executável Windows via PyInstaller.

`Django · SQLite · Bootstrap 5` — 21 arquivos de teste

**[Ver projeto](./finanças)**

---

## Dados e análise

| Projeto | O que faz | Stack |
|---|---|---|
| [Análise de Combustíveis](./analise_de_combustiveis) | Baixa os dados da ANP, processa com Polars, grava em Parquet/DuckDB e serve um dashboard com previsão de preço | Python · DuckDB · Go · Next.js |
| [Panorama BR](./panorama_br) | Indicadores econômicos brasileiros com coleta automática do Banco Central e yfinance | Python · Go · Next.js 14 |
| [ENEM Insights](./enem_insights) | Impacto de renda, escola, região e raça nas notas do ENEM, com modelo preditivo | Python · Streamlit · scikit-learn |
| [DataNarrator](./data_narrator) | Recebe um CSV ou Excel e devolve a análise exploratória com narrativa gerada por IA e relatório em PDF | Python · Streamlit · Mistral AI |
| [DevMetrics](./devmetrics) | Métricas de perfil e repositórios do GitHub com leitura automatizada | Go · Next.js · Mistral AI |
| [WealthMap Analytics](./wealthmap_analytics) | Gestão de carteira com previsão de 30 dias, Sharpe, volatilidade e matriz de correlação | Python · FastAPI · Next.js · scikit-learn |

## IA aplicada

| Projeto | O que faz | Stack |
|---|---|---|
| [Nexus](./nexus) | Terminal de IA com interface TUI que executa ferramentas de verdade em loop ReAct, com sessões persistentes | Python · TUI |
| [MemMap](./memmap) | Editor de notas que extrai entidades com spaCy e monta um grafo de conhecimento interativo em tempo real | Go · spaCy · D3.js · WebSocket |
| [DocuMind Local](./documind_local) | Assistente de documentos que roda na própria máquina: upload, extração de texto, busca e análise | Go · Python · Mistral AI |
| [Transcritor WhatsApp](./transcritor_whatsapp) | Transcreve áudios do WhatsApp offline e cruza com o texto exportado para identificar autor e trechos de interesse | Python · faster-whisper · Streamlit |
| [VoxBR](./voxbr) | Transcrição de áudio com Whisper e geração de resumo | Python · Whisper · Mistral AI · Next.js |
| [Gerador de Roteiros](https://jiqucdwsimgpjhzzhmn3f2.streamlit.app/) | Roteiros de viagem personalizados, com fallback entre dois provedores de IA — **no ar** | Python · Streamlit · Mistral · Gemini |
| [PriceTrack AI](https://pricetrack-ai.streamlit.app) | Monitor de preço em e-commerce com alerta proativo — **no ar** | Python · Streamlit · Gemini · SQLAlchemy |
| [Bot Telegram](./bot_telegram) | Bot de produtividade com tarefas, lembretes e respostas por IA | Python · Telegram API · Mistral AI |

## Sistemas de negócio

| Projeto | O que faz | Stack |
|---|---|---|
| [CompraBio](./aprovacao_compras) | Solicitação e aprovação de pedidos de compra com histórico auditável, notificação por e-mail e exportação | Python · web |
| [Plataforma de Rifas](https://plataforma-rifas-pro.streamlit.app) | Gestão de rifas com analytics e geração de PDF — **no ar** | Python · Streamlit · SQLite · Docker |
| [WhatsApp Suporte](./whatsapp-sup-master) | Bot que coleta um chamado por fluxo guiado e grava em SQLite, deliberadamente sem IA no caminho | TypeScript · SQLite |
| [Encurtador de URL](./encurtador_url) | Encurtador com analytics de clique e painel de estatísticas | Go · Next.js · SQLite |

## Jogos

| Projeto | O que faz | Stack |
|---|---|---|
| [Neon Drift](./neon_drift) | Jogo arcade com backend de configuração e placar global | Go · HTML5 Canvas |
| [Neon Snake](./neon_snake) | Arcade single-player com placar persistido | Go · HTML5 Canvas |

---

## Como este repositório é organizado

Cada pasta é um projeto independente, com as próprias dependências, o próprio README e as próprias
instruções de execução. Não há build compartilhado na raiz: todo comando roda de dentro da pasta do
projeto.

Três stacks se repetem:

- **Python + Streamlit** para aplicações de dados e IA que precisam de interface rápida
- **Go no backend + Next.js no frontend** quando a carga justifica separar a API
- **Django** no ERP, onde o admin e o ORM economizam meses

Dados sempre com Polars e Parquet, nunca pandas. Consulta analítica em DuckDB.

## Contato

- GitHub: [@TassioSales](https://github.com/TassioSales)
- LinkedIn: [Tássio Sales](https://www.linkedin.com/in/t%C3%A1ssio-sales-141826386/)
- E-mail: tassiolucian.ljs@gmail.com
