"""
Funções de validação para o Gerenciador de Ativos.
"""
import re
from typing import Optional, Union, Tuple, Dict, Any
from datetime import datetime
from src.utils.logger import get_logger

logger = get_logger(__name__)

def validar_ticker(ticker: str) -> Tuple[bool, str]:
    """
    Valida o formato de um ticker.
    
    Args:
        ticker: Código do ativo a ser validado
        
    Returns:
        Tuple[bool, str]: (True, '') se válido, (False, mensagem_de_erro) caso contrário
    """
    if not ticker or not isinstance(ticker, str) or not ticker.strip():
        return False, "O ticker não pode estar vazio."
    
    # Remove espaços em branco e converte para maiúsculas
    ticker = ticker.strip().upper()
    
    # Expressão regular para validar o formato do ticker
    # Aceita letras, números, pontos, hífens e o sufixo .SA (opcional)
    padrao = r'^[A-Z0-9.-]+(\.[A-Z]{1,3})?$'
    
    if not re.match(padrao, ticker):
        return False, "Formato de ticker inválido. Use apenas letras, números, pontos e hífens."
    
    # Verifica se tem pelo menos 2 caracteres
    if len(ticker.replace('.SA', '').replace('.', '')) < 2:
        return False, "O ticker deve ter pelo menos 2 caracteres."
    
    # Verifica se começa com letra
    if not ticker[0].isalpha():
        return False, "O ticker deve começar com uma letra."
    
    return True, ""

def validar_valor(
    valor: Union[str, int, float], 
    minimo: float = 0, 
    maximo: Optional[float] = None
) -> Tuple[bool, str]:
    """
    Valida um valor numérico.
    
    Args:
        valor: Valor a ser validado (pode ser string, int ou float)
        minimo: Valor mínimo permitido (inclusive)
        maximo: Valor máximo permitido (inclusive, opcional)
        
    Returns:
        Tuple[bool, str]: (True, valor_convertido) se válido, (False, mensagem_de_erro) caso contrário
    """
    if valor is None:
        return False, "O valor não pode ser vazio."
    
    # Tenta converter para float
    try:
        valor_float = float(str(valor).replace(',', '.'))
    except (ValueError, TypeError):
        return False, "Valor inválido. Informe um número."
    
    # Verifica valor mínimo
    if valor_float < minimo:
        return False, f"O valor deve ser maior ou igual a {minimo}."
    
    # Verifica valor máximo, se especificado
    if maximo is not None and valor_float > maximo:
        return False, f"O valor deve ser menor ou igual a {maximo}."
    
    return True, valor_float

def validar_data(
    data: str, 
    formato: str = '%d/%m/%Y',
    data_minima: Optional[datetime] = None,
    data_maxima: Optional[datetime] = None
) -> Tuple[bool, Union[str, datetime]]:
    """
    Valida uma data no formato especificado.
    
    Args:
        data: Data no formato de string
        formato: Formato da data (padrão: 'DD/MM/AAAA')
        data_minima: Data mínima permitida (opcional)
        data_maxima: Data máxima permitida (opcional)
        
    Returns:
        Tuple[bool, Union[str, datetime]]: (True, data_convertida) se válido, (False, mensagem_de_erro) caso contrário
    """
    if not data or not isinstance(data, str):
        return False, "A data não pode estar vazia."
    
    try:
        data_obj = datetime.strptime(data.strip(), formato)
        
        # Verifica data mínima
        if data_minima is not None and data_obj < data_minima:
            return False, f"A data deve ser posterior a {data_minima.strftime(formato)}."
        
        # Verifica data máxima (geralmente não pode ser no futuro)
        if data_maxima is not None and data_obj > data_maxima:
            return False, f"A data deve ser anterior a {data_maxima.strftime(formato)}."
        
        return True, data_obj
    except ValueError:
        return False, f"Formato de data inválido. Use o formato {formato}."

def validar_campos_obrigatorios(
    dados: Dict[str, Any], 
    campos_obrigatorios: list
) -> Tuple[bool, str]:
    """
    Valida se todos os campos obrigatórios estão presentes no dicionário de dados.
    
    Args:
        dados: Dicionário com os dados a serem validados
        campos_obrigatorios: Lista de chaves que são obrigatórias
        
    Returns:
        Tuple[bool, str]: (True, '') se todos os campos estiverem presentes, 
                         (False, mensagem_de_erro) caso contrário
    """
    if not dados or not isinstance(dados, dict):
        return False, "Nenhum dado fornecido para validação."
    
    campos_faltantes = [campo for campo in campos_obrigatorios if campo not in dados or dados[campo] is None]
    
    if campos_faltantes:
        return False, f"Campos obrigatórios faltando: {', '.join(campos_faltantes)}"
    
    return True, ""

def validar_tipo_ativo(tipo: str, tipos_validos: list = None) -> Tuple[bool, str]:
    """
    Valida se o tipo de ativo está na lista de tipos válidos.
    
    Args:
        tipo: Tipo de ativo a ser validado
        tipos_validos: Lista de tipos válidos (se None, usa uma lista padrão)
        
    Returns:
        Tuple[bool, str]: (True, '') se válido, (False, mensagem_de_erro) caso contrário
    """
    if tipos_validos is None:
        tipos_validos = [
            'Ação', 'FII', 'ETF', 'BDR', 'Criptomoeda', 'Opção', 'Futuro', 
            'Renda Fixa', 'Tesouro Direto', 'Fundos', 'Outros'
        ]
    
    if not tipo or not isinstance(tipo, str):
        return False, "O tipo de ativo não pode estar vazio."
    
    if tipo not in tipos_validos:
        return False, f"Tipo de ativo inválido. Tipos válidos: {', '.join(tipos_validos)}"
    
    return True, ""

def validar_quantidade(quantidade: Union[str, int, float]) -> Tuple[bool, Union[str, float]]:
    """
    Valida uma quantidade de ativos.
    
    Args:
        quantidade: Quantidade a ser validada
        
    Returns:
        Tuple[bool, Union[str, float]]: (True, quantidade_convertida) se válido, 
                                      (False, mensagem_de_erro) caso contrário
    """
    return validar_valor(quantidade, minimo=0.00000001, maximo=1000000000)
