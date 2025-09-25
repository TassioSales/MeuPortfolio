#!/bin/bash

# Cria o diretório .streamlit se não existir
mkdir -p .streamlit

# Copia o arquivo de configuração para o local correto
cp streamlit_config.toml .streamlit/config.toml

# Cria um arquivo de exemplo para secrets se não existir
if [ ! -f ".streamlit/secrets.toml" ]; then
    echo "[secrets]" > .streamlit/secrets.toml
    echo "MISTRAL_API_KEY = ''" >> .streamlit/secrets.toml
    echo "GEMINI_API_KEY = ''" >> .streamlit/secrets.toml
fi

echo "Configuração concluída. Por favor, adicione suas chaves de API no arquivo .streamlit/secrets.toml"
