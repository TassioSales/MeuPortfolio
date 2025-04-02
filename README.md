# Product Management API

Uma API REST simples para gerenciamento de produtos usando FastAPI.

## Funcionalidades

- CRUD completo de produtos
- Validação de dados
- Documentação automática (Swagger UI)
- Banco de dados SQLite

## Como executar

1. Instale as dependências:
```bash
pip install -r requirements.txt
```

2. Execute o servidor:
```bash
uvicorn app.main:app --reload
```

3. Acesse a documentação:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Estrutura do Projeto

```
app/
├── main.py           # Arquivo principal da aplicação
├── models.py         # Modelos do banco de dados
├── schemas.py        # Schemas Pydantic
└── database.py       # Configuração do banco de dados
``` 