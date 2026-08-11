# Transcritor & Analisador de Áudios do WhatsApp

Ferramenta local (offline) para **transcrever áudios do WhatsApp em português** e
fazer uma **triagem de conteúdo** — cruzando cada áudio com o texto exportado da
conversa para identificar quem enviou, quando, e sinalizar trechos de interesse.

Roda 100% na sua máquina com [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper).
Nenhum áudio é enviado para a internet (só o download único do modelo de fala).

> ⚠️ **Dados pessoais:** a pasta `dados/` (áudios, transcrições, relatório) está no
> `.gitignore` e **não deve ser publicada**. É conteúdo privado.

---

## Stack

Python + faster-whisper (CTranslate2) + Streamlit + ffmpeg

## Estrutura

```
transcritor_whatsapp/
├── src/
│   ├── transcrever.py    # transcreve os áudios (retomável, salva incremental)
│   ├── analisar.py       # cruza com a conversa + sinaliza termos por categoria
│   └── app.py            # visualizador web (Streamlit) com busca e filtro
├── dados/                # (gitignored) seus dados reais
│   ├── audios/           # coloque aqui os .opus / .ogg / .m4a / .mp3 / .wav
│   ├── conversa_whatsapp.txt   # o "Conversa do WhatsApp com ....txt" exportado
│   └── saidas/           # transcricoes.txt/.json e relatorio_analise.txt
├── requirements.txt
├── run.bat               # atalho Windows: instala + transcreve + analisa
└── README.md
```

---

## Como usar

### 1. Pré-requisitos
- **Python 3.9+**
- **ffmpeg** (necessário para ler `.opus`). No Windows: `winget install Gyan.FFmpeg`

### 2. Instalar
```bash
pip install -r requirements.txt
```

### 3. Colocar os dados
- Exporte a conversa no WhatsApp (**Conversa → Mais → Exportar conversa → Incluir mídia**).
- Extraia o `.zip` e coloque os áudios em `dados/audios/` e o `.txt` como
  `dados/conversa_whatsapp.txt`.

### 4. Transcrever
```bash
python src/transcrever.py                 # modelo small (rápido)
python src/transcrever.py -m medium       # mais preciso, ~3x mais lento
```
Gera `dados/saidas/transcricoes.txt` e `.json`. **É retomável**: se parar, rode de
novo que ele continua de onde parou.

### 5. Analisar (cruza remetente + sinaliza termos)
```bash
python src/analisar.py
python src/analisar.py --autor "+55 61 9657-4839"   # foca num remetente
```
Gera `dados/saidas/relatorio_analise.txt`.

### 6. Visualizar (opcional)
```bash
streamlit run src/app.py
```
Interface web com busca no texto e filtro por remetente.

### Atalho (Windows)
Dê dois cliques em **`run.bat`** — instala, transcreve e gera o relatório.

---

## Escolha do modelo

| Modelo | Velocidade (CPU) | Qualidade | Quando usar |
|--------|------------------|-----------|-------------|
| `small` | ~4x tempo real | boa | uso geral (padrão) |
| `medium` | ~1.5x tempo real | ótima | áudio ruim / sotaque forte |
| `large-v3` | lento sem GPU | melhor | só com GPU (CUDA) |

Detecta GPU CUDA automaticamente e usa `float16`; sem GPU usa `int8` na CPU.

---

## ⚠️ Aviso importante sobre a análise

O `analisar.py` faz uma **triagem automática por palavras-chave** — serve para
localizar rapidamente trechos que merecem leitura atenta. **Não é laudo nem prova
jurídica**, e produz falsos positivos e negativos. Sempre leia a transcrição
completa no contexto. Para fins legais/trabalhistas, procure um(a) advogado(a).

## Licença

Uso pessoal. Os dados em `dados/` são privados e não fazem parte do projeto.
