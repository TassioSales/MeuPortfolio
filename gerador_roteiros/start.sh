#!/bin/bash

# Configura as variáveis de ambiente
export STREAMLIT_SERVER_PORT=8501
export STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Inicia o Streamlit
streamlit run app.py --server.port=$STREAMLIT_SERVER_PORT --server.address=$STREAMLIT_SERVER_ADDRESS
