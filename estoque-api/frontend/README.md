# Frontend do Sistema de Estoque

Interface web do sistema de gerenciamento de estoque construída com Flask e Bootstrap.

## 🎯 Características

- 📊 Dashboard interativo
- 📱 Design responsivo
- 🎨 Interface moderna e intuitiva
- ⚡ Validações em tempo real
- 🔔 Feedback visual para o usuário

## 🛠️ Tecnologias

- Flask
- Bootstrap 4
- JavaScript
- HTML5/CSS3
- Jinja2 Templates

## 📋 Dependências

```
Flask==2.0.1
Flask-Bootstrap4==4.0.2
requests==2.26.0
python-dotenv==0.19.0
```

## 🚀 Como Executar

1. Instale as dependências:
```bash
pip install -r requirements.txt
```

2. Configure as variáveis de ambiente (opcional):
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

3. Execute o servidor:
```bash
python app.py
```

4. Acesse http://localhost:5000

## 📚 Estrutura do Projeto

```
frontend/
├── app.py              # Aplicação Flask
├── static/            
│   ├── css/           # Estilos CSS
│   ├── js/            # Scripts JavaScript
│   └── img/           # Imagens
├── templates/
│   ├── base.html      # Template base
│   └── index.html     # Página principal
└── requirements.txt    # Dependências
```

## 🔒 Validações

- Validação de formulários em JavaScript
- Feedback visual imediato
- Mensagens de erro claras
- Confirmação de ações importantes

## ⚙️ Configurações

O frontend se conecta ao backend através da variável `API_BASE_URL` em `app.py`. Por padrão, usa:
```python
API_BASE_URL = "http://localhost:8000"
```

## 🔄 Funcionalidades

1. **Dashboard**
   - Visão geral do estoque
   - Estatísticas importantes
   - Alertas de estoque baixo

2. **Gestão de Produtos**
   - Listagem com paginação
   - Busca e filtros
   - CRUD completo

3. **Controle de Estoque**
   - Entrada e saída
   - Histórico de movimentações
   - Validações de quantidade

4. **Interface**
   - Design responsivo
   - Temas Bootstrap
   - Ícones intuitivos

## 🐛 Tratamento de Erros

- Mensagens de erro amigáveis
- Feedback visual claro
- Logs detalhados
- Tratamento de conexão offline

## 📝 Notas de Desenvolvimento

- Use `python app.py` para desenvolvimento
- O modo debug está ativado por padrão
- As alterações são recarregadas automaticamente
- Logs detalhados no console
