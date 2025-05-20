def format_currency(value):
    """Formata um valor numérico para moeda brasileira."""
    try:
        # Converte para float se for string
        if isinstance(value, str):
            value = float(value.replace(',', '.'))
        
        # Formata com separador de milhar e duas casas decimais
        # Primeiro converte para string com ponto como separador decimal
        formatted = f"{value:,.2f}"
        # Substitui a vírgula por ponto e o ponto por vírgula
        formatted = formatted.replace(',', 'V').replace('.', ',').replace('V', '.')
        return formatted
    except (ValueError, TypeError):
        return "0,00"
