"""
Componente de barra lateral (sidebar) para o sistema PDV.
"""
import streamlit as st
from typing import Dict, Any, Optional
from datetime import datetime
import os

# Importa funções auxiliares
from utils.helpers import format_date
from utils.logger import logger

def render_sidebar(user: Optional[Dict[str, Any]] = None) -> None:
    """
    Renderiza a barra lateral do sistema com o menu de navegação.
    
    Args:
        user: Dicionário com os dados do usuário logado (opcional)
    """
    # Configurações da barra lateral
    st.sidebar.title("📊 Menu Principal")
    
    # Exibe informações do usuário se estiver logado
    if user:
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"👤 **{user.get('nome', 'Usuário')}**")
        st.sidebar.markdown(f"🔑 {user.get('role', 'N/A').capitalize()}")
        
        # Último acesso
        ultimo_acesso = user.get('ultimo_acesso')
        if ultimo_acesso:
            if isinstance(ultimo_acesso, str):
                try:
                    ultimo_acesso = datetime.fromisoformat(ultimo_acesso)
                except (ValueError, TypeError):
                    ultimo_acesso = None
            
            if ultimo_acesso:
                st.sidebar.markdown(f"🕒 Último acesso: {format_date(ultimo_acesso, '%d/%m/%Y %H:%M')}")
    
    # Menu de navegação
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Navegação")
    
    # Páginas disponíveis para todos os usuários
    menu_items = [
        {"label": "🏠 Dashboard", "page": "01_🏠_dashboard.py", "roles": ["admin", "vendedor"]},
        {"label": "🛒 PDV", "page": "02_🛒_pdv.py", "roles": ["admin", "vendedor"]},
        {"label": "📦 Estoque", "page": "03_📦_estoque.py", "roles": ["admin", "vendedor"]},
        {"label": "📊 Relatórios", "page": "04_📊_relatorios.py", "roles": ["admin", "vendedor"]},
        {"label": "👥 Clientes", "page": "05_👥_clientes.py", "roles": ["admin"]},
        {"label": "👤 Usuários", "page": "06_👤_usuarios.py", "roles": ["admin"]},
        {"label": "⚙️ Configurações", "page": "07_⚙️_configuracoes.py", "roles": ["admin"]},
    ]
    
    # Filtra os itens do menu com base nas permissões do usuário
    user_role = user.get("role", "").lower() if user else ""
    
    for item in menu_items:
        if not user_role or user_role in item["roles"]:
            # Cria um link de navegação para cada item do menu
            st.sidebar.page_link(
                f"pages/{item['page']}",
                label=item["label"],
                disabled=not user  # Desativa os links se não houver usuário logado
            )
    
    # Seção de informações do sistema
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Sistema")
    
    # Exibe a versão do sistema (pode ser carregada de um arquivo de configuração)
    st.sidebar.markdown(f"ℹ️ **Versão:** 1.0.0")
    
    # Data e hora atual
    st.sidebar.markdown(f"📅 **{format_date(datetime.now(), '%d/%m/%Y %H:%M')}**")
    
    # Botão de logout
    if user:
        st.sidebar.markdown("---")
        if st.sidebar.button("🚪 Sair", use_container_width=True):
            # Remove os dados da sessão
            st.session_state.clear()
            
            # Redireciona para a página de login
            st.rerun()
            
            # Registra o logout
            logger.info(f"Usuário {user.get('email', 'desconhecido')} fez logout")
    else:
        # Botão de login se não estiver logado
        st.sidebar.markdown("---")
        if st.sidebar.button("🔑 Fazer Login", use_container_width=True):
            st.switch_page("pages/00_🔐_login.py")
    
    # Estilos CSS personalizados para a barra lateral
    st.markdown("""
        <style>
            /* Estilo para a barra lateral */
            [data-testid="stSidebar"] {
                background-color: #f8f9fa;
                padding: 1rem;
            }
            
            /* Estilo para os itens do menu */
            .stSidebarNav {
                margin-top: 1rem;
            }
            
            /* Estilo para os botões */
            .stButton>button {
                width: 100%;
                border-radius: 5px;
                font-weight: 500;
                transition: all 0.3s ease;
            }
            
            .stButton>button:hover {
                transform: translateY(-2px);
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            
            /* Estilo para o rodapé */
            .sidebar-footer {
                font-size: 0.8rem;
                color: #6c757d;
                text-align: center;
                margin-top: 2rem;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Rodapé da barra lateral
    st.sidebar.markdown("""
        <div class="sidebar-footer">
            <hr>
            <p>PDV System © 2025</p>
            <p>Todos os direitos reservados</p>
        </div>
    """, unsafe_allow_html=True)

# Teste do componente
if __name__ == "__main__":
    # Exemplo de uso
    st.title("Teste da Barra Lateral")
    
    # Simula um usuário logado
    user_data = {
        "id": 1,
        "nome": "Admin",
        "email": "admin@loja.com",
        "role": "admin",
        "ultimo_acesso": datetime.now().isoformat()
    }
    
    # Renderiza a barra lateral
    render_sidebar(user_data)
    
    # Conteúdo principal
    st.write("Conteúdo principal da página")
    st.write("A barra lateral está à esquerda com o menu de navegação.")
    
    # Instruções
    with st.expander("Instruções"):
        st.markdown("""
        ## Teste da Barra Lateral
        
        Este é um teste do componente de barra lateral do sistema PDV.
        
        ### Funcionalidades:
        - Exibe o menu de navegação com base nas permissões do usuário
        - Mostra informações do usuário logado
        - Inclui botão de logout
        - Layout responsivo
        
        ### Como usar:
        1. Passe um dicionário com os dados do usuário para a função `render_sidebar()`
        2. A função irá renderizar a barra lateral automaticamente
        3. Os itens do menu serão filtrados com base no papel (role) do usuário
        """)
