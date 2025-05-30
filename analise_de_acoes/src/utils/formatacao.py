"""
Módulo para formatação de valores monetários, porcentagens e números.
"""
from typing import Union, Optional
from decimal import Decimal, ROUND_HALF_UP

def format_currency(value: Union[float, int, str, Decimal], currency: str = 'R$', 
                     decimal_places: int = 2, show_plus: bool = False) -> str:
    """
    Formata um valor como moeda.
    
    Args:
        value: Valor a ser formatado (pode ser float, int, str ou Decimal)
        currency: Símbolo da moeda (padrão: 'R$')
        decimal_places: Número de casas decimais (padrão: 2)
        show_plus: Se True, mostra o sinal de + para valores positivos
        
    Returns:
        str: Valor formatado como moeda
    """
    try:
        # Converte para Decimal para evitar problemas de ponto flutuante
        if isinstance(value, str):
            # Remove caracteres não numéricos, exceto o sinal de menos e ponto decimal
            cleaned = ''.join(c for c in value if c.isdigit() or c in '-,.')
            # Substitui vírgula por ponto para o Decimal
            cleaned = cleaned.replace(',', '.')
            # Remove múltiplos pontos decimais
            if cleaned.count('.') > 1:
                cleaned = cleaned.replace('.', '', cleaned.count('.') - 1)
            value = Decimal(cleaned)
        else:
            value = Decimal(str(value))
            
        # Arredonda o valor
        value = value.quantize(
            Decimal('0.' + '0' * decimal_places), 
            rounding=ROUND_HALF_UP
        )
        
        # Formata o valor com separadores de milhar e casas decimais
        formatted = f"{value:,.{decimal_places}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        # Adiciona o sinal, se necessário
        if value >= 0 and show_plus:
            sign = "+"
        elif value < 0:
            sign = "-"
            formatted = formatted.lstrip("-")
        else:
            sign = ""
            
        return f"{sign}{currency} {formatted}"
        
    except (ValueError, TypeError, ArithmeticError):
        return f"{currency} 0,{''.join(['0'] * decimal_places)}"

def format_percentage(value: Union[float, int, str, Decimal], 
                      decimal_places: int = 2, 
                      show_plus: bool = True) -> str:
    """
    Formata um valor como porcentagem.
    
    Args:
        value: Valor a ser formatado (pode ser float, int, str ou Decimal)
        decimal_places: Número de casas decimais (padrão: 2)
        show_plus: Se True, mostra o sinal de + para valores positivos
        
    Returns:
        str: Valor formatado como porcentagem
    """
    try:
        # Converte para Decimal
        if isinstance(value, str):
            # Remove caracteres não numéricos, exceto o sinal de menos e ponto decimal
            cleaned = ''.join(c for c in value if c.isdigit() or c in '-,.%')
            # Remove o símbolo de porcentagem, se existir
            cleaned = cleaned.replace('%', '')
            # Substitui vírgula por ponto para o Decimal
            cleaned = cleaned.replace(',', '.')
            # Remove múltiplos pontos decimais
            if cleaned.count('.') > 1:
                cleaned = cleaned.replace('.', '', cleaned.count('.') - 1)
            value = Decimal(cleaned or '0')
        else:
            value = Decimal(str(value))
        
        # Arredonda o valor
        value = value.quantize(
            Decimal('0.' + '0' * decimal_places), 
            rounding=ROUND_HALF_UP
        )
        
        # Formata o valor com separadores de milhar e casas decimais
        formatted = f"{value:,.{decimal_places}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        # Adiciona o sinal, se necessário
        if value > 0 and show_plus:
            sign = "+"
        elif value < 0:
            sign = "-"
            formatted = formatted.lstrip("-")
        else:
            sign = ""
            
        return f"{sign}{formatted}%"
        
    except (ValueError, TypeError, ArithmeticError):
        return f"0,{''.join(['0'] * decimal_places)}%"

def format_number(value: Union[float, int, str, Decimal], 
                  decimal_places: int = 2, 
                  decimal_separator: str = ',',
                  thousand_separator: str = '.',
                  show_plus: bool = False) -> str:
    """
    Formata um número com separadores de milhar e casas decimais.
    
    Args:
        value: Valor a ser formatado (pode ser float, int, str ou Decimal)
        decimal_places: Número de casas decimais (padrão: 2)
        decimal_separator: Separador decimal (padrão: ',')
        thousand_separator: Separador de milhar (padrão: '.')
        show_plus: Se True, mostra o sinal de + para valores positivos
        
    Returns:
        str: Número formatado
    """
    try:
        # Converte para Decimal
        if isinstance(value, str):
            # Remove caracteres não numéricos, exceto o sinal de menos e ponto decimal
            cleaned = ''.join(c for c in value if c.isdigit() or c in '-,.')
            # Substitui vírgula por ponto para o Decimal
            cleaned = cleaned.replace(',', '.')
            # Remove múltiplos pontos decimais
            if cleaned.count('.') > 1:
                cleaned = cleaned.replace('.', '', cleaned.count('.') - 1)
            value = Decimal(cleaned or '0')
        else:
            value = Decimal(str(value))
        
        # Arredonda o valor
        value = value.quantize(
            Decimal('0.' + '0' * decimal_places), 
            rounding=ROUND_HALF_UP
        )
        
        # Formata o valor com separadores de milhar e casas decimais
        formatted = f"{value:,.{decimal_places}f}"
        
        # Aplica os separadores personalizados
        if decimal_separator != '.':
            formatted = formatted.replace('.', 'X').replace(',', thousand_separator).replace('X', decimal_separator)
        else:
            formatted = formatted.replace(',', thousand_separator)
        
        # Adiciona o sinal, se necessário
        if value > 0 and show_plus:
            sign = "+"
        elif value < 0:
            sign = "-"
            formatted = formatted.lstrip("-")
        else:
            sign = ""
            
        return f"{sign}{formatted}"
        
    except (ValueError, TypeError, ArithmeticError):
        return f"0{decimal_separator}{''.join(['0'] * decimal_places)}"

# Funções auxiliares para os templates
def format_brl(value: Union[float, int, str, Decimal], decimal_places: int = 2) -> str:
    """Formata um valor como moeda brasileira (R$)."""
    return format_currency(value, 'R$', decimal_places)

def format_usd(value: Union[float, int, str, Decimal], decimal_places: int = 2) -> str:
    """Formata um valor como dólar americano (US$)."""
    return format_currency(value, 'US$', decimal_places)

def format_eur(value: Union[float, int, str, Decimal], decimal_places: int = 2) -> str:
    """Formata um valor como euro (€)."""
    return format_currency(value, '€', decimal_places)

def format_btc(value: Union[float, int, str, Decimal], decimal_places: int = 8) -> str:
    """Formata um valor como Bitcoin (₿)."""
    return format_currency(value, '₿', decimal_places, show_plus=False)

# Adiciona as funções ao contexto global do Jinja2
def init_app(app):
    """Registra os filtros no aplicativo Flask."""
    app.jinja_env.filters['brl'] = format_brl
    app.jinja_env.filters['usd'] = format_usd
    app.jinja_env.filters['eur'] = format_eur
    app.jinja_env.filters['btc'] = format_btc
    app.jinja_env.filters['pct'] = format_percentage
    app.jinja_env.filters['num'] = format_number
