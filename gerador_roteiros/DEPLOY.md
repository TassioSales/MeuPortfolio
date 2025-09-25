# Instruções de Implantação no Streamlit Cloud

## Pré-requisitos
- Conta no [Streamlit Cloud](https://streamlit.io/cloud)
- Repositório GitHub com o código do projeto
- Chaves de API para os serviços de IA (Mistral e/ou Gemini)

## Passos para Implantação

1. **Configure as chaves de API**
   - Acesse o [Streamlit Cloud](https://share.streamlit.io/)
   - Vá para "Your Apps" e clique em "New app"
   - Selecione seu repositório e branch
   - No campo "Advanced settings", adicione as seguintes variáveis de ambiente:
     - `MISTRAL_API_KEY`: Sua chave da API Mistral
     - `GEMINI_API_KEY`: Sua chave da API Google Gemini

2. **Configuração do Aplicativo**
   - **Pasta do App**: `/` (raiz do repositório)
   - **Arquivo Principal**: `app.py`
   - **Versão do Python**: 3.13.7 (definido em `runtime.txt`)

3. **Arquivos de Configuração**
   - `requirements.txt`: Contém todas as dependências necessárias
   - `.streamlit/config.toml`: Configurações do Streamlit
   - `.streamlit/secrets.toml`: Chaves de API (não versionado no Git)

4. **Testes Locais (Opcional)**
   ```bash
   # Crie um ambiente virtual
   python -m venv venv
   source venv/bin/activate  # No Windows: venv\Scripts\activate

   # Instale as dependências
   pip install -r requirements.txt

   # Execute o aplicativo localmente
   streamlit run app.py
   ```

5. **Implante no Streamlit Cloud**
   - Faça commit e push das alterações para o GitHub
   - O Streamlit Cloud irá detectar automaticamente as alterações e fazer um novo deploy

## Solução de Problemas

### Erro de Conexão
- Verifique se o endereço e a porta estão corretos no `config.toml`
- Certifique-se de que o aplicativo está configurado para aceitar conexões externas (`0.0.0.0`)

### Problemas de Dependência
- Verifique se todas as dependências estão listadas no `requirements.txt`
- Tente usar versões específicas das bibliotecas para evitar conflitos

### Erros de API
- Verifique se as chaves de API estão configuradas corretamente
- Verifique se você tem créditos suficientes no serviço de IA

## Recursos Adicionais
- [Documentação do Streamlit Cloud](https://docs.streamlit.io/streamlit-cloud/)
- [Guia de Implantação](https://docs.streamlit.io/streamlit-cloud/get-started/deploy-an-app)
- [Solução de Problemas](https://docs.streamlit.io/streamlit-cloud/troubleshooting)
