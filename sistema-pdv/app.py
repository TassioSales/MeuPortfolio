"""
Sistema de Ponto de Venda (PDV)
Aplicativo principal que gerencia a navegação entre as páginas.
"""
import os
import streamlit as st
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv()

# Configurações da página
st.set_page_config(
    page_title="Sistema PDV",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Importa os utilitários necessários
from utils.logger import logger
from utils.database import init_db

# Inicializa o banco de dados
init_db()

# Verifica se o usuário está autenticado
def verificar_autenticacao():
    """Verifica se o usuário está autenticado."""
    if 'usuario' not in st.session_state:
        # Se não estiver autenticado, redireciona para a página de login
        st.switch_page("pages/00_🔐_login.py")
    return st.session_state.get('usuario')

# Página inicial
def main():
    """Página principal do aplicativo."""
    st.title("Sistema de Ponto de Venda (PDV)")
    st.markdown("---")
    
    # Verifica se o usuário está autenticado
    usuario = verificar_autenticacao()
    
    # Se chegou até aqui, o usuário está autenticado
    st.success(f"Bem-vindo(a) ao Sistema PDV, {usuario.get('nome', 'Usuário')}!")
    
    # Redireciona para o dashboard
    st.switch_page("pages/01_🏠_dashboard.py")

if __name__ == "__main__":
    main()
