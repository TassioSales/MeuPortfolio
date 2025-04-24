import os
from mistralai import Mistral
from dotenv import load_dotenv

load_dotenv()

MAX_TOKENS = 32000  # Novo limite para modelos maiores (ex: mistral-large-latest)
TOKEN_MARGIN = 2000  # Margem de segurança maior

# Função para estimar tokens (1 token ~ 4 caracteres)
def estimar_tokens(texto):
    return int(len(texto) / 4)

def truncar_texto_token(texto, max_tokens):
    aprox_chars = max_tokens * 4
    if len(texto) <= aprox_chars:
        return texto
    corte = texto[:int(aprox_chars)].rfind(' ')
    return texto[:corte] if corte > 0 else texto[:int(aprox_chars)]

def gerar_resumo(texto):
    """
    Gera um resumo textual do texto usando o modelo mistral-large-latest (MistralAI)
    Retorna o resumo textual gerado pela IA.
    Limita o texto para não exceder o máximo de tokens do modelo (32000).
    Também imprime no log a quantidade de tokens usada no prompt.
    """
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("API key Mistral não encontrada no ambiente!")
    model = "mistral-large-latest"
    client = Mistral(api_key=api_key)
    prompt_fixo = (
        "Resuma o texto abaixo de forma clara, objetiva e organizada, seguindo estes tópicos:\n"
        "- Tema principal\n"
        "- Pontos mais importantes\n"
        "- Personagens ou elementos centrais (se houver)\n"
        "- Conclusão ou desfecho\n"
        "- Linguagem simples, sem copiar trechos\n"
        "Texto:\n"
    )
    tokens_prompt = estimar_tokens(prompt_fixo)
    tokens_disponiveis = MAX_TOKENS - TOKEN_MARGIN - tokens_prompt
    texto_truncado = truncar_texto_token(texto, tokens_disponiveis)
    prompt = prompt_fixo + texto_truncado
    while estimar_tokens(prompt) > (MAX_TOKENS - TOKEN_MARGIN):
        texto_truncado = truncar_texto_token(texto_truncado, tokens_disponiveis - 1000)
        prompt = prompt_fixo + texto_truncado
        if len(texto_truncado) < 1000:
            break
    total_tokens = estimar_tokens(prompt)
    print(f"[RESUMO] Tokens usados no prompt: {total_tokens}")
    chat_response = client.chat.complete(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            },
        ]
    )
    resumo = chat_response.choices[0].message.content
    print("Resumo gerado:\n", resumo)
    return resumo
