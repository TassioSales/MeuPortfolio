# 📊 DataNarrator

<div align="center">

<img src="https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Bar%20chart/3D/bar_chart_3d.png" width="100" alt="DataNarrator">

**Transforme qualquer CSV em uma análise completa com narrativa gerada por IA.**

![Python](https://img.shields.io/badge/Python-3.12+-3776ab?style=flat-square&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.37%2B-ff4b4b?style=flat-square&logo=streamlit&logoColor=white)
![Mistral AI](https://img.shields.io/badge/Mistral_AI-Large-ff7000?style=flat-square)
![Plotly](https://img.shields.io/badge/Plotly-5.23-3f4f75?style=flat-square&logo=plotly&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-00d4aa?style=flat-square)

</div>

---

## O que é

DataNarrator é uma ferramenta de análise exploratória automatizada. Você sobe um CSV ou Excel, e a aplicação:

1. **Perfila** o dataset automaticamente (tipos, ausentes, duplicatas, estatísticas)
2. **Visualiza** distribuições, correlações e scatter interativo
3. **Narra** os dados com Mistral AI — resumo executivo, qualidade, padrões, recomendações
4. **Exporta** o relatório em PDF, CSV limpo e JSON de perfil

## Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Interface | Streamlit |
| Visualizações | Plotly |
| IA | Mistral Large |
| PDF | fpdf2 |
| Dados | Pandas |

## Como rodar

```bash
# 1. Clone o repositório
git clone https://github.com/TassioSales/MeuPortfolio.git
cd MeuPortfolio/data_narrator

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Configure a API Key
cp .env.example .env
# edite .env e coloque sua MISTRAL_API_KEY

# 4. Rode
streamlit run app.py
```

## Funcionalidades

- **Upload** CSV ou Excel (UTF-8, Latin-1, CP1252 auto-detectado)
- **Métricas** rápidas: linhas, colunas, ausentes, duplicatas
- **EDA automático**: histogramas, barras para categóricas, matriz de correlação, scatter explorer
- **Narrativa IA**: resumo executivo, qualidade dos dados, padrões, correlações esperadas, recomendações de negócio
- **Exportação**: PDF com narrativa completa, CSV limpo, JSON de perfil, CSV de estatísticas

## Estrutura

```
data_narrator/
├── app.py           # aplicação principal
├── requirements.txt
├── .env.example
└── README.md
```

## Casos de uso

- Análise rápida de datasets desconhecidos
- Geração de relatório inicial para stakeholders
- Exploração de dados antes de modelagem ML
- Auditoria de qualidade de dados

---

<div align="center">

Feito por [Tássio Sales](https://github.com/TassioSales)

</div>
