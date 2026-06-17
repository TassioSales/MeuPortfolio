<div align="center">

# 📚 ENEM Insights

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-3776ab?style=flat-square&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/Streamlit-1.35+-ff4b4b?style=flat-square&logo=streamlit&logoColor=white">
  <img src="https://img.shields.io/badge/Scikit--learn-GradientBoosting-f7931e?style=flat-square&logo=scikit-learn&logoColor=white">
  <img src="https://img.shields.io/badge/Plotly-Interactive-3F4F75?style=flat-square&logo=plotly&logoColor=white">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ed?style=flat-square&logo=docker&logoColor=white">
</p>

**Dashboard interativo de análise do ENEM com modelo de Machine Learning que prevê a nota de um estudante com base em seu perfil socioeconômico.**

</div>

---

## Sobre o Projeto

O **ENEM (Exame Nacional do Ensino Médio)** é realizado por cerca de **5 milhões de estudantes** por ano e é a principal porta de entrada para o ensino superior no Brasil. O INEP disponibiliza os microdados completos como dados abertos.

Este projeto transforma esses dados em insights visuais e preditivos, respondendo perguntas como:

- Quanto a renda familiar influencia na nota?
- Qual a diferença real entre escola pública e privada?
- Quais regiões do Brasil têm melhor desempenho e por quê?
- Dado o perfil de um estudante, qual nota ele pode esperar no ENEM?

---

## Funcionalidades

### 5 Páginas Interativas

| Página | Descrição |
|--------|-----------|
| 🏠 Visão Geral | KPIs, distribuição de notas por disciplina, evolução anual |
| 🗺️ Análise Regional | Ranking de regiões e estados, radar de desempenho por disciplina |
| 🏫 Pública vs Privada | Gap de desempenho por tipo de escola em todas as disciplinas |
| 💰 Fatores Socioeconômicos | Impacto de renda, raça/etnia e gênero na nota, matriz de correlação |
| 🤖 Preditor de Nota | Modelo ML que estima sua nota com base no perfil pessoal |

### Modelo de Machine Learning

- **Algoritmo:** Gradient Boosting Regressor
- **Features:** tipo de escola, faixa de renda, região, gênero, raça/etnia
- **Performance:** MAE ~60 pontos, R² ~0.6
- **Visualização:** gauge interativo com faixas de desempenho

### Dados

O app funciona em dois modos:

- **Demo (padrão):** 50.000 registros sintéticos com as mesmas distribuições estatísticas dos microdados reais do INEP
- **Real:** aponta para o CSV oficial do INEP via variável de ambiente

---

## Instalação

### Requisitos

- Python 3.12+
- pip

### Rodando localmente

```bash
# Clone o repositório e entre na pasta
cd enem_insights

# Instale as dependências
pip install -r requirements.txt

# Copie e configure as variáveis de ambiente
cp .env.example .env

# Inicie o app
streamlit run app/main.py
```

Acesse em `http://localhost:8501`

### Com Docker

```bash
docker-compose up --build
```

---

## Usando Dados Reais do INEP

1. Baixe os microdados em: [gov.br/inep — Microdados ENEM](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enem)
2. Extraia o arquivo `.csv` (encoding Latin-1, separador `;`)
3. Configure no `.env`:

```env
ENEM_DATA_PATH=/caminho/para/MICRODADOS_ENEM_2023.csv
ENEM_SAMPLE_SIZE=100000   # 0 = todos os registros (~5M linhas)
```

---

## Estrutura do Projeto

```
enem_insights/
├── app/
│   ├── main.py            # Dashboard Streamlit (5 páginas)
│   ├── data_loader.py     # Carregamento e geração de dados sintéticos
│   ├── analytics.py       # Funções de análise estatística
│   ├── ml_model.py        # Pipeline de ML (Gradient Boosting)
│   └── charts.py          # Gráficos Plotly
├── data/                  # Coloque os CSVs do INEP aqui
├── tests/
│   └── test_analytics.py  # Testes unitários (pytest)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Testes

```bash
python -m pytest tests/ -v
```

---

## Stack Técnica

| Camada | Tecnologia |
|--------|-----------|
| Interface | Streamlit |
| Visualização | Plotly |
| Análise de dados | Pandas, NumPy |
| Machine Learning | Scikit-learn (GradientBoostingRegressor) |
| Infraestrutura | Docker, docker-compose |
| Qualidade | pytest |

---

## Fonte dos Dados

- **INEP/MEC** — [Microdados ENEM](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enem) (dados abertos do governo federal)
- Em modo demo, os dados sintéticos são gerados com `numpy` respeitando as distribuições reais de participação por estado, tipo de escola e faixa de renda.

---

<div align="center">

**© 2025 — Tássio Sales**

</div>
