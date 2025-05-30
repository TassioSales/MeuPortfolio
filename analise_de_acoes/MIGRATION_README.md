# Migração do Banco de Dados

Este guia explica como executar as migrações necessárias para atualizar o banco de dados com as novas colunas adicionadas ao modelo `Ativo`.

## Pré-requisitos

- Python 3.8+
- Pipenv (ou seu gerenciador de pacotes Python preferido)
- Banco de dados SQLite configurado (o padrão da aplicação)

## Passo a Passo

### 1. Ative o ambiente virtual

Certifique-se de que você está no diretório raiz do projeto e ative o ambiente virtual:

```bash
# Se estiver usando Pipenv
pipenv shell

# Ou, se estiver usando outro gerenciador de ambientes virtuais
# source venv/bin/activate  # Linux/Mac
# .\venv\Scripts\activate  # Windows
```

### 2. Instale as dependências

Certifique-se de que todas as dependências estão instaladas:

```bash
pip install -r requirements.txt
```

### 3. Execute a migração do banco de dados

Execute o script de migração para adicionar as novas colunas à tabela `ativos`:

```bash
python migrations/add_columns_to_ativos.py
```

Este script irá:
1. Conectar-se ao banco de dados
2. Adicionar as novas colunas à tabela `ativos`
3. Confirmar as alterações no banco de dados

### 4. Popule o banco de dados com dados de exemplo (opcional)

Para testar a aplicação com alguns dados iniciais, execute:

```bash
python migrations/seed_ativos.py
```

Este script irá:
1. Gerar dados de exemplo para diferentes tipos de ativos (ações, criptomoedas, FIIs, ETFs)
2. Inserir ou atualizar os registros na tabela `ativos`

### 5. Verifique as alterações

Você pode verificar se as alterações foram aplicadas corretamente usando uma ferramenta de banco de dados SQLite como o [DB Browser for SQLite](https://sqlitebrowser.org/) ou usando o SQLite CLI:

```bash
sqlite3 instance/financas.db

-- No prompt do SQLite:
.schema ativos
SELECT symbol, name, tipo, setor, bolsa FROM ativos;
.quit
```

## Solução de Problemas

### Erro ao executar a migração

Se encontrar erros ao executar a migração, verifique:

1. Se o banco de dados existe e está acessível
2. Se o usuário do banco de dados tem permissões suficientes
3. Se há alguma outra instância do aplicativo acessando o banco de dados

### Colunas já existentes

O script de migração usa `ADD COLUMN IF NOT EXISTS` para evitar erros se as colunas já existirem. Se precisar recriar as colunas, você pode excluí-las manualmente primeiro.

## Estrutura das Novas Colunas

As seguintes colunas foram adicionadas à tabela `ativos`:

| Nome da Coluna | Tipo | Descrição |
|----------------|------|-----------|
| preco_abertura | FLOAT | Preço de abertura do dia |
| preco_max | FLOAT | Preço máximo do dia |
| preco_min | FLOAT | Preço mínimo do dia |
| preco_fechamento_anterior | FLOAT | Preço de fechamento do dia anterior |
| variacao_24h | FLOAT | Variação em valor absoluto nas últimas 24h |
| variacao_percentual_24h | FLOAT | Variação percentual nas últimas 24h |
| volume_24h | FLOAT | Volume negociado nas últimas 24h |
| valor_mercado | FLOAT | Valor de mercado (market cap) |
| max_52s | FLOAT | Preço máximo das últimas 52 semanas |
| min_52s | FLOAT | Preço mínimo das últimas 52 semanas |
| pe_ratio | FLOAT | Índice Preço/Lucro (P/L) |
| pb_ratio | FLOAT | Índice Preço/Valor Patrimonial (P/VP) |
| dividend_yield | FLOAT | Dividend Yield (rendimento de dividendos) |
| roe | FLOAT | Return on Equity (Retorno sobre Patrimônio Líquido) |
| setor | VARCHAR(100) | Setor do ativo |
| subsetor | VARCHAR(100) | Subsetor do ativo |
| segmento | VARCHAR(100) | Segmento do ativo |
| bolsa | VARCHAR(50) | Bolsa de valores onde o ativo é negociado |
| tipo | VARCHAR(20) | Tipo do ativo (stocks, crypto, fii, etf, etc.) |
| historico_precos | TEXT | Dados históricos de preços em formato JSON |

## Próximos Passos

1. Execute os testes para garantir que tudo está funcionando corretamente
2. Atualize a documentação da API, se necessário
3. Faça commit das alterações no controle de versão
4. Implante as alterações no ambiente de produção
