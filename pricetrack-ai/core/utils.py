"""
Funções Auxiliares e Utilitários para PriceTrack AI
Validações, helpers e funcionalidades de suporte
"""

import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
import streamlit as st
from core.logger import get_logger, log_user_action
from core.models import Product

logger = get_logger(__name__)


class ValidationError(Exception):
    """Exceção para erros de validação"""
    pass


def validate_price(price: Union[str, float, int]) -> float:
    """
    Valida e converte preço para float
    
    Args:
        price: Preço em string, float ou int
        
    Returns:
        Preço como float
        
    Raises:
        ValidationError: Se preço for inválido
    """
    try:
        if isinstance(price, str):
            # Remover caracteres não numéricos exceto ponto e vírgula
            cleaned = re.sub(r'[^\d,.]', '', price)
            # Substituir vírgula por ponto se necessário
            cleaned = cleaned.replace(',', '.')
            price_float = float(cleaned)
        else:
            price_float = float(price)
        
        if price_float <= 0:
            raise ValidationError("Preço deve ser maior que zero")
        
        if price_float > 1000000:  # Limite razoável
            raise ValidationError("Preço muito alto (máximo R$ 1.000.000)")
        
        logger.info(f"Preço validado: R$ {price_float:.2f}")
        log_user_action(logger, "price_validation", f"Preço validado: R$ {price_float:.2f}")
        return price_float
        
    except (ValueError, TypeError) as e:
        logger.error(f"Erro na validação de preço '{price}': {str(e)}")
        raise ValidationError(f"Preço inválido: {price}")


def validate_product_name(name: str) -> str:
    """
    Valida nome do produto
    
    Args:
        name: Nome do produto
        
    Returns:
        Nome validado e limpo
        
    Raises:
        ValidationError: Se nome for inválido
    """
    if not name or not name.strip():
        raise ValidationError("Nome do produto é obrigatório")
    
    cleaned_name = name.strip()
    
    if len(cleaned_name) < 2:
        raise ValidationError("Nome deve ter pelo menos 2 caracteres")
    
    if len(cleaned_name) > 255:
        raise ValidationError("Nome muito longo (máximo 255 caracteres)")
    
    # Verificar caracteres especiais perigosos
    dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')']
    if any(char in cleaned_name for char in dangerous_chars):
        logger.warning(f"Nome contém caracteres especiais: {cleaned_name}")
    
    logger.info(f"Nome de produto validado: {cleaned_name}")
    return cleaned_name


def validate_email(email: str) -> bool:
    """
    Valida formato de email
    
    Args:
        email: Email para validar
        
    Returns:
        True se email é válido
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    is_valid = bool(re.match(pattern, email))
    
    if not is_valid:
        logger.warning(f"Email inválido: {email}")
    
    return is_valid


def format_currency(value: float, currency: str = "BRL") -> str:
    """
    Formata valor como moeda brasileira
    
    Args:
        value: Valor numérico
        currency: Código da moeda
        
    Returns:
        Valor formatado
    """
    if currency == "BRL":
        return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    else:
        return f"{currency} {value:,.2f}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Formata valor como porcentagem
    
    Args:
        value: Valor numérico (0.1 = 10%)
        decimals: Número de casas decimais
        
    Returns:
        Valor formatado como porcentagem
    """
    return f"{value:.{decimals}f}%"


def calculate_price_change(old_price: float, new_price: float) -> Dict[str, Any]:
    """
    Calcula mudança de preço
    
    Args:
        old_price: Preço anterior
        new_price: Preço atual
        
    Returns:
        Dicionário com mudança absoluta e percentual
    """
    change = new_price - old_price
    percentage = (change / old_price) * 100 if old_price > 0 else 0
    
    return {
        "change": change,
        "percentage": percentage,
        "direction": "up" if change > 0 else "down" if change < 0 else "stable"
    }


def parse_tags(tags_string: str) -> List[str]:
    """
    Converte string de tags em lista
    
    Args:
        tags_string: Tags separadas por vírgula
        
    Returns:
        Lista de tags limpas
    """
    if not tags_string:
        return []
    
    tags = [tag.strip() for tag in tags_string.split(',') if tag.strip()]
    # Remover duplicatas mantendo ordem
    unique_tags = list(dict.fromkeys(tags))
    
    logger.info(f"Tags parseadas: {unique_tags}")
    return unique_tags


def format_tags(tags_list: List[str]) -> str:
    """
    Converte lista de tags em string
    
    Args:
        tags_list: Lista de tags
        
    Returns:
        String de tags separadas por vírgula
    """
    if not tags_list:
        return ""
    
    return ", ".join(tags_list)


def get_price_trend_icon(trend_percentage: float) -> str:
    """
    Retorna ícone baseado na tendência de preço
    
    Args:
        trend_percentage: Percentual de mudança
        
    Returns:
        Emoji representando a tendência
    """
    if trend_percentage > 5:
        return "📈"  # Subindo muito
    elif trend_percentage > 0:
        return "↗️"  # Subindo pouco
    elif trend_percentage < -5:
        return "📉"  # Descendo muito
    elif trend_percentage < 0:
        return "↘️"  # Descendo pouco
    else:
        return "➡️"  # Estável


def get_recommendation_color(recommendation: str) -> str:
    """
    Retorna cor baseada na recomendação
    
    Args:
        recommendation: Tipo de recomendação
        
    Returns:
        Cor em formato CSS
    """
    colors = {
        "COMPRAR_AGORA": "#28a745",  # Verde
        "AGUARDAR": "#ffc107",       # Amarelo
        "EVITAR": "#dc3545"          # Vermelho
    }
    return colors.get(recommendation, "#6c757d")  # Cinza padrão


def send_email_alert(product: Product, reason: str, current_price: float) -> bool:
    """
    Envia alerta por email (simulação)
    
    Args:
        product: Produto do alerta
        reason: Motivo do alerta
        current_price: Preço atual
        
    Returns:
        True se email foi enviado com sucesso
    """
    try:
        # Verificar se credenciais SMTP estão disponíveis
        smtp_server = st.secrets.get("SMTP_SERVER")
        smtp_user = st.secrets.get("SMTP_USER")
        smtp_password = st.secrets.get("SMTP_PASSWORD")
        
        if not all([smtp_server, smtp_user, smtp_password]):
            logger.info("Credenciais SMTP não configuradas, simulando envio de email")
            return True  # Simular sucesso
        
        # Configurar email
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = smtp_user  # Auto-envio para demonstração
        msg['Subject'] = f"🚨 Alerta de Preço - {product.product_name}"
        
        # Corpo do email
        body = f"""
        Olá!
        
        Seu alerta de preço foi ativado!
        
        📦 Produto: {product.product_name}
        💰 Preço Atual: R$ {current_price:.2f}
        🎯 Threshold: R$ {product.alert_threshold:.2f}
        💡 Motivo: {reason}
        
        Economia: R$ {product.alert_threshold - current_price:.2f}
        
        Acesse o PriceTrack AI para mais detalhes!
        
        Atenciosamente,
        Artemis - PriceTrack AI
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Enviar email
        server = smtplib.SMTP(smtp_server, st.secrets.get("SMTP_PORT", 587))
        server.starttls()
        server.login(smtp_user, smtp_password)
        
        text = msg.as_string()
        server.sendmail(smtp_user, smtp_user, text)
        server.quit()
        
        logger.info(f"Email de alerta enviado para produto: {product.product_name}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao enviar email de alerta: {str(e)}")
        return False


def generate_product_id() -> str:
    """
    Gera ID único para produto (para uso em session state)
    
    Returns:
        String com ID único
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"prod_{timestamp}"


def format_date_range(days: int) -> str:
    """
    Formata período de dias em texto legível
    
    Args:
        days: Número de dias
        
    Returns:
        String formatada
    """
    if days == 1:
        return "último dia"
    elif days == 7:
        return "última semana"
    elif days == 30:
        return "último mês"
    elif days == 90:
        return "últimos 3 meses"
    else:
        return f"últimos {days} dias"


def calculate_savings_percentage(original_price: float, current_price: float) -> float:
    """
    Calcula percentual de economia
    
    Args:
        original_price: Preço original
        current_price: Preço atual
        
    Returns:
        Percentual de economia (positivo = economia)
    """
    if original_price <= 0:
        return 0
    
    savings = ((original_price - current_price) / original_price) * 100
    return max(0, savings)  # Não retornar valores negativos


def get_rating_stars(rating: int) -> str:
    """
    Converte rating numérico em estrelas
    
    Args:
        rating: Rating de 1 a 5
        
    Returns:
        String com estrelas
    """
    if not rating or rating < 1 or rating > 5:
        return "⭐" * 0
    
    return "⭐" * rating


def validate_budget(budget: Union[str, float, int]) -> Optional[float]:
    """
    Valida orçamento do usuário
    
    Args:
        budget: Orçamento em string, float ou int
        
    Returns:
        Orçamento como float ou None se inválido
    """
    try:
        if not budget or budget == "":
            return None
        
        budget_float = validate_price(budget)
        
        if budget_float < 10:
            logger.warning(f"Orçamento muito baixo: R$ {budget_float:.2f}")
            return None
        
        return budget_float
        
    except ValidationError:
        return None


def create_price_chart_data(price_history: List[Dict]) -> Dict[str, Any]:
    """
    Prepara dados para gráfico de preços
    
    Args:
        price_history: Histórico de preços
        
    Returns:
        Dados formatados para Plotly
    """
    if not price_history:
        return {"dates": [], "prices": [], "trend": []}
    
    # Ordenar por data
    sorted_history = sorted(price_history, key=lambda x: x.get("date", ""))
    
    dates = [entry["date"] for entry in sorted_history]
    prices = [entry["price"] for entry in sorted_history]
    
    # Calcular linha de tendência simples
    if len(prices) >= 2:
        x = list(range(len(prices)))
        trend = polyfit(x, prices, 1)
        trend_line = [trend[0] * i + trend[1] for i in x]
    else:
        trend_line = prices
    
    return {
        "dates": dates,
        "prices": prices,
        "trend": trend_line
    }


def get_product_status(product: Product) -> Dict[str, Any]:
    """
    Calcula status do produto baseado em dados disponíveis
    
    Args:
        product: Produto a analisar
        
    Returns:
        Status do produto
    """
    status = {
        "has_price_history": bool(product.price_history),
        "has_tags": bool(product.tags),
        "has_alert": bool(product.alert_threshold and product.alert_threshold > 0),
        "has_rating": bool(product.user_rating),
        "completeness_score": 0
    }
    
    # Calcular score de completude
    score = 0
    if status["has_price_history"]:
        score += 30
    if status["has_tags"]:
        score += 20
    if status["has_alert"]:
        score += 25
    if status["has_rating"]:
        score += 15
    if product.product_name:
        score += 10
    
    status["completeness_score"] = score
    
    return status


def format_completeness_score(score: int) -> str:
    """
    Formata score de completude
    
    Args:
        score: Score de 0 a 100
        
    Returns:
        String formatada
    """
    if score >= 90:
        return "🟢 Completo"
    elif score >= 70:
        return "🟡 Quase completo"
    elif score >= 50:
        return "🟠 Parcialmente completo"
    else:
        return "🔴 Incompleto"


def polyfit(x, y, degree):
    """Fallback simples para polyfit"""
    if len(x) != len(y) or len(x) < 2:
        return [0, y[0] if y else 0]
    
    # Regressão linear simples
    n = len(x)
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(x[i] * y[i] for i in range(n))
    sum_x2 = sum(x[i] ** 2 for i in range(n))
    
    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
    intercept = (sum_y - slope * sum_x) / n
    
    return [slope, intercept]
