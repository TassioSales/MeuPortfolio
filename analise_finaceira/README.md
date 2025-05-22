# analise_financeira - Sistema de Gerenciamento

**analise_financeira** é um sistema completo para controle, análise e visualização de finanças pessoais ou empresariais. O projeto é dividido em módulos principais:
- **Upload de Arquivos:** Importação e processamento automatizado de extratos e dados financeiros.
- **Dashboard:** Visualização interativa de métricas, gráficos e relatórios.
- **Alertas Manuais:** Gerenciamento de alertas financeiros personalizados.

O sistema possui arquitetura modular, interface moderna, logging padronizado e foco em usabilidade, performance e segurança.

Este é um sistema de análise financeira desenvolvido em Python com Flask, projetado para processar, analisar e visualizar dados financeiros de forma eficiente. O sistema é modular e inclui funcionalidades para upload de arquivos, geração de alertas e visualização de dados em dashboards interativos.

## 🚀 Funcionalidades Principais

- **Página Inicial Moderna**: Saudação dinâmica (bom dia/tarde/noite), destaques com métricas, dicas de uso e novidades do sistema.
- **Logo Personalizado**: Logo "TS" (Tassio Sales) no topo da home.
- **Relógio Digital**: Mostra a hora atual na navbar, alinhado à direita.
- **Upload de Arquivos**: Processamento de arquivos financeiros (incluindo PDFs).
- **Análise de Dados**: Processamento e análise de dados financeiros.
- **Alertas Manuais**: Gerenciamento completo de alertas financeiros personalizados.
- **Dashboard**: Visualização interativa de métricas financeiras.
- **Banco de Dados**: Armazenamento seguro de transações e configurações.
- **Visual Premium**: Gradiente de fundo, cards animados, efeitos de hover e responsividade.

## 🛠️ Tecnologias Utilizadas

- **Backend**: Python 3.x, Flask
- **Banco de Dados**: SQLAlchemy
- **Processamento de Dados**: Pandas, NumPy
- **Processamento de PDF**: pdfplumber, PyPDF2
- **Frontend**: HTML, CSS, JavaScript
- **Outras Bibliotecas**: 
  - Flask-WTF para formulários
  - python-dotenv para gerenciamento de variáveis de ambiente

## 📦 Estrutura do Projeto

```
analise_financeira/
├── alertas_arq/         # Módulo de alertas
├── banco/               # Configurações do banco de dados
├── dashboard_arq/       # Módulo de dashboard
│   └── src/
│       ├── __init__.py
│       ├── acoes.py     # Gerenciamento de transações
│       ├── inserir_dados.py  # Inserção de dados
│       └── logger.py    # Configuração de logging
├── static/              # Arquivos estáticos (CSS, JS, imagens)
├── templates/          # Templates HTML
├── upload_arq/         # Módulo de upload de arquivos
├── uploads/            # Arquivos enviados pelos usuários
├── venv/               # Ambiente virtual
├── .gitignore          # Arquivo gitignore
├── main.py             # Ponto de entrada da aplicação
├── requirements.txt    # Dependências do projeto
└── README.md           # Este arquivo
```

## 🆕 Novidades Recentes

- **22/05/2025:** Melhorias no gerenciamento de transações:
  - Aprimoramento do sistema de edição de transações
  - Validação robusta de tipos de dados
  - Tratamento automático de valores negativos para despesas
  - Sistema de logging aprimorado com rastreamento de requisições
  - Melhor tratamento de erros e mensagens para o usuário
  - Prevenção de condições de corrida em operações de banco de dados

- **20/05/2025:** Melhorias no sistema:
  - Upload de arquivos: Suporte a mais colunas e processamento aprimorado
  - Limpeza de dados: Correção do tratamento de respostas no frontend
  - JavaScript: Melhorias no tratamento de respostas HTTP
  - Mensagens: Padronização de mensagens de sucesso e erro

- **19/05/2025:** Logging padronizado em todo o sistema, facilitando rastreio de erros e manutenção.

- Melhorias de usabilidade: ajustes visuais e de navegação para uma experiência mais intuitiva.
- Correções de bugs: diversas correções para maior estabilidade e segurança.
- Modernização visual: interface mais limpa, responsiva e agradável.
- Alertas Manuais: gerencie alertas financeiros personalizados facilmente.
- Filtros avançados na tabela de transações para facilitar sua análise.

## 🚦 Status do Projeto

> ⚠️ **EM DESENVOLVIMENTO ATIVO**

O projeto analise_financeira está em constante evolução. Novas funcionalidades e melhorias visuais são implementadas regularmente.

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

Para mais informações, entre em contato através do [seu-email@exemplo.com](mailto:seu-email@exemplo.com)
