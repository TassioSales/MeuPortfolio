# analise_inteligente.py
# Nova análise de sentimento com contexto e visualização (LlamaIndex, WordCloud, Gráficos)

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from transformers import pipeline
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS
import os
from collections import Counter
import json
from deep_translator import GoogleTranslator
import nltk
import re

# --- Função para ler texto e traduzir ---
def ler_texto_e_traduzir(tipo, input_dir="uploads"):
    if tipo == 'manual':
        caminho = os.path.join(input_dir, 'manual_text.json')
    else:
        caminho = os.path.join(input_dir, 'upload_text.json')
    with open(caminho, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    conteudo_pt = dados.get('conteudo', '')
    try:
        conteudo_en = GoogleTranslator(source='auto', target='en').translate(conteudo_pt)
    except Exception:
        conteudo_en = conteudo_pt
    return conteudo_pt, conteudo_en

# --- Função para construir índice com embedding local ---
def build_index(input_dir="uploads", index_dir="index/storage"):
    """
    Constrói o índice LlamaIndex usando embedding local HuggingFace (sentence-transformers/all-MiniLM-L6-v2).
    """
    from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    from llama_index.core import StorageContext
    # Usa embedding local
    embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    documents = SimpleDirectoryReader(input_dir).load_data()
    index = VectorStoreIndex.from_documents(documents, embed_model=embed_model)
    index.storage_context.persist(persist_dir=index_dir)
    return index

# --- 2. Consulta com contexto ---
def ask_question(query, index_path="index/storage"):
    storage_context = StorageContext.from_defaults(persist_dir=index_path)
    index = load_index_from_storage(storage_context, embed_model=HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2"))
    response = index.as_query_engine().query(query)
    return str(response)

# --- 3. Análise de sentimentos frase a frase ---
def analyze_sentiments(texts):
    analyzer = pipeline("sentiment-analysis")
    return [analyzer(sentence)[0] for sentence in texts]

# --- 3b. Análise de emoções frase a frase ---
def analyze_emotions(texts):
    emotion_analyzer = pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base", top_k=1)
    return [emotion_analyzer(sentence)[0][0] for sentence in texts]

# --- 4. Visualização: WordCloud e Gráficos ---
def gerar_wordcloud(texto, path_out="static/wordcloud.png"):
    # Remove quebras de linha e caracteres estranhos
    texto = texto.replace('\n', ' ').replace('\r', ' ')
    # Remove pontuação básica
    texto = re.sub(r'[\.,;:!?\-\"\(\)\[\]{}<>]', '', texto)
    # Remove stopwords em português
    stopwords_pt = set(STOPWORDS)
    stopwords_pt.update([
        'de', 'a', 'o', 'que', 'e', 'do', 'da', 'em', 'um', 'para', 'é', 'com', 'não', 'uma', 'os', 'no', 'se', 'na',
        'por', 'mais', 'as', 'dos', 'como', 'mas', 'foi', 'ao', 'ele', 'das', 'tem', 'à', 'seu', 'sua', 'ou', 'ser',
        'quando', 'muito', 'há', 'nos', 'já', 'está', 'eu', 'também', 'só', 'pelo', 'pela', 'até', 'isso', 'ela',
        'entre', 'era', 'depois', 'sem', 'mesmo', 'aos', 'ter', 'seus', 'quem', 'nas', 'me', 'esse', 'eles', 'estão',
        'você', 'tinha', 'foram', 'essa', 'num', 'nem', 'suas', 'meu', 'às', 'minha', 'têm', 'numa', 'pelos', 'elas',
        'havia', 'seja', 'qual', 'será', 'nós', 'tenho', 'lhe', 'deles', 'essas', 'esses', 'pelas', 'este', 'dele',
        'tu', 'te', 'vocês', 'vos', 'lhes', 'meus', 'minhas', 'teu', 'tua', 'teus', 'tuas', 'nosso', 'nossa', 'nossos',
        'nossas', 'dela', 'delas', 'esta', 'estes', 'estas', 'aquele', 'aquela', 'aqueles', 'aquelas', 'isto', 'aquilo',
        'estou', 'está', 'estamos', 'estão', 'estive', 'esteve', 'estivemos', 'estiveram', 'estava', 'estávamos',
        'estavam', 'estivera', 'estivéramos', 'esteja', 'estejamos', 'estejam', 'estivesse', 'estivéssemos',
        'estivessem', 'estiver', 'estivermos', 'estiverem', 'hei', 'há', 'havemos', 'hão', 'houve', 'houvemos',
        'houveram', 'houvera', 'houvéramos', 'haja', 'hajamos', 'hajam', 'houvesse', 'houvéssemos', 'houvessem',
        'houver', 'houvermos', 'houverem', 'houverei', 'houverá', 'houveremos', 'houverão', 'houveria', 'houveríamos',
        'houveriam', 'sou', 'somos', 'são', 'era', 'éramos', 'eram', 'fui', 'foi', 'fomos', 'foram', 'fora', 'fôramos',
        'seja', 'sejamos', 'sejam', 'fosse', 'fôssemos', 'fossem', 'for', 'formos', 'forem', 'serei', 'será', 'seremos',
        'serão', 'seria', 'seríamos', 'seriam', 'tenho', 'tem', 'temos', 'tém', 'tinha', 'tínhamos', 'tinham', 'tive',
        'teve', 'tivemos', 'tiveram', 'tivera', 'tivéramos', 'tenha', 'tenhamos', 'tenham', 'tivesse', 'tivéssemos',
        'tivessem', 'tiver', 'tivermos', 'tiverem', 'terei', 'terá', 'teremos', 'terão', 'teria', 'teríamos', 'teriam'
    ])
    wc = WordCloud(
        width=800,
        height=400,
        background_color="white",
        stopwords=stopwords_pt,
        collocations=False,
        regexp=r"\b\w{3,}\b",  # só palavras com 3+ letras
        contour_color='#31415a',
        colormap='viridis',
        font_path=None  # pode-se definir um font_path se quiser garantir acentuação
    ).generate(texto)
    wc.to_file(path_out)
    return path_out

def plot_distribuicao_sentimentos(sentimentos, path_out="static/sentimentos_bar.png"):
    from collections import Counter
    labels = [s['label'] for s in sentimentos]
    contagem = Counter(labels)
    plt.figure(figsize=(6,4))
    plt.bar(contagem.keys(), contagem.values(), color=['red','gray','green'])
    plt.title('Distribuição dos Sentimentos')
    plt.xlabel('Sentimento')
    plt.ylabel('Frequência')
    plt.tight_layout()
    plt.savefig(path_out)
    plt.close()
    return path_out

# --- Função para responder perguntas via LlamaIndex ---
def responder_pergunta_chatbot(pergunta, tipo="manual", input_dir="uploads", index_path="index/storage"):
    """
    Usa LlamaIndex para responder perguntas sobre o texto/documento carregado.
    Se o índice não existir, constrói automaticamente.
    """
    # Lê o texto original (português)
    conteudo_pt, conteudo_en = ler_texto_e_traduzir(tipo, input_dir)
    if not os.path.exists(index_path):
        build_index(input_dir, index_dir=index_path)
    # Carrega índice com embedding local
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    from llama_index.core import StorageContext, load_index_from_storage
    embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    storage_context = StorageContext.from_defaults(persist_dir=index_path)
    index = load_index_from_storage(storage_context, embed_model=embed_model)
    # Usa LlamaIndex para buscar resposta
    query_engine = index.as_query_engine()
    resposta = query_engine.query(pergunta)
    return str(resposta)

# --- Função principal para análise inteligente ---
def analise_inteligente(tipo="manual", pergunta=None, input_dir="uploads", index_path="index/storage"):
    """
    Executa todo o fluxo:
    1. Lê texto (manual/upload)
    2. Preprocessa e separa frases
    3. Cria índice LlamaIndex (se necessário)
    4. Analisa sentimentos frase a frase
    5. Gera WordCloud e gráfico de barras
    6. (Opcional) Busca contexto com LlamaIndex
    7. Retorna caminhos das imagens e resultados
    8. Calcula sentimento e emoção geral
    """
    nltk.download('punkt', quiet=True)
    from nltk.tokenize import sent_tokenize
    # 1. Lê texto
    conteudo_pt, conteudo_en = ler_texto_e_traduzir(tipo, input_dir)
    # 2. Pré-processa e separa frases
    frases = [fr.strip() for fr in sent_tokenize(conteudo_pt) if fr.strip()]
    frases_en = [fr.strip() for fr in sent_tokenize(conteudo_en) if fr.strip()]
    # 3. Cria índice se não existir
    if not os.path.exists(index_path):
        build_index(input_dir, index_dir=index_path)
    # 4. Analisa sentimentos e emoções com frases traduzidas
    resultados = analyze_sentiments(frases_en)
    resultados_emocao = analyze_emotions(frases_en)
    # Corrigir caso não haja frases válidas ou resultados vazios
    if not frases or not resultados:
        return {
            "frases": frases,
            "sentimentos": resultados,
            "emocoes": resultados_emocao,
            "wordcloud": gerar_wordcloud(' '.join(frases_en)),
            "grafico": plot_distribuicao_sentimentos(resultados),
            "resposta_contexto": None,
            "sentimento_geral": '-',
            "emocao_geral": '-'
        }
    # 5. Gera WordCloud com texto original em português
    wordcloud_path = gerar_wordcloud(conteudo_pt)
    grafico_path = plot_distribuicao_sentimentos(resultados)
    # 6. Busca contexto (usa texto em português para resposta contextual)
    resposta_contexto = None
    if pergunta:
        resposta_contexto = ask_question(pergunta, index_path=index_path)
    # 7. Calcula sentimento e emoção geral (em português)
    labels = [r['label'] for r in resultados]
    contagem = Counter(labels)
    sentimento_geral = contagem.most_common(1)[0][0].capitalize() if labels else '-'
    sentimento_geral_pt = traduzir_label_sentimento(sentimento_geral)
    if resultados_emocao:
        labels_emocao = [e['label'] for e in resultados_emocao]
        contagem_emocao = Counter(labels_emocao)
        emocao_geral = traduzir_label_emocao(contagem_emocao.most_common(1)[0][0])
    else:
        emocao_geral = '-'
    # 8. Retorna resultados com frases originais
    return {
        "frases": frases,  # em português
        "sentimentos": resultados,
        "emocoes": resultados_emocao,
        "wordcloud": wordcloud_path,
        "grafico": grafico_path,
        "resposta_contexto": resposta_contexto,
        "sentimento_geral": sentimento_geral_pt,
        "emocao_geral": emocao_geral
    }

def traduzir_label_sentimento(label):
    if label == 'positive':
        return 'Positivo'
    elif label == 'negative':
        return 'Negativo'
    elif label == 'neutral':
        return 'Neutro'
    else:
        return label.capitalize()

def traduzir_label_emocao(label):
    label = label.lower()
    if label in ['joy', 'alegria']:
        return 'Alegria'
    elif label in ['sadness', 'tristeza']:
        return 'Tristeza'
    elif label in ['anger', 'raiva']:
        return 'Raiva'
    elif label in ['fear', 'medo']:
        return 'Medo'
    elif label in ['surprise', 'surpresa']:
        return 'Surpresa'
    elif label in ['disgust', 'desgosto']:
        return 'Desgosto'
    elif label in ['neutral', 'neutra', 'neutro']:
        return 'Neutro'
    else:
        return label.capitalize()

# (Opcional) Gráfico temporal pode ser implementado se houver timestamps
