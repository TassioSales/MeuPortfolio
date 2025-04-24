# 🚀 Meu Portfólio de Projetos

Bem-vindo ao meu portfólio de projetos! Aqui você encontrará uma coleção de aplicações que desenvolvi, demonstrando minhas habilidades em desenvolvimento de software, ciência de dados e inteligência artificial.

## 📦 Projetos

### 1. Sistema de Gerenciamento de Estoque

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white)

Um sistema completo para gerenciamento de estoque com backend em FastAPI e frontend em Flask. Permite controle total de produtos, movimentações de estoque e geração de relatórios.

**Principais funcionalidades:**
- Cadastro e gerenciamento de produtos
- Controle de entradas e saídas
- Dashboard com estatísticas
- Interface moderna e responsiva

📝 [Documentação Completa](https://github.com/TassioSales/MeuPortfolio/blob/main/estoque-api/README.md)  
📄 [Licença](https://github.com/TassioSales/MeuPortfolio/blob/main/estoque-api/LICENSE)

### 2. API de Gerenciamento de Tarefas (TODO)

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![SQLite](https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white)

Uma API RESTful para gerenciamento de tarefas, construída com FastAPI. Oferece funcionalidades completas para criar, atualizar, listar e excluir tarefas.

**Principais funcionalidades:**
- CRUD completo de tarefas
- Categorização de tarefas
- Priorização
- Documentação Swagger/OpenAPI

📝 [Documentação Completa](https://github.com/TassioSales/MeuPortfolio/blob/main/todo_api/README.md)  
📄 [Licença](https://github.com/TassioSales/MeuPortfolio/blob/main/todo_api/LICENSE)

---

## 🧠 Projeto Destaque: Análise Inteligente de Textos

### Descrição Geral

Este sistema web permite a análise avançada de textos em português, incluindo:
- **Resumo automático**
- **Análise de sentimento** (vários modelos)
- **Análise inteligente com contexto** (LlamaIndex)
- **Chatbot contextual**
- **Visualização de dados** (WordCloud e gráficos)
- Upload e processamento de arquivos `.txt` e `.pdf`

### Principais Tecnologias
- Flask (backend web)
- HTML, CSS, JavaScript (frontend)
- Python (core)
- MistralAI (IA generativa)
- LlamaIndex (busca contextual)
- Transformers (modelos de sentimento)
- NLTK, TextBlob, scikit-learn, PyPDF2, matplotlib, wordcloud

### Estrutura do Projeto
```
projeto/
├── app.py                  # Servidor Flask principal
├── analise_de_sentimento.py # Análise de sentimento (vários modelos)
├── analise_inteligente.py   # Pipeline de análise inteligente e visualização
├── resumo.py                # Geração de resumo automático
├── chatbot_backend.py       # Backend do chatbot contextual
├── requirements.txt         # Dependências Python
├── static/                  # Arquivos estáticos (CSS, JS, logo.svg)
├── templates/               # Templates HTML (interface web)
├── uploads/                 # Textos enviados pelo usuário
│   ├── manual_text.json
│   └── upload_text.json
├── index/                   # Armazenamento de índices/contexto
└── ...
```

### Funcionalidades Detalhadas
- **Texto Manual:** Digite ou cole textos diretamente na interface para análise.
- **Upload de Arquivo:** Envie arquivos `.txt` ou `.pdf` para análise automática.
- **Visualização:** Veja o texto carregado e navegue entre modos manual/upload.
- **Resumo:** Gere resumos automáticos com IA (MistralAI) para textos extensos.
- **Análise de Sentimento:** Utilize diferentes modelos (TextBlob, transformers, scikit-learn, pysentimiento, CardiffNLP) para avaliar o sentimento do texto.
- **Análise Inteligente:** Pipeline completo que inclui extração de frases, análise de sentimentos, geração de WordCloud, gráficos e insights contextuais.
- **Chatbot do Documento:** Faça perguntas sobre o texto carregado e obtenha respostas contextuais.
- **Visualização de Dados:** WordCloud de palavras-chave e gráficos de distribuição de sentimentos.

### Como Executar Localmente

1. **Pré-requisitos:**
   - Python 3.8+
   - `pip` (gerenciador de pacotes)
   - Crie um arquivo `.env` com sua chave da API MistralAI:  
     `MISTRAL_API_KEY=SEU_TOKEN_AQUI`

2. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Execute o servidor Flask:**
   ```bash
   python app.py
   ```

4. **Acesse o sistema:**
   - Abra o navegador e acesse: [http://localhost:5000](http://localhost:5000)

### Fluxo de Uso

1. **Escolha o modo de entrada:**
   - Digite texto manualmente ou faça upload de um arquivo.
2. **Visualize e confira o texto carregado.**
3. **Gere resumo** (opcional para textos grandes).
4. **Execute a análise de sentimento** e veja o resultado por frase e geral.
5. **Acesse a análise inteligente** para insights avançados, WordCloud e gráficos.
6. **Utilize o chatbot** para perguntas contextuais sobre o texto/documento.
7. **Baixe ou copie resultados** conforme necessário.

### Observações Importantes
- O sistema é totalmente web, não requer instalação de aplicativos adicionais.
- Todos os dados permanecem privados e são processados localmente.
- O logo do sistema é gerado automaticamente (SVG).
- Para uso de IA generativa, é necessário possuir uma chave de API MistralAI.

## 📑 Créditos e Referências
- [MistralAI](https://mistral.ai/)
- [LlamaIndex](https://github.com/jerryjliu/llama_index)
- [HuggingFace Transformers](https://huggingface.co/transformers/)
- [NLTK](https://www.nltk.org/)
- [TextBlob](https://textblob.readthedocs.io/en/dev/)
- [scikit-learn](https://scikit-learn.org/)
- [matplotlib](https://matplotlib.org/)
- [wordcloud](https://github.com/amueller/word_cloud)

## 👤 Autor

**Tassio Sales**
- GitHub: [@TassioSales](https://github.com/TassioSales)

## 📝 Licença

Todos os projetos estão sob a licença MIT. Veja os arquivos LICENSE em cada projeto para mais detalhes.