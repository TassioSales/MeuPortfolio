"""
Página de Login do Sistema PDV
"""
import streamlit as st
import time
from utils.auth import authenticate
from utils.logger import logger

# Configurações da página
st.set_page_config(
    page_title="Login - Sistema PDV",
    page_icon="🔐",
    layout="centered",
    initial_sidebar_state="collapsed"
)

def login_page():
    """Renderiza a página de login."""
    st.title("🔐 Acesso ao Sistema")
    st.markdown("---")
    
    # Se já estiver logado, redireciona para o dashboard
    if 'usuario' in st.session_state:
        st.switch_page("pages/01_🏠_dashboard.py")
        return
    
    # Formulário de login
    with st.form("login_form"):
        email = st.text_input("E-mail", placeholder="Digite seu e-mail")
        senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            submit_button = st.form_submit_button("Entrar", use_container_width=True)
        
        # Link para recuperação de senha
        with col2:
            st.markdown(
                "<div style='text-align: right; margin-top: 10px;'>"
                "<a href='#recuperar-senha' style='text-decoration: none; color: #1E88E5;'>"
                "Esqueceu sua senha?"
                "</a>"
                "</div>",
                unsafe_allow_html=True
            )
    
    # Processamento do formulário
    if submit_button:
        if not email or not senha:
            st.error("Por favor, preencha todos os campos.")
            return
        
        # Tenta autenticar o usuário
        with st.spinner("Autenticando..."):
            usuario = authenticate(email, senha)
            
            if usuario:
                # Armazena os dados do usuário na sessão
                st.session_state['usuario'] = {
                    'id': usuario['id'],
                    'nome': usuario['nome'],
                    'email': usuario['email'],
                    'role': usuario['role']
                }
                
                # Atualiza o último acesso no banco de dados
                try:
                    execute_query(
                        "UPDATE usuarios SET ultimo_acesso = CURRENT_TIMESTAMP WHERE id = ?",
                        (usuario['id'],),
                        fetch="none"
                    )
                except Exception as e:
                    logger.error(f"Erro ao atualizar último acesso do usuário ID {usuario['id']}: {e}")
                
                # Log de sucesso
                logger.info(f"Login bem-sucedido: {usuario['email']} (ID: {usuario['id']})")
                
                # Feedback visual e redirecionamento
                st.success(f"Bem-vindo(a), {usuario['nome']}!")
                time.sleep(1)
                st.switch_page("pages/01_🏠_dashboard.py")
            else:
                st.error("E-mail ou senha inválidos. Tente novamente.")
                logger.warning(f"Tentativa de login falhou para o e-mail: {email}")
    
    # Rodapé
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666; font-size: 0.9em;'>"
        "Sistema PDV © 2025 - Todos os direitos reservados"
        "</div>",
        unsafe_allow_html=True
    )
    
    # Estilos CSS personalizados
    st.markdown("""
        <style>
            /* Estilo para o formulário de login */
            .stForm {
                background-color: #f8f9fa;
                padding: 2rem;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            
            /* Estilo para os campos de entrada */
            .stTextInput>div>div>input {
                border-radius: 5px;
                border: 1px solid #ced4da;
                padding: 10px;
            }
            
            /* Estilo para o botão de login */
            .stButton>button {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 5px;
                padding: 0.5rem 1rem;
                cursor: pointer;
                transition: background-color 0.3s;
            }
            
            .stButton>button:hover {
                background-color: #45a049;
            }
            
            /* Estilo para o título */
            h1 {
                color: #2c3e50;
                text-align: center;
                margin-bottom: 1.5rem;
            }
            
            /* Estilo para a mensagem de erro */
            .stAlert {
                border-radius: 5px;
            }
        </style>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    login_page()
