import pytest
from app.utils import clean_text, detect_language, validate_file

def test_clean_text():
    text = "Olá, estou muito feliz!!!"
    cleaned = clean_text(text)
    assert cleaned.islower()
    assert '!!!' not in cleaned
    assert 'olá' not in cleaned  # Should be lemmatized

def test_detect_language():
    assert detect_language("Eu amo programar") == 'pt'
    assert detect_language("I love coding") == 'en'

def test_validate_file():
    assert validate_file('test.txt') == True
    assert validate_file('test.pdf') == True
    assert validate_file('test.jpg') == False
