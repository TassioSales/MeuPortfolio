<div align="center">

# Patrimônio — ERP Financeiro Pessoal

**Gestão completa de finanças, investimentos e empréstimos em um único app portátil.**

<p align="center">
  <img src="https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Gem%20stone/3D/gem_stone_3d.png" width="100" alt="Patrimônio">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13-3776ab?style=flat-square&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/Django-5.1.4-092E20?style=flat-square&logo=django&logoColor=white">
  <img src="https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=flat-square&logo=bootstrap&logoColor=white">
  <img src="https://img.shields.io/badge/SQLite-default-003B57?style=flat-square&logo=sqlite&logoColor=white">
  <img src="https://img.shields.io/badge/Windows-Portátil-0078d4?style=flat-square&logo=windows&logoColor=white">
  <img src="https://img.shields.io/badge/License-MIT-00d4aa?style=flat-square">
</p>

</div>

---

## Visão Geral

**Patrimônio** é um ERP financeiro pessoal construído com Django 5.1.4, distribuído como executável Windows standalone (`.exe`) via PyInstaller + Waitress. Roda 100% offline, sem instalar nada, diretamente do pendrive ou pasta local.

Cobre desde o controle básico de receitas e despesas até cotações em tempo real de ações e FIIs, simulações de empréstimos com SAC/Price e cálculo de CET.

---

## Funcionalidades

### Dashboard & Visão Geral
- Painel centralizado com Receitas, Despesas, Saldo do Mês e Saldo Total
- Gráfico de Fluxo Financeiro (últimos 6 meses)
- Feed de atividades recentes
- Navegação por mês com setas

### Transações
- Cadastro de receitas e despesas com categoria, método de pagamento e data
- Lançamento rápido via modal flutuante (disponível em todas as telas)
- Filtros por tipo, categoria e período
- Importação via **CSV** e **OFX** (extrato bancário)
- Transações recorrentes (semanal, mensal, anual) com geração automática

### Orçamentos & Metas
- Orçamentos mensais por categoria com barra de progresso e alertas visuais
- Metas financeiras com acompanhamento percentual de conclusão

### Calendário Financeiro
- Visualização mensal de transações em formato de calendário
- Navegação por mês com totais de receitas e despesas por dia

### Fluxo de Caixa
- Projeção de entradas e saídas futuras com base em transações recorrentes
- Gráfico de saldo projetado semana a semana

### Contas Bancárias
- Gerenciamento de múltiplas contas (corrente, poupança, investimento, carteira)
- Transferências entre contas com registro automático de débito e crédito
- Saldo consolidado por conta

### Investimentos — Carteira de Ativos
- Suporte a **ações**, **FIIs**, **criptomoedas**, **moedas estrangeiras** e **renda fixa**
- Preço atual, variação diária (%), Mín/Máx do dia, Mín/Máx 52 semanas
- Gráfico histórico de preços dos últimos **6 meses** por ativo
- Lucro/Prejuízo absoluto e percentual em tempo real
- Agrupamento por símbolo com preço médio calculado automaticamente
- **Market Intelligence**: busca de qualquer ticker com cotação e gráfico instantâneos

### Investimentos — Porto Seguro
- Painel separado para renda fixa (CDB, LCI, LCA, Tesouro, Poupança)
- Cálculo de rentabilidade por índice: **CDI**, **Pré-fixado** e **IPCA+**
- Taxas atualizadas via API do **Banco Central (SELIC/CDI)**
- Acompanhamento de moeda estrangeira (USD, EUR) com cotação em tempo real

### Empréstimos & Financiamentos
- Sistemas de amortização **SAC** e **Price (Tabela Francesa)**
- Cálculo automático de **IOF**, seguro mensal e **CET (Custo Efetivo Total)**
- Tabela de amortização completa parcela a parcela
- Registro de pagamentos com histórico e saldo devedor atualizado
- Suporte a aporte adicional de capital

### Relatórios
- Gráficos de pizza (distribuição de despesas) e barras (evolução mensal)
- Exportação em **PDF**, **CSV**, **XLSX** e **JSON**
- Filtros por período, categoria e tipo

### Auditoria
- Log de todas as operações criação/edição/exclusão com usuário e timestamp

### Configurações
- Interface para inserir o **token BRAPI** sem editar arquivos manualmente
- Instruções passo a passo para criar conta gratuita em brapi.dev
- Status em tempo real das fontes de dados (BRAPI, Yahoo Finance, BCB)
- Token salvo e ativado imediatamente, sem reiniciar o servidor

---

## Fontes de Dados de Mercado

| Fonte | Uso | Autenticação |
|-------|-----|-------------|
| **brapi.dev** | Cotações de ações e FIIs brasileiros (.SA) | Token gratuito (opcional) |
| **Yahoo Finance v8** | Fallback universal para todos os tickers | Sem autenticação |
| **AwesomeAPI** | Câmbio USD/BRL e EUR/BRL em tempo real | Sem autenticação |
| **BCB (SGSA API)** | SELIC, CDI, IPCA, IGPM mensais | Sem autenticação |

> Todas as cotações são cacheadas por 5 minutos para evitar rate limiting.

---

## Início Rápido — Executável Portátil

A maneira mais simples de usar o Patrimônio é via executável.

**1. Execute o arquivo**

Dê duplo clique em `Patrimonio.exe` (pasta `dist/`). O servidor sobe na porta **8080** e o navegador abre automaticamente.

**2. (Opcional) Configure o token BRAPI**

Para cotações mais estáveis de FIIs e ações brasileiras, acesse **Configurações** no menu lateral e siga os 4 passos exibidos na tela. O plano gratuito do brapi.dev é suficiente.

**3. Acesso na rede local**

O terminal exibe seu IP local (ex: `http://192.168.1.10:8080`). Use esse endereço no celular ou tablet na mesma Wi-Fi.

> Na primeira execução o sistema pode levar alguns segundos para montar o ambiente temporário.

---

## Instalação para Desenvolvimento

### Pré-requisitos

- Python 3.10+
- Git

### Passo a Passo

```bash
# 1. Clone o repositório
git clone https://github.com/TassioSales/MeuPortfolio.git
cd MeuPortfolio/finanças

# 2. Crie o ambiente virtual
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env conforme necessário

# 5. Rode as migrações
python manage.py migrate

# 6. (Opcional) Popule com dados de exemplo
python manage.py reset_data

# 7. Inicie o servidor
python manage.py runserver
```

Acesse: `http://localhost:8000`

---

## Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto (`finanças/`):

```env
# Obrigatório em produção
SECRET_KEY=sua-chave-secreta-aqui

# Modo debug (True em dev, False em produção)
DEBUG=True

# Cotações de FIIs e ações BR — obtenha grátis em brapi.dev
BRAPI_TOKEN=seu-token-aqui

# PostgreSQL (opcional — deixe em branco para usar SQLite)
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5432

# Caminho personalizado do SQLite (opcional)
SQLITE_DB_PATH=db.sqlite3
```

> O token BRAPI também pode ser configurado diretamente pela interface em **Configurações → Token BRAPI**, sem editar nenhum arquivo.

---

## Scripts de Automação

| Arquivo | Função |
|---------|--------|
| `install.bat` | Configura Python, cria venv e instala dependências |
| `run.bat` | Inicia o servidor local e abre o navegador |
| `build.bat` | Gera o `Patrimonio.exe` na pasta `dist/` |
| `populate_data.bat` | Cria usuário de teste com transações fictícias |
| `backup.bat` | Exporta o projeto em `.zip` |

---

## Stack Tecnológico

| Camada | Tecnologia |
|--------|-----------|
| Framework | Django 5.1.4 |
| Servidor WSGI | Waitress |
| Banco de Dados | SQLite (padrão) / PostgreSQL |
| Frontend | Bootstrap 5.3 + Bootstrap Icons + Chart.js |
| Interatividade | HTMX |
| Formulários | django-crispy-forms + crispy-bootstrap5 |
| PDF | xhtml2pdf |
| Dados de Mercado | brapi.dev + Yahoo Finance + AwesomeAPI + BCB API |
| Logging | Loguru |
| Arquivos Estáticos | WhiteNoise |
| Build Portátil | PyInstaller 6.x |

---

## Estrutura do Projeto

```
finanças/
├── core/                        # App principal
│   ├── models.py                # Category, Transaction, Budget, Investment, Goal, Loan...
│   ├── views_dashboard.py       # Dashboard, calendário, registro
│   ├── views_transactions.py    # CRUD de transações + importação CSV/OFX
│   ├── views_investments.py     # Carteira, Porto Seguro, busca de ticker
│   ├── views_loans.py           # Empréstimos SAC/Price com IOF e CET
│   ├── views_accounts.py        # Contas bancárias e transferências
│   ├── views_reports.py         # Relatórios + exportação PDF/CSV/XLSX/JSON
│   ├── views_settings.py        # Configuração de token BRAPI
│   ├── market_data.py           # APIs de mercado (BCB, brapi.dev, Yahoo Finance)
│   ├── forms.py                 # Formulários com limpeza de moeda BR (1.234,56)
│   └── urls.py                  # 60+ rotas
├── finance_project/
│   ├── settings.py
│   └── urls.py
├── templates/                   # HTML (Bootstrap 5 + dark mode)
├── static/                      # CSS customizado + favicon
├── manage.py
├── run_app.py                   # Entry point do PyInstaller
├── finance_project.spec         # Spec do PyInstaller
└── requirements.txt
```

---

## Testes

```bash
# Rodar todos os testes
python manage.py test core

# Ou com pytest
python -m pytest
```

| Arquivo de Teste | Cobertura |
|-----------------|-----------|
| `core/tests.py` | Models e views gerais |
| `core/tests_alerts.py` | Alertas de orçamento |
| `core/tests_calendar.py` | Calendário financeiro |
| `core/tests_goals.py` | Progresso de metas |
| `core/tests_import.py` | Importação CSV |
| `core/tests_recurrence.py` | Transações recorrentes |

---

## Gerar o Executável

```bash
# Com o venv ativo
build.bat
```

O arquivo `dist/Patrimonio.exe` é gerado com todos os templates, arquivos estáticos e dependências Python embutidos. Basta copiar a pasta `dist/` para qualquer computador Windows — sem instalar Python.

---

## Contribuição

1. Faça um **Fork** do projeto
2. Crie uma branch: `git checkout -b feature/minha-feature`
3. Commit: `git commit -m 'feat: descrição da mudança'`
4. Push: `git push origin feature/minha-feature`
5. Abra um **Pull Request**

---

## Licença

Distribuído sob a **Licença MIT**.

---

<div align="center">

Desenvolvido por **Tassio Sales**

</div>
