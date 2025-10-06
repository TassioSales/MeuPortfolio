# 🎯 Guia de Uso Rápido - PriceTrack AI

## 🚀 Início Rápido

### 1. Configuração Inicial
```bash
# Clone o repositório
git clone https://github.com/seu-usuario/pricetrack-ai.git
cd pricetrack-ai

# Execute o script de inicialização
chmod +x start.sh
./start.sh

# Ou use Python diretamente
python3 setup.py
```

### 2. Configurar API Gemini
1. Obtenha uma chave da API Google Gemini em [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Edite `.streamlit/secrets.toml`:
```toml
GEMINI_API_KEY = "sua_chave_aqui"
```

### 3. Iniciar a Aplicação
```bash
streamlit run 🏠_Home.py
```

## 📱 Como Usar

### 🔍 Pesquisar Produtos
1. Acesse a página "Pesquisar e Adicionar Produto"
2. Digite o nome do produto (ex: "iPhone 15 Pro Max")
3. A Artemis simulará buscas em e-commerces
4. Clique em "Adicionar ao Monitoramento" para produtos interessantes

### 📊 Dashboard de Análise
1. Selecione um produto na página "Dashboard"
2. Visualize gráficos de preços interativos
3. Leia resumos inteligentes e análises de reviews
4. Use o chatbot para fazer perguntas sobre o produto

### ⚔️ Comparar Produtos
1. Acesse "Comparador Inteligente"
2. Selecione 2-5 produtos para comparar
3. Defina seu foco (ex: "melhor custo-benefício")
4. Receba análise detalhada e recomendações

### 🔔 Configurar Alertas
1. Vá para "Alertas e Notificações"
2. Configure thresholds para produtos monitorados
3. Receba notificações quando preços caem
4. Simule envio de emails para testes

## 🛠️ Funcionalidades Avançadas

### Tags Automáticas
- A Artemis gera tags relevantes automaticamente
- Use tags para filtrar produtos no dashboard
- Tags ajudam na organização e busca

### Análise Preditiva
- Visualize tendências de preços
- Receba forecasts baseados em IA
- Configure alertas inteligentes

### Chatbot Contextual
- Faça perguntas sobre produtos específicos
- A Artemis mantém contexto da conversa
- Respostas baseadas em conhecimento geral

### Logging Robusto
- Todos os logs são salvos em `logs/app.log`
- Rotação automática de arquivos
- Rastreamento de ações do usuário

## 🔧 Configurações

### SMTP para Emails Reais
```toml
# .streamlit/secrets.toml
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "seu_email@gmail.com"
SMTP_PASSWORD = "sua_senha_app"
```

### Personalização de IA
- Ajuste temperatura para respostas mais criativas/conservadoras
- Configure max_tokens para controlar tamanho das respostas
- Modifique safety_settings para diferentes níveis de filtro

## 🐛 Troubleshooting

### Problema: "GEMINI_API_KEY não encontrada"
**Solução**: Configure a chave no arquivo `.streamlit/secrets.toml`

### Problema: "Erro ao conectar com banco"
**Solução**: Verifique permissões de escrita no diretório

### Problema: "Produto não encontrado"
**Solução**: Adicione produtos primeiro na página de pesquisa

### Problema: "Erro na API Gemini"
**Solução**: Verifique sua chave de API e limite de uso

## 📊 Monitoramento

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
- Alertas disparados
- Produtos monitorados

## 🚀 Deploy

### Streamlit Cloud
1. Conecte seu repositório GitHub
2. Configure secrets no painel do Streamlit Cloud
3. Deploy automático a cada push

### Local com Docker (Futuro)
```dockerfile
FROM python:3.9-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "🏠_Home.py"]
```

## 💡 Dicas de Uso

### Para Melhores Resultados
- Seja específico nas buscas de produtos
- Configure thresholds realistas
- Monitore produtos que você realmente compra
- Use o chatbot para dúvidas específicas

### Otimização de Performance
- O cache é automático (30 minutos para IA)
- Logs são rotacionados automaticamente
- Banco SQLite é otimizado com índices

### Segurança
- Nunca commite arquivos de secrets
- Use validação de inputs (automática)
- Monitore logs para atividades suspeitas

## 📞 Suporte

- 📧 Email: suporte@pricetrack-ai.com
- 🐛 Issues: [GitHub Issues](https://github.com/seu-usuario/pricetrack-ai/issues)
- 📖 Documentação: [Wiki](https://github.com/seu-usuario/pricetrack-ai/wiki)

---

**🎉 Divirta-se usando o PriceTrack AI!**
