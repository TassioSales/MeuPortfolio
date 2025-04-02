# Todo API com Interface Kivy

Uma aplicação moderna e robusta para gerenciamento de tarefas, desenvolvida com FastAPI e Kivy.

## 🚀 Tecnologias Utilizadas

- **Backend**: FastAPI (Python)
- **Frontend**: Kivy (Interface Gráfica)
- **Banco de Dados**: SQLite
- **APIs**: RESTful
- **Validação**: Pydantic

## ✨ Funcionalidades

### Backend (FastAPI)
- API RESTful completa
- Validação de dados com Pydantic
- Banco de dados SQLite com constraints
- Geração de IDs aleatórios de 8 dígitos
- Validação de status de tarefas
- Tratamento de erros robusto

### Frontend (Kivy)
- Interface gráfica moderna e responsiva
- Navegação intuitiva entre telas
- Indicador de carregamento durante operações
- Validação de campos em tempo real
- Menu dropdown para seleção de status
- Botão de copiar ID para área de transferência
- Atualização automática da lista de tarefas

## 🛠️ Estrutura do Projeto

```
todo_api/
├── app/
│   ├── __init__.py
│   ├── main.py           # Configuração do FastAPI
│   ├── database.py       # Funções do banco de dados
│   ├── crud.py          # Operações CRUD
│   ├── interface.py     # Interface Kivy
│   └── routers/
│       └── tasks.py     # Rotas da API
├── requirements.txt
└── README.md
```

## 🚀 Como Executar

1. Clone o repositório:
```bash
git clone https://github.com/TassioSales/todo_api.git
cd todo_api
```

2. Crie um ambiente virtual e ative-o:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Inicie o servidor FastAPI:
```bash
uvicorn app.main:app --reload
```

5. Em outro terminal, inicie a interface Kivy:
```bash
python -m app.interface
```

## 📝 Endpoints da API

- `GET /tasks/` - Lista todas as tarefas
- `GET /tasks/{task_id}` - Obtém uma tarefa específica
- `POST /tasks/` - Cria uma nova tarefa
- `PUT /tasks/{task_id}` - Atualiza uma tarefa existente
- `DELETE /tasks/{task_id}` - Remove uma tarefa

## 🎯 Status de Tarefas

As tarefas podem ter os seguintes status:
- `pendente`
- `concluido`
- `em andamento`

## 🔒 Validações

- IDs únicos de 8 dígitos
- Status restritos aos valores permitidos
- Campos obrigatórios validados
- Tratamento de erros em todas as operações

## 💡 Recursos Adicionais

- Interface responsiva que se adapta ao tamanho da janela
- Indicador de carregamento durante operações de rede
- Feedback visual para todas as ações do usuário
- Navegação intuitiva entre diferentes telas
- Cópia rápida de IDs para área de transferência

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👥 Autores

- Tassio Sales - [@TassioSales](https://github.com/TassioSales)

## 🙏 Agradecimentos

- FastAPI por fornecer um framework web moderno e rápido
- Kivy por permitir criar interfaces gráficas multiplataforma
- SQLite por oferecer um banco de dados leve e eficiente 