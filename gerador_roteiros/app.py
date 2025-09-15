# Improved app.py
import streamlit as st
from datetime import date
from typing import Optional, Dict, Any
import requests
import re
import json
from loguru import logger

from utils.prompts import SYSTEM_PROMPT_VIAGEM, format_user_prompt_viagem

# Configure loguru
logger.add("logs/app.log", rotation="1 day", retention="7 days", level="INFO")
logger.add("logs/error.log", rotation="1 day", retention="30 days", level="ERROR")

# Custom CSS for modern design with dark-mode support
st.markdown("""
<style>
    :root {
        --bg: #f6f7f9;
        --text: #1f2937;
        --muted: #6b7280;
        --card-bg: #ffffff;
        --section-bg: #f3f4f6;
        --border: #e5e7eb;
    }
    @media (prefers-color-scheme: dark) {
        :root {
            --bg: #0b0f14;
            --text: #e5e7eb;
            --muted: #9ca3af;
            --card-bg: #111827;
            --section-bg: rgba(255,255,255,0.04);
            --border: #1f2937;
        }
        body { color: var(--text); }
    }

    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    div[data-testid="stDecoration"] {display:none;}
    div[data-testid="stToolbar"] {display:none;}
    
    /* Custom navigation */
    .nav-container {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 0.75rem 1.25rem;
        margin-bottom: 1.25rem;
        border-radius: 10px;
        box-shadow: 0 3px 5px rgba(0, 0, 0, 0.08);
    }
    
    .nav-title {
        color: white;
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0;
        text-align: center;
    }
    
    .nav-subtitle {
        color: rgba(255, 255, 255, 0.85);
        font-size: 0.95rem;
        text-align: center;
        margin-top: 0.35rem;
    }
    
    /* Main container */
    .main-container {
        max-width: 1100px;
        margin: 0 auto;
        padding: 0 1rem;
    }
    
    /* Quick settings bar */
    .quick-settings {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 0.75rem 1rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        flex-wrap: wrap;
    }
    .quick-settings label { color: var(--muted); font-size: 0.95rem; }
    
    /* Cards */
    .card {
        background: var(--card-bg);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 3px 6px rgba(0, 0, 0, 0.08);
        border: 1px solid var(--border);
    }
    
    .card-header {
        border-bottom: 1px solid var(--border);
        padding-bottom: 0.75rem;
        margin-bottom: 1rem;
    }
    
    .card-title {
        color: var(--text);
        font-size: 1.25rem;
        font-weight: 600;
        margin: 0;
    }
    
    .card-subtitle {
        color: var(--muted);
        font-size: 0.95rem;
        margin-top: 0.35rem;
    }
    
    /* Form styling */
    .form-section {
        background: var(--section-bg);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        border: 1px solid var(--border);
    }
    
    .section-title {
        color: var(--text);
        font-size: 1.05rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
    }
    
    .section-icon {
        margin-right: 0.5rem;
        font-size: 1.2rem;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 22px;
        padding: 0.6rem 1.5rem;
        font-size: 1rem;
        font-weight: 600;
        transition: all 0.25s ease;
        box-shadow: 0 3px 6px rgba(0, 0, 0, 0.1);
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 5px 10px rgba(0, 0, 0, 0.15);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    @media (prefers-color-scheme: dark) {
        .css-1d391kg { background: linear-gradient(180deg, #0b0f14 0%, #0e141b 100%); }
    }
    
    /* Status messages */
    .success-box {
        background: rgba(40, 167, 69, 0.12);
        border: 1px solid rgba(40, 167, 69, 0.35);
        border-radius: 10px;
        padding: 0.85rem;
        margin: 0.85rem 0;
        color: var(--text);
    }
    
    .warning-box {
        background: rgba(255, 193, 7, 0.12);
        border: 1px solid rgba(255, 193, 7, 0.35);
        border-radius: 10px;
        padding: 0.85rem;
        margin: 0.85rem 0;
        color: var(--text);
    }
    
    .error-box {
        background: rgba(220, 53, 69, 0.12);
        border: 1px solid rgba(220, 53, 69, 0.35);
        border-radius: 10px;
        padding: 0.85rem;
        margin: 0.85rem 0;
        color: var(--text);
    }
    
    /* Navigation buttons */
    .nav-button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 18px;
        padding: 0.45rem 1.2rem;
        font-size: 0.95rem;
        font-weight: 500;
        text-decoration: none;
        display: inline-block;
        transition: all 0.25s ease;
        margin: 0.35rem;
    }
    
    .nav-button:hover {
        transform: translateY(-1px);
        box-shadow: 0 3px 6px rgba(0, 0, 0, 0.1);
        text-decoration: none;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Gemini imports
try:
	from google import genai
except Exception:  # pragma: no cover
	genai = None  # type: ignore


def _strip_code_fences(text: str) -> str:
	"""Remove leading/trailing triple backticks and language tags like ```markdown."""
	if not text:
		return text
	# Normalize newlines
	t = text.strip()
	# Pattern for ```lang
	fence_start = re.compile(r"^```[a-zA-Z0-9_-]*\s*")
	fence_end = re.compile(r"```\s*$")
	# Remove start fence
	t = fence_start.sub("", t)
	# Remove ending fence
	t = fence_end.sub("", t)
	# Fix common typos like 'markdomw'
	t = t.replace("markdomw", "").strip()
	return t


def _parse_json_response(text: str) -> Optional[Dict[Any, Any]]:
	"""Parse JSON response from AI, handling common issues."""
	if not text:
		return None
	
	# Clean the text first
	cleaned = _strip_code_fences(text)
	
	try:
		# Try to parse as JSON directly
		return json.loads(cleaned)
	except json.JSONDecodeError:
		# Try to extract JSON from the text
		json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
		if json_match:
			try:
				return json.loads(json_match.group())
			except json.JSONDecodeError:
				pass
		
		# If all else fails, create a fallback structure
		logger.warning("Could not parse JSON response, creating fallback structure")
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


def _call_mistral(user_prompt: str) -> Optional[str]:
	"""Call Mistral API using requests. Returns text or None."""
	logger.info("Iniciando chamada para API Mistral via requests")
	
	api_key = st.secrets.get("MISTRAL_API_KEY")
	if not api_key:
		logger.error("Chave API Mistral não encontrada")
		return None
		
	try:
		url = "https://api.mistral.ai/v1/chat/completions"
		headers = {
			"Authorization": f"Bearer {api_key}",
			"Content-Type": "application/json"
		}
		
		data = {
			"model": "mistral-large-latest",
			"messages": [
				{"role": "system", "content": SYSTEM_PROMPT_VIAGEM},
				{"role": "user", "content": user_prompt}
			],
			"temperature": 0.7
		}
		
		logger.info("Enviando requisição para Mistral com modelo mistral-large-latest")
		response = requests.post(url, headers=headers, json=data)
		
		if response.status_code == 200:
			result = response.json()
			if "choices" in result and len(result["choices"]) > 0:
				content = result["choices"][0]["message"]["content"]
				logger.success(f"Resposta Mistral recebida com {len(content)} caracteres")
				return content
			else:
				logger.warning("Resposta Mistral sem choices válidas")
				return None
		else:
			logger.error(f"Erro HTTP Mistral: {response.status_code}, {response.text}")
			return None
		
	except Exception as e:
		logger.error(f"Erro na chamada Mistral: {e}")
		return None


def _call_gemini(user_prompt: str, model_name: str = "gemini-2.5-flash") -> Optional[str]:
	"""Call Gemini using the new google-genai client."""
	logger.info("Iniciando chamada para API Gemini")
	
	if genai is None:
		logger.error("Módulo genai não disponível")
		return None
		
	api_key = st.secrets.get("GEMINI_API_KEY")
	if not api_key:
		logger.error("Chave API Gemini não encontrada")
		return None
	
	try:
		client = genai.Client(api_key=api_key)
		full_prompt = f"{SYSTEM_PROMPT_VIAGEM}\n\n{user_prompt}"
		
		logger.info(f"Enviando requisição para Gemini com modelo {model_name}")
		response = client.models.generate_content(
			model=model_name,
			contents=full_prompt,
		)
		
		text = getattr(response, "text", None)
		if text:
			logger.success(f"Resposta Gemini recebida com {len(text)} caracteres")
		else:
			logger.warning("Resposta Gemini vazia")
		return text
		
	except Exception as e:
		logger.error(f"Erro na chamada Gemini: {e}")
		return None


def _offline_fallback(user_prompt: str) -> str:
	"""Last-resort offline template if both AIs fail."""
	logger.warning("Usando gerador offline (fallback final)")
	return (
		"### Roteiro Base (Offline)\n\n"
		"Não foi possível consultar os modelos online. Aqui está um roteiro-base.\n\n"
		"- Manhã: passeio leve pela região central e pontos icônicos.\n"
		"- Tarde: visita a um museu/mercado local.\n"
		"- Noite: jantar típico e caminhada por bairro charmoso.\n\n"
		"Inclua deslocamentos, reservas antecipadas e adapte ao seu ritmo."
	)


def _navigate_to_results(json_data: Dict[Any, Any], provider_used: str) -> None:
	st.session_state["roteiro_json"] = json_data
	st.session_state["provider_used"] = provider_used
	st.switch_page("pages/01_Roteiro.py")


def run_app() -> None:
	st.set_page_config(page_title="Planejador de Viagens IA", page_icon="🗺️", layout="wide", initial_sidebar_state="collapsed")
	
	# Custom navigation header
	st.markdown("""
	<div class="nav-container">
		<h1 class="nav-title">🗺️ Planejador de Viagens IA</h1>
		<p class="nav-subtitle">Gere roteiros personalizados com inteligência artificial</p>
	</div>
	""", unsafe_allow_html=True)
	
	# Main container
	st.markdown('<div class="main-container">', unsafe_allow_html=True)

	# Quick settings (visible) for provider selection
	colA, colB = st.columns([2, 3])
	with colA:
		provider = st.radio("Modelo preferido", ["Mistral", "Gemini"], horizontal=True, index=0)
	with colB:
		gemini_model = st.selectbox("Modelo do Gemini", ["gemini-2.5-flash", "gemini-2.0-pro", "gemini-1.5-pro-latest"], index=0)

	# Sidebar only for status (no provider controls) to avoid confusion
	with st.sidebar:
		st.markdown("### 📊 Status")
		if st.secrets.get("MISTRAL_API_KEY") and st.secrets.get("MISTRAL_API_KEY") != "coloque_sua_chave_da_mistral_aqui":
			st.success("✅ Mistral configurado")
		else:
			st.error("❌ Mistral não configurado")
		if st.secrets.get("GEMINI_API_KEY") and st.secrets.get("GEMINI_API_KEY") != "coloque_sua_chave_do_gemini_aqui":
			st.success("✅ Gemini configurado")
		else:
			st.error("❌ Gemini não configurado")

	# Main form card
	st.markdown("""
	<div class="card">
		<div class="card-header">
			<h2 class="card-title">✈️ Seu Perfil de Viagem</h2>
			<p class="card-subtitle">Preencha os detalhes para um roteiro personalizado</p>
		</div>
	""", unsafe_allow_html=True)
	
	with st.form("form_viagem"):
		# Basic info section
		st.markdown("""
		<div class="form-section">
			<h3 class="section-title"><span class="section-icon">📍</span>Informações Básicas</h3>
		""", unsafe_allow_html=True)
		
		col1, col2, col3 = st.columns(3)
		with col1:
			destino = st.text_input("Destino principal", placeholder="Ex.: Roma, Itália", help="Cidade ou país de destino")
		with col2:
			tipo_data = st.selectbox("Tipo de data", 
				["Data específica (dia/mês/ano)", "Mês e ano", "Melhor período (IA escolhe)"], 
				help="Escolha como especificar o período", key="tipo_data_select")
		with col3:
			duracao = st.number_input("Duração (dias)", min_value=1, max_value=60, value=7, step=1, help="Quantos dias de viagem")
		
		# MELHORIA: Removido o uso de session_state para detectar mudança e rerun. Em vez disso, usamos condicionais diretos.
		# Isso evita reruns desnecessários e melhora a estabilidade do formulário.
		# Configuração de data baseada na opção escolhida - CAMPOS CONDICIONAIS
		# Não precisamos mais de st.empty(), pois o form é renderizado condicionalmente de forma simples.
		
		if tipo_data == "Data específica (dia/mês/ano)":
			st.markdown("**📅 Data de Início:**")
			data_inicio = st.date_input("Selecione a data exata", value=date.today(), help="Data exata da viagem", label_visibility="collapsed", key="data_especifica")
			data_flexivel = False
			periodo_especifico = f"Data específica: {data_inicio.strftime('%d/%m/%Y')}"
		elif tipo_data == "Mês e ano":
			st.markdown("**📅 Mês e Ano:**")
			col_mes, col_ano = st.columns(2)
			with col_mes:
				mes = st.selectbox("Mês", 
					["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
					 "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"],
					index=date.today().month - 1, label_visibility="collapsed", key="mes_select")
			with col_ano:
				ano = st.selectbox("Ano", 
					[date.today().year, date.today().year + 1, date.today().year + 2],
					index=0, label_visibility="collapsed", key="ano_select")
			
			# Converter para data (primeiro dia do mês)
			mes_num = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
					   "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"].index(mes) + 1
			data_inicio = date(ano, mes_num, 1)
			data_flexivel = True
			periodo_especifico = f"Mês e ano: {mes} de {ano}"
		else:  # Melhor período (IA escolhe)
			st.markdown("**🤖 IA Escolherá o Melhor Período**")
			st.info("A IA analisará o destino e escolherá as melhores datas considerando clima, eventos e temporadas.")
			# NÃO mostrar campo de data quando IA escolhe
			data_inicio = None  # MELHORIA: Set to None instead of today() to indicate no specific date
			data_flexivel = True
			periodo_especifico = "Melhor período para o destino (IA escolherá as datas ideais)"
		
		st.markdown("</div>", unsafe_allow_html=True)
		
		# Traveler profile section
		st.markdown("""
		<div class="form-section">
			<h3 class="section-title"><span class="section-icon">👥</span>Perfil dos Viajantes</h3>
		""", unsafe_allow_html=True)
		
		col1, col2, col3, col4 = st.columns(4)
		with col1:
			perfil = st.selectbox("Tipo de viagem", ["Casal", "Família", "Solo", "Grupo de amigos", "Negócios"], index=0)
		with col2:
			num_viajantes = st.number_input("Número de viajantes", min_value=1, max_value=20, value=2)
		with col3:
			faixa_etaria = st.selectbox("Faixa etária", ["18-25", "26-35", "36-50", "51+"], index=1)
		with col4:
			criancas = st.toggle("Leva crianças?")
		
		st.markdown("</div>", unsafe_allow_html=True)
		
		# Preferences section
		st.markdown("""
		<div class="form-section">
			<h3 class="section-title"><span class="section-icon">🎯</span>Preferências de Viagem</h3>
		""", unsafe_allow_html=True)
		
		col1, col2 = st.columns(2)
		with col1:
			orcamento = st.selectbox("Orçamento", ["Econômico", "Intermediário", "Luxo"], index=1)
			ritmo = st.selectbox("Ritmo da viagem", ["Relaxado", "Moderado", "Intenso"], index=1)
			hospedagem = st.selectbox("Hospedagem", ["Hostel", "Hotel 3*", "Hotel 4*", "Hotel 5*", "Apartamento"], index=2)
		with col2:
			interesses = st.multiselect("Interesses", ["Gastronomia", "História", "Natureza", "Arte e museus", "Vida noturna", "Compras", "Aventura", "Tecnologia"], help="Selecione seus principais interesses")
			nivel_caminhada = st.select_slider("Nível de caminhada", options=["Muito baixo", "Baixo", "Médio", "Alto"], value="Médio")
			clima_desejado = st.selectbox("Clima desejado", ["Ameno", "Frio", "Quente"], index=0)
		
		st.markdown("</div>", unsafe_allow_html=True)
		
		# Additional details section
		st.markdown("""
		<div class="form-section">
			<h3 class="section-title"><span class="section-icon">📝</span>Detalhes Adicionais</h3>
		""", unsafe_allow_html=True)
		
		col1, col2 = st.columns(2)
		with col1:
			restricoes_alimentares = st.text_input("Restrições alimentares", placeholder="Ex.: vegetariano, sem lactose, halal, kosher")
			horarios_preferidos = st.text_input("Horários preferidos", placeholder="Ex.: acorda tarde, jantar cedo")
			aversoes = st.text_input("Aversões (evitar)", placeholder="Ex.: filas longas, locais muito turísticos")
		with col2:
			datas_flexiveis = st.selectbox("Datas flexíveis?", ["Não", "Sim"], index=0)
			cidades_proximas = st.text_input("Cidades próximas de interesse", placeholder="Ex.: Nápoles, Florença")
		
		observacoes = st.text_area("Observações e pedidos especiais", placeholder="Restrições, mobilidade, locais dos sonhos, etc.", height=100)
		
		st.markdown("</div>", unsafe_allow_html=True)
		
		# Submit button
		col1, col2, col3 = st.columns([1, 2, 1])
		with col2:
			submitted = st.form_submit_button("✨ Gerar Roteiro Personalizado", use_container_width=True)
	
	# Close card
	st.markdown("</div>", unsafe_allow_html=True)

	if submitted:
		if not destino:
			st.markdown("""
			<div class="warning-box">
				⚠️ Por favor, informe o destino principal.
			</div>
			""", unsafe_allow_html=True)
			return

		logger.info(f"Iniciando geração de roteiro para destino: {destino}")
		user_data = {
			"destino": destino.strip(),
			"data_inicio": data_inicio,  # MELHORIA: Agora pode ser None para "Melhor período"
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

		# Provider selection with smart fallback
		providers_order = [provider, "Gemini" if provider == "Mistral" else "Mistral"]
		for prov in providers_order:
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

		if not resultado:
			resultado = _offline_fallback(user_prompt)
			provider_used = "Offline"

		if resultado:
			# Parse JSON response
			json_data = _parse_json_response(resultado)
			if json_data:
				logger.success(f"Roteiro gerado com sucesso usando {provider_used}")
				st.markdown(f"""
				<div class="success-box">
					✅ Roteiro gerado com sucesso usando {provider_used}!
				</div>
				""", unsafe_allow_html=True)
				_navigate_to_results(json_data, provider_used)
			else:
				logger.error("Falha ao processar resposta JSON")
				st.markdown("""
				<div class="error-box">
					❌ Erro ao processar resposta da IA. Tente novamente.
				</div>
				""", unsafe_allow_html=True)
		else:
			logger.error("Falha total: não foi possível gerar o roteiro")
			st.markdown("""
			<div class="error-box">
				❌ Não foi possível gerar o roteiro. Verifique suas configurações.
			</div>
			""", unsafe_allow_html=True)

	# Close main container
	st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
	run_app()