<div align="center">

# 💰 Análise Financeira Inteligente

**Sistema completo para gestão financeira pessoal e empresarial**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-yellow.svg)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status: Ativo](https://img.shields.io/badge/Status-Ativo-brightgreen.svg)]()

[![Arquitetura Modular](https://img.shields.io/badge/arquitetura-modular-ff69b4)](https://github.com/TassioSales/MeuPortfolio/tree/main/analise_financeira)
[![Segurança Avançada](https://img.shields.io/badge/segurança-avançada-yellowgreen)](https://github.com/TassioSales/MeuPortfolio/tree/main/analise_financeira)
[![Interface Responsiva](https://img.shields.io/badge/interface-responsiva-9cf)](https://github.com/TassioSales/MeuPortfolio/tree/main/analise_financeira)

</div>

## 🌟 Visão Geral

O **Análise Financeira Inteligente** é uma solução abrangente desenvolvida para simplificar e otimizar o gerenciamento financeiro. Com foco em usabilidade e performance, o sistema oferece ferramentas poderosas para análise de gastos, planejamento orçamentário e tomada de decisões financeiras informadas.

### 🎯 Objetivos

- Fornecer uma visão clara e detalhada das finanças pessoais/empresariais
- Automatizar o processo de importação e categorização de transações
- Oferecer insights acionáveis através de análises e relatórios
- Facilitar o controle e planejamento financeiro
- Garantir segurança e privacidade dos dados financeiros

## 🚀 Funcionalidades Principais

### 📊 Dashboard Interativo
- Visualização em tempo real de receitas, despesas e saldo
- Gráficos dinâmicos e interativos
- Filtros avançados por período, categoria e tipo de transação
- Métricas-chave de desempenho financeiro

### 📤 Upload Inteligente
- Suporte a múltiplos formatos (CSV, PDF, XLSX)
- Processamento automático de extratos bancários
- Reconhecimento inteligente de padrões
- Validação e correção de dados em tempo real
- Processamento otimizado para arquivos grandes
- Suporte a mais colunas e formatos de dados

### 💰 Gestão de Transações
- Cadastro manual de receitas e despesas
- Categorização automática inteligente
- Anexo de comprovantes
- Histórico completo com busca avançada
- Tabela otimizada com rolagem suave
- Filtros avançados por múltiplos critérios

### 🔔 Sistema de Alertas
- Notificações personalizáveis
- Alertas de orçamento
- Lembretes de contas a pagar
- Análise de padrões de gastos

### 📱 Interface Moderna
- Design responsivo (desktop e mobile)
- Tema claro/escuro
- Navegação intuitiva com atalhos
- Tempo de carregamento otimizado
- Tabelas com colunas fixas para melhor navegação
- Experiência do usuário aprimorada

## 🛠️ Stack Tecnológica

### Backend
- **Linguagem**: Python 3.8+
- **Framework Web**: Flask 2.0+
- **Autenticação**: Flask-Login, Flask-JWT-Extended
- **API REST**: Flask-RESTful
- **Tarefas Assíncronas**: Celery
- **Cache**: Redis
- **Fila de Processamento**: RabbitMQ

### Banco de Dados
- **SGBD**: SQLite (Desenvolvimento) / PostgreSQL (Produção)
- **ORM**: SQLAlchemy 1.4+
- **Migrações**: Flask-Migrate (Alembic)
- **Backup Automático**: Scripts personalizados

### Frontend
- **HTML5** semântico
- **CSS3** com pré-processador SASS
- **JavaScript** (ES6+)
- **Bibliotecas**:
  - Chart.js para gráficos
  - DataTables para tabelas interativas
  - Select2 para seleção avançada
  - Moment.js para manipulação de datas

### Processamento de Dados
- **Análise**: Pandas, NumPy
- **Visualização**: Matplotlib, Plotly
- **PDF**: pdfplumber, PyPDF2
- **Excel**: openpyxl, xlrd
- **Otimização**: Processamento em lote para grandes volumes
- **Validação**: Schemas avançados para garantia de qualidade dos dados

### DevOps
- **Controle de Versão**: Git
- **CI/CD**: GitHub Actions
- **Containerização**: Docker, Docker Compose
- **Monitoramento**: Prometheus, Grafana
- **Logs**: ELK Stack (Elasticsearch, Logstash, Kibana)

## 🏗️ Arquitetura do Projeto

```
analise_financeira/
├── .github/                    # Configurações do GitHub
│   └── workflows/             # Fluxos de CI/CD
│
├── alertas_arq/              # Módulo de alertas
│   ├── src/
│   │   ├── models.py         # Modelos de dados
│   │   ├── routes.py          # Rotas da API
│   │   └── services.py        # Lógica de negócios
│   └── tests/                 # Testes unitários
│
├── dashboard_arq/            # Módulo de dashboard
│   ├── static/               # Recursos estáticos
│   ├── templates/            # Templates específicos
│   └── src/
│       ├── __init__.py      # Inicialização
│       ├── acoes.py          # Gerenciamento de transações
│       ├── inserir_dados.py  # Inserção de dados
│       ├── logger.py         # Configuração de logging
│       └── utils/            # Utilitários diversos
│
├── upload_arq/              # Módulo de upload
│   ├── src/
│   │   └── processamento.py  # Lógica de processamento
│   └── tests/                # Testes de integração
│
├── static/                  # Arquivos estáticos globais
│   ├── css/                  # Folhas de estilo
│   ├── js/                   # Scripts JavaScript
│   └── img/                  # Imagens e ícones
│
├── templates/               # Templates base
│   ├── base/                # Layouts base
│   ├── components/          # Componentes reutilizáveis
│   └── macros/              # Macros Jinja2
│
├── tests/                   # Testes de aceitação
│   ├── e2e/                 # Testes end-to-end
│   └── fixtures/            # Dados de teste
│
├── .env.example            # Variáveis de ambiente de exemplo
├── .gitignore               # Arquivos ignorados pelo Git
├── config.py                # Configurações da aplicação
├── main.py                  # Ponto de entrada
├── requirements-dev.txt     # Dependências de desenvolvimento
├── requirements.txt         # Dependências de produção
└── README.md               # Documentação
```

## 📅 Histórico de Atualizações

### 🔥 Últimas Atualizações (v2.1.0 - Maio/2025)

#### Melhorias no Gerenciamento de Transações
- ✅ Sistema de edição em tempo real
- ✅ Validação avançada de tipos de dados
- ✅ Tratamento automático de valores negativos
- ✅ Logging unificado com rastreamento de requisições
- ✅ Prevenção de condições de corrida no banco de dados

#### Aprimoramentos no Frontend
- 🎨 Redesign da interface do usuário
- ⚡ Melhorias de performance na renderização
- 📱 Melhor experiência em dispositivos móveis
- 🌓 Suporte a tema claro/escuro

#### Novos Recursos
- 🔍 Busca avançada com filtros combinados
- 📊 Novos gráficos e visualizações
- 📤 Exportação de relatórios em múltiplos formatos
- 🔄 Sincronização em tempo real

### Versões Anteriores

<details>
<summary>📌 v2.0.0 - Abril/2025</summary>

- Arquitetura modular redesenhada
- Novas APIs RESTful
- Suporte a múltiplos usuários
- Sistema de permissões granular
- Documentação da API com Swagger

</details>

<details>
<summary>📌 v1.5.0 - Março/2025</summary>

- Módulo de orçamento
- Planejador financeiro
- Metas de economia
- Análise de investimentos
- Relatórios personalizados

</details>

## 🚦 Status do Projeto

### 📈 Métricas
- **Cobertura de Testes**: 85%
- **Tempo de Atividade**: 99.9%
- **Usuários Ativos**: 1.2K+
- **Transações Processadas**: 1M+

### 🤝 Contribuição

Contribuições são bem-vindas! Siga estes passos:

1. Faça um Fork do projeto
2. Crie sua Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a Branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

### 📄 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.

### 📧 Contato

Link do Projeto: [https://github.com/TassioSales/MeuPortfolio/tree/main/analise_finaceira](https://github.com/seu-usuario/analise_financeira)

## 📖 Logging Padronizado

O projeto agora utiliza um sistema de logging unificado baseado em Loguru. Todos os módulos e scripts usam o logger padronizado, facilitando o rastreamento de erros, auditoria e manutenção. Prints e logs inconsistentes foram substituídos por chamadas ao logger, com níveis adequados (`info`, `warning`, `error`, `debug`).

Exemplo de uso:
```python
from logger import get_logger
logger = get_logger("nome_do_modulo")
logger.info("Mensagem informativa")
```

## 🗃️ Estrutura da Tabela de Transações

A tabela `transacoes` armazena todas as transações financeiras do sistema. Abaixo está a estrutura completa dos campos:

| Coluna | Tipo | Obrigatório | Descrição | Exemplo |
|--------|------|-------------|-----------|----------|
| `data` | Data | ✅ Sim | Data da transação | 2025-05-22 |
| `descricao` | Texto | ✅ Sim | Descrição da transação | Supermercado |
| `valor` | Número | ✅ Sim | Valor da transação (use . como separador decimal) | 150.75 |
| `tipo` | Texto | ✅ Sim | Tipo da transação | receita/despesa |
| `categoria` | Texto | ❌ Opcional | Categoria da transação | Alimentação |
| `preco` | Número | ❌ Opcional | Preço unitário (para investimentos) | 45.20 |
| `quantidade` | Número | ❌ Opcional | Quantidade (para investimentos) | 10 |
| `tipo_operacao` | Texto | ❌ Opcional | Tipo de operação | compra/venda |
| `taxa` | Número | ❌ Opcional | Taxa da operação (em %) | 0.5 |
| `ativo` | Texto | ❌ Opcional | Ativo financeiro relacionado | PETR4, BTC |
| `forma_pagamento` | Texto | ❌ Opcional | Forma de pagamento utilizada | Cartão, PIX |
| `indicador1` | Número | ❌ Opcional | Indicador personalizado 1 | 1.5 |
| `indicador2` | Número | ❌ Opcional | Indicador personalizado 2 | 2.3 |

### Dicas de Uso

- **Para transações comuns**: Preencha pelo menos os campos obrigatórios (`data`, `descricao`, `valor`, `tipo`).
- **Para investimentos**: Utilize os campos específicos como `preco`, `quantidade` e `ativo`.
- **Categorização**: Use o campo `categoria` para classificar suas transações.
- **Indicadores**: Os campos `indicador1` e `indicador2` podem ser usados para métricas personalizadas.
- **Formas de pagamento**: Registre como cada transação foi paga usando `forma_pagamento`.

## 📋 Índice de Arquivos

### 📁 Diretórios Principais

#### alertas_arq/
- **Descrição**: Módulo responsável pelo gerenciamento de alertas financeiros
- **Arquivos Importantes**:
  - `src/__init__.py`: Inicialização do módulo
  - `src/routes.py`: Rotas relacionadas a alertas
  - `static/js/alertas.js`: Lógica de frontend para alertas

#### dashboard_arq/
- **Descrição**: Módulo do dashboard de visualização de dados
- **Arquivos Importantes**:
  - `src/inserir_dados.py`: Lógica para inserção de dados no dashboard
  - `src/routes.py`: Rotas do dashboard
  - `templates/`: Templates HTML do dashboard

#### upload_arq/
- **Descrição**: Módulo para upload e processamento de arquivos
- **Arquivos Importantes**:
  - `src/processamento.backup.py`: Backup da lógica de processamento
  - `src/routes.py`: Rotas para upload de arquivos

### 📄 Arquivos na Raiz

- `main.py`: Ponto de entrada principal da aplicação
- `requirements.txt`: Lista de dependências do projeto
- `init_db.py`: Script para inicialização do banco de dados
- `update_db.py`: Script para atualização do esquema do banco de dados
- `logger.py`: Configuração de logs da aplicação
- `check_db.py`: Ferramentas para verificação do banco de dados
- `.gitignore`: Configuração de arquivos a serem ignorados pelo Git

## 🔧 Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/analise_financeira
   cd analise_financeira
   ```

2. Crie e ative um ambiente virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # No Windows: venv\Scripts\activate
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure as variáveis de ambiente (crie um arquivo `.env` baseado no `.env.example`)

5. Inicialize o banco de dados:
   ```bash
   python init_db.py
   ```

6. Execute a aplicação:
   ```bash
   python main.py
   ```

## 📝 Licença

Este projeto está sob a licença MIT. Consulte o arquivo LICENSE para obter mais detalhes.

## 🤝 Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues e enviar pull requests.

## 📧 Contato

Para mais informações, entre em contato através do [tassio.ljs@gmail.com](mailto:seu-email@exemplo.com)
