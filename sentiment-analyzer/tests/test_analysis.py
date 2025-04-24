import pytest
import asyncio
import logging
from app.analysis import analyze_text
from app.utils import clean_text

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_analyze_text_valid_input():
    """Test analyze_text with valid Portuguese text."""
    text = "Estou muito feliz hoje! A vida está maravilhosa."
    try:
        results = await analyze_text(text)
        logger.debug(f"Resultados do teste: {results}")
        
        # Verify structure of results
        assert isinstance(results, dict), "Resultados devem ser um dicionário"
        assert 'sentiment' in results, "Chave 'sentiment' não encontrada"
        assert 'emotions' in results, "Chave 'emotions' não encontrada"
        assert 'visualizations' in results, "Chave 'visualizations' não encontrada"
        assert 'text' in results, "Chave 'text' não encontrada"
        
        # Verify content
        assert len(results['sentiment']) > 0, "Lista de sentimentos vazia"
        assert len(results['emotions']) > 0, "Lista de emoções vazia"
        assert 'wordcloud' in results['visualizations'], "WordCloud não gerada"
        assert 'sentiment_bar' in results['visualizations'], "Gráfico de sentimentos não gerado"
        
        # Verify sentiment and emotion data
        for sent in results['sentiment']:
            assert 'text' in sent and 'score' in sent, "Formato de sentimento inválido"
        for emo in results['emotions']:
            assert 'emotions' in emo, "Formato de emoção inválido"
            assert isinstance(emo['emotions'], dict), "Emoções devem ser um dicionário"
            
    except Exception as e:
        logger.error(f"Erro no teste de análise: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_analyze_text_short_input():
    """Test analyze_text with short text to handle edge cases."""
    text = "Feliz!"
    try:
        results = await analyze_text(text)
        logger.debug(f"Resultados com texto curto: {results}")
        
        assert 'sentiment' in results
        assert 'emotions' in results
        assert 'visualizations' in results
        assert len(results['sentiment']) >= 1
        assert len(results['emotions']) >= 1
        # WordCloud may be empty for short text, so we only check its presence
        assert 'wordcloud' in results['visualizations']
        
    except Exception as e:
        logger.error(f"Erro no teste com texto curto: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_analyze_text_non_portuguese():
    """Test analyze_text with non-Portuguese text."""
    text = "I am very happy today!"
    try:
        results = await analyze_text(text)
        logger.debug(f"Resultados com texto não-português: {results}")
        
        assert 'error' in results
        assert results['error'] == 'Apenas textos em português são suportados.'
        
    except Exception as e:
        logger.error(f"Erro no teste com texto não-português: {str(e)}")
        raise