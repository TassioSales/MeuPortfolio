# 🧠 Análise Inteligente de Textos

Este sistema web permite a análise avançada de textos em português, combinando IA generativa, análise de sentimentos, visualização e chatbot contextual. O objetivo é oferecer uma solução completa para explorar, resumir, compreender e interagir com textos de qualquer tamanho, de forma simples e visual.

## 🚀 Principais Funcionalidades

- **Texto Manual:** Digite ou cole textos diretamente na interface para análise.
- **Upload de Arquivo:** Envie arquivos `.txt` ou `.pdf` e o sistema extrai e processa automaticamente o conteúdo.
- **Visualização:** Veja o texto carregado, alterne entre modos manual/upload e confira o conteúdo antes de analisar.
- **Resumo Automático:** Gere resumos de textos extensos usando IA (MistralAI), facilitando a compreensão rápida do conteúdo.
- **Análise de Sentimento:** Utilize múltiplos modelos (TextBlob, transformers, scikit-learn, pysentimiento, CardiffNLP) para avaliar o sentimento de cada frase e do texto geral.
- **Análise Inteligente:** Pipeline completo que inclui extração de frases, análise de sentimentos, geração de WordCloud, gráficos e insights contextuais com LlamaIndex.
- **Chatbot do Documento:** Faça perguntas sobre o texto carregado e obtenha respostas contextuais baseadas apenas no conteúdo fornecido.
- **Visualização de Dados:** WordCloud de palavras-chave e gráficos de distribuição de sentimentos, tornando os resultados mais intuitivos.
- **Exportação e Cópia:** Copie ou baixe resultados de resumo e análise facilmente.

## 🏗️ Estrutura da Aplicação

```
projeto/
├── app.py                  # Servidor Flask principal, define as rotas e integra todos os módulos
├── analise_de_sentimento.py # Funções de análise de sentimento (vários modelos)
├── analise_inteligente.py   # Pipeline de análise inteligente, visualização e contexto
├── resumo.py                # Geração automática de resumos com IA
├── chatbot_backend.py       # Backend do chatbot contextual (perguntas e respostas)
├── requirements.txt         # Lista de dependências Python
├── static/                  # Arquivos estáticos (CSS, JS, logo.svg, imagens)
├── templates/               # Templates HTML da interface web
├── uploads/                 # Textos enviados pelo usuário (armazenados em JSON)
│   ├── manual_text.json     # Texto digitado manualmente
│   └── upload_text.json     # Texto extraído de upload
├── index/                   # Armazenamento de índices/contexto para busca inteligente
├── logging_config.py        # Configuração e padronização dos logs do sistema
└── ...
```

## ⚙️ Tecnologias Utilizadas

- **Flask:** Backend web e roteamento
- **HTML/CSS/JavaScript:** Frontend moderno e responsivo
- **MistralAI:** Geração de resumos e respostas com IA generativa
- **LlamaIndex:** Busca contextual e análise inteligente
- **Transformers (HuggingFace):** Modelos de sentimento e emoção
- **NLTK, TextBlob, scikit-learn, joblib:** NLP tradicional e ML
- **PyPDF2:** Extração de texto de PDFs
- **matplotlib, wordcloud:** Visualização de dados
- **deep-translator:** Tradução automática, se necessário

## 🔒 Privacidade e Segurança
- Todos os dados enviados pelo usuário são processados localmente.
- Nenhum texto ou resultado é compartilhado com terceiros.
- O logo do sistema é gerado automaticamente (SVG) e não depende de imagens externas.

## 📝 Pré-requisitos
- Python 3.8+
- `pip` instalado
- Chave de API MistralAI (crie um arquivo `.env` na raiz do projeto):
  ```
  MISTRAL_API_KEY=SEU_TOKEN_AQUI
  ```

## 🛠️ Instalação e Execução
1. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Execute o servidor Flask:**
   ```bash
   python app.py
   ```
3. **Acesse pelo navegador:**
   - Vá para [http://localhost:5000](http://localhost:5000)

## 🧩 Como Usar

1. **Escolha o modo de entrada:**
   - Digite texto manualmente ou faça upload de um arquivo `.txt` ou `.pdf`.
2. **Visualize o texto carregado:**
   - Confira se o conteúdo está correto antes de analisar.
3. **Gere o resumo (opcional):**
   - Para textos grandes, utilize o botão de resumo para obter uma versão condensada.
4. **Execute a análise de sentimento:**
   - Veja o sentimento por frase e o sentimento geral do texto.
5. **Acesse a análise inteligente:**
   - Veja insights detalhados, WordCloud, gráficos e contexto extraído do texto.
6. **Utilize o chatbot:**
   - Faça perguntas sobre o texto/documento e obtenha respostas precisas baseadas apenas no conteúdo carregado.
7. **Baixe ou copie resultados:**
   - Use os botões de exportação para salvar ou copiar resumos e análises.

## 💡 Dicas Avançadas
- O sistema aceita textos longos e arquivos grandes, mas recomenda-se usar o resumo para garantir análises rápidas.
- O chatbot responde apenas com base no texto carregado, garantindo privacidade e foco.
- Os logs do sistema são organizados e podem ser consultados no console para depuração.

## 🖼️ Prints e Exemplos
> Adicione aqui prints de tela ou GIFs mostrando o uso do sistema para facilitar o entendimento de novos usuários.

## 📚 Créditos e Referências
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

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.
