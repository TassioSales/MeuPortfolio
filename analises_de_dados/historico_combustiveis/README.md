<div align="center">

# 📊 Análise de Dados de Combustíveis no Brasil (2004-2011)

<p align="center">
  <img src="https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Fuel%20pump/3D/fuel_pump_3d.png" width="120" alt="Bomba de Combustível">
</p>

<h3 align="center">✨ <em>Análise detalhada dos preços de combustíveis em todo o território nacional</em> ✨</h3>
<p align="center"><strong>Dados históricos da ANP (Agência Nacional do Petróleo, Gás Natural e Biocombustíveis)</strong></p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-3776ab?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Pandas-2.0%2B-150458?style=flat-square&logo=pandas&logoColor=white" alt="Pandas">
  <img src="https://img.shields.io/badge/Matplotlib-3.7%2B-11557c?style=flat-square&logo=matplotlib&logoColor=white" alt="Matplotlib">
  <img src="https://img.shields.io/badge/Seaborn-0.12%2B-4a8bbf?style=flat-square&logo=seaborn&logoColor=white" alt="Seaborn">
  <img src="https://img.shields.io/badge/Jupyter-Notebook-orange?style=flat-square&logo=jupyter&logoColor=white" alt="Jupyter">
</p>

</div>

## 📊 Visão Geral do Projeto

Este repositório contém a análise completa dos dados históricos de preços de combustíveis no Brasil, coletados pela ANP entre os anos de 2004 e 2011. O projeto foi desenvolvido para entender as variações de preços, tendências regionais e comportamento do mercado de combustíveis no período.

## 🚀 Principais Recursos

- **Análise temporal** dos preços de combustíveis
- **Comparação regional** entre estados e municípios
- **Tratamento completo** de dados faltantes e outliers
- **Visualizações interativas** de tendências de preços
- **Análise de sazonalidade** e variações anuais

## 📂 Estrutura do Projeto

```
📁 historico_combustiveis/
├── 📄 download_de_arquivos.ipynb    # Script para baixar os dados da ANP
├── 📄 tratamento_2004.ipynb         # Análise do ano de 2004
├── 📄 tratamento_2005.ipynb         # Análise do ano de 2005
├── 📄 tratamento_2006.ipynb         # Análise do ano de 2006
├── 📄 tratamento_2007.ipynb         # Análise do ano de 2007
├── 📄 tratamento_2008.ipynb         # Análise do ano de 2008
├── 📄 tratamento_2009.ipynb         # Análise do ano de 2009
├── 📄 tratamento_2010.ipynb         # Análise do ano de 2010
└── 📄 tratamento_2011.ipynb         # Análise do ano de 2011
```

## 🛠️ Tecnologias Utilizadas

- **Python 3.8+**
- **Pandas**: Para manipulação e análise de dados
- **Matplotlib/Seaborn**: Para visualização de dados
- **Jupyter Notebook**: Para documentação interativa
- **NumPy**: Para operações numéricas
- **Datetime**: Para manipulação de datas

## 🚀 Como Executar

1. **Pré-requisitos**
   ```bash
   pip install -r requirements.txt
   ```

2. **Executando as Análises**
   - Abra o Jupyter Notebook:
     ```bash
     jupyter notebook
     ```
   - Navegue até a pasta do projeto e abra o notebook desejado
   - Execute as células em sequência

## 📊 Exemplo de Visualização

```python
# Gráfico de linha mostrando a evolução dos preços médios
plt.figure(figsize=(14, 7))
sns.lineplot(data=df, x='data', y='valor_venda', hue='produto')
plt.title('Evolução dos Preços de Combustíveis (2004-2011)')
plt.xlabel('Ano')
plt.ylabel('Preço Médio (R$)')
plt.legend(title='Combustível')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
```

## 📌 Principais Descobertas

1. **Tendência de Alta**
   - Aumento médio de X% ao ano nos preços dos combustíveis
   - Maior variação observada no ano de 20XX

2. **Diferenças Regionais**
   - Região X apresenta os preços mais altos
   - Estado Y tem a menor variação de preços

3. **Sazonalidade**
   - Períodos de maior demanda (feriados, férias) impactam significativamente os preços

## 🤝 Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou enviar pull requests.

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas alterações (`git commit -m 'Add some AmazingFeature'`)
4. Dê push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.

## ✨ Destaques Técnicos

- **Tratamento de Dados**: Limpeza e padronização de mais de 1 milhão de registros
- **Análise Exploratória**: Descoberta de padrões e tendências
- **Visualização**: Gráficos profissionais e informativos
- **Documentação**: Código comentado e explicado


</div>
