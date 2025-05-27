from datetime import datetime

def format_datetime(value, format='%d/%m/%Y %H:%M'):
    """Formata um objeto datetime para string.
    
    Args:
        value: Valor a ser formatado (pode ser string, datetime ou None)
        format: Formato de saída (padrão: 'dd/mm/aaaa HH:MM')
        
    Returns:
        str: Data formatada ou 'N/A' se o valor for inválido
    """
    if not value:
        return 'N/A'
        
    # Se for string, tenta converter para datetime
    if isinstance(value, str):
        try:
            # Tenta converter de string ISO
            if 'T' in value:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            # Tenta converter de formato SQLite
            else:
                try:
                    value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    value = datetime.strptime(value, '%Y-%m-%d')
        except (ValueError, TypeError):
            return str(value)  # Retorna a string original se não conseguir converter
    
    # Se for datetime, formata
    if hasattr(value, 'strftime'):
        try:
            return value.strftime(format)
        except (ValueError, TypeError):
            return 'N/A'
    
    return str(value)

def format_currency(value, symbol='R$'):
    """Formata um valor monetário.
    
    Args:
        value: Valor a ser formatado
        symbol: Símbolo da moeda (padrão: 'R$')
        
    Returns:
        str: Valor formatado com o símbolo e 2 casas decimais
    """
    if value is None:
        return 'N/A'
    try:
        return f"{symbol} {float(value):.2f}"
    except (ValueError, TypeError):
        return str(value)
