# Este módulo é dedicado apenas à análise de sentimento.
# Não deve conter nenhuma referência a chatbot, LlamaIndex ou embeddings externos.
# Certifique-se de que não há funções, imports ou chamadas relacionadas ao chatbot.

# --- IMPORTS PRINCIPAIS (mantidos) ---
import os
from mistralai import Mistral
from dotenv import load_dotenv
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
import joblib
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from textblob import TextBlob
import json
from transformers import pipeline
from transformers import AutoModelForSequenceClassification
from transformers import XLMRobertaTokenizer
import torch
import numpy as np
from deep_translator import GoogleTranslator
from logging_config import get_logger

# --- NÃO DEVE HAVER ---
# Nenhuma referência a: llama_index, HuggingFaceEmbedding, chatbot_backend, build_index, responder_pergunta_chatbot
# Nenhuma função de chatbot, indexação ou embeddings externos

# Configuração e utilitários
load_dotenv()
api_key = os.environ.get("MISTRAL_API_KEY")
if not api_key:
    raise RuntimeError("API key Mistral não encontrada no ambiente!")
client = Mistral(api_key=api_key)

# Baixar recursos NLTK se necessário
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

# Logger customizado
logger = get_logger("Sentimento")

# Função de pré-processamento
def preprocessar_texto(texto, idioma='portuguese'):
    tokens = word_tokenize(texto, language=idioma)
    stop_words = set(stopwords.words(idioma))
    tokens_filtrados = [t for t in tokens if t.lower() not in stop_words and t.isalpha()]
    return ' '.join(tokens_filtrados)

# Limite de tokens para embeddings Mistral
MAX_TOKENS_EMBED = 8000  # margem de segurança

# Função utilitária para gerar resumo se texto for muito grande para embeddings
def resumir_se_necessario(texto, max_tokens=MAX_TOKENS_EMBED):
    max_chars = max_tokens * 4
    if len(texto) <= max_chars:
        return texto, False
    # Importa função de resumo
    from resumo import gerar_resumo
    logger.info("Texto excede o limite de tokens, gerando resumo para análise de sentimento...")
    resumo = gerar_resumo(texto)
    # Pode ser necessário cortar o resumo também, se ainda for muito grande
    if len(resumo) > max_chars:
        resumo = resumo[:max_chars]
    return resumo, True

# Função para truncar texto para embeddings
def truncar_texto_para_embeddings(texto, max_tokens=MAX_TOKENS_EMBED):
    # Aproximação: 1 token ~ 4 caracteres
    max_chars = max_tokens * 4
    if len(texto) <= max_chars:
        return texto
    corte = texto[:max_chars].rfind(' ')
    return texto[:corte] if corte > 0 else texto[:max_chars]

# Função para gerar embeddings
MODEL_EMBED = "mistral-embed"
def gerar_embeddings(lista_textos):
    textos_proc = [preprocessar_texto(t) for t in lista_textos]
    textos_final = []
    for t in textos_proc:
        t_resumido, foi_resumido = resumir_se_necessario(t)
        textos_final.append(t_resumido)
    response = client.embeddings.create(model=MODEL_EMBED, inputs=textos_final)
    return [e.embedding for e in response.data]

# Função para treinar classificador
def treinar_classificador(textos, labels, modelo_path="sentiment_clf.joblib"):
    X = gerar_embeddings(textos)
    y = labels
    X_train, X_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=42)
    clf = LogisticRegression(max_iter=1000)
    clf.fit(X_train, y_train)
    joblib.dump(clf, modelo_path)
    logger.info(f"Modelo salvo em {modelo_path}")
    logger.info(f"Acurácia no teste: {clf.score(X_test, y_test):.2f}")
    return clf

# Função para prever sentimento
def prever_sentimento(texto, modelo_path="sentiment_clf.joblib"):
    clf = joblib.load(modelo_path)
    texto_proc = preprocessar_texto(texto)
    texto_final, foi_resumido = resumir_se_necessario(texto_proc)
    embed = gerar_embeddings([texto_final])[0]
    return clf.predict([embed])[0], foi_resumido

# Função para análise de sentimento com TextBlob
# Retorna polaridade (-1 a 1) e sentimento categórico
def analisar_sentimento_textblob(texto):
    blob = TextBlob(texto)
    polaridade = blob.sentiment.polarity
    if polaridade > 0.1:
        sentimento = "positivo"
    elif polaridade < -0.1:
        sentimento = "negativo"
    else:
        sentimento = "neutro"
    return sentimento, polaridade

# Carregar pipeline HuggingFace para sentimento em português (lazy loading)
_hf_sent_pipeline = None
def analisar_sentimento_pt(texto):
    global _hf_sent_pipeline
    if _hf_sent_pipeline is None:
        _hf_sent_pipeline = pipeline("sentiment-analysis", model="nlptown/bert-base-multilingual-uncased-sentiment")
    resultado = _hf_sent_pipeline(texto[:512])  # aceita até 512 tokens
    label = resultado[0]['label'].lower()
    score = resultado[0]['score']
    # Interpretação: 1-2 stars = negativo, 3 = neutro, 4-5 = positivo
    if '1' in label or '2' in label:
        sentimento = 'negativo'
    elif '3' in label:
        sentimento = 'neutro'
    else:
        sentimento = 'positivo'
    return sentimento, float(score)

# Função para análise de sentimento com pysentimiento (Português)
try:
    from pysentimiento import create_analyzer
    _pysent_analyzer = create_analyzer(task="sentiment", lang="pt")
except ImportError:
    _pysent_analyzer = None

def analisar_sentimento_pysentimiento(texto):
    if _pysent_analyzer is None:
        return "indisponível", 0.0
    resultado = _pysent_analyzer.predict(texto)
    sentimento = resultado.output  # 'POS', 'NEG', 'NEU'
    score = float(resultado.probas.get(sentimento, 0.0))
    if sentimento == 'POS':
        return 'positivo', score
    elif sentimento == 'NEG':
        return 'negativo', score
    else:
        return 'neutro', score

# --- Novo modelo: CardiffNLP XLM-RoBERTa ---
_cardiff_tokenizer = None
_cardiff_model = None

CARDIFF_MODEL_NAME = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
CARDIFF_LABELS = ['negative', 'neutral', 'positive']

def analisar_sentimento_cardiff(texto):
    global _cardiff_tokenizer, _cardiff_model
    if _cardiff_tokenizer is None or _cardiff_model is None:
        _cardiff_tokenizer = XLMRobertaTokenizer.from_pretrained(CARDIFF_MODEL_NAME)
        _cardiff_model = AutoModelForSequenceClassification.from_pretrained(CARDIFF_MODEL_NAME)
    # Tokenização e inferência
    inputs = _cardiff_tokenizer(texto, return_tensors="pt", truncation=True, max_length=256)
    with torch.no_grad():
        logits = _cardiff_model(**inputs).logits
        scores = torch.softmax(logits, dim=1).detach().cpu().numpy()[0]
        idx = int(np.argmax(scores))
        label = CARDIFF_LABELS[idx]
        score = float(scores[idx])
    # Ajustar para PT
    if label == 'positive':
        return 'positivo', score
    elif label == 'negative':
        return 'negativo', score
    else:
        return 'neutro', score

def traduzir_label_sentimento(label):
    if label.lower() in ['positive', 'positivo']:
        return 'Positivo'
    elif label.lower() in ['negative', 'negativo']:
        return 'Negativo'
    elif label.lower() in ['neutral', 'neutro']:
        return 'Neutro'
    else:
        return label.capitalize()

def analisar_arquivo_json(tipo, pasta_uploads="uploads"):
    """
    Lê o arquivo JSON correto da pasta uploads e executa a análise de sentimento.
    tipo: 'manual' ou 'upload'
    """
    if tipo == 'manual':
        file_path = os.path.join(pasta_uploads, "manual_text.json")
    elif tipo == 'upload':
        file_path = os.path.join(pasta_uploads, "upload_text.json")
    else:
        raise ValueError("Tipo inválido para análise de sentimento.")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    texto = data.get('conteudo', '')
    # Traduza para inglês para análise com TextBlob
    try:
        texto_en = GoogleTranslator(source='auto', target='en').translate(texto)
    except Exception:
        texto_en = texto
    sent_ml, foi_resumido = prever_sentimento(texto)
    sent_blob, pol_blob = analisar_sentimento_textblob(texto_en)
    sent_pt, score_pt = analisar_sentimento_pt(texto)
    sent_psent, score_psent = analisar_sentimento_pysentimiento(texto)
    sent_cardiff, score_cardiff = analisar_sentimento_cardiff(texto)
    # Traduzir todos os rótulos para português
    return {
        "texto": texto,
        "sentimento_ml": traduzir_label_sentimento(sent_ml),
        "sentimento_textblob": traduzir_label_sentimento(sent_blob),
        "polaridade": pol_blob,
        "sentimento_pt": traduzir_label_sentimento(sent_pt),
        "score_pt": score_pt,
        "sentimento_pysent": traduzir_label_sentimento(sent_psent),
        "score_pysent": score_psent,
        "sentimento_cardiff": traduzir_label_sentimento(sent_cardiff),
        "score_cardiff": score_cardiff,
        "foi_resumido": foi_resumido
    }

if __name__ == "__main__":
    # (re)treina o classificador e salva o modelo
    dataset = {
        "filmes": {
            "positivo": [
                "Filme emocionante e envolvente.",
                "Atuações excelentes e roteiro criativo.",
                "Gostei muito da trilha sonora.",
                "Ótima direção e fotografia.",
                "Recomendo este filme para todos."
            ],
            "negativo": [
                "O filme foi cansativo e previsível.",
                "Não gostei do final.",
                "Atuação fraca dos atores.",
                "História sem graça.",
                "Não recomendo este filme."
            ]
        },
        "restaurantes": {
            "positivo": [
                "A comida estava deliciosa e o ambiente agradável.",
                "Atendimento rápido e simpático.",
                "Melhor refeição que já tive.",
                "Ótimo custo-benefício.",
                "Voltarei mais vezes."
            ],
            "negativo": [
                "A comida estava fria e sem sabor.",
                "Demorou muito para chegar.",
                "Atendimento ruim.",
                "Lugar barulhento e desconfortável.",
                "Não gostei da experiência."
            ]
        },
        "ecommerce": {
            "positivo": [
                "Produto chegou antes do prazo.",
                "Qualidade excelente do produto.",
                "Compra fácil e entrega rápida.",
                "Ótimo atendimento ao cliente.",
                "Muito satisfeito com a compra."
            ],
            "negativo": [
                "O produto veio com defeito.",
                "Entrega atrasou muito.",
                "Atendimento ao cliente foi péssimo.",
                "Não recomendo essa loja.",
                "Tive problemas para trocar o produto."
            ]
        },
        "servicos": {
            "positivo": [
                "Serviço realizado com excelência.",
                "Profissionais atenciosos e competentes.",
                "Fiquei muito satisfeito com o resultado.",
                "Superou minhas expectativas.",
                "Recomendo o serviço a todos."
            ],
            "negativo": [
                "Serviço mal executado.",
                "Profissionais despreparados.",
                "Não resolveu meu problema.",
                "Cobrança abusiva pelo serviço.",
                "Experiência frustrante."
            ]
        }
    }
    textos = []
    labels = []
    for fonte, sentimentos in dataset.items():
        for sentimento, frases in sentimentos.items():
            textos.extend(frases)
            labels.extend([sentimento] * len(frases))

    clf = treinar_classificador(textos, labels)
    logger.info("Modelo de sentimento treinado e salvo em 'sentiment_clf.joblib'.")
