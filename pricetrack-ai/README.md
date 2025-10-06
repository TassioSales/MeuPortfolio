# 🚀 PriceTrack AI - Consultora de E-commerce Inteligente

<div align="center">

![PriceTrack AI](https://img.shields.io/badge/PriceTrack-AI-blue?style=for-the-badge&logo=streamlit)
![Python](https://img.shields.io/badge/Python-3.8+-green?style=for-the-badge&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red?style=for-the-badge&logo=streamlit)
![Google Gemini](https://img.shields.io/badge/Google-Gemini-orange?style=for-the-badge&logo=google)

**Transforme dados de preços em decisões acionáveis com a Artemis, sua consultora de e-commerce pessoal**

[![Demo](https://img.shields.io/badge/Ver-Demo-green?style=for-the-badge)](https://pricetrack-ai.streamlit.app)
[![Documentação](https://img.shields.io/badge/Ler-Documentação-blue?style=for-the-badge)](#documentação)

</div>

## 🎯 Visão Geral

O **PriceTrack AI** é uma aplicação Streamlit avançada que funciona como um consultor de e-commerce pessoal e proativo. Utilizando a API Google Gemini 1.5 Pro, a aplicação oferece:

- 🔍 **Pesquisa Inteligente**: Busca produtos usando linguagem natural
- 📊 **Dashboard Preditivo**: Análise de preços com insights de IA
- ⚔️ **Comparador Avançado**: Comparação lado a lado com recomendações personalizadas
- 🔔 **Alertas Proativos**: Notificações quando preços caem abaixo de thresholds
- 🤖 **Chatbot Contextual**: Artemis responde perguntas com memória de conversa

## ✨ Funcionalidades Principais

### 🔍 Pesquisa e Adição de Produtos
- Busca por linguagem natural em e-commerces brasileiros
- Simulação inteligente de ofertas com scores de relevância
- Geração automática de tags e thresholds de alerta
- Adição manual com validação robusta

### 📊 Dashboard de Análise
- Visualizações interativas com Plotly
- Resumos inteligentes gerados pela IA
- Análise de sentimento de reviews
- Avaliação de qualidade de ofertas com forecasts
- Chatbot contextual com memória

### ⚔️ Comparador Inteligente
- Comparação de até 5 produtos simultaneamente
- Recomendações personalizadas baseadas no foco do usuário
- Análise de custo-benefício detalhada
- Histórico de comparações salvas

### 🔔 Alertas e Notificações
- Configuração de thresholds inteligentes
- Notificações por email (SMTP configurável)
- Dashboard de alertas pendentes
- Analytics de economia e performance

## 🛠️ Tecnologias Utilizadas

- **Frontend**: Streamlit 1.28+
- **IA**: Google Gemini 1.5 Pro
- **Banco de Dados**: SQLite + SQLAlchemy ORM
- **Validação**: Pydantic
- **Visualização**: Plotly
- **Logging**: Python logging com rotação
- **Email**: SMTP para notificações

## 🚀 Instalação e Configuração

### 1. Pré-requisitos

- Python 3.8 ou superior
- Conta Google Cloud com API Gemini habilitada
- (Opcional) Conta SMTP para notificações por email

### 2. Clone o Repositório

```bash
git clone https://github.com/seu-usuario/pricetrack-ai.git
cd pricetrack-ai
```

### 3. Instale as Dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as Secrets

Crie o arquivo `.streamlit/secrets.toml`:

```toml
# .streamlit/secrets.toml
GEMINI_API_KEY = "sua_chave_api_gemini_aqui"

# Opcional: Configurações SMTP para alertas por email
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "seu_email@gmail.com"
SMTP_PASSWORD = "sua_senha_app"
```

### 5. Execute a Aplicação

```bash
streamlit run 🏠_Home.py
```

A aplicação estará disponível em `http://localhost:8501`

## 📁 Estrutura do Projeto

```
pricetrack-ai/
├── 🏠_Home.py                          # Página inicial
├── pages/
│   ├── 1_🔎_Pesquisar_e_Adicionar_Produto.py
│   ├── 2_📊_Dashboard_de_Análise.py
│   ├── 3_⚔️_Comparador_Inteligente.py
│   └── 4_🔔_Alertas_e_Notificações.py
├── core/
│   ├── logger.py                       # Sistema de logging
│   ├── models.py                       # Modelos SQLAlchemy + Pydantic
│   ├── database.py                     # Operações de banco
│   ├── ai_services.py                  # Serviços de IA
│   └── utils.py                        # Funções auxiliares
├── logs/                               # Arquivos de log
├── tests/
│   └── test_ai_services.py            # Testes unitários
├── .streamlit/
│   └── secrets.toml                    # Configurações
├── requirements.txt                    # Dependências
└── README.md                          # Este arquivo
```

## 🔧 Configuração Avançada

### Logging

O sistema de logging está configurado para:
- Rotação automática de arquivos (10MB, 5 backups)
- Níveis INFO para sucessos, ERROR para falhas
- Formatação estruturada com timestamp
- Logs salvos em `logs/app.log`

### Banco de Dados

- SQLite com SQLAlchemy ORM
- Migrações via Alembic (futuro)
- Índices otimizados para performance
- Validação com Pydantic

### IA e Segurança

- Safety settings configurados para Gemini
- Retry logic com exponential backoff
- Cache inteligente para otimização
- Validação de inputs para segurança

## 🧪 Testes

Execute os testes unitários:

```bash
pytest tests/ -v
```

Os testes incluem:
- Mocking da API Gemini
- Validação de modelos Pydantic
- Testes de funções auxiliares

## 📊 Monitoramento e Logs

### Verificar Logs

```bash
# Logs em tempo real
tail -f logs/app.log

# Logs de erro
grep "ERROR" logs/app.log

# Logs de ações do usuário
grep "Ação do usuário" logs/app.log
```

### Métricas Importantes

- Taxa de sucesso da API Gemini
- Tempo de resposta das consultas
- Erros de validação de dados
- Alertas disparados

## 🚨 Troubleshooting

### Problemas Comuns

**1. Erro de API Key**
```
Erro: GEMINI_API_KEY não encontrada
Solução: Verifique o arquivo .streamlit/secrets.toml
```

**2. Erro de Banco de Dados**
```
Erro: Falha na conexão com banco
Solução: Verifique permissões de escrita no diretório
```

**3. Erro de Dependências**
```
Erro: Módulo não encontrado
Solução: pip install -r requirements.txt
```

### Logs de Debug

Para debug detalhado, altere o nível de logging em `core/logger.py`:

```python
logging.basicConfig(level=logging.DEBUG)
```

## 🚀 Deploy em Produção

### Streamlit Cloud

1. Conecte seu repositório GitHub
2. Configure as secrets no painel do Streamlit Cloud
3. Deploy automático a cada push

### Docker (Futuro)

```dockerfile
FROM python:3.9-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "🏠_Home.py"]
```

## 🔮 Roadmap

### Versão 2.0
- [ ] Integração real com APIs de e-commerce (Mercado Livre, Amazon)
- [ ] Sistema de autenticação completo
- [ ] Dashboard administrativo
- [ ] API REST para integrações
- [ ] Notificações push mobile

### Versão 3.0
- [ ] Machine Learning para previsão de preços
- [ ] Análise de sentimento em tempo real
- [ ] Integração com redes sociais
- [ ] Sistema de cashback
- [ ] Marketplace próprio

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 👥 Equipe

- **Desenvolvedor Principal**: [Seu Nome]
- **IA Specialist**: Artemis (Google Gemini)
- **Design**: Streamlit + Custom CSS

## 📞 Suporte

- 📧 Email: suporte@pricetrack-ai.com
- 🐛 Issues: [GitHub Issues](https://github.com/seu-usuario/pricetrack-ai/issues)
- 📖 Documentação: [Wiki](https://github.com/seu-usuario/pricetrack-ai/wiki)

---

<div align="center">

**Desenvolvido com ❤️ usando Streamlit e Google Gemini AI**

[![Made with Streamlit](https://img.shields.io/badge/Made%20with-Streamlit-red?style=for-the-badge&logo=streamlit)](https://streamlit.io)
[![Powered by Gemini](https://img.shields.io/badge/Powered%20by-Gemini-orange?style=for-the-badge&logo=google)](https://ai.google.dev)

</div>
