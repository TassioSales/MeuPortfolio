# 🤖 Bot Telegram — Assistente Pessoal com IA

Bot de produtividade pessoal para Telegram com controle de gastos, notas rápidas e insights com Inteligência Artificial via Mistral AI.

## Funcionalidades

- 💸 **Controle de gastos** — registre e consulte despesas por categoria e mês
- 📝 **Notas rápidas** — salve e acesse anotações diretamente no chat
- 🤖 **IA integrada** — faça perguntas sobre seus dados e receba análises personalizadas
- 📊 **Resumo inteligente** — relatório mensal gerado por IA com sugestões de economia

## Comandos

| Comando | Descrição |
|---------|-----------|
| `/start` | Boas-vindas e lista de comandos |
| `/gasto 25.50 almoço alimentação` | Registrar gasto (valor, descrição, categoria) |
| `/gastos` | Listar gastos do mês atual com total |
| `/gastos_mes 2025-01` | Gastos de um mês específico |
| `/nota Comprar leite amanhã` | Salvar uma nota |
| `/notas` | Listar todas as notas |
| `/apagar_nota 3` | Apagar nota pelo ID |
| `/perguntar Qual meu maior gasto?` | Pergunta com contexto dos seus dados |
| `/resumo` | Resumo mensal com análise de IA |

## Stack Técnica

- **Python 3.12** — linguagem principal
- **python-telegram-bot 21.x** — framework do bot
- **Mistral AI** — análise e insights com IA
- **SQLite** — banco de dados local
- **Loguru** — logging estruturado
- **Docker** — containerização

## Como Usar

### 1. Criar o Bot no Telegram

1. Abra o Telegram e fale com [@BotFather](https://t.me/botfather)
2. Digite `/newbot` e siga as instruções
3. Copie o token gerado

### 2. Configurar o Ambiente

```bash
cp .env.example .env
# Edite o .env com seu token e chave Mistral
```

### 3. Rodar Localmente

```bash
pip install -r requirements.txt
python -m bot.main
```

### 4. Rodar com Docker

```bash
docker-compose up -d
```

## Variáveis de Ambiente

| Variável | Descrição |
|----------|-----------|
| `TELEGRAM_TOKEN` | Token do bot (obtido no BotFather) |
| `MISTRAL_API_KEY` | Chave da API Mistral AI |
| `DB_PATH` | Caminho do banco SQLite (padrão: `data/bot.db`) |
| `ALLOWED_USERS` | IDs de usuários permitidos, separados por vírgula |
