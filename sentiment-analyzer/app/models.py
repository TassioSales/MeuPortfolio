import spacy
from nltk.corpus import stopwords
from langdetect import detect
import re
import logging

def clean_text(text):
    """Clean and preprocess text."""
    try:
        # Convert to lowercase
        text = text.lower()
        # Remove special characters, keep letters and spaces
        text = re.sub(r'[^a-zà-ú\s]', '', text)
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        if not text:
            logging.warning("Texto vazio após limpeza inicial")
            return text
        
        # Load spaCy model
        nlp = spacy.load('pt_core_news_sm')
        doc = nlp(text)
        
        # Remove stopwords, keep meaningful words
        stop_words = set(stopwords.words('portuguese'))
        tokens = [token.lemma_ for token in doc if token.text not in stop_words and not token.is_punct and len(token.text) > 2]
        
        cleaned = ' '.join(tokens)
        if not cleaned:
            logging.warning("Texto vazio após remoção de stopwords")
            return text  # Return original if cleaned is empty
        return cleaned
    
    except Exception as e:
        logging.error(f"Erro na limpeza de texto: {str(e)}")
        raise

def detect_language(text):
    """Detect the language of the text."""
    try:
        if not text.strip():
            return 'unknown'
        return detect(text)
    except Exception as e:
        logging.warning(f"Erro na detecção de idioma: {str(e)}")
        return 'unknown'

def validate_file(filename):
    """Validate file extension."""
    return filename.lower().endswith(('.txt', '.pdf'))