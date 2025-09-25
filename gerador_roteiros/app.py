import os
os.environ["STREAMLIT_SERVER_ADDRESS"] = "0.0.0.0"
os.environ["STREAMLIT_SERVER_PORT"] = "8501"

import streamlit as st
from datetime import date
from typing import Optional, Dict, Any
import json
from loguru import logger
import re

# Configuração da página para remover menu e rodapé
st.set_page_config(
    page_title="Gerador de Roteiros de Viagem",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para ajustar o layout
hide_streamlit_style = """
    <style>
        /* Remove menu padrão do Streamlit */
        #MainMenu {visibility: hidden;}
        
        /* Remove o rodapé */
        footer {visibility: hidden;}
        
        /* Ajusta o cabeçalho */
        header {visibility: visible; height: auto !important; padding: 1rem 1rem 0.5rem !important;}
        
        /* Remove o botão de deploy */
        .stDeployButton {display: none;}
        
        /* Ajusta o espaçamento do conteúdo principal */
        .stApp {
            margin-top: 0px;
            padding-top: 1rem;
        }
        
        /* Ajusta o padding da seção principal */
        .main .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }
        
        /* Ajusta o título da página */
        .stApp h1 {
            margin-top: 0.5rem;
            margin-bottom: 1.5rem;
        }
        
        /* Remove o menu lateral */
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Mistral SDK
try:
    from mistralai import Mistral
except ImportError:
    Mistral = None

# Gemini SDK
try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig
except ImportError:
    genai = None

from utils.prompts import SYSTEM_PROMPT_VIAGEM, format_user_prompt_viagem

# Configure loguru
logger.add("logs/app.log", rotation="1 day", retention="7 days", level="INFO")
logger.add("logs/error.log", rotation="1 day", retention="30 days", level="ERROR")

# Custom CSS (forced dark theme)
st.markdown("""
<style>
    /* Cores do tema */
    :root {
        --bg: #0b0f14;
        --text: #e5e7eb;
        --muted: #9ca3af;
        --card-bg: #111827;
        --section-bg: rgba(255,255,255,0.04);
        --border: #1f2937;
        --primary: #667eea;
        --secondary: #764ba2;
        --sidebar-bg: #0f172a;
        --sidebar-text: #e2e8f0;
        --sidebar-hover: #1e293b;
        --sidebar-border: #334155;
    }
    
    /* Estilos do Menu Lateral */
    .sidebar .sidebar-content {
        background: var(--sidebar-bg) !important;
        border-right: 1px solid var(--sidebar-border) !important;
    }
    
    .sidebar .stMarkdown h3 {
        color: var(--sidebar-text) !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        margin: 1.5rem 0 0.75rem 0 !important;
        padding: 0 1rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }
    
    .sidebar .stTextInput>div>div>input {
        background: #1e293b !important;
        border: 1px solid var(--sidebar-border) !important;
        color: var(--sidebar-text) !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    .sidebar .stTextInput>div>div>input:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
    }
    
    .sidebar .stMarkdown p {
        color: var(--muted) !important;
        font-size: 0.9rem !important;
        padding: 0 1rem !important;
    }
    
    .sidebar .stButton>button {
        width: 100% !important;
        margin: 0.5rem 0 !important;
        background: linear-gradient(90deg, var(--primary) 0%, var(--secondary) 100%) !important;
        border: none !important;
    }
    
    .sidebar .stButton>button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
    }
    body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
    #MainMenu, footer, header, .stDeployButton, div[data-testid="stDecoration"], div[data-testid="stToolbar"] { display: none; }
    .nav-container {
        background: linear-gradient(90deg, var(--primary) 0%, var(--secondary) 100%);
        padding: 1rem 1.5rem;
        margin-bottom: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease;
    }
    .nav-container:hover { transform: translateY(-2px); }
    .nav-title { color: white; font-size: 1.8rem; font-weight: 700; text-align: center; margin: 0; }
    .nav-subtitle { color: rgba(255, 255, 255, 0.9); font-size: 1rem; text-align: center; margin-top: 0.5rem; }
    .main-container { max-width: 1200px; margin: 0 auto; padding: 0 1.5rem; }
    .quick-settings {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1.5rem;
        display: flex;
        gap: 1.5rem;
        flex-wrap: wrap;
        align-items: center;
    }
    .quick-settings label { color: var(--muted); font-size: 0.95rem; font-weight: 500; }
    .card {
        background: var(--card-bg);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        border: 1px solid var(--border);
        transition: transform 0.3s ease;
    }
    .card:hover { transform: translateY(-2px); }
    .card-header { border-bottom: 1px solid var(--border); padding-bottom: 1rem; margin-bottom: 1.5rem; }
    .card-title { color: var(--text); font-size: 1.5rem; font-weight: 600; margin: 0; }
    .card-subtitle { color: var(--muted); font-size: 1rem; margin-top: 0.5rem; }
    .form-section {
        background: var(--section-bg);
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        border: 1px solid var(--border);
    }
    .section-title { color: var(--text); font-size: 1.2rem; font-weight: 600; margin-bottom: 1rem; display: flex; align-items: center; }
    .section-icon { margin-right: 0.75rem; font-size: 1.3rem; }
    .stButton > button {
        background: linear-gradient(90deg, var(--primary) 0%, var(--secondary) 100%);
        color: white;
        border: none;
        border-radius: 24px;
        padding: 0.75rem 2rem;
        font-size: 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 3px 6px rgba(0, 0, 0, 0.1);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }
    .success-box, .warning-box, .error-box {
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
        color: var(--text);
    }
    .success-box { background: rgba(40, 167, 69, 0.12); border: 1px solid rgba(40, 167, 69, 0.35); }
    .warning-box { background: rgba(255, 193, 7, 0.12); border: 1px solid rgba(255, 193, 7, 0.35); }
    .error-box { background: rgba(220, 53, 69, 0.12); border: 1px solid rgba(220, 53, 69, 0.35); }
    .stTextInput > div > div > input[type="password"] {
        background: var(--section-bg);
        color: var(--text);
        border: 1px solid var(--border);
        border-radius: 8px;
    }
    @media (max-width: 768px) {
        .main-container { padding: 0 1rem; }
        .nav-title { font-size: 1.5rem; }
        .card { padding: 1rem; }
        .stButton > button { padding: 0.75rem 1.5rem; }
    }
</style>
""", unsafe_allow_html=True)

def _strip_code_fences(text: str) -> str:
    """Remove code fences if present (fallback, less needed with JSON mode)."""
    if not text:
        return text
    t = text.strip()
    fence_start = re.compile(r"^```[a-zA-Z0-9_-]*\s*")
    fence_end = re.compile(r"```\s*$")
    t = fence_start.sub("", t)
    t = fence_end.sub("", t)
    return t.strip()

def _parse_json_response(text: str) -> Optional[Dict[Any, Any]]:
    """Parse JSON response, with fallback for malformed responses."""
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao parsear JSON: {e}")
        cleaned = _strip_code_fences(text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Usando estrutura de fallback devido a erro de parsing")
            return {
                "titulo": "Roteiro de Viagem",
                "subtitulo": "Roteiro personalizado gerado",
                "visao_geral": {
                    "destino": "Destino não especificado",
                    "duracao": 1,
                    "estilo": "Personalizado",
                    "clima_esperado": "Verifique as condições locais",
                    "hospedagem_sugerida": "Consulte sites de hospedagem"
                },
                "cronograma": [{
                    "dia": 1,
                    "titulo": "Dia de Exploração",
                    "atividades": [{
                        "horario": "Manhã",
                        "atividade": cleaned[:200] + "..." if len(cleaned) > 200 else cleaned,
                        "dica": ""
                    }]
                }],
                "gastronomia": {
                    "pratos_indispensaveis": ["Experimente a culinária local"],
                    "restaurante_tesouro": "Consulte recomendações locais",
                    "experiencia_culinaria": "Explore mercados e restaurantes locais"
                },
                "vida_noturna": {
                    "bares_recomendados": ["Explore bares locais e pubs tradicionais"],
                    "clubes_festas": ["Consulte eventos locais e festas da região"],
                    "shows_eventos": ["Verifique agenda de shows e eventos noturnos"],
                    "roteiro_bar_hopping": "Explore a vida noturna local",
                    "dicas_noturnas": "Mantenha-se seguro e respeite os horários locais"
                },
                "dicas_viagem": {
                    "mobilidade": "Use transporte público ou aplicativos de carona",
                    "comunicacao": "Aprenda frases básicas do idioma local",
                    "alerta_especialista": "Mantenha-se seguro e hidratado"
                }
            }

def get_api_key(provider: str) -> Optional[str]:
    """
    Solicita ao usuário a chave de API do provedor especificado.
    
    Args:
        provider: Nome do provedor (Mistral ou Gemini)
        
    Returns:
        str: A chave de API fornecida pelo usuário ou None se cancelado
    """
    try:
        key_name = f"{provider.upper()}_API_KEY"
        
        # Se já tiver na sessão, retorna
        if key_name in st.session_state and st.session_state.get(key_name):
            return st.session_state[key_name]
            
        # Se não tiver, pede ao usuário
        with st.sidebar.expander(f"🔑 Configurar Chave {provider}", expanded=True):
            st.info(f"Por favor, insira sua chave de API do {provider} para continuar.")
            api_key = st.text_input(
                f"Chave API {provider}",
                type="password",
                help=f"Sua chave de API do {provider}",
                key=f"{key_name}_input"
            )
            
            if st.button(f"Salvar Chave {provider}"):
                if api_key and len(api_key) > 10:  # Verificação básica
                    st.session_state[key_name] = api_key
                    st.success(f"Chave {provider} configurada com sucesso!")
                    st.rerun()
                else:
                    st.error("Por favor, insira uma chave de API válida.")
            
            st.markdown(f"""
            <div style="margin-top: 1rem; padding: 0.5rem; background: var(--section-bg); border-radius: 0.5rem;">
                <small>Não tem uma chave? Obtenha em:</small><br>
                <a href="https://console.mistral.ai/" target="_blank" style="color: var(--primary);">Mistral AI</a> | 
                <a href="https://ai.google.dev/" target="_blank" style="color: var(--primary);">Google Gemini</a>
            </div>
            """, unsafe_allow_html=True)
            
        return st.session_state.get(key_name) if api_key else None
        
    except Exception as e:
        logger.error(f"Erro ao obter chave {provider}")
        return None

def _call_mistral(user_prompt: str) -> Optional[str]:
    """
    Chama a API do Mistral de forma segura.
    
    Args:
        user_prompt: O prompt do usuário a ser enviado para a API
        
    Returns:
        str: A resposta da API ou None em caso de erro
    """
    logger.info("Iniciando chamada para API Mistral")
    
    if Mistral is None:
        logger.error("SDK Mistral não está disponível")
        return None
        
    api_key = get_api_key("MISTRAL")
    if not api_key:
        logger.error("Não foi possível obter a chave da API Mistral")
        return None
        
    try:
        # Cria o cliente com a chave de API
        client = Mistral(api_key=api_key)
        
        # Faz a chamada para a API
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_VIAGEM},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        # Processa a resposta
        if response and hasattr(response, 'choices') and response.choices:
            content = response.choices[0].message.content
            logger.info(f"Resposta Mistral recebida com {len(content)} caracteres")
            return content
            
        logger.warning("Resposta vazia ou inválida da API Mistral")
        return None
        
    except Exception as e:
        # Log do erro sem expor detalhes sensíveis
        error_msg = str(e)
        if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            logger.error("Erro de autenticação na API Mistral")
        else:
            logger.error(f"Erro ao chamar API Mistral: {error_msg[:100]}...")
        return None

def _call_gemini(user_prompt: str, model_name: str = "gemini-1.5-flash") -> Optional[str]:
    """
    Chama a API do Gemini de forma segura.
    
    Args:
        user_prompt: O prompt do usuário a ser enviado para a API
        model_name: Nome do modelo a ser usado (padrão: gemini-1.5-flash)
        
    Returns:
        str: A resposta da API ou None em caso de erro
    """
    logger.info(f"Iniciando chamada para API Gemini com modelo {model_name}")
    
    if genai is None:
        logger.error("Módulo genai não está disponível")
        return None
        
    api_key = get_api_key("GEMINI")
    if not api_key:
        logger.error("Não foi possível obter a chave da API Gemini")
        return None
        
    try:
        # Configura a chave da API
        genai.configure(api_key=api_key)
        
        # Cria o modelo e faz a chamada
        model = genai.GenerativeModel(model_name)
        
        # Prepara o prompt com instruções claras
        full_prompt = (
            f"{SYSTEM_PROMPT_VIAGEM}\n\n{user_prompt}\n\n"
            "IMPORTANTE: Responda APENAS com um JSON válido, sem markdown ou texto adicional."
        )
        
        # Faz a chamada para a API
        response = model.generate_content(
            full_prompt,
            generation_config=GenerationConfig(
                response_mime_type="application/json",
                temperature=0.3,
                top_p=0.95,
                top_k=40
            )
        )
        
        # Processa a resposta
        if response and hasattr(response, 'text') and response.text:
            text = response.text
            logger.info(f"Resposta Gemini recebida com {len(text)} caracteres")
            return text
            
        logger.warning("Resposta vazia ou inválida da API Gemini")
        return None
        
    except Exception as e:
        # Log do erro sem expor detalhes sensíveis
        error_msg = str(e)
        if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            logger.error("Erro de autenticação na API Gemini")
        else:
            logger.error(f"Erro ao chamar API Gemini: {error_msg[:100]}...")
        return None

def _offline_fallback(user_prompt: str) -> str:
    """Offline template if APIs fail."""
    logger.warning("Usando gerador offline (fallback)")
    return json.dumps({
        "titulo": "Roteiro Base (Offline)",
        "subtitulo": "Roteiro gerado offline",
        "visao_geral": {
            "destino": "Destino genérico",
            "duracao": 1,
            "estilo": "Exploração básica",
            "clima_esperado": "Verifique localmente",
            "hospedagem_sugerida": "Consulte opções locais"
        },
        "cronograma": [{
            "dia": 1,
            "titulo": "Dia de Exploração",
            "atividades": [
                {"horario": "Manhã", "atividade": "Passeio pela região central", "dica": "Leve calçados confortáveis"},
                {"horario": "Tarde", "atividade": "Visita a um museu ou mercado local", "dica": "Confira horários"},
                {"horario": "Noite", "atividade": "Jantar típico e caminhada", "dica": "Reserve com antecedência"}
            ]
        }],
        "gastronomia": {
            "pratos_indispensaveis": ["Prato local típico"],
            "restaurante_tesouro": "Restaurante local recomendado",
            "experiencia_culinaria": "Explore mercados locais"
        },
        "vida_noturna": {
            "bares_recomendados": ["Bar central da cidade"],
            "clubes_festas": ["Verifique eventos locais"],
            "shows_eventos": ["Consulte agenda local"],
            "roteiro_bar_hopping": "Caminhe por bares no centro",
            "dicas_noturnas": "Mantenha-se seguro"
        },
        "dicas_viagem": {
            "mobilidade": "Use transporte público",
            "comunicacao": "Aprenda saudações básicas",
            "alerta_especialista": "Hidrate-se e use protetor solar"
        }
    })

def _navigate_to_results(json_data: Dict[Any, Any], provider_used: str) -> None:
    st.session_state["roteiro_json"] = json_data
    st.session_state["provider_used"] = provider_used
    st.switch_page("pages/01_Roteiro.py")

def run_app() -> None:
    # Configuração da página já foi movida para o topo do arquivo
    
    # Cabeçalho moderno e atraente
    st.markdown("""
    <style>
        @keyframes gradientBG {
            0% {background-position: 0% 50%;}
            50% {background-position: 100% 50%;}
            100% {background-position: 0% 50%;}
        }
        .modern-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #4f46e5 100%);
            background-size: 200% 200%;
            padding: 1.5rem 2rem;
            margin: -1rem -1rem 2rem -1rem;
            border-radius: 0 0 20px 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
            animation: gradientBG 10s ease infinite;
            position: relative;
            overflow: hidden;
        }
        .modern-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #4f46e5, #8b5cf6, #ec4899);
        }
        .modern-header h1 {
            color: white;
            font-size: 2rem;
            font-weight: 800;
            margin: 0 0 0.5rem 0;
            text-align: center;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            letter-spacing: 0.5px;
        }
        .modern-header p {
            color: rgba(255, 255, 255, 0.95);
            font-size: 1.05rem;
            text-align: center;
            margin: 0;
            font-weight: 400;
            max-width: 700px;
            margin: 0 auto;
            line-height: 1.5;
        }
        .emoji {
            font-size: 1.2em;
            display: inline-block;
            animation: float 3s ease-in-out infinite;
        }
        @keyframes float {
            0% { transform: translateY(0px); }
            50% { transform: translateY(-5px); }
            100% { transform: translateY(0px); }
        }
    </style>
    
    <div class="modern-header">
        <h1><span class="emoji">🗺️</span> Planejador de Viagens IA</h1>
        <p>Gere roteiros personalizados com inteligência artificial para sua próxima aventura</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Main container
    st.markdown('<div class="main-container">', unsafe_allow_html=True)

    # Quick settings
    colA, colB = st.columns([2, 3])
    with colA:
        provider = st.radio("Modelo preferido", ["Mistral", "Gemini"], horizontal=True, index=0)
    with colB:
        gemini_model = st.radio("Modelo do Gemini", ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.5-flash"], index=0)

    # Sidebar - Menu Lateral
    with st.sidebar:
        # Cabeçalho
        st.markdown("""
        <div style="padding: 1rem; border-bottom: 1px solid var(--sidebar-border); margin-bottom: 1.5rem;">
            <h2 style="color: var(--primary); margin: 0;">🔑 Configurações</h2>
            <p style="color: var(--muted); margin: 0.25rem 0 0 0; font-size: 0.9rem;">Gerencie suas chaves de API</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Botão para limpar chaves
        if st.button("🗑️ Limpar chaves da sessão", 
                    help="Remove as chaves da sessão atual",
                    use_container_width=True,
                    type="secondary"):
            if "MISTRAL_API_KEY" in st.session_state:
                del st.session_state["MISTRAL_API_KEY"]
            if "GEMINI_API_KEY" in st.session_state:
                del st.session_state["GEMINI_API_KEY"]
            st.rerun()
            
        st.markdown("---")
        
        # Seção de Ajuda
        with st.expander("❓ Como obter as chaves", expanded=False):
            st.markdown("""
            <div style="padding: 0.5rem 0;">
                <div style="margin-bottom: 1rem;">
                    <strong>Mistral AI</strong><br>
                    <a href="https://console.mistral.ai" target="_blank" style="color: var(--primary);">Obter chave API</a>
                </div>
                <div>
                    <strong>Google Gemini</strong><br>
                    <a href="https://makersuite.google.com" target="_blank" style="color: var(--primary);">Obter chave API</a>
                </div>
                <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border); color: var(--muted); font-size: 0.8rem;">
                    As chaves são salvas apenas nesta sessão do navegador.
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Seção de Chaves
        st.markdown("### 🔐 Configuração de API")
        
        with st.expander("🔑 Configurar Chaves de API", expanded=False):
            st.info("As chaves são armazenadas apenas na sua sessão e serão perdidas ao atualizar a página.")
            
            # Chave Mistral
            mistral_key = st.text_input(
                "Chave API Mistral",
                type="password",
                help="Formato: mst-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                key="mistral_key_input"
            )
            if mistral_key:
                st.session_state["MISTRAL_API_KEY"] = mistral_key
                st.success("Chave Mistral configurada com sucesso!")
            
            # Chave Gemini
            gemini_key = st.text_input(
                "Chave API Gemini (Opcional)",
                type="password",
                help="Sua chave da API Google Gemini",
                key="gemini_key_input"
            )
            if gemini_key:
                st.session_state["GEMINI_API_KEY"] = gemini_key
                st.success("Chave Gemini configurada com sucesso!")
        
        # Status das APIs
        st.markdown("### 📊 Status do Sistema")
        
        # Status Mistral
        mistral_status = get_api_key("MISTRAL")
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <div style="width: 12px; height: 12px; border-radius: 50%; background: {'#4ade80' if mistral_status else '#f87171'};"></div>
                <span>Mistral</span>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            if Mistral is None:
                st.caption("🔧 SDK não instalado", help="Instale com: pip install mistralai")
            elif not mistral_status:
                st.caption("⏳ Aguardando chave")
            else:
                st.caption("✅ Conectado")
        
        # Status Gemini
        gemini_status = get_api_key("GEMINI")
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <div style="width: 12px; height: 12px; border-radius: 50%; background: {'#4ade80' if gemini_status else '#f87171'};"></div>
                <span>Gemini</span>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            if genai is None:
                st.caption("🔧 SDK não instalado", help="Instale com: pip install google-generativeai")
            elif not gemini_status:
                st.caption("⏳ Aguardando chave")
            else:
                st.caption("✅ Conectado")
        
        # Rodapé
        st.markdown("""
        <div style="margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--border); color: var(--muted); font-size: 0.8rem;">
            <p>Dúvidas? Consulte a documentação ou entre em contato com o suporte.</p>
        </div>
        """, unsafe_allow_html=True)

    # Main form card
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <h2 class="card-title">✈️ Seu Perfil de Viagem</h2>
            <p class="card-subtitle">Preencha os detalhes para um roteiro personalizado</p>
        </div>
    """, unsafe_allow_html=True)
    
    with st.form("form_viagem"):
        # Basic info
        st.markdown('<div class="form-section"><h3 class="section-title"><span class="section-icon">📍</span>Informações Básicas</h3>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            destino = st.text_input("Destino principal", placeholder="Ex.: Roma, Itália", help="Cidade ou país de destino")
        with col2:
            tipo_data = st.radio("Tipo de data", 
                ["Data específica (dia/mês/ano)", "Mês e ano", "Melhor período (IA escolhe)"], 
                help="Escolha como especificar o período")
        with col3:
            duracao = st.number_input("Duração (dias)", min_value=1, max_value=60, value=7, step=1, help="Quantos dias de viagem")
        
        # Date handling
        if tipo_data == "Data específica (dia/mês/ano)":
            st.markdown("**📅 Data de Início:**")
            data_inicio = st.date_input("Selecione a data exata", value=date.today(), help="Data exata da viagem", label_visibility="collapsed")
            data_flexivel = False
            periodo_especifico = f"Data específica: {data_inicio.strftime('%d/%m/%Y')}"
        elif tipo_data == "Mês e ano":
            st.markdown("**📅 Mês e Ano:**")
            col_mes, col_ano = st.columns(2)
            with col_mes:
                mes = st.radio("Mês", 
                    ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                     "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"],
                    index=date.today().month - 1)
            with col_ano:
                ano = st.radio("Ano", 
                    [date.today().year, date.today().year + 1, date.today().year + 2],
                    index=0)
            mes_num = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                       "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"].index(mes) + 1
            data_inicio = date(ano, mes_num, 1)
            data_flexivel = True
            periodo_especifico = f"Mês e ano: {mes} de {ano}"
        else:
            st.markdown("**🤖 IA Escolherá o Melhor Período**")
            st.info("A IA analisará o destino e escolherá as melhores datas considerando clima, eventos e temporadas.")
            data_inicio = None
            data_flexivel = True
            periodo_especifico = "Melhor período para o destino (IA escolherá)"
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Traveler profile
        st.markdown('<div class="form-section"><h3 class="section-title"><span class="section-icon">👥</span>Perfil dos Viajantes</h3>', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            perfil = st.radio("Tipo de viagem", ["Casal", "Família", "Solo", "Grupo de amigos", "Negócios"])
        with col2:
            num_viajantes = st.number_input("Número de viajantes", min_value=1, max_value=20, value=2)
        with col3:
            faixa_etaria = st.radio("Faixa etária", ["18-25", "26-35", "36-50", "51+"])
        with col4:
            criancas = st.toggle("Leva crianças?")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Preferences
        st.markdown('<div class="form-section"><h3 class="section-title"><span class="section-icon">🎯</span>Preferências de Viagem</h3>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            orcamento = st.radio("Orçamento", ["Econômico", "Intermediário", "Luxo"])
            ritmo = st.radio("Ritmo da viagem", ["Relaxado", "Moderado", "Intenso"])
            hospedagem = st.radio("Hospedagem", ["Hostel", "Hotel 3*", "Hotel 4*", "Hotel 5*", "Apartamento"])
        with col2:
            interesses = st.multiselect("Interesses", ["Gastronomia", "História", "Natureza", "Arte e museus", "Vida noturna", "Compras", "Aventura", "Tecnologia"], help="Selecione pelo menos um")
            nivel_caminhada = st.radio("Nível de caminhada", ["Muito baixo", "Baixo", "Médio", "Alto"])
            clima_desejado = st.radio("Clima desejado", ["Ameno", "Frio", "Quente"])
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Additional details
        st.markdown('<div class="form-section"><h3 class="section-title"><span class="section-icon">📝</span>Detalhes Adicionais</h3>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            restricoes_alimentares = st.text_input("Restrições alimentares", placeholder="Ex.: vegetariano, sem lactose")
            horarios_preferidos = st.text_input("Horários preferidos", placeholder="Ex.: acorda tarde, jantar cedo")
            aversoes = st.text_input("Aversões (evitar)", placeholder="Ex.: filas longas, locais muito turísticos")
        with col2:
            datas_flexiveis = st.radio("Datas flexíveis?", ["Não", "Sim"])
            cidades_proximas = st.text_input("Cidades próximas de interesse", placeholder="Ex.: Nápoles, Florença")
        
        observacoes = st.text_area("Observações e pedidos especiais", placeholder="Restrições, mobilidade, locais dos sonhos", height=100)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Submit button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button("✨ Gerar Roteiro Personalizado", use_container_width=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

    if submitted:
        if not destino or not interesses:
            st.markdown('<div class="warning-box">⚠️ Preencha o destino principal e selecione pelo menos um interesse.</div>', unsafe_allow_html=True)
            return

        if provider == "Mistral" and not get_api_key("MISTRAL"):
            st.markdown('<div class="error-box">❌ Forneça a chave API Mistral manualmente ou em secrets.toml.</div>', unsafe_allow_html=True)
            return
        if provider == "Gemini" and not get_api_key("GEMINI"):
            st.markdown('<div class="error-box">❌ Forneça a chave API Gemini manualmente ou em secrets.toml.</div>', unsafe_allow_html=True)
            return

        logger.info(f"Iniciando geração de roteiro para destino: {destino}")
        user_data = {
            "destino": destino.strip(),
            "data_inicio": data_inicio,
            "duracao": int(duracao),
            "perfil": perfil,
            "orcamento": orcamento,
            "interesses": interesses,
            "ritmo": ritmo,
            "observacoes": (observacoes or "").strip() or "Sem observações.",
            "num_viajantes": int(num_viajantes),
            "criancas": bool(criancas),
            "faixa_etaria": faixa_etaria,
            "hospedagem": hospedagem,
            "restricoes_alimentares": restricoes_alimentares or "Nenhuma",
            "nivel_caminhada": nivel_caminhada,
            "horarios_preferidos": horarios_preferidos or "Flexível",
            "aversoes": aversoes or "Nenhuma",
            "clima_desejado": clima_desejado,
            "datas_flexiveis": datas_flexiveis,
            "cidades_proximas": cidades_proximas or "",
            "tipo_data": tipo_data,
            "data_flexivel": data_flexivel,
            "periodo_especifico": periodo_especifico,
        }

        logger.info(f"Dados do usuário coletados: {user_data}")
        user_prompt = format_user_prompt_viagem(user_data)

        resultado: Optional[str] = None
        provider_used = None
        progress_bar = st.progress(0)

        providers_order = [provider, "Gemini" if provider == "Mistral" else "Mistral"]
        for i, prov in enumerate(providers_order):
            if prov == "Mistral" and not get_api_key("MISTRAL"):
                continue
            if prov == "Gemini" and not get_api_key("GEMINI"):
                continue
            progress_bar.progress((i + 1) / len(providers_order))
            with st.spinner(f"🤖 Consultando {prov}..."):
                try:
                    if prov == "Mistral":
                        resultado = _call_mistral(user_prompt)
                    else:
                        resultado = _call_gemini(user_prompt, model_name=gemini_model)
                    provider_used = prov if resultado else provider_used
                except Exception as e:
                    logger.error(f"Erro ao consultar {prov}: {e}")
                    resultado = resultado or None
            if resultado:
                break

        progress_bar.empty()
        if not resultado:
            resultado = _offline_fallback(user_prompt)
            provider_used = "Offline"

        if resultado:
            json_data = _parse_json_response(resultado)
            if json_data:
                logger.success(f"Roteiro gerado com sucesso usando {provider_used}")
                st.markdown(f'<div class="success-box">✅ Roteiro gerado com sucesso usando {provider_used}!</div>', unsafe_allow_html=True)
                _navigate_to_results(json_data, provider_used)
            else:
                logger.error("Falha ao processar resposta JSON")
                st.markdown('<div class="error-box">❌ Erro ao processar resposta da IA. Verifique sua chave API e tente novamente.</div>', unsafe_allow_html=True)
        else:
            logger.error("Falha total: não foi possível gerar o roteiro")
            st.markdown('<div class="error-box">❌ Não foi possível gerar o roteiro. Verifique suas configurações e chaves API.</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    run_app()