# Sistema de Gerenciamento de Estoque

Um sistema completo para gerenciamento de estoque construído com FastAPI (backend) e Flask (frontend).

## 🚀 Funcionalidades

- ✨ Cadastro e gerenciamento de produtos
- 📦 Controle de estoque (entradas e saídas)
- 📊 Dashboard com estatísticas
- 📝 Histórico de movimentações
- 🔍 Busca e filtros avançados
- ⚡ Interface moderna e responsiva

## 🛠️ Tecnologias

### Backend
- FastAPI
- SQLAlchemy
- Pydantic
- SQLite

### Frontend
- Flask
- Bootstrap 4
- JavaScript
- HTML/CSS

## 📋 Pré-requisitos

- Python 3.8+
- pip (gerenciador de pacotes Python)

## 🔧 Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/estoque-api.git
cd estoque-api
```

2. Instale as dependências do backend:
```bash
pip install -r requirements.txt
```

3. Instale as dependências do frontend:
```bash
cd frontend
pip install -r requirements.txt
```

## ▶️ Como executar

1. Inicie o backend (na pasta raiz):
```bash
python -m uvicorn app.main:app --reload
```

2. Inicie o frontend (na pasta frontend):
```bash
python app.py
```

3. Acesse:
- Frontend: http://localhost:5000
- API: http://localhost:8000
- Documentação da API: http://localhost:8000/docs

## 📚 Estrutura do Projeto

```
estoque-api/
├── app/
│   ├── __init__.py
│   ├── main.py          # Configuração principal da API
│   ├── database.py      # Configuração do banco de dados
│   ├── models.py        # Modelos do banco de dados
│   ├── schemas.py       # Schemas Pydantic
│   ├── crud.py         # Operações CRUD
│   └── routers/        # Rotas da API
│       └── products.py
├── frontend/
│   ├── app.py          # Aplicação Flask
│   ├── static/         # Arquivos estáticos
│   └── templates/      # Templates HTML
└── sql_app.db         # Banco de dados SQLite
```

## 🔒 Validações e Segurança

- Validação rigorosa de dados em múltiplas camadas
- Proteção contra estoque negativo
- Histórico detalhado de alterações
- Tratamento adequado de erros
- Feedback claro para o usuário

## 🔄 Atualizações Recentes

- Melhorada a validação de dados
- Corrigido bug na atualização de estoque
- Adicionadas constraints no banco de dados
- Melhorado o tratamento de erros
- Interface mais intuitiva

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👤 Autor

Seu Nome
- GitHub: [@seu-usuario](https://github.com/seu-usuario)
- LinkedIn: [seu-linkedin](https://linkedin.com/in/seu-usuario)

## 🤝 Contribuindo

Contribuições são sempre bem-vindas! Por favor, leia o [CONTRIBUTING.md](CONTRIBUTING.md) primeiro.
