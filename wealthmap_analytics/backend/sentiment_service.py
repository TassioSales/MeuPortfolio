import feedparser
from bs4 import BeautifulSoup
import re

# Dicionários de sentimento (Português e Inglês) baseados no projeto original
POSITIVE_WORDS = [
    "alta", "avanço", "cresce", "crescimento", "melhora", "recorde", "aprova", "aprovado",
    "lucro", "ganha", "recupera", "inovação", "investimento", "expande", "supera", "reduz",
    "up", "surge", "gain", "profit", "bull", "bullish", "record", "jump", "jumped", "growth",
    "beats", "beat", "strong", "positive", "buy", "upgrade", "outperform", "soar", "soars"
]

NEGATIVE_WORDS = [
    "queda", "cai", "crise", "risco", "alerta", "prejuízo", "perda", "investigação", 
    "denúncia", "fraude", "inflação", "demissão", "corte", "bloqueio", "colapso",
    "down", "plunge", "plunges", "loss", "bear", "bearish", "drop", "drops", "miss",
    "misses", "weak", "negative", "sell", "downgrade", "underperform", "crash", "crashes"
]

def clean_html(raw_html):
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text()

def analyze_sentiment(text: str):
    text = text.lower()
    # Pega apenas as palavras (remover pontuações)
    words = re.findall(r'\b\w+\b', text)
    
    score = 0
    for word in words:
        if word in POSITIVE_WORDS:
            score += 1
        if word in NEGATIVE_WORDS:
            score -= 1
            
    return score

def get_asset_sentiment(ticker: str):
    # Trata tickers brasileiros para melhorar a busca no Google News
    search_term = ticker.replace(".SA", "")
    url = f"https://news.google.com/rss/search?q={search_term}+stock+OR+ação&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    
    feed = feedparser.parse(url)
    
    total_score = 0
    headlines = []
    
    # Analisa até 10 notícias mais recentes
    for entry in feed.entries[:10]:
        title = entry.title
        # Às vezes o título do Google News traz o nome do site no final, vamos limpar
        clean_title = title.split(" - ")[0]
        
        # Pega a descrição para ajudar na análise
        summary = clean_html(entry.summary if 'summary' in entry else "")
        
        text_to_analyze = clean_title + " " + summary
        score = analyze_sentiment(text_to_analyze)
        
        total_score += score
        headlines.append({
            "title": clean_title,
            "link": entry.link,
            "score": score
        })
        
    # Classificação
    if total_score > 2:
        sentiment_label = "Bullish (Otimista)"
    elif total_score < -2:
        sentiment_label = "Bearish (Pessimista)"
    else:
        sentiment_label = "Neutral (Neutro)"
        
    # Normaliza o score de -100 a +100 para o velocímetro (Gauge)
    # Assumindo que o score máximo absoluto provável seja em torno de 20 (2 palavras por notícia x 10 notícias)
    normalized_score = max(-100, min(100, int((total_score / 20.0) * 100)))
    
    # Para o Gauge do UI (0 a 100 onde 50 é neutro)
    gauge_value = 50 + (normalized_score / 2)
        
    return {
        "ticker": ticker,
        "sentiment": sentiment_label,
        "score_raw": total_score,
        "gauge_value": gauge_value,  # 0 to 100
        "headlines": headlines
    }
