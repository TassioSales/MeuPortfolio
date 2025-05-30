"""
Funções auxiliares para formatação de dados.
"""
from typing import Any, Optional, Union
from datetime import datetime

def formatar_moeda(
    valor: Optional[Union[float, int, str]], 
    moeda: str = 'R$', 
    casas_decimais: int = 2
) -> str:
    """
    Formata um valor numérico como moeda.
    
    Args:
        valor: Valor a ser formatado
        moeda: Símbolo da moeda (padrão: 'R$')
        casas_decimais: Número de casas decimais (padrão: 2)
        
    Returns:
        str: Valor formatado como moeda
    """
    if valor is None:
        return f"{moeda} --"
    
    try:
        # Converte para float, independentemente do tipo de entrada
        valor_float = float(valor)
        
        # Formata o valor com separadores de milhar e casas decimais
        valor_formatado = f"{valor_float:,.{casas_decimais}f}"
        
        # Substitui pontos por X, vírgulas por pontos e X por vírgulas
        valor_formatado = valor_formatado.replace(".", "X").replace(",", ".").replace("X", ",")
        
        return f"{moeda} {valor_formatado}"
    except (ValueError, TypeError):
        return f"{moeda} --"

def formatar_percentual(
    valor: Optional[Union[float, int, str]], 
    casas_decimais: int = 2, 
    incluir_simbolo: bool = True
) -> str:
    """
    Formata um valor como percentual.
    
    Args:
        valor: Valor a ser formatado (ex: 0.05 para 5%)
        casas_decimais: Número de casas decimais (padrão: 2)
        incluir_simbolo: Se True, inclui o símbolo de % (padrão: True)
        
    Returns:
        str: Valor formatado como percentual
    """
    if valor is None:
        return "--%" if incluir_simbolo else "--"
    
    try:
        # Converte para float e multiplica por 100 para obter a porcentagem
        valor_float = float(valor) * 100
        
        # Formata o valor com o número especificado de casas decimais
        format_str = f"%.{casas_decimais}f"
        valor_formatado = format_str % valor_float
        
        # Substitui ponto por vírgula, se necessário
        if ',' in valor_formatado or '.' in valor_formatado:
            valor_formatado = valor_formatado.replace('.', 'X').replace(',', '.').replace('X', ',')
        
        return f"{valor_formatado}%" if incluir_simbolo else valor_formatado
    except (ValueError, TypeError):
        return "--%" if incluir_simbolo else "--"

def formatar_data(
    data: Union[str, datetime], 
    formato_entrada: str = '%Y-%m-%d', 
    formato_saida: str = '%d/%m/%Y'
) -> str:
    """
    Formata uma data de um formato para outro.
    
    Args:
        data: Data a ser formatada (string ou objeto datetime)
        formato_entrada: Formato da data de entrada (padrão: 'YYYY-MM-DD')
        formato_saida: Formato de saída desejado (padrão: 'DD/MM/YYYY')
        
    Returns:
        str: Data formatada
    """
    if not data:
        return "--/--/----"
        
    try:
        if isinstance(data, str):
            data_obj = datetime.strptime(data, formato_entrada)
        else:
            data_obj = data
            
        return data_obj.strftime(formato_saida)
    except (ValueError, TypeError):
        return "--/--/----"

def formatar_quantidade(
    valor: Optional[Union[float, int, str]], 
    casas_decimais: int = 2
) -> str:
    """
    Formata um valor numérico como quantidade.
    
    Args:
        valor: Valor a ser formatado
        casas_decimais: Número de casas decimais (padrão: 2)
        
    Returns:
        str: Valor formatado
    """
    if valor is None:
        return "--"
    
    try:
        valor_float = float(valor)
        
        # Formata o valor com separadores de milhar e casas decimais
        valor_formatado = f"{valor_float:,.{casas_decimais}f}"
        
        # Substitui pontos por X, vírgulas por pontos e X por vírgulas
        valor_formatado = valor_formatado.replace(".", "X").replace(",", ".").replace("X", ",")
        
        return valor_formatado
    except (ValueError, TypeError):
        return "--"

def formatar_dados_mercado(dados: dict) -> dict:
    """
    Formata os dados de mercado para exibição.
    
    Args:
        dados: Dicionário com os dados de mercado
        
    Returns:
        dict: Dicionário com os dados formatados
    """
    if not dados:
        return {}
    
    formatados = {}
    
    for chave, valor in dados.items():
        if valor is None:
            formatados[chave] = "--"
        elif isinstance(valor, (int, float)):
            # Para valores monetários
            if chave in ['marketCap', 'valorDeMercado', 'fiftyTwoWeekHigh', 
                        'fiftyTwoWeekLow', 'regularMarketPrice', 'currentPrice']:
                formatados[chave] = formatar_moeda(valor)
            # Para percentuais
            elif chave in ['dividendYield', 'regularMarketChangePercent']:
                formatados[chave] = formatar_percentual(valor / 100 if valor > 1 else valor)
            # Para quantidades
            else:
                formatados[chave] = formatar_quantidade(valor)
        else:
            formatados[chave] = str(valor)
    
    return formatados
