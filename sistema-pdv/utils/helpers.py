"""
Módulo com funções auxiliares para o sistema PDV.
"""
import re
import locale
import unicodedata
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import os

# Importa o logger
from .logger import logger

# Configura a localização para pt_BR
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

def format_currency(value: Union[float, int, str]) -> str:
    """
    Formata um valor numérico como moeda brasileira (R$).
    
    Args:
        value: Valor numérico a ser formatado
        
    Returns:
        String formatada como moeda (ex: 'R$ 1.234,56')
    """
    try:
        if value is None:
            return 'R$ 0,00'
            
        # Converte para float se for string
        if isinstance(value, str):
            # Remove caracteres não numéricos, exceto vírgula e ponto
            value = re.sub(r'[^0-9.,]', '', value)
            # Substitui vírgula por ponto para conversão
            value = value.replace('.', '').replace(',', '.')
        
        value = float(value)
        return f'R$ {value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError) as e:
        logger.warning(f"Erro ao formatar valor monetário '{value}': {e}")
        return 'R$ 0,00'

def parse_currency(currency_str: str) -> float:
    """
    Converte uma string de moeda para float.
    
    Args:
        currency_str: String no formato 'R$ 1.234,56'
        
    Returns:
        Valor numérico (float)
    """
    if not currency_str:
        return 0.0
        
    try:
        # Remove caracteres não numéricos, exceto vírgula e ponto
        value = re.sub(r'[^0-9,]', '', currency_str)
        # Substitui vírgula por ponto
        value = value.replace('.', '').replace(',', '.')
        return float(value) if value else 0.0
    except (ValueError, TypeError) as e:
        logger.warning(f"Erro ao converter valor monetário '{currency_str}': {e}")
        return 0.0

def format_date(date_obj: Union[date, datetime, str], fmt: str = '%d/%m/%Y') -> str:
    """
    Formata uma data para string.
    
    Args:
        date_obj: Objeto date/datetime ou string de data
        fmt: Formato de saída (padrão: 'dd/mm/aaaa')
        
    Returns:
        String formatada
    """
    if not date_obj:
        return ''
        
    try:
        if isinstance(date_obj, str):
            # Tenta converter a string para datetime
            for date_fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y'):
                try:
                    date_obj = datetime.strptime(date_obj, date_fmt)
                    break
                except ValueError:
                    continue
                    
        if isinstance(date_obj, (date, datetime)):
            return date_obj.strftime(fmt)
            
        return str(date_obj)
    except Exception as e:
        logger.warning(f"Erro ao formatar data '{date_obj}': {e}")
        return str(date_obj) if date_obj else ''

def parse_date(date_str: str, fmt: str = '%d/%m/%Y') -> Optional[date]:
    """
    Converte uma string de data para objeto date.
    
    Args:
        date_str: String de data
        fmt: Formato de entrada (padrão: 'dd/mm/aaaa')
        
    Returns:
        Objeto date ou None se não for possível converter
    """
    if not date_str:
        return None
        
    try:
        return datetime.strptime(date_str, fmt).date()
    except (ValueError, TypeError) as e:
        logger.warning(f"Erro ao converter data '{date_str}': {e}")
        return None

def format_cpf(cpf: str) -> str:
    """
    Formata um CPF no formato 000.000.000-00.
    
    Args:
        cpf: String com o CPF (apenas números)
        
    Returns:
        CPF formatado
    """
    if not cpf:
        return ''
        
    # Remove caracteres não numéricos
    cpf = re.sub(r'[^0-9]', '', str(cpf))
    
    # Verifica se tem 11 dígitos
    if len(cpf) != 11:
        return cpf  # Retorna sem formatação se não for um CPF válido
    
    # Formata o CPF
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

def validate_cpf(cpf: str) -> bool:
    """
    Valida um CPF.
    
    Args:
        cpf: String com o CPF (com ou sem formatação)
        
    Returns:
        True se o CPF for válido, False caso contrário
    """
    # Remove caracteres não numéricos
    cpf = re.sub(r'[^0-9]', '', str(cpf))
    
    # Verifica se tem 11 dígitos e não é uma sequência repetida
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    
    # Calcula o primeiro dígito verificador
    total = 0
    for i in range(9):
        total += int(cpf[i]) * (10 - i)
    resto = 11 - (total % 11)
    if resto > 9:
        resto = 0
    if resto != int(cpf[9]):
        return False
    
    # Calcula o segundo dígito verificador
    total = 0
    for i in range(10):
        total += int(cpf[i]) * (11 - i)
    resto = 11 - (total % 11)
    if resto > 9:
        resto = 0
    if resto != int(cpf[10]):
        return False
    
    return True

def format_phone(phone: str) -> str:
    """
    Formata um número de telefone no padrão brasileiro.
    
    Args:
        phone: String com o telefone (apenas números)
        
    Returns:
        Telefone formatado
    """
    if not phone:
        return ''
        
    # Remove caracteres não numéricos
    phone = re.sub(r'[^0-9]', '', str(phone))
    
    # Formatação baseada no tamanho
    if len(phone) == 11:  # Celular com DDD
        return f"({phone[:2]}) {phone[2]} {phone[3:7]}-{phone[7:]}"
    elif len(phone) == 10:  # Fixo com DDD
        return f"({phone[:2]}) {phone[2:6]}-{phone[6:]}"
    elif len(phone) == 9:  # Celular sem DDD
        return f"{phone[0]} {phone[1:5]}-{phone[5:]}"
    elif len(phone) == 8:  # Fixo sem DDD
        return f"{phone[:4]}-{phone[4:]}"
    else:
        return phone

def validate_email(email: str) -> bool:
    """
    Valida um endereço de email.
    
    Args:
        email: String com o email a ser validado
        
    Returns:
        True se o email for válido, False caso contrário
    """
    if not email:
        return False
        
    # Expressão regular para validar email
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def remove_accents(text: str) -> str:
    """
    Remove acentos de uma string.
    
    Args:
        text: Texto com acentos
        
    Returns:
        Texto sem acentos
    """
    if not text:
        return ''
    
    # Normaliza a string para a forma NFD (Decomposição de Diacríticos)
    text = unicodedata.normalize('NFD', str(text))
    
    # Remove os caracteres de acentuação
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    
    return text

def get_week_dates() -> Tuple[date, date]:
    """
    Retorna as datas de início e fim da semana atual.
    
    Returns:
        Tupla com (data_inicio, data_fim) da semana atual
    """
    today = date.today()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start, end

def get_month_dates() -> Tuple[date, date]:
    """
    Retorna as datas de início e fim do mês atual.
    
    Returns:
        Tupla com (primeiro_dia, ultimo_dia) do mês atual
    """
    today = date.today()
    first_day = date(today.year, today.month, 1)
    
    if today.month == 12:
        last_day = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(today.year, today.month + 1, 1) - timedelta(days=1)
    
    return first_day, last_day

def generate_random_string(length: int = 8) -> str:
    """
    Gera uma string aleatória com letras e números.
    
    Args:
        length: Tamanho da string desejada
        
    Returns:
        String aleatória
    """
    import random
    import string
    
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def load_json_file(file_path: str) -> Any:
    """
    Carrega dados de um arquivo JSON.
    
    Args:
        file_path: Caminho para o arquivo JSON
        
    Returns:
        Dados carregados do JSON
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erro ao carregar arquivo JSON {file_path}: {e}")
        return None

def save_json_file(data: Any, file_path: str) -> bool:
    """
    Salva dados em um arquivo JSON.
    
    Args:
        data: Dados a serem salvos
        file_path: Caminho para salvar o arquivo JSON
        
    Returns:
        True se salvou com sucesso, False caso contrário
    """
    try:
        # Cria o diretório se não existir
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar arquivo JSON {file_path}: {e}")
        return False

# Testes unitários
if __name__ == "__main__":
    # Teste de formatação de moeda
    print(f"Formatação de moeda: {format_currency(1234.56)}")
    print(f"Conversão de moeda: {parse_currency('R$ 1.234,56')}")
    
    # Teste de formatação de data
    today = date.today()
    print(f"Data formatada: {format_date(today)}")
    print(f"Data convertida: {parse_date('31/12/2023')}")
    
    # Teste de CPF
    cpf = '12345678909'
    print(f"CPF formatado: {format_cpf(cpf)}")
    print(f"CPF válido? {validate_cpf(cpf)}")
    
    # Teste de telefone
    print(f"Telefone formatado: {format_phone('11999998888')}")
    
    # Teste de email
    print(f"Email válido? {validate_email('teste@exemplo.com')}")
    
    # Teste de remoção de acentos
    print(f"Sem acentos: {remove_accents('Café São João')}")
