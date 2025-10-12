import streamlit as st
import pandas as pd
import numpy as np
import random
import re
import io
import sys
import time
from datetime import datetime
from loguru import logger
import traceback
import pyperclip
import urllib.parse

# Configure logging
logger.remove()  # Remove default handler
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="30 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    enqueue=True,  # Thread-safe logging
)

# Add console handler with DEBUG level
logger.add(
    sys.stderr,
    level="DEBUG",  # Alterado de INFO para DEBUG
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

# Log application startup
logger.info("Aplicação iniciada")


def expand_numbers_field(field_text):
    """
    Expande formatos como:
    - '1,2,3' -> [1, 2, 3]
    - '1-5' -> [1, 2, 3, 4, 5]
    - '1;2;3' -> [1, 2, 3]
    - '1.2.3' -> [1, 2, 3]
    - '1 2 3' -> [1, 2, 3]
    - '5/6;7 8' -> [5, 6, 7, 8]
    """
    def is_valid_number(n):
        # Aceita apenas números entre 1 e 200
        return 1 <= n <= 200
    
    if not field_text or pd.isna(field_text):
        return []
        
    # Converte para string para garantir
    text = str(field_text).strip()
    if not text:
        return []
    
    logger.debug(f"Processando campo: '{field_text}'")
    
    # Remove espaços em branco extras
    text = re.sub(r'\s+', ' ', text)
    
    # Verifica se parece ser um número grande inválido
    if re.match(r'^\d{4,}$', text):
        logger.warning(f"Número muito grande ou inválido detectado: '{text}'. Será ignorado.")
        return []
    
    # Tenta processar como lista de números primeiro
    if ',' in text:
        try:
            numbers = []
            for num in text.split(','):
                num = num.strip()
                if num.isdigit():
                    n = int(num)
                    if is_valid_number(n):
                        numbers.append(n)
                    else:
                        logger.warning(f"Número fora do intervalo 1-200: {n}")
            if numbers:
                return numbers
        except Exception as e:
            logger.warning(f"Erro ao processar lista de números: {str(e)}")
    
    # Para outros formatos, mantém o processamento original
    text = re.sub(r'[;|/\\\.\u2011\u2012\u2013\u2014]', ',', text)
    
    # Separa por vírgulas, espaços ou outros
    parts = re.split(r'[,\s]+', text)
    
    nums = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        # Tenta converter para número diretamente
        try:
            num = int(part)
            if is_valid_number(num):
                nums.append(num)
            else:
                logger.warning(f"Número fora do intervalo 1-200: {num}")
            continue
        except ValueError:
            pass
            
        # Range com hífen
        if '-' in part and part.count('-') == 1:  # Apenas um hífen
            try:
                a, b = part.split('-')
                a = int(re.sub(r'\D', '', a))
                b = int(re.sub(r'\D', '', b))
                
                # Limita o range a 1-200
                a = max(1, min(a, 200))
                b = max(1, min(b, 200))
                
                if a <= b:
                    range_nums = list(range(a, b + 1))
                else:
                    range_nums = list(range(b, a + 1))
                    
                logger.debug(f"Range processado: {part} -> {range_nums}")
                nums.extend(range_nums)
            except Exception as e:
                logger.warning(f"Erro ao expandir range '{part}': {str(e)}")
                continue
        
        # Tenta extrair número de strings
        m = re.search(r'(\d+)', part)
        if m:
            try:
                num = int(m.group(1))
                if is_valid_number(num):
                    nums.append(num)
                else:
                    logger.warning(f"Número extraído fora do intervalo 1-200: {num}")
            except ValueError:
                pass
    
    # Remove duplicatas e ordena
    nums = sorted(list(set(nums)))
    logger.debug(f"Números extraídos de '{field_text}': {nums}")
    return nums


def find_num_and_name_columns(df):
    """
    Tenta encontrar automaticamente as colunas de número e nome no DataFrame.
    Retorna (coluna_numero, coluna_nome) se encontrado, senão (None, None)
    """
    # Lista de possíveis nomes para as colunas
    possiveis_numeros = ['numero', 'nro', 'núm', 'num', 'id', 'cota', 'bilhete', 'ticket']
    possiveis_nomes = ['nome', 'name', 'participante', 'pessoa', 'sorteado', 'ganhador']
    
    # Converte nomes de colunas para minúsculas para comparação
    colunas = [str(col).lower() for col in df.columns]
    
    # Tenta encontrar a coluna de número
    col_num = None
    for num in possiveis_numeros:
        matches = [i for i, col in enumerate(colunas) if num in col]
        if matches:
            col_num = df.columns[matches[0]]
            break
    
    # Tenta encontrar a coluna de nome
    col_name = None
    for nome in possiveis_nomes:
        matches = [i for i, col in enumerate(colunas) if nome in col]
        if matches:
            col_name = df.columns[matches[0]]
            break
    
    # Se não encontrou pelo nome, pega a primeira coluna que não é a de número
    if col_num and not col_name and len(df.columns) > 1:
        col_name = [col for col in df.columns if col != col_num][0]
    
    return col_num, col_name


def build_ticket_list(df, exclude_set=None):
    """
    Constrói lista de tickets a partir do DataFrame, aplicando exclusões se fornecidas.
    
    Args:
        df: DataFrame com colunas contendo números e nomes
        exclude_set: Conjunto de números a serem excluídos
        
    Returns:
        Lista de tuplas (número, nome) para o sorteio
    """
    logger.info(f"Construindo lista de tickets a partir de {len(df)} registros")
    
    # Tenta encontrar as colunas de número e nome
    col_num, col_name = find_num_and_name_columns(df)
    
    if not col_num or not col_name:
        error_msg = "Não foi possível identificar as colunas de número e nome no DataFrame"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info(f"Usando colunas: '{col_num}' para números e '{col_name}' para nomes")
    
    if exclude_set:
        logger.info(f"Excluindo {len(exclude_set)} números: {sorted(exclude_set)}")
    
    tickets = []
    total_nums = 0
    valid_nums = 0
    invalid_nums = 0
    errors = []
    
    for idx, row in df.iterrows():
        try:
            # Obtém o nome, garantindo que seja uma string
            nome = str(row[col_name]).strip() if pd.notna(row[col_name]) else f"Participante {idx+1}"
            
            # Obtém o valor do número (pode ser string, int, float, etc.)
            num_val = row[col_num]
            
            # Se for NaN, pula
            if pd.isna(num_val):
                logger.warning(f"Linha {idx+1}: Valor ausente na coluna de números")
                continue
                
            # Log do valor bruto antes do processamento
            logger.debug(f"Linha {idx+1}: Processando valor bruto: '{num_val}' para '{nome}'")
                
            # Converte para string e processa os números
            nums = expand_numbers_field(str(num_val))
            
            if not nums:
                logger.warning(f"Linha {idx+1}: Nenhum número válido encontrado para '{nome}'. Valor original: '{num_val}'")
                continue
                
            logger.debug(f"Linha {idx+1}: Números extraídos: {nums}")
                
            for n in nums:
                if exclude_set and n in exclude_set:
                    logger.debug(f"Excluindo número {n} (solicitado)")
                    continue
                    
                tickets.append((n, nome))
                total_nums += 1
                
        except Exception as e:
            error_msg = f"Erro ao processar linha {idx+1} (valor: '{num_val}'): {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            errors.append(error_msg)
    
    # Se houve erros, mostra um resumo
    if errors:
        logger.warning(f"Encontrados {len(errors)} erros ao processar o arquivo")
    
    # Log detalhado dos números encontrados
    if tickets:
        # Ordena os números para análise
        sorted_nums = sorted([n for n, _ in tickets])
        logger.info(f"Lista completa de números: {sorted_nums}")
        
        # Verifica duplicatas
        from collections import Counter
        counter = Counter([n for n, _ in tickets])
        duplicates = {k: v for k, v in counter.items() if v > 1}
        if duplicates:
            logger.warning(f"Números duplicados encontrados: {duplicates}")
        
        # Log dos números mínimos e máximos
        min_num = min(n for n, _ in tickets)
        max_num = max(n for n, _ in tickets)
        logger.info(f"Faixa de números: {min_num} a {max_num}")
        
        # Verifica se há números muito grandes
        large_numbers = [(n, name) for n, name in tickets if n > 1000]
        if large_numbers:
            logger.warning(f"Encontrados {len(large_numbers)} números acima de 1000: {large_numbers}")
    
    if not tickets:
        error_msg = "Nenhum número válido encontrado para o sorteio"
        logger.error(error_msg)
        raise ValueError(error_msg)
        
    return tickets


def display_data_table(df):
    st.markdown("### \U0001f4cb Dados Carregados")
    
    # Cria uma cópia para não modificar o DataFrame original
    df_display = df.copy()
    
    # Converte a coluna de Número para string para exibição
    if 'Número' in df_display.columns:
        df_display['Número'] = df_display['Número'].astype(str)
    
    # Estatísticas rápidas (usando o DataFrame original para cálculos)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Participantes", len(df))
    with col2:
        # Encontra o menor valor numérico
        numeric_vals = [x for x in df["Número"] if isinstance(x, (int, float, np.number))]
        min_val = min(numeric_vals) if numeric_vals else "-"
        st.metric("Menor Número", min_val if min_val != "-" else "-")
    with col3:
        # Encontra o maior valor numérico
        max_val = max(numeric_vals) if numeric_vals else "-"
        st.metric("Maior Número", max_val if max_val != "-" else "-")
    
    # Ordena os dados para exibição
    try:
        # Tenta ordenar numericamente primeiro
        df_display = df_display.sort_values(
            by="Número",
            key=lambda x: pd.to_numeric(x, errors='coerce')
        )
    except Exception as e:
        # Se falhar, ordena como string
        df_display = df_display.sort_values(by="Número", key=lambda x: x.astype(str).str.lower())
    
    # Exibe a tabela com paginação
    st.dataframe(
        df_display.reset_index(drop=True),
        use_container_width=True,
        height=400,
        column_config={
            "Número": st.column_config.TextColumn("Nº"),
            "Nome": st.column_config.TextColumn("Nome do Participante")
        },
        hide_index=True
    )


def clean_number(value):
    """
    Limpa e converte valores para números, lidando com TODOS os formatos:
    - Listas: 1,2,3 ou 1, 2, 3 ou 1-2-3 ou 1 - 2 - 3
    - Números com vírgula: 1,5 → 1.5
    - Números com ponto: 1.5 → 1.5
    - Múltiplos separadores: 1, 2-3, 4.5 ou 5/6;7 8
    - Remove espaços extras e caracteres inválidos
    """
    if pd.isna(value) or value == '':
        return None
    
    # Converte para string e remove espaços extras
    value = str(value).strip()
    
    # Se for vazio após limpeza, retorna None
    if not value:
        return None
    
    # Lista para armazenar todos os números encontrados
    all_numbers = []
    
    # Primeiro, normaliza todos os separadores para vírgula (inclui /, ;, .)
    normalized = re.sub(r'\s+', ' ', value)
    normalized = re.sub(r'[;|/\\\.\u2011\u2012\u2013\u2014]', ',', normalized)
    normalized = normalized.replace('-', ',')
    # Remove espaços após as vírgulas
    normalized = re.sub(r',\s*', ',', normalized)
    
    # Agora processa cada número na lista
    for part in normalized.split(','):
        part = part.strip()
        if not part:
            continue
            
        # Remove caracteres não numéricos, exceto ponto e sinal negativo
        num_str = re.sub(r'[^0-9\.\-]', '', part.replace(',', '.'))
        
        if num_str:  # Se sobrar algo após limpar
            try:
                num = float(num_str)
                # Se for inteiro, converte para int, senão mantém como float com 2 casas
                num_str = str(int(num)) if num.is_integer() else f"{num:.2f}"
                all_numbers.append(num_str)
            except (ValueError, AttributeError):
                # Se não conseguir converter, mantém o valor original limpo
                all_numbers.append(part)
    
    # Retorna os números separados por vírgula e espaço
    return ', '.join(all_numbers) if all_numbers else value


# Função auxiliar para extrair números de uma string
def extract_numbers(value):
    """Extrai todos os números de uma string, incluindo listas e intervalos"""
    if not value or pd.isna(value):
        return []
    
    # Converte para string e remove espaços
    value = str(value).replace(' ', '')
    
    # Encontra todos os números (incluindo decimais)
    numbers = []
    for num_str in re.findall(r'-?\d+(?:\.\d+)?', value):
        try:
            num = float(num_str)
            numbers.append(num)
        except (ValueError, TypeError):
            continue
    
    return numbers


# Configuração da página
st.set_page_config(
    page_title="\U0001f3c6 Sorteador de Rifas Pro",
    page_icon="\U0001f3b2",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------
# Estilos CSS personalizados
# -------------------------
st.markdown("""
    <style>
    /* Estilos gerais */
    .main {
        max-width: 1200px;
        margin: 0 auto;
        padding: 2rem;
    }
    
    /* Cabeçalho */
    .header {
        text-align: center;
        margin-bottom: 2.5rem;
        padding: 1.5rem;
        background: linear-gradient(135deg, #1E3C72 0%, #2A5298 100%);
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    /* Cards */
    .card {
        background: #1E1E1E;
        border-radius: 12px;
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
        border: 1px solid #2D2D2D;
        transition: transform 0.3s, box-shadow 0.3s;
    }
    .card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2);
    }
    
    /* Títulos */
    .card h2, .card h3 {
        color: #00D1B2;
        margin-top: 0;
        border-bottom: 2px solid #2D2D2D;
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
    }
    
    /* Botões */
    .stButton>button {
        background: linear-gradient(135deg, #00D1B2 0%, #00B39E 100%);
        color: white;
        font-weight: bold;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        width: 100%;
        transition: all 0.3s;
        font-size: 1.1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
        background: linear-gradient(135deg, #00B39E 0%, #009688 100%);
    }
    
    /* Inputs */
    .stTextInput>div>div>input, 
    .stTextArea>div>div>textarea,
    .stNumberInput>div>div>input {
        background: #2D2D2D !important;
        color: white !important;
        border: 1px solid #444 !important;
        border-radius: 8px !important;
        padding: 0.75rem 1rem !important;
    }
    
    .stTextInput>label, 
    .stTextArea>label,
    .stNumberInput>label {
        color: #00D1B2 !important;
        font-weight: bold !important;
        font-size: 1rem !important;
    }
    
    /* Alertas */
    .stAlert {
        border-radius: 10px;
        border-left: 5px solid;
    }
    
    /* Card do vencedor */
    .winner-card {
        background: linear-gradient(135deg, #1E3C72 0%, #2A5298 100%);
        color: white;
        padding: 3rem 2rem;
        border-radius: 15px;
        text-align: center;
        margin: 2rem 0;
        box-shadow: 0 15px 30px rgba(0,0,0,0.2);
        border: 1px solid rgba(255,255,255,0.1);
        animation: fadeIn 0.8s ease-in-out;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .winner-name {
        font-size: 2.8rem;
        font-weight: bold;
        color: #FFD700;
        margin: 1.5rem 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    
    .prize {
        font-size: 1.8rem;
        color: #00FFA3;
        margin-bottom: 1rem;
        font-weight: 600;
    }
    
    .ticket-number {
        font-size: 2.5rem;
        color: #FF6B6B;
        font-weight: bold;
        background: rgba(0,0,0,0.2);
        display: inline-block;
        padding: 0.5rem 2rem;
        border-radius: 50px;
        margin-top: 1rem;
        border: 2px solid rgba(255,255,255,0.1);
    }
    
    /* Abas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        align-items: center;
        border-radius: 8px 8px 0 0;
        padding: 0 1.5rem;
        transition: all 0.3s;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #00D1B2;
        color: white !important;
    }
    
    /* Rodapé */
    .footer {
        text-align: center;
        margin-top: 4rem;
        padding: 1.5rem;
        color: #888;
        font-size: 0.9rem;
        border-top: 1px solid #2D2D2D;
    }
    
    /* Responsividade */
    @media (max-width: 768px) {
        .header h1 {
            font-size: 1.8rem;
        }
        .winner-name {
            font-size: 2rem;
        }
        .prize {
            font-size: 1.4rem;
        }
        .ticket-number {
            font-size: 2rem;
        }
    }
    
    .winner-card-custom {
        background: linear-gradient(145deg, #f8f9fa, #ffffff);
        border-radius: 15px;
        padding: 25px;
        margin: 20px 0;
        box-shadow: 0 6px 15px rgba(0,0,0,0.08);
        border-left: 5px solid #4CAF50;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .winner-card-custom:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.12);
    }
    .winner-card-custom::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 5px;
        background: linear-gradient(90deg, #4CAF50, #8BC34A);
    }
    .prize-title {
        color: #2E7D32;
        font-size: 1.8rem;
        font-weight: 700;
        margin: 20px 0;
        text-align: center;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
    }
    .winner-name-custom {
        color: #1A237E;
        font-size: 1.5rem;
        font-weight: 600;
        margin: 10px 0 5px;
    }
    .winner-number-custom {
        font-size: 1.2rem;
        color: #616161;
        margin: 5px 0;
    }
    .position-badge {
        background: #4CAF50;
        color: white;
        border-radius: 50%;
        width: 50px;
        height: 50px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        margin: 0 auto 15px;
        font-size: 1.2rem;
        box-shadow: 0 3px 10px rgba(0,0,0,0.15);
    }
    .share-button {
        background: linear-gradient(135deg, #25D366, #128C7E);
        color: white !important;
        border: none;
        padding: 12px 30px;
        border-radius: 50px;
        font-size: 1.1rem;
        font-weight: 500;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 10px;
        text-decoration: none;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(37, 211, 102, 0.3);
    }
    .share-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(37, 211, 102, 0.4);
        color: white;
        text-decoration: none;
    }
    </style>
""", unsafe_allow_html=True)

# Título e descrição
st.markdown("""
<div class="header">
    <h1>&#127942; Sorteador de Rifas Profissional</h1>
    <p>Realize sorteios de forma justa e transparente com nossa ferramenta profissional</p>
</div>
""", unsafe_allow_html=True)

# Inicializa o DataFrame na sessão se não existir
if 'df' not in st.session_state:
    st.session_state['df'] = pd.DataFrame(columns=['Número', 'Nome'])

# Obtém o DataFrame da sessão
df = st.session_state['df'].copy()

# Abas principais
tab1, tab2 = st.tabs(["\U0001f3af Realizar Sorteio", "\U0001f4ca Histórico"])

with tab1:
    # Seção de configuração do sorteio
    with st.expander("\u2699\uFE0F Configurações do Sorteio", expanded=True):
        num_ganhadores = st.number_input("\U0001f3af Nº de Ganhadores", 
                                      min_value=1, 
                                      value=1, 
                                      step=1)
    
    # Seção de upload de arquivo
    with st.expander("\U0001f4e4 1. Importar Dados (Arquivo CSV/Excel)", expanded=True):
        uploaded_file = st.file_uploader("Selecione um arquivo CSV ou Excel", 
                                      type=["csv", "xlsx", "xls"], 
                                      key="file_uploader",
                                      help="Arquivos suportados: .csv, .xlsx, .xls")
        
        if uploaded_file is not None:
            try:
                # Verifica o tipo de arquivo
                file_ext = uploaded_file.name.lower().split('.')[-1]
                
                # Dicionário para armazenar mensagens de erro
                error_messages = []
                
                if file_ext in ['csv', 'txt']:
                    # Tenta diferentes encodings comuns
                    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                    df_loaded = None
                    
                    for encoding in encodings:
                        try:
                            uploaded_file.seek(0)  # Volta para o início do arquivo
                            # Lê o arquivo mantendo os dados brutos para análise
                            df_loaded = pd.read_csv(
                                uploaded_file, 
                                encoding=encoding, 
                                on_bad_lines='warn',
                                sep=None,  # Detecta o separador automaticamente
                                engine='python',
                                dtype=str,  # Lê tudo como string primeiro
                                skipinitialspace=True,  # Remove espaços em branco extras
                                na_values=['', ' ', '  ', '   ', '    '],  # Trata strings vazias como NaN
                                keep_default_na=True
                            )
                            
                            # Identifica colunas que podem conter números
                            numeric_cols = []
                            non_numeric_values = []
                            
                            for col in df_loaded.columns:
                                if df_loaded[col].notna().any():  # Se a coluna não estiver vazia
                                    # Faz uma cópia da coluna original para validação
                                    original_values = df_loaded[col].copy()
                                    
                                    # Aplica a limpeza dos números
                                    cleaned_series = df_loaded[col].apply(clean_number)
                                    
                                    # Conta quantos valores foram convertidos com sucesso
                                    numeric_mask = pd.notna(cleaned_series) & (cleaned_series != '')
                                    if numeric_mask.any():
                                        # Se mais de 50% dos valores foram convertidos, considera como coluna numérica
                                        if numeric_mask.mean() > 0.5:
                                            numeric_cols.append(col)
                                            
                                            # Identifica valores não numéricos para relatório
                                            non_numeric_mask = df_loaded[col].notna() & ~numeric_mask
                                            for idx, val in original_values[non_numeric_mask].items():
                                                # Mostra o valor original e o valor limpo (se houver)
                                                cleaned_val = cleaned_series[idx]
                                                msg = f"Linha {idx+2}, Coluna '{col}': '{val}'"
                                                if pd.notna(cleaned_val) and cleaned_val != '':
                                                    msg += f" (convertido para: {cleaned_val})"
                                                non_numeric_values.append(msg)
                                            
                                            # Atualiza a coluna com os valores limpos
                                            df_loaded[col] = cleaned_series
                            
                            # Mostra aviso com detalhes sobre valores não numéricos
                            if non_numeric_values:
                                non_numeric_count = len(non_numeric_values)
                                st.warning(f"\u26A0\uFE0F {non_numeric_count} valor(es) não numérico(s) encontrados. Eles serão ignorados no sorteio.")
                                
                                # Mostra os primeiros 5 valores problemáticos
                                with st.expander("Ver detalhes dos valores não numéricos", expanded=False):
                                    st.write("Os seguintes valores não puderam ser convertidos para números e serão ignorados:")
                                    for i, value in enumerate(non_numeric_values[:5], 1):
                                        st.write(f"{i}. {value}")
                                    if non_numeric_count > 5:
                                        st.write(f"... e mais {non_numeric_count - 5} valores não numéricos.")
                                
                            break  # Se chegou aqui, o encoding funcionou
                        except Exception as e:
                            error_messages.append(f"Erro com codificação {encoding}: {str(e)}")
                            continue
                            
                    if df_loaded is None:
                        error_msg = "Não foi possível ler o arquivo com as codificações suportadas.\n\n"
                        error_msg += "Tente salvar o arquivo como UTF-8 ou CSV com separador de vírgula."
                        raise ValueError(error_msg)
                        
                elif file_ext in ['xlsx', 'xls']:
                    # Para arquivos Excel
                    try:
                        df_loaded = pd.read_excel(uploaded_file, engine='openpyxl', dtype=str)
                    except Exception as e:
                        try:
                            # Tenta com engine alternativa se openpyxl falhar
                            df_loaded = pd.read_excel(uploaded_file, engine='xlrd', dtype=str)
                        except Exception as e2:
                            logger.error(f"Erro ao ler arquivo Excel: {str(e2)}")
                            raise ValueError("Erro ao processar o arquivo Excel. Verifique se o formato é válido.")
                else:
                    raise ValueError("Formato de arquivo não suportado. Use CSV, XLSX ou XLS.")
                
                # Verifica se o DataFrame não está vazio
                if df_loaded.empty:
                    raise ValueError("O arquivo está vazio ou não contém dados válidos.")
                
                # Tenta encontrar as colunas de número e nome
                col_num, col_name = find_num_and_name_columns(df_loaded)
                
                if not col_num or not col_name:
                    # Se não encontrou automaticamente, mostra as colunas disponíveis
                    st.warning("\u26A0\uFE0F Não foi possível identificar as colunas automaticamente. Selecione as colunas corretas:")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        col_num = st.selectbox("Selecione a coluna de NÚMERO:", df_loaded.columns)
                    with col2:
                        # Remove a coluna de número das opções de nome
                        nome_options = [c for c in df_loaded.columns if c != col_num]
                        col_name = st.selectbox("Selecione a coluna de NOME:", nome_options)
                    
                    # Botão para confirmar a seleção
                    if st.button("Confirmar Colunas", key="confirm_columns"):
                        st.rerun()
                
                # Processa as colunas selecionadas
                if col_num and col_name:
                    try:
                        # Cria um novo DataFrame apenas com as colunas necessárias
                        df_clean = df_loaded[[col_num, col_name]].copy()
                        df_clean.columns = ['Número', 'Nome']
                        
                        # Remove linhas vazias
                        df_clean = df_clean.dropna(how='all')
                        
                        # Remove espaços extras e converte para string
                        df_clean['Nome'] = df_clean['Nome'].astype(str).str.strip()
                        
                        # Aplica a limpeza aos números
                        df_clean['Número'] = df_clean['Número'].apply(clean_number)
                        
                        # Verifica se há valores não numéricos
                        non_numeric = df_clean['Número'].apply(
                            lambda x: x is not None and not isinstance(x, (int, float, np.number))
                        )
                        
                        if non_numeric.any():
                            st.warning(f"\u26A0\uFE0F {non_numeric.sum()} valores não numéricos encontrados. Eles serão tratados como texto.")
                        
                        # Remove duplicatas mantendo a primeira ocorrência
                        df_clean = df_clean.drop_duplicates(subset=['Número'], keep='first')
                        
                        # Salva no estado da sessão
                        st.session_state['df'] = df_clean
                        
                        # Mostra mensagem de sucesso
                        st.success(f"\u2705 {len(df_clean)} registros carregados com sucesso!")
                        
                        # Exibe a prévia dos dados
                        display_data_table(df_clean)
                        
                    except Exception as e:
                        error_msg = f"Erro ao processar os dados: {str(e)}\n\n"
                        error_msg += "Verifique se as colunas selecionadas estão corretas e se os dados estão no formato esperado."
                        st.error(error_msg)
                        logger.error(f"Erro ao processar dados: {traceback.format_exc()}")
                
            except Exception as e:
                error_msg = f"\u274C Erro ao processar o arquivo: {str(e)}\n\n"
                error_msg += "Dicas para resolver:\n"
                error_msg += "1. Verifique se o arquivo não está corrompido\n"
                error_msg += "2. Para arquivos CSV, tente salvar como UTF-8\n"
                error_msg += "3. Verifique se as colunas de número e nome estão corretas\n"
                error_msg += "4. Se for Excel, tente salvar como CSV e enviar novamente"
                
                st.error(error_msg)
                logger.error(f"Erro ao processar arquivo: {traceback.format_exc()}")
    
    # Seção de entrada manual
    # Abas para escolher entre inserção em lote ou um por um
    tab_manual, tab_individual = st.tabs(["\U0001f4dd Inserção em Lote", "\U0001f464 Cadastrar Individualmente"])
    
    with tab_manual:
        st.write("**MODO LOTE** - Insira todos os nomes e números de uma vez")
        col1, col2 = st.columns(2)
        with col1:
            nomes_manual = st.text_area("Nomes (um por linha)", 
                                     placeholder="João da Silva\nMaria Oliveira\nCarlos Souza", 
                                     height=150,
                                     key="nomes_manual")
        with col2:
            numeros_manual = st.text_area("Números (um por linha)", 
                                       placeholder="1\n2\n3\n4-6 (irá gerar 4,5,6)", 
                                       height=150,
                                       key="numeros_manual")
            st.caption("Suporta múltiplos formatos: 1,2,3 ou 1-3 ou 1;2;3")
        
        if st.button("\u2705 Processar Dados em Lote", key="btn_processar_lote"):
            if nomes_manual and numeros_manual:
                try:
                    # Processa os nomes, removendo linhas vazias
                    nomes_list = [nome.strip() for nome in nomes_manual.split('\n') if nome.strip()]
                    
                    # Processa os números, garantindo correspondência exata
                    nums_list = []
                    num_lines = [n.strip() for n in numeros_manual.split('\n') if n.strip()]
                    
                    # Se tivermos menos linhas de números que nomes, preenche com None
                    if len(num_lines) < len(nomes_list):
                        num_lines.extend([''] * (len(nomes_list) - len(num_lines)))
                    
                    # Contador para números não numéricos
                    non_numeric_count = 0
                    
                    for i, num_line in enumerate(num_lines):
                        if i >= len(nomes_list):  # Se já processamos todos os nomes, para
                            break
                            
                        if not num_line:  # Se não houver número, usa o índice + 1
                            nums_list.append(i + 1)
                            continue
                        
                        # Limpa a string removendo caracteres não numéricos, exceto hífen e vírgula
                        cleaned = re.sub(r'[^\d,\-]', '', num_line.strip())
                        
                        # Tenta converter diretamente para inteiro se for um único número
                        if re.match(r'^\s*\d+\s*$', num_line):
                            try:
                                nums_list.append(int(cleaned))
                                continue
                            except (ValueError, TypeError):
                                pass
                        
                        # Se tiver hífen, processa como intervalo
                        if '-' in cleaned:
                            try:
                                start, end = map(int, cleaned.split('-'))
                                # Pega o primeiro número do intervalo
                                nums_list.append(min(start, end))
                                continue
                            except (ValueError, TypeError):
                                pass
                        
                        # Se tiver vírgula, pega o primeiro número
                        if ',' in cleaned:
                            try:
                                first_num = cleaned.split(',')[0].strip()
                                if first_num:  # Verifica se não está vazio
                                    nums_list.append(int(first_num))
                                    continue
                            except (ValueError, TypeError):
                                pass
                        
                        # Se chegou até aqui, não conseguiu processar o número
                        non_numeric_count += 1
                        # Usa o índice + 1 como fallback
                        nums_list.append(i + 1)
                    
                    # Mostra aviso se houver números não numéricos
                    if non_numeric_count > 0:
                        st.warning(f"\u26A0\uFE0F {non_numeric_count} valor(es) não numérico(s) encontrado(s). Eles foram substituídos por números sequenciais.")
                    
                    if len(nomes_list) == len(nums_list):
                        df_manual = pd.DataFrame({
                            'Número': nums_list,
                            'Nome': nomes_list
                        })
                        st.session_state['df'] = df_manual
                        st.success(f"\u2705 {len(df_manual)} registros processados com sucesso!")
                        display_data_table(df_manual)
                    else:
                        st.error(f"""
                        \u274C O número de nomes e números não corresponde!
                        - Nomes fornecidos: {len(nomes_list)}
                        - Números fornecidos: {len(nums_list)}
                        
                        Verifique se há linhas vazias ou formatação incorreta.
                        """)
                except Exception as e:
                    st.error(f"\u274C Erro ao processar os dados: {str(e)}")
            else:
                st.warning("\u26A0\uFE0F Preencha ambos os campos de nomes e números.")
    
    with tab_individual:
        st.write("**MODO INDIVIDUAL** - Cadastre um participante por vez")
        
        # Inicializa a lista de participantes na sessão se não existir
        if 'participantes' not in st.session_state:
            st.session_state.participantes = []
        
        # Formulário para cadastro individual
        with st.form("form_individual"):
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Nome do participante", key="nome_individual")
            with col2:
                numero = st.text_input("Número", key="numero_individual")
            
            submitted = st.form_submit_button("\u2795 Adicionar Participante")
            
            if submitted:
                if nome and numero:
                    try:
                        # Processa o número, aceitando vírgulas e hífens
                        try:
                            # Remove espaços e divide por vírgula ou hífen
                            numeros = re.split(r'[,\-\s]+', numero.strip())
                            numeros_validos = []
                            
                            for num_str in numeros:
                                if num_str:  # Se não for string vazia
                                    try:
                                        num = int(num_str)
                                        numeros_validos.append(num)
                                    except ValueError:
                                        st.warning(f"\u26A0\uFE0F Valor inválido ignorado: '{num_str}'. Use apenas números inteiros.")
                                        continue
                            
                            if not numeros_validos:
                                st.error("\u274C Nenhum número válido encontrado!")
                            else:
                                # Verifica se algum número já existe
                                numeros_existentes = [p['Número'] for p in st.session_state.participantes]
                                duplicados = [n for n in numeros_validos if n in numeros_existentes]
                                
                                if duplicados:
                                    st.warning(f"\u26A0\uFE0F Número(s) já cadastrado(s): {', '.join(map(str, duplicados))}")
                                else:
                                    # Adiciona todos os números válidos
                                    for num in numeros_validos:
                                        st.session_state.participantes.append({
                                            'Número': num,
                                            'Nome': nome.strip()
                                        })
                                    
                                    st.success(f"\u2705 {len(numeros_validos)} participante(s) adicionado(s) com sucesso!")
                                    
                                    # Atualiza o DataFrame na sessão
                                    if st.session_state.participantes:
                                        df_individual = pd.DataFrame(st.session_state.participantes)
                                        st.session_state['df'] = df_individual
                                        display_data_table(df_individual)
                                    
                                    # Limpa os campos do formulário
                                    st.session_state.nome_individual = ""
                                    st.session_state.numero_individual = ""
                        except Exception as e:
                            st.error(f"\u274C Erro ao processar os números: {str(e)}")
                    except Exception as e:
                        st.error(f"\u274C Erro ao adicionar participante: {str(e)}")
                else:
                    st.warning("\u26A0\uFE0F Preencha todos os campos!")
        
        # Mostra contagem atual
        if 'participantes' in st.session_state and st.session_state.participantes:
            st.info(f"\U0001f4cb Total de participantes cadastrados: {len(st.session_state.participantes)}")
            
            # Botão para limpar todos os participantes
            if st.button("\U0001f5d1 Limpar todos os participantes", type="secondary"):
                st.session_state.participantes = []
                st.session_state['df'] = pd.DataFrame(columns=['Número', 'Nome'])
                st.rerun()
    
    # Seção de configurações avançadas
    with st.expander("\u2699\uFE0F 3. Configurações Avançadas"):
        st.markdown("### \U0001f522 Números a serem excluídos")
        st.write("Informe os números que devem ser excluídos do sorteio (opcional):")
        
        excl_input = st.text_input("Números a excluir (separados por vírgula ou hífen)",
                                 placeholder="Ex: 1, 3, 5-10, 100-110",
                                 help="Separe por vírgula ou use hífen para intervalos",
                                 key="excluir_numeros")
        
        if st.button("\U0001f504 Atualizar Visualização", key="btn_atualizar"):
            if 'df' in st.session_state:
                display_data_table(st.session_state['df'])

        # Botão para limpar cache
        if st.button("\U0001f9f9 Limpar cache do Streamlit (apenas local)", key="btn_limpar_cache"):
            try:
                st.cache_data.clear()
                st.cache_resource.clear()
                st.success("\u2705 Cache limpo com sucesso!")
            except Exception as e:
                st.warning(f"\u26A0\uFE0F Não foi possível limpar algum cache: {str(e)}")

# Seção de ajuda
st.markdown("""
    ### \u2753 Como usar
    1. **Prêmio**: Digite o prêmio que será sorteado
    2. **Nº de Ganhadores**: Selecione quantos ganhadores deseja sortear
    3. **Upload de Arquivo**: Envie uma planilha com as colunas 'Número' e 'Nome' (opcional)
    4. **Entrada Manual**: Digite os nomes e números manualmente (um por linha)
    5. Clique em "\U0001f389 SORTEAR AGORA" para sortear os ganhadores

    \U0001f4a1 Dica: Você pode usar vírgulas, hífens ou quebras de linha para listar múltiplos números.
""")

# -------------------------
# Seção de configuração do sorteio
# -------------------------
st.markdown("## 2) Configuração do Sorteio")

# Seção de configuração dos prêmios
with st.expander("\U0001f381 Configuração dos Prêmios", expanded=True):
    # Campo para o prêmio principal
    premio = st.text_input("\U0001f381 Descrição do Prêmio",
                         placeholder="Ex: 1 iPhone 15, R$ 1000,00 em compras, etc.",
                         help="Descreva o prêmio que será sorteado",
                         key="premio_sorteio")
    
    # Configuração de múltiplos ganhadores
    col1, col2 = st.columns(2)
    with col1:
        num_ganhadores = st.number_input("\U0001f465 Número de Ganhadores",
                                       min_value=1,
                                       max_value=100,
                                       value=1,
                                       step=1,
                                       help="Quantas pessoas serão sorteadas para este prêmio")
    
    with col2:
        permite_repeticao = st.checkbox("\U0001f501 Permitir que uma pessoa ganhe mais de um prêmio",
                                     value=False,
                                     help="Se ativado, a mesma pessoa pode ser sorteada mais de uma vez")
    
    # Se for mais de um ganhador, mostrar opções adicionais
    if num_ganhadores > 1:
        st.info(f"\u2139\uFE0F Serão sorteados {num_ganhadores} ganhadores para este prêmio.")
        if not permite_repeticao:
            st.warning("\u26A0\uFE0F Com repetição desativada, o mesmo número não poderá ser sorteado mais de uma vez.")

# Verifica se há dados para o sorteio
if 'df' not in st.session_state or st.session_state['df'].empty:
    st.warning("\u26A0\uFE0F Nenhum dado para o sorteio. Por favor, importe um arquivo ou insira os dados manualmente.")
    st.stop()

# Mostra estatísticas dos dados carregados
st.sidebar.markdown("### \U0001f4ca Dados Carregados")
st.sidebar.metric("Total de Participantes", len(st.session_state['df']))

# Extrai todos os números da coluna 'Número'
try:
    all_numbers = []
    for num_str in st.session_state['df']['Número']:
        all_numbers.extend(extract_numbers(str(num_str)))
    
    if all_numbers:
        min_val = min(all_numbers)
        max_val = max(all_numbers)
        st.sidebar.metric("Menor Número", int(min_val) if min_val.is_integer() else f"{min_val:.2f}")
        st.sidebar.metric("Maior Número", int(max_val) if max_val.is_integer() else f"{max_val:.2f}")
    else:
        st.sidebar.metric("Menor Número", "-")
        st.sidebar.metric("Maior Número", "-")
except Exception as e:
    logger.warning(f"Erro ao calcular estatísticas: {e}")
    st.sidebar.metric("Menor Número", "Erro")
    st.sidebar.metric("Maior Número", "Erro")

# -------------------------
# Executa sorteio
# -------------------------
if st.button("\U0001f389 SORTEAR AGORA!", use_container_width=True, type="primary"):
    logger.info(f"Iniciando processo de sorteio para {num_ganhadores} ganhador(es)")
    
    # Validação do prêmio
    if not premio:
        error_msg = "Prêmio não informado"
        logger.error(error_msg)
        st.error("\u274C Informe o prêmio do sorteio.")
        st.stop()
    
    logger.info(f"Prêmio definido: {premio}")
    
    # Processa lista de exclusão
    excl_set = set()
    if excl_input:
        logger.debug(f"Processando lista de exclusão: {excl_input}")
        try:
            # Expande intervalos na exclusão
            excl_parts = re.split(r'[,\s]+', excl_input)
            for part in excl_parts:
                part = part.strip()
                if '-' in part:
                    try:
                        a, b = map(int, re.split(r'-', part))
                        excl_set.update(range(min(a, b), max(a, b) + 1))
                    except ValueError:
                        try:
                            excl_set.add(int(part))
                        except ValueError:
                            pass
                else:
                    try:
                        excl_set.add(int(part))
                    except ValueError:
                        pass
            logger.info(f"Números a serem excluídos: {sorted(excl_set) if excl_set else 'Nenhum'}")
        except Exception as e:
            error_msg = f"Formato inválido na lista de exclusão: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            st.error(f"\u274C {error_msg}. Use números separados por vírgula ou espaço.")
            st.stop()
    
    # Verifica se há participantes suficientes
    num_participantes = len(df)
    if num_participantes < num_ganhadores and not permite_repeticao:
        st.error(f"\u274C Número insuficiente de participantes únicos ({num_participantes}) para sortear {num_ganhadores} ganhadores sem repetição.")
        st.stop()
    
    # Constrói lista de tickets
    logger.info("Construindo lista de tickets para sorteio")
    tickets = build_ticket_list(df, exclude_set=excl_set)
    
    # Validações da lista de tickets
    if not tickets:
        error_msg = "Nenhum ticket válido encontrado após processamento"
        logger.error(error_msg)
        st.error(" \u274C Nenhum ticket válido encontrado (verifique os números e exclusões).")
        st.stop()
    
    logger.info(f"Total de tickets válidos para sorteio: {len(tickets)}")
    
    # Verifica duplicatas
    if df['Número'].duplicated().any():
        contagem_numeros = df['Número'].value_counts()
        duplicados = contagem_numeros[contagem_numeros > 1]
        
        total_duplicados = int(duplicados.sum() - len(duplicados))
        mensagem = f"\u26A0\uFE0F **Atenção: {len(duplicados)} números aparecem mais de uma vez**\n\n"
        mensagem += f"**Total de entradas duplicadas:** {total_duplicados}\n\n"
        
        if len(duplicados) <= 10:
            mensagem += "**Números duplicados:**\n"
            for num, count in duplicados.items():
                nomes = df[df['Número'] == num]['Nome'].tolist()
                mensagem += f"- Número **{num}**: {count} vezes - Participantes: {', '.join(nomes[:3])}"
                if len(nomes) > 3:
                    mensagem += f" e mais {len(nomes)-3}..."
                mensagem += "\n"
        else:
            mensagem += f"**Exemplo de números duplicados (10 de {len(duplicados)}):**\n"
            for num, count in duplicados.head(10).items():
                mensagem += f"- Número **{num}**: {count} participantes\n"
        
        mensagem += "\n**Recomendações:**\n"
        mensagem += "1. Verifique se os números devem realmente estar duplicados\n"
        mensagem += "2. Se não for intencional, corrija os dados antes de prosseguir\n"
        mensagem += "3. O sorteio continuará, mas números duplicados terão maior chance de serem sorteados"
        
        with st.expander("\u26A0\uFE0F Clique para ver detalhes dos números duplicados", expanded=False):
            st.markdown(mensagem)
    
    # Valida quantidade de ganhadores
    if len(tickets) < num_ganhadores:
        error_msg = f"Número insuficiente de tickets ({len(tickets)}) para sortear {num_ganhadores} ganhadores"
        logger.error(error_msg)
        st.error(f"\u274C {error_msg}.")
        st.stop()
    
    # Realiza o sorteio
    logger.info(f"Realizando sorteio para {num_ganhadores} ganhador(es) entre {len(tickets)} tickets")
    
    with st.spinner("Sorteando... \U0001f3b2"):
        try:
            # Pequeno delay para dar um efeito visual
            time.sleep(1.1)
            
            # Verifica se há tickets suficientes para o sorteio
            if len(tickets) < num_ganhadores:
                error_msg = f"Número insuficiente de tickets únicos ({len(tickets)}) para sortear {num_ganhadores} ganhadores"
                logger.error(error_msg)
                st.error(f"\u274C {error_msg}. Por favor, verifique os dados de entrada e tente novamente.")
                st.stop()
                
            # Executa o sorteio
            if permite_repeticao:
                winners = [random.choice(tickets) for _ in range(num_ganhadores)]
            else:
                winners = random.sample(tickets, k=num_ganhadores)
            logger.info("Sorteio concluído com sucesso!")
            
            # Log dos vencedores (sem expor dados sensíveis em produção)
            for i, (num, nome) in enumerate(winners, 1):
                logger.info(f"Ganhador {i}: Número {num} - {nome}")
                
        except ValueError as ve:
            error_msg = f"Erro de valor durante o sorteio: {str(ve)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            st.error(f"\u274C {error_msg}. Verifique se existem tickets suficientes e tente novamente.")
            st.stop()
            
        except Exception as e:
            error_msg = f"Erro inesperado durante o sorteio: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            st.error(error_msg)
            st.stop()
    
    st.markdown("---")
    st.markdown("## \U0001f389 Resultado do Sorteio")
    
    st.balloons()
    st.success(f"## \U0001f3c6 {num_ganhadores} Ganhadores do Prêmio: {premio}")
    
    # Título do prêmio
    st.markdown(f"""
    <div class="prize-title">
        &#127942; {premio} &#127942;
    </div>
    """, unsafe_allow_html=True)
    
    # Exibe os vencedores em cards
    if num_ganhadores == 1:
        # Layout para único vencedor
        num_ganhador, nome_ganhador = winners[0]
        st.markdown("""
        <div style="text-align: center; margin: 20px 0 40px;">
            <h1 style="color: #2E7D32; font-size: 2.2rem; margin-bottom: 30px;">
                &#127881; Parabéns ao vencedor! &#127881;
            </h1>
            <div class="winner-card-custom" style="max-width: 500px; margin: 0 auto;">
                <div class="position-badge">1º</div>
                <div class="winner-name-custom">{}</div>
                <div class="winner-number-custom">Número da Sorte: <strong>{}</strong></div>
                <div style="margin-top: 15px; color: #757575; font-size: 1rem;">
                    Entre em contato para receber seu prêmio!
                </div>
            </div>
        </div>
        """.format(nome_ganhador, num_ganhador), unsafe_allow_html=True)
        
        # Mostra os dados completos do ganhador
        st.markdown("### Dados do Ganhador:")
        ganhador_df = df[df['Número'] == num_ganhador]
        if not ganhador_df.empty:
            dados_ganhador = ganhador_df.iloc[0].to_dict()
            for chave, valor in dados_ganhador.items():
                st.text(f"{chave}: {valor}")
        else:
            st.warning("\u26A0\uFE0F Dados adicionais do ganhador não encontrados.")
            st.json({"Número": num_ganhador, "Nome": nome_ganhador})
    else:
        # Layout para múltiplos vencedores
        st.markdown("""
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #2E7D32; font-size: 2.2rem;">
                &#x1F973; Parabéns aos vencedores! &#x1F973;&#x1F973;
            </h1>
        </div>
        """, unsafe_allow_html=True)
        
        # Cria colunas responsivas
        cols = st.columns(min(3, num_ganhadores) or 1)
        
        for i, (num, nome) in enumerate(winners, 1):
            with cols[(i-1) % len(cols)]:
                # Cores diferentes para as medalhas
                position_colors = {
                    1: ("#FFD700", "\U0001f947"),  # Ouro
                    2: ("#C0C0C0", "\U0001f948"),  # Prata
                    3: ("#CD7F32", "\U0001f949")    # Bronze
                }
                color, medal = position_colors.get(i, ("#4CAF50", "\U0001f3c5"))
                
                st.markdown(f"""
                <div class="winner-card-custom" style="border-left-color: {color}; margin-bottom: 30px;">
                    <div class="position-badge" style="background: {color}">{i}º</div>
                    <div style="font-size: 2.5rem; margin: 10px 0;">{medal}</div>
                    <div class="winner-name-custom">{nome}</div>
                    <div class="winner-number-custom">Nº: <strong>{num}</strong></div>
                </div>
                """, unsafe_allow_html=True)
                
                # Mostra os dados completos do ganhador
                st.markdown("**Dados do Ganhador:**")
                ganhador_df = df[df['Número'] == num]
                if not ganhador_df.empty:
                    dados_ganhador = ganhador_df.iloc[0].to_dict()
                    for chave, valor in dados_ganhador.items():
                        st.text(f"{chave}: {valor}")
                else:
                    st.warning("\u26A0\uFE0F Dados adicionais não encontrados.")
                    st.json({"Número": num, "Nome": nome})
    
    # Adiciona botão para copiar resultados
    st.markdown("---")
    st.markdown("### \U0001f4cb Copiar Resultados")
    if st.button("\U0001f4cb Copiar para a Área de Transferência", key="btn_copiar"):
        if num_ganhadores == 1:
            num_ganhador, nome_ganhador = winners[0]
            texto = f"Vencedor do Prêmio: {premio}\n"
            texto += f"Número Sorteado: {num_ganhador}\n"
            texto += f"Nome: {nome_ganhador}"
        else:
            texto = f"Resultado do Sorteio: {premio}\n\n"
            for i, (num, nome) in enumerate(winners, 1):
                texto += f"{i}º Lugar - Nº {num}: {nome}\n"
        
        pyperclip.copy(texto)
        st.success("\u2705 Resultados copiados para a área de transferência!")
    
    # Rodapé com botão de compartilhamento
    st.markdown("""
    <div style="text-align: center; margin: 40px 0 20px;">
        <a href="https://wa.me/?text=Confira%20os%20vencedores%20do%20sorteio%20{premio_encoded}%20&#127881;" 
           class="share-button" 
           target="_blank" 
           rel="noopener noreferrer">
            &#128241; Compartilhar no WhatsApp
        </a>
    </div>
    """.format(premio_encoded=urllib.parse.quote(f"{premio} - ")), unsafe_allow_html=True)
    
    # Adiciona um pouco de espaço
    st.markdown("<div style='margin: 30px 0;'></div>", unsafe_allow_html=True)
    
    # Exibe a lista completa de participantes (opcional)
    with st.expander(f"\U0001f4cb Ver todos os {len(tickets)} tickets participantes"):
        df_tickets = pd.DataFrame(tickets, columns=["Número", "Nome"])
        st.dataframe(df_tickets.sort_values(by="Número").reset_index(drop=True), use_container_width=True)
    
    logger.info("Exibição dos resultados concluída")

# -------------------------
# Rodapé
# -------------------------
st.markdown('<div style="margin-top:2rem; color:#9aa6c0;">Desenvolvido com \u2764\uFE0F — Envie CSV/Excel ou preencha manualmente. Qualquer dúvida me chama.</div>', unsafe_allow_html=True)