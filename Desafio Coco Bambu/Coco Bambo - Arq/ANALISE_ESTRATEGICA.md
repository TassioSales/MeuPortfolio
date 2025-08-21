# Análise Estratégica de Performance - Coco Bambu

## Índice
- [1. Decisões Estratégicas de Modelagem e ETL](#1-decisões-estratégicas-de-modelagem-e-etl)
  - [Modelagem de Dados](#modelagem-de-dados)
  - [Tratamento e Preparação dos Dados](#tratamento-e-preparação-dos-dados)
- [2. Arquitetura Visual e Análises Desenvolvidas](#2-arquitetura-visual-e-análises-desenvolvidas)
  - [Visão Geral do Dashboard](#visão-geral-do-dashboard)
  - [Análises Principais](#análises-principais)
- [3. Métricas de Negócio (DAX)](#3-métricas-de-negócio-dax)
- [4. Análise de Resultados e Insights Estratégicos](#4-análise-de-resultados-e-insights-estratégicos)
  - [Sumário Executivo](#sumário-executivo)
  - [Destaques e Pontos de Atenção](#destaques-e-pontos-de-atenção)
  - [Recomendações Estratégicas](#recomendações-estratégicas)

## 1. Decisões Estratégicas de Modelagem e ETL

### Modelagem de Dados
A arquitetura do projeto foi desenvolvida com foco em performance, escalabilidade e experiência do usuário final, permitindo que os insights fossem extraídos de forma rápida e intuitiva.

**Principais características:**
- Modelo estrela otimizado para análise dimensional
- Tabelas de fatos e dimensões bem definidas
- Relacionamentos otimizados para performance

### Tratamento e Preparação dos Dados (Power Query - ETL)

**Transformações realizadas:**
- Padronização de formatos de data
- Tratamento de valores nulos e outliers
- Criação de hierarquias e categorizações
- Cálculo de métricas derivadas

**Exemplo de transformação em Power Query:**
```powerquery
// Transformação de Data
let
    Source = Excel.Workbook(File.Contents("Caminho\\Arquivo.xlsx"), null, true),
    Fato_Sheet = Source{[Item="Fato",Kind="Sheet"]}[Data],
    #"Cabeçalhos Promovidos" = Table.PromoteHeaders(Fato_Sheet, [PromoteAllScalars=true])
in
    #"Cabeçalhos Promovidos"
```

## 2. Arquitetura Visual e Análises Desenvolvidas

### Visão Geral do Dashboard
O dashboard foi projetado seguindo princípios de design thinking e análise de negócios, organizado em camadas analíticas que permitem uma navegação intuitiva dos indicadores macro até os detalhes operacionais.

### Análises Principais

#### 📊 Desempenho Mensal
Análise comparativa mês a mês entre receita realizada e orçada.

#### 📅 Comparativo Anual
Visão comparativa (YoY) que permite identificar tendências e padrões de crescimento.

#### 🗺️ Análise Geográfica
Distribuição de receita por região/UF, identificando mercados-chave.

#### 📈 Performance por Modelo
Avaliação da eficiência dos diferentes modelos de negócio.

## 3. Métricas de Negócio (DAX)

### Medidas de Receita
```dax
// Receita Total
Receita Total = 
CALCULATE(
    SUM(Fato[valor]), 
    Campos[conta] = "1 FATURAMENTO"
)

// Orçamento de Receita
Orçamento Receita = 
CALCULATE(
    SUM(Fato[valor_orcado]), 
    Campos[conta] = "1 FATURAMENTO"
)

// Variação % vs Orçamento
Variação % vs Orçamento = 
DIVIDE(
    [Receita Total] - [Orçamento Receita], 
    [Orçamento Receita]
)
```

### Medidas de Custo e Rentabilidade
```dax
// Custo de Matéria Prima
Custo de Matéria Prima = 
ABS(
    CALCULATE(
        SUM(Fato[valor]), 
        Campos[conta] = "2 MATERIA PRIMA"
    )
)

// Margem Bruta
Margem Bruta = [Receita Total] - [Custo de Matéria Prima]

// Margem Bruta %
Margem Bruta % = 
DIVIDE(
    [Margem Bruta], 
    [Receita Total]
)
```

## 4. Análise de Resultados e Insights Estratégicos

### Sumário Executivo
A análise revelou crescimento anual positivo de **1.59%**, com a rede superando o orçamento em **2.06%**. No entanto, existem diferenças significativas no desempenho entre diferentes modelos de negócio e regiões.

**Métricas Principais:**
- **Receita Total:** R$ 21.40 bi
- **Resultado vs Orçamento:** +2.06%
- **Crescimento Anual:** +1.59%

### Destaques e Pontos de Atenção

#### ✅ Destaques Positivos
- **Nordeste:** Melhor performance, superando metas com destaque em lojas âncora
- **Modelos "Conceito" e "Buffet":** Menor participação no faturamento, mas maior eficiência em superar orçamento
- **Junho/2025:** Crescimento expressivo de **+10.9%** (YoY)

#### ⚠️ Pontos de Atenção
- **Modelo "Restaurante" (R$ 17.09 bi):** Apesar de representar o maior volume, ficou abaixo do orçamento
- **Modelo "VASTO":** Apresenta resultado negativo frente ao planejado
- **Custos:** Categoria "2.1 INSUMOS" = 82.78% dos custos totais

### Recomendações Estratégicas

#### 1. Otimização de Custos
- Revisão de contratos com fornecedores de insumos
- Implementação de programas de redução de desperdício
- Análise de substituição de itens de alto custo

#### 2. Melhoria de Desempenho
- Replicação das melhores práticas dos modelos "Conceito" e "Buffet"
- Análise detalhada das lojas com desempenho abaixo da média
- Treinamento de equipes nas regiões com menor desempenho

#### 3. Aprofundamento Analítico
- Investigação das causas do crescimento de junho
- Análise de sazonalidade para melhor planejamento orçamentário
- Segmentação de clientes por perfil de consumo

---
*Relatório gerado em 20 de Agosto de 2025 | Desenvolvido por Tassio Lucian de Jesus Sales*  
*Confidencial - Uso exclusivo da Coco Bambu*
