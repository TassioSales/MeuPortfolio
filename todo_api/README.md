<div align="center">
  <h1 style="color: #2c3e50; font-size: 2.5em; margin-bottom: 20px;">Todo API com Interface Kivy</h1>
  <p style="color: #7f8c8d; font-size: 1.2em; max-width: 800px; margin: 0 auto;">
    Uma aplicação moderna e robusta para gerenciamento de tarefas, desenvolvida com FastAPI e Kivy.
  </p>
</div>

<div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
  <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">🚀 Tecnologias Utilizadas</h2>
  <ul style="list-style: none; padding: 0;">
    <li style="margin: 10px 0; color: #34495e;">• <strong>Backend:</strong> FastAPI (Python)</li>
    <li style="margin: 10px 0; color: #34495e;">• <strong>Frontend:</strong> Kivy (Interface Gráfica)</li>
    <li style="margin: 10px 0; color: #34495e;">• <strong>Banco de Dados:</strong> SQLite</li>
    <li style="margin: 10px 0; color: #34495e;">• <strong>APIs:</strong> RESTful</li>
    <li style="margin: 10px 0; color: #34495e;">• <strong>Validação:</strong> Pydantic</li>
  </ul>
</div>

<div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
  <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">✨ Funcionalidades</h2>
  
  <div style="margin: 20px 0;">
    <h3 style="color: #2c3e50;">Backend (FastAPI)</h3>
    <ul style="list-style: none; padding: 0;">
      <li style="margin: 10px 0; color: #34495e;">• API RESTful completa</li>
      <li style="margin: 10px 0; color: #34495e;">• Validação de dados com Pydantic</li>
      <li style="margin: 10px 0; color: #34495e;">• Banco de dados SQLite com constraints</li>
      <li style="margin: 10px 0; color: #34495e;">• Geração de IDs aleatórios de 8 dígitos</li>
      <li style="margin: 10px 0; color: #34495e;">• Validação de status de tarefas</li>
      <li style="margin: 10px 0; color: #34495e;">• Tratamento de erros robusto</li>
    </ul>
  </div>

  <div style="margin: 20px 0;">
    <h3 style="color: #2c3e50;">Frontend (Kivy)</h3>
    <ul style="list-style: none; padding: 0;">
      <li style="margin: 10px 0; color: #34495e;">• Interface gráfica moderna e responsiva</li>
      <li style="margin: 10px 0; color: #34495e;">• Navegação intuitiva entre telas</li>
      <li style="margin: 10px 0; color: #34495e;">• Indicador de carregamento durante operações</li>
      <li style="margin: 10px 0; color: #34495e;">• Validação de campos em tempo real</li>
      <li style="margin: 10px 0; color: #34495e;">• Menu dropdown para seleção de status</li>
      <li style="margin: 10px 0; color: #34495e;">• Botão de copiar ID para área de transferência</li>
      <li style="margin: 10px 0; color: #34495e;">• Atualização automática da lista de tarefas</li>
    </ul>
  </div>
</div>

<div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
  <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">🛠️ Estrutura do Projeto</h2>
  <pre style="background-color: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 5px; overflow-x: auto;">
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
└── README.md</pre>
</div>

<div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
  <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">🚀 Como Executar</h2>
  <ol style="color: #34495e;">
    <li style="margin: 10px 0;">Clone o repositório:
      <pre style="background-color: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 5px; overflow-x: auto;">git clone https://github.com/TassioSales/todo_api.git
cd todo_api</pre>
    </li>
    <li style="margin: 10px 0;">Crie um ambiente virtual e ative-o:
      <pre style="background-color: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 5px; overflow-x: auto;">python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows</pre>
    </li>
    <li style="margin: 10px 0;">Instale as dependências:
      <pre style="background-color: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 5px; overflow-x: auto;">pip install -r requirements.txt</pre>
    </li>
    <li style="margin: 10px 0;">Inicie o servidor FastAPI:
      <pre style="background-color: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 5px; overflow-x: auto;">uvicorn app.main:app --reload</pre>
    </li>
    <li style="margin: 10px 0;">Em outro terminal, inicie a interface Kivy:
      <pre style="background-color: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 5px; overflow-x: auto;">python -m app.interface</pre>
    </li>
  </ol>
</div>

<div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
  <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">📝 Endpoints da API</h2>
  <ul style="list-style: none; padding: 0;">
    <li style="margin: 10px 0; color: #34495e;">• <code style="background-color: #2c3e50; color: #ecf0f1; padding: 2px 5px; border-radius: 3px;">GET /tasks/</code> - Lista todas as tarefas</li>
    <li style="margin: 10px 0; color: #34495e;">• <code style="background-color: #2c3e50; color: #ecf0f1; padding: 2px 5px; border-radius: 3px;">GET /tasks/{task_id}</code> - Obtém uma tarefa específica</li>
    <li style="margin: 10px 0; color: #34495e;">• <code style="background-color: #2c3e50; color: #ecf0f1; padding: 2px 5px; border-radius: 3px;">POST /tasks/</code> - Cria uma nova tarefa</li>
    <li style="margin: 10px 0; color: #34495e;">• <code style="background-color: #2c3e50; color: #ecf0f1; padding: 2px 5px; border-radius: 3px;">PUT /tasks/{task_id}</code> - Atualiza uma tarefa existente</li>
    <li style="margin: 10px 0; color: #34495e;">• <code style="background-color: #2c3e50; color: #ecf0f1; padding: 2px 5px; border-radius: 3px;">DELETE /tasks/{task_id}</code> - Remove uma tarefa</li>
  </ul>
</div>

<div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
  <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">🎯 Status de Tarefas</h2>
  <p style="color: #34495e;">As tarefas podem ter os seguintes status:</p>
  <ul style="list-style: none; padding: 0;">
    <li style="margin: 10px 0; color: #34495e;">• <code style="background-color: #2c3e50; color: #ecf0f1; padding: 2px 5px; border-radius: 3px;">pendente</code></li>
    <li style="margin: 10px 0; color: #34495e;">• <code style="background-color: #2c3e50; color: #ecf0f1; padding: 2px 5px; border-radius: 3px;">concluido</code></li>
    <li style="margin: 10px 0; color: #34495e;">• <code style="background-color: #2c3e50; color: #ecf0f1; padding: 2px 5px; border-radius: 3px;">em andamento</code></li>
  </ul>
</div>

<div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
  <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">🔒 Validações</h2>
  <ul style="list-style: none; padding: 0;">
    <li style="margin: 10px 0; color: #34495e;">• IDs únicos de 8 dígitos</li>
    <li style="margin: 10px 0; color: #34495e;">• Status restritos aos valores permitidos</li>
    <li style="margin: 10px 0; color: #34495e;">• Campos obrigatórios validados</li>
    <li style="margin: 10px 0; color: #34495e;">• Tratamento de erros em todas as operações</li>
  </ul>
</div>

<div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
  <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">💡 Recursos Adicionais</h2>
  <ul style="list-style: none; padding: 0;">
    <li style="margin: 10px 0; color: #34495e;">• Interface responsiva que se adapta ao tamanho da janela</li>
    <li style="margin: 10px 0; color: #34495e;">• Indicador de carregamento durante operações de rede</li>
    <li style="margin: 10px 0; color: #34495e;">• Feedback visual para todas as ações do usuário</li>
    <li style="margin: 10px 0; color: #34495e;">• Navegação intuitiva entre diferentes telas</li>
    <li style="margin: 10px 0; color: #34495e;">• Cópia rápida de IDs para área de transferência</li>
  </ul>
</div>

<div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
  <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">📄 Licença</h2>
  <p style="color: #34495e;">Este projeto está sob a licença MIT. Veja o arquivo <a href="LICENSE" style="color: #3498db; text-decoration: none;">LICENSE</a> para mais detalhes.</p>
</div>

<div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
  <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">👥 Autores</h2>
  <p style="color: #34495e;">• Tassio Sales - <a href="https://github.com/TassioSales" style="color: #3498db; text-decoration: none;">@TassioSales</a></p>
</div>

<div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
  <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">🙏 Agradecimentos</h2>
  <ul style="list-style: none; padding: 0;">
    <li style="margin: 10px 0; color: #34495e;">• FastAPI por fornecer um framework web moderno e rápido</li>
    <li style="margin: 10px 0; color: #34495e;">• Kivy por permitir criar interfaces gráficas multiplataforma</li>
    <li style="margin: 10px 0; color: #34495e;">• SQLite por oferecer um banco de dados leve e eficiente</li>
  </ul>
</div> 