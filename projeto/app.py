import os
import json
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from resumo import gerar_resumo
from analise_inteligente import analise_inteligente
from deep_translator import GoogleTranslator
from chatbot_backend import responder_pergunta_chatbot

# Garante que o caminho de uploads seja absoluto e correto
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'txt', 'pdf'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
load_dotenv()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def logMessage(status, message):
    print(f"[{status}] - {message}")

def extract_text_from_pdf(file):
    from PyPDF2 import PdfReader
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def traduzir_para_ingles(texto):
    try:
        return GoogleTranslator(source='auto', target='en').translate(texto)
    except Exception:
        return texto

def ler_conteudo_json_traduzido(tipo):
    import json, os
    pasta = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    if tipo == 'manual':
        caminho = os.path.join(pasta, 'manual_text.json')
    else:
        caminho = os.path.join(pasta, 'upload_text.json')
    with open(caminho, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    conteudo = dados.get('conteudo', '')
    conteudo_en = traduzir_para_ingles(conteudo)
    return conteudo, conteudo_en

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        file = request.files.get('file')
        if not file or not allowed_file(file.filename):
            return jsonify({"status": "erro", "mensagem": "Arquivo não enviado ou formato não suportado."}), 400
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower()
        text = ""
        if ext == 'txt':
            text = file.read().decode('utf-8')
        elif ext == 'pdf':
            text = extract_text_from_pdf(file)
        else:
            return jsonify({"status": "erro", "mensagem": "Formato de arquivo não suportado."}), 400
        json_path = os.path.join(app.config['UPLOAD_FOLDER'], "upload_text.json")
        with open(json_path, 'w', encoding='utf-8') as json_file:
            json.dump({"conteudo": text}, json_file, ensure_ascii=False, indent=4)
        logMessage('SUCESSO', f"Arquivo {filename} carregado e texto salvo com sucesso!")
        return jsonify({"status": "sucesso", "mensagem": f"Arquivo {filename} carregado com sucesso!"})
    except Exception as e:
        logMessage('ERRO', f"Erro ao carregar o arquivo: {str(e)}")
        return jsonify({"status": "erro", "mensagem": f"Erro ao carregar o arquivo: {str(e)}"}), 500

@app.route('/manual', methods=['POST'])
def manual_text():
    try:
        texto = request.form.get('texto', '')
        print(f"[DEBUG] Tamanho do texto recebido via POST: {len(texto)} caracteres")
        if not texto.strip():
            return jsonify({"status": "erro", "mensagem": "Texto manual vazio."}), 400
        json_path = os.path.join(app.config['UPLOAD_FOLDER'], "manual_text.json")
        with open(json_path, 'w', encoding='utf-8') as json_file:
            json.dump({"conteudo": texto}, json_file, ensure_ascii=False, indent=4)
        logMessage('SUCESSO', "Texto manual enviado e salvo com sucesso!")
        return jsonify({"status": "sucesso", "mensagem": "Texto manual salvo com sucesso!"})
    except Exception as e:
        logMessage('ERRO', f"Erro ao salvar o texto manual: {str(e)}")
        return jsonify({"status": "erro", "mensagem": f"Erro ao salvar o texto manual: {str(e)}"}), 500

@app.route('/visualizar', methods=['GET'])
def visualizar():
    tipo = request.args.get('tipo')
    if tipo == 'upload':
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], "upload_text.json")
    elif tipo == 'manual':
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], "manual_text.json")
    else:
        return jsonify({"status": "erro", "mensagem": "Tipo de visualização inválido!"}), 400
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        return jsonify({"status": "sucesso", "conteudo": file_content})
    except FileNotFoundError:
        return jsonify({"status": "erro", "mensagem": "Arquivo não encontrado!"}), 404
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": f"Erro ao ler o arquivo: {str(e)}"}), 500

@app.route('/resumo', methods=['POST'])
def resumo():
    tipo = request.form.get('tipo')
    if tipo == 'upload':
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], "upload_text.json")
    elif tipo == 'manual':
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], "manual_text.json")
    else:
        return jsonify({"status": "erro", "mensagem": "Tipo inválido!"}), 400
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        texto = data.get("conteudo", "")
        if not texto.strip():
            return jsonify({"status": "erro", "mensagem": "Nenhum texto encontrado!"}), 400
        # Chama função do resumo.py
        resumo_gerado = gerar_resumo(texto)
        # NÃO TRUNCA o resumo, retorna ele completo
        return jsonify({"status": "sucesso", "resumo": resumo_gerado})
    except FileNotFoundError:
        return jsonify({"status": "erro", "mensagem": "Arquivo não encontrado para resumo!"}), 404
    except Exception as e:
        logMessage('ERRO', f"Erro ao gerar o resumo: {str(e)}")
        return jsonify({"status": "erro", "mensagem": f"Erro ao gerar o resumo: {str(e)}"}), 500

@app.route('/sentimento', methods=['POST'])
def sentimento():
    tipo = request.form.get('tipo')
    print(f"[DEBUG] Tipo recebido para análise de sentimento: {tipo}")
    try:
        from analise_de_sentimento import analisar_arquivo_json
        resultado = analisar_arquivo_json(tipo, pasta_uploads=app.config['UPLOAD_FOLDER'])
        texto_completo = resultado.get('texto', '')
        print(f"[DEBUG] Tamanho do texto analisado: {len(texto_completo)} caracteres")
        sentimento_ml = resultado.get('sentimento_ml')
        sentimento_blob = resultado.get('sentimento_textblob')
        polaridade_blob = resultado.get('polaridade')
        sentimento_pt = resultado.get('sentimento_pt')
        score_pt = resultado.get('score_pt')
        sentimento_pysent = resultado.get('sentimento_pysent')
        score_pysent = resultado.get('score_pysent')
        sentimento_cardiff = resultado.get('sentimento_cardiff')
        score_cardiff = resultado.get('score_cardiff')
        foi_resumido = resultado.get('foi_resumido', False)

        # Nova explicação baseada em todos os modelos
        explicacao = ""
        detalhes = []
        # ML
        if sentimento_ml == "Positivo":
            detalhes.append(f"O modelo supervisionado treinado com exemplos reais em português classificou o texto como <b>positivo</b>.")
        elif sentimento_ml == "Negativo":
            detalhes.append(f"O modelo supervisionado treinado com exemplos reais em português classificou o texto como <b>negativo</b>.")
        elif sentimento_ml == "Neutro":
            detalhes.append(f"O modelo supervisionado não identificou emoções fortes, indicando neutralidade.")
        else:
            detalhes.append(f"O modelo supervisionado está indisponível.")
        # BERT
        if sentimento_pt == "Positivo":
            detalhes.append(f"O modelo BERT multilíngue (HuggingFace) atribuiu <b>sentimento positivo</b> ao texto, com confiança de {(score_pt*100):.1f}%.")
        elif sentimento_pt == "Negativo":
            detalhes.append(f"O modelo BERT multilíngue (HuggingFace) atribuiu <b>sentimento negativo</b> ao texto, com confiança de {(score_pt*100):.1f}%.")
        elif sentimento_pt == "Neutro":
            detalhes.append(f"O modelo BERT multilíngue (HuggingFace) considerou o texto neutro.")
        else:
            detalhes.append(f"O modelo BERT multilíngue (HuggingFace) está indisponível.")
        # PySentimiento
        if sentimento_pysent == "Positivo":
            detalhes.append(f"O modelo PySentimiento, especializado em português, classificou o texto como <b>positivo</b> com confiança de {(score_pysent*100):.1f}%.")
        elif sentimento_pysent == "Negativo":
            detalhes.append(f"O modelo PySentimiento, especializado em português, classificou o texto como <b>negativo</b> com confiança de {(score_pysent*100):.1f}%.")
        elif sentimento_pysent == "Neutro":
            detalhes.append(f"O modelo PySentimiento considerou o texto neutro.")
        else:
            detalhes.append(f"O modelo PySentimiento está indisponível.")
        # Cardiff
        if sentimento_cardiff == "Positivo":
            detalhes.append(f"O modelo XLM-RoBERTa (CardiffNLP) classificou o texto como <b>positivo</b>, com confiança de {(score_cardiff*100):.1f}%.")
        elif sentimento_cardiff == "Negativo":
            detalhes.append(f"O modelo XLM-RoBERTa (CardiffNLP) classificou o texto como <b>negativo</b>, com confiança de {(score_cardiff*100):.1f}%.")
        elif sentimento_cardiff == "Neutro":
            detalhes.append(f"O modelo XLM-RoBERTa (CardiffNLP) considerou o texto neutro.")
        else:
            detalhes.append(f"O modelo XLM-RoBERTa (CardiffNLP) está indisponível.")
        # TextBlob
        if sentimento_blob == "Positivo":
            detalhes.append(f"O TextBlob detectou polaridade positiva (polaridade: {polaridade_blob:.2f}).")
        elif sentimento_blob == "Negativo":
            detalhes.append(f"O TextBlob detectou polaridade negativa (polaridade: {polaridade_blob:.2f}).")
        elif sentimento_blob == "Neutro":
            detalhes.append(f"O TextBlob considerou o texto neutro (polaridade: {polaridade_blob:.2f}).")
        else:
            detalhes.append(f"O TextBlob está indisponível.")

        # Explicação final baseada em consenso, mas detalhada
        votos = [sentimento_ml, sentimento_pt, sentimento_pysent, sentimento_cardiff]
        votos_validos = [v for v in votos if v in ("Positivo","Negativo","Neutro")]
        if len(set(votos_validos)) == 1 and votos_validos:
            explicacao = f"<b>Há consenso entre os modelos principais: o texto é {votos_validos[0].lower()}.</b><br>\n"
        elif votos_validos.count("Positivo") >= 2:
            explicacao = "<b>A maioria dos modelos classificou o texto como positivo.</b><br>\n"
        elif votos_validos.count("Negativo") >= 2:
            explicacao = "<b>A maioria dos modelos classificou o texto como negativo.</b><br>\n"
        elif votos_validos.count("Neutro") >= 2:
            explicacao = "<b>A maioria dos modelos classificou o texto como neutro.</b><br>\n"
        else:
            explicacao = "<b>Os modelos apresentaram divergências nos resultados.</b><br>\n"
        explicacao += "<ul>" + "".join(f"<li>{d}</li>" for d in detalhes) + "</ul>"

        aviso = ""
        if foi_resumido:
            aviso = "O texto enviado era muito grande e foi resumido automaticamente antes da análise de sentimento. O resultado reflete o resumo gerado."
        return jsonify({
            "status": "sucesso",
            "texto": texto_completo,  # garantir que o texto completo analisado é retornado
            "sentimento_ml": sentimento_ml,
            "sentimento_textblob": sentimento_blob,
            "polaridade": polaridade_blob,
            "sentimento_pt": sentimento_pt,
            "score_pt": score_pt,
            "sentimento_pysent": sentimento_pysent,
            "score_pysent": score_pysent,
            "sentimento_cardiff": sentimento_cardiff,
            "score_cardiff": score_cardiff,
            "explicacao": explicacao.strip(),
            "aviso": aviso
        })
    except FileNotFoundError as e:
        print(f"[DEBUG] FileNotFoundError: {str(e)}")
        return jsonify({"status": "erro", "mensagem": f"Arquivo não encontrado para análise de sentimento! {str(e)}"}), 404
    except Exception as e:
        print(f"[DEBUG] Exception: {str(e)}")
        return jsonify({"status": "erro", "mensagem": f"Erro ao analisar sentimento: {str(e)}"}), 500

@app.route('/analise_inteligente', methods=['POST'])
def rota_analise_inteligente():
    data = request.get_json(force=True)
    tipo = data.get('tipo', 'manual')
    pergunta = data.get('pergunta', None)
    try:
        resultado = analise_inteligente(tipo=tipo, pergunta=pergunta)
        return jsonify({
            "status": "sucesso",
            "frases": resultado["frases"],
            "sentimentos": resultado["sentimentos"],
            "emocoes": resultado.get("emocoes", []),
            "wordcloud": resultado["wordcloud"],
            "grafico": resultado["grafico"],
            "resposta_contexto": resultado["resposta_contexto"],
            "sentimento_geral": resultado["sentimento_geral"],
            "emocao_geral": resultado["emocao_geral"]
        })
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)})

@app.route('/chatbot')
def chatbot_page():
    return render_template('chatbot.html')

@app.route('/chatbot', methods=['POST'])
def chatbot_api():
    data = request.get_json()
    pergunta = data.get('pergunta','').strip()
    tipo = data.get('tipo','manual')
    if not pergunta:
        return jsonify({'status':'erro','mensagem':'Pergunta vazia.'})
    try:
        resposta = responder_pergunta_chatbot(pergunta, tipo=tipo, input_dir=app.config['UPLOAD_FOLDER'])
        return jsonify({'status':'sucesso','resposta':resposta})
    except Exception as e:
        return jsonify({'status':'erro','mensagem':f'Erro ao obter resposta do chatbot: {str(e)}'})

@app.route('/debug_uploads')
def debug_uploads():
    uploads_path = app.config['UPLOAD_FOLDER']
    try:
        files = os.listdir(uploads_path)
        results = {}
        for fname in files:
            fpath = os.path.join(uploads_path, fname)
            results[fname] = {
                "exists": os.path.exists(fpath),
                "readable": os.access(fpath, os.R_OK),
                "size": os.path.getsize(fpath) if os.path.exists(fpath) else None
            }
        return jsonify({"status": "sucesso", "uploads_path": uploads_path, "arquivos": results})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)})

if __name__ == '__main__':
    app.run(debug=True)
