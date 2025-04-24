Sentiment Analyzer
Uma aplicação web para análise de sentimentos e emoções em textos em português.
Funcionalidades

Upload de arquivos .txt ou .pdf
Entrada de texto via formulário
Análise de sentimentos e emoções com modelos de NLP
Visualizações interativas (WordCloud, gráficos de barras, pizza, heatmap)
Exportação de resultados em CSV ou JSON
Interface amigável com Bootstrap

Tecnologias

Back-end: Flask, Python, asyncio
NLP: spaCy, Hugging Face Transformers
Gráficos: Matplotlib, Seaborn, WordCloud
Front-end: HTML, Bootstrap, JavaScript
Testes: Pytest

Instalação

Clone o repositório:
git clone <repo-url>
cd sentiment-analyzer


Crie um ambiente virtual:
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows


Instale as dependências:
pip install -r requirements.txt


Instale o modelo spaCy:
python -m spacy download pt_core_news_sm


Crie um arquivo .env com:
SECRET_KEY=your-secret-key


Execute a aplicação:
python run.py



Uso

Acesse http://localhost:5000 no navegador.
Insira um texto ou faça upload de um arquivo .txt/.pdf.
Visualize os resultados e exporte em CSV ou JSON.

Testes
Execute os testes com:
pytest tests/


