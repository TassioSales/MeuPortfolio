import os
import json
from mistralai import Mistral

def carregar_texto(tipo, input_dir="uploads"):
    """
    Lê o texto salvo, seja manual (manual_text.json) ou upload (upload_text.json).
    """
    if tipo == 'manual':
        caminho = os.path.join(input_dir, 'manual_text.json')
    else:
        caminho = os.path.join(input_dir, 'upload_text.json')
    if not os.path.exists(caminho):
        return ''
    with open(caminho, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    return dados.get('conteudo', '')

def otimizar_resposta(resposta):
    """
    Limpa e organiza a resposta do modelo para ser direta, clara e sem enumeração de tópicos.
    """
    resposta = resposta.strip()
    # Remove enumeração e marcadores no início de linhas
    linhas = resposta.splitlines()
    novas_linhas = []
    for linha in linhas:
        l = linha.strip()
        if l[:2] in ('- ', '* ', '• ', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.'):
            l = l[2:].strip()
        elif l[:3] in ('10.', '11.', '12.','13.','14.','15.','16.','17.','18.','19.','20.'):
            l = l[3:].strip()
        novas_linhas.append(l)
    resposta = ' '.join([l for l in novas_linhas if l])
    # Remove espaços duplicados e ajusta pontuação
    resposta = resposta.replace(' .', '.').replace(' ,', ',').replace(' ;', ';')
    while '  ' in resposta:
        resposta = resposta.replace('  ', ' ')
    return resposta.strip()

def gerar_resposta_mistral(pergunta, contexto=None, modelo="mistral-large-latest"):
    """
    Gera uma resposta usando o modelo MistralAI, com prompt otimizado para ser direta, clara e sem detalhamento excessivo.
    """
    api_key = os.environ["MISTRAL_API_KEY"]
    client = Mistral(api_key=api_key)
    if contexto:
        prompt = (
            "Responda de forma direta, clara e concisa, sem listar tópicos.\n"
            "Utilize apenas as informações do texto abaixo para responder.\n"
            "Se não houver informação suficiente, diga explicitamente.\n"
            "Evite detalhamento excessivo, mas garanta que a resposta seja fácil de entender.\n"
            "\n[Texto do Documento]:\n" + contexto.strip() + "\n"
            "[Pergunta]: " + pergunta.strip() + "\n"
            "[Resposta]:"
        )
    else:
        prompt = (
            "Responda de forma direta, clara e concisa, sem listar tópicos.\n"
            "Evite detalhamento excessivo, mas garanta que a resposta seja fácil de entender.\n"
            "\n[Pergunta]: " + pergunta.strip() + "\n[Resposta]:"
        )
    response = client.chat.complete(
        model=modelo,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.12,
        max_tokens=512
    )
    resposta_bruta = response.choices[0].message.content.strip()
    return otimizar_resposta(resposta_bruta)

def responder_pergunta_chatbot(pergunta, contexto=None, tipo=None, input_dir="uploads", index_path=None):
    """
    Recebe pergunta, tipo ('manual' ou 'upload'), lê o texto correspondente e passa como contexto para o modelo Mistral.
    """
    if not contexto:
        contexto = carregar_texto(tipo, input_dir)
    return gerar_resposta_mistral(pergunta, contexto)

# Exemplo de uso isolado
if __name__ == "__main__":
    resposta = responder_pergunta_chatbot(
        pergunta="Quais são os tópicos principais do texto?",
        tipo="manual"
    )
    print(resposta)
