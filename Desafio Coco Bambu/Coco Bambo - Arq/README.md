# Análise Estratégica de Performance - Coco Bambu

## 📊 Visão Geral do Projeto

**Dashboard Estratégico de Análise de Receita e Orçamento**  
*Desenvolvido por: Tassio Lucian de Jesus Sales*  
*Data: 20 de Agosto de 2025*

---

## 📋 Sumário

1. [Decisões Estratégicas de Modelagem e ETL](#1-decisões-estratégicas-de-modelagem-e-etl)
2. [Arquitetura Visual e Análises Desenvolvidas](#2-arquitetura-visual-e-análises-desenvolvidas)
3. [Métricas de Negócio (DAX)](#3-métricas-de-negócio-dax)
4. [Análise de Resultados e Insights Estratégicos](#4-análise-de-resultados-e-insights-estratégicos)

---

## 1. Decisões Estratégicas de Modelagem e ETL

### Modelagem de Dados

A arquitetura do projeto foi desenvolvida com foco em performance, escalabilidade e experiência do usuário final, permitindo que os insights fossem extraídos de forma rápida e intuitiva.

#### Principais Características

- **Esquema Estrela (Star Schema)** com tabela Fato centralizada para consultas eficientes
- **Tabela Calendário em DAX** dinâmica para análises temporais avançadas (YoY, MTD, QTD, YTD)
- Relacionamentos otimizados entre dimensões (Campos, Lojas) e fatos garantindo consistência
- Hierarquias bem definidas para navegação intuitiva (Ano > Mês > Dia)
- Medidas calculadas para métricas de negócio complexas

### Tratamento e Preparação dos Dados (Power Query - ETL)

#### Processo ETL Robusto
Foram implementadas transformações avançadas no Power Query para garantir a qualidade e consistência dos dados.

| Categoria | Detalhes |
|-----------|----------|
| 📅 **Transformação de Datas** | - Padronização do formato de data<br>- Extração de dia, mês, ano, trimestre<br>- Criação de hierarquias temporais |
| 🧹 **Limpeza de Dados** | - Tratamento de valores nulos<br>- Padronização de formatos<br>- Validação de consistência |
| 🗺️ **Enriquecimento Geográfico** | - Separação de Cidade/UF<br>- Agregação por região<br>- Preparação para visualizações de mapa |

#### Exemplo de Código Power Query

```powerquery
// Transformação de Data
let
    Source = Excel.Workbook(File.Contents("Caminho\\Arquivo.xlsx"), null, true),
    Fato_Sheet = Source{[Item="Fato",Kind="Sheet"]}[Data],
    #"Cabeçalhos Promovidos" = Table.PromoteHeaders(Fato_Sheet, [PromoteAllScalars=true]),
    #"Tipo Alterado" = Table.TransformColumnTypes(#"Cabeçalhos Promovidos",{{"mes_ano", type date}})
in
    #"Tipo Alterado"
```

---

## 2. Arquitetura Visual e Análises Desenvolvidas

### Visão Geral do Dashboard

O dashboard foi projetado seguindo princípios de design thinking e análise de negócios, organizado em camadas analíticas que permitem uma navegação intuitiva dos indicadores macro até os detalhes operacionais.

![Dashboard Overview](image/Captura%20de%20tela%202025-08-20%20215011.png)

### Principais Análises

#### 📊 Desempenho Mensal
- Análise comparativa mês a mês entre receita realizada e orçada
- Destaque para sazonalidades e desvios significativos

#### 📅 Comparativo Anual (Matriz)
- Receita de um mês comparada ao mesmo mês do ano anterior (YoY same month)
- Identificação de tendências de crescimento

#### 🌎 Performance Geográfica
- Visualização por cidade/UF com comparação ao orçamento
- Identificação de mercados estratégicos

#### 📊 Treemap por Modelo de Negócio
- Análise de receita vs eficiência em bater metas
- Identificação de padrões por segmento

---

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

// Crescimento Anual %
Crescimento Anual % = 
DIVIDE(
    [Receita Total] - [Receita Ano Anterior], 
    [Receita Ano Anual]
)
```

### Medidas de Custo e Rentabilidade

```dax
// Custo de Matéria Prima
Custo de Matéria Prima = 
CALCULATE(
    SUM(Fato[valor]), 
    Campos[conta] = "2 MATERIA PRIMA"
)

// Margem Bruta
Margem Bruta = 
[Receita Total] - [Custo de Matéria Prima]
```

---

## 4. Análise de Resultados e Insights Estratégicos

### 📊 Sumário Executivo

A análise revelou crescimento anual positivo de **1.59%**, com a rede superando o orçamento em **2.06%**. No entanto, existem diferenças significativas no desempenho entre diferentes modelos de negócio e regiões.

| Métrica | Valor |
|---------|-------|
| Receita Total | R$ 21.40 bi |
| Resultado vs Orçamento | +2.06% (Acima da meta) |
| Crescimento Anual (YoY) | +1.59% |

### ✅ Destaques Positivos

- **Nordeste**: Melhor performance, superando metas com destaque em lojas âncora
- **Modelos "Conceito" e "Buffet"**: Menor participação no faturamento, mas maior eficiência em superar orçamento
- **Junho/2025**: Crescimento expressivo de **+10.9%** (YoY), sinalizando retomada positiva

### ⚠️ Pontos de Atenção
- **Modelo "Restaurante" (R$ 17.09 bi)**: Apesar de representar o maior volume, ficou abaixo do orçamento
- **Modelo "VASTO"**: Apresenta resultado negativo frente ao planejado
- **Custos**: Categoria "2.1 INSUMOS" = 82.78% dos custos totais → precisa de otimização

### 📌 Recomendações Estratégicas

#### 1. Otimização de Custos
- Revisão de contratos com fornecedores de insumos
- Implementação de programas de redução de desperdício

#### 2. Melhoria de Desempenho
- Replicação das melhores práticas dos modelos "Conceito" e "Buffet"
- Análise detalhada das lojas com desempenho abaixo da média

#### 3. Aprofundamento Analítico
- Investigação das causas do crescimento de junho
- Análise de sazonalidade para melhor planejamento orçamentário

---

> **Nota:** Este dashboard foi desenvolvido no Power BI, utilizando boas práticas de modelagem de dados e visualização, garantindo desempenho e usabilidade para tomada de decisão estratégica.

---

📅 *Última atualização: 20 de Agosto de 2025*  
👤 *Desenvolvido por Tassio Lucian de Jesus Sales*

# Análise Estratégica de Performance - Coco Bambu

## 📊 Visão Geral do Projeto

**Dashboard Estratégico de Análise de Receita e Orçamento**  
*Desenvolvido por: Tassio Lucian de Jesus Sales*  
*Data: 20 de Agosto de 2025*

---

## 📋 Sumário

1. [Decisões Estratégicas de Modelagem e ETL](#1-decisões-estratégicas-de-modelagem-e-etl)
2. [Arquitetura Visual e Análises Desenvolvidas](#2-arquitetura-visual-e-análises-desenvolvidas)
3. [Métricas de Negócio (DAX)](#3-métricas-de-negócio-dax)
4. [Análise de Resultados e Insights Estratégicos](#4-análise-de-resultados-e-insights-estratégicos)

---

## 1. Decisões Estratégicas de Modelagem e ETL

### Modelagem de Dados

A arquitetura do projeto foi desenvolvida com foco em performance, escalabilidade e experiência do usuário final, permitindo que os insights fossem extraídos de forma rápida e intuitiva.

#### Principais Características

- **Esquema Estrela (Star Schema)** com tabela Fato centralizada para consultas eficientes
- **Tabela Calendário em DAX** dinâmica para análises temporais avançadas (YoY, MTD, QTD, YTD)
- Relacionamentos otimizados entre dimensões (Campos, Lojas) e fatos garantindo consistência
- Hierarquias bem definidas para navegação intuitiva (Ano > Mês > Dia)
- Medidas calculadas para métricas de negócio complexas

### Tratamento e Preparação dos Dados (Power Query - ETL)

#### Processo ETL Robusto
Foram implementadas transformações avançadas no Power Query para garantir a qualidade e consistência dos dados.

| Categoria | Detalhes |
|-----------|----------|
| 📅 **Transformação de Datas** | - Padronização do formato de data<br>- Extração de dia, mês, ano, trimestre<br>- Criação de hierarquias temporais |
| 🧹 **Limpeza de Dados** | - Tratamento de valores nulos<br>- Padronização de formatos<br>- Validação de consistência |
| 🗺️ **Enriquecimento Geográfico** | - Separação de Cidade/UF<br>- Agregação por região<br>- Preparação para visualizações de mapa |

#### Exemplo de Código Power Query

```powerquery
// Transformação de Data
let
    Source = Excel.Workbook(File.Contents("Caminho\\Arquivo.xlsx"), null, true),
    Fato_Sheet = Source{[Item="Fato",Kind="Sheet"]}[Data],
    #"Cabeçalhos Promovidos" = Table.PromoteHeaders(Fato_Sheet, [PromoteAllScalars=true]),
    #"Tipo Alterado" = Table.TransformColumnTypes(#"Cabeçalhos Promovidos",{{"mes_ano", type date}})
in
    #"Tipo Alterado"
```

---

## 2. Arquitetura Visual e Análises Desenvolvidas

### Visão Geral do Dashboard

O dashboard foi projetado seguindo princípios de design thinking e análise de negócios, organizado em camadas analíticas que permitem uma navegação intuitiva dos indicadores macro até os detalhes operacionais.

### Principais Análises

#### 📊 Desempenho Mensal
- Análise comparativa mês a mês entre receita realizada e orçada
- Destaque para sazonalidades e desvios significativos

#### 📅 Comparativo Anual (Matriz)
- Receita de um mês comparada ao mesmo mês do ano anterior (YoY same month)
- Identificação de tendências de crescimento

#### 🌎 Performance Geográfica
- Visualização por cidade/UF com comparação ao orçamento
- Identificação de mercados estratégicos

#### 📊 Treemap por Modelo de Negócio
- Análise de receita vs eficiência em bater metas
- Identificação de padrões por segmento

---

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

// Crescimento Anual %
Crescimento Anual % = 
DIVIDE(
    [Receita Total] - [Receita Ano Anterior], 
    [Receita Ano Anual]
)
```

### Medidas de Custo e Rentabilidade

```dax
// Custo de Matéria Prima
Custo de Matéria Prima = 
CALCULATE(
    SUM(Fato[valor]), 
    Campos[conta] = "2 MATERIA PRIMA"
)

// Margem Bruta
Margem Bruta = 
[Receita Total] - [Custo de Matéria Prima]
```

---

## 4. Análise de Resultados e Insights Estratégicos

### 📊 Sumário Executivo

A análise revelou crescimento anual positivo de **1.59%**, com a rede superando o orçamento em **2.06%**. No entanto, existem diferenças significativas no desempenho entre diferentes modelos de negócio e regiões.

### Métricas Principais

| Métrica | Valor |
|---------|-------|
| Receita Total | R$ 21.40 bi |
| Resultado vs Orçamento | +2.06% (Acima da meta) |
| Crescimento Anual (YoY) | +1.59% |

### ✅ Destaques Positivos

- **Nordeste**: Melhor performance, superando metas com destaque em lojas âncora
- **Modelos "Conceito" e "Buffet"**: Menor participação no faturamento, mas maior eficiência em superar orçamento
- **Junho/2025**: Crescimento expressivo de **+10.9%** (YoY), sinalizando retomada positiva

### ⚠️ Pontos de Atenção

- **Modelo "Restaurante" (R$ 17.09 bi)**: Apesar de representar o maior volume, ficou abaixo do orçamento
- **Modelo "VASTO"**: Apresenta resultado negativo frente ao planejado
- **Custos**: Categoria "2.1 INSUMOS" = 82.78% dos custos totais → precisa de otimização

### 📌 Recomendações Estratégicas

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

> **Nota:** Este dashboard foi desenvolvido no Power BI, utilizando boas práticas de modelagem de dados e visualização, garantindo desempenho e usabilidade para tomada de decisão estratégica.

---

📅 *Última atualização: 20 de Agosto de 2025*  
👤 *Desenvolvido por Tassio Lucian de Jesus Sales*
- **Relacionamentos**: Otimizados (Integridade referencial garantida)

### Principais Características

- **Esquema Estrela (Star Schema)** com tabela Fato centralizada para consultas eficientes
- **Tabela Calendário em DAX** dinâmica para análises temporais avançadas (YoY, MTD, QTD, YTD)
- Relacionamentos otimizados entre dimensões (Campos, Lojas) e fatos garantindo consistência
- Hierarquias bem definidas para navegação intuitiva (Ano > Mês > Dia)
- Medidas calculadas para métricas de negócio complexas

## Tratamento e Preparação dos Dados (Power Query - ETL)

### Processo ETL Robusto

Foram implementadas transformações avançadas no Power Query para garantir a qualidade e consistência dos dados.

### Categorias de Transformação

#### 📅 Transformação de Datas
- Padronização do formato de data
- Extração de dia, mês, ano, trimestre
- Criação de hierarquias temporais

#### 🧹 Limpeza de Dados
- Tratamento de valores nulos
- Padronização de formatos
- Validação de consistência

#### 🗺️ Enriquecimento Geográfico
- Separação de Cidade/UF
- Agregação por região
- Preparação para visualizações de mapa
### Exemplo de Código Power Query

```powerquery
// Transformação de Data
let
    Source = Excel.Workbook(File.Contents("Caminho\\Arquivo.xlsx"), null, true),
    Fato_Sheet = Source{[Item="Fato",Kind="Sheet"]}[Data],
    #"Cabeçalhos Promovidos" = Table.PromoteHeaders(Fato_Sheet, [PromoteAllScalars=true]),
    #"Tipo Alterado" = Table.TransformColumnTypes(#"Cabeçalhos Promovidos",{{"mes_ano", type date}})
in
    #"Tipo Alterado"

// Tratamento de Nulos
let
    Source = ...
    #"Valores Substituídos" = Table.ReplaceValue(Source,null,0,Replacer.ReplaceValue,{"valor", "valor_orcado"})
in
    #"Valores Substituídos"

// Separação Cidade-UF
let
    Source = ...
    #"Colunas Divididas" = Table.SplitColumn(Source, "cidade", Splitter.SplitTextByDelimiter("-", QuoteStyle.Csv), {"cidade", "uf"})
in
    #"Colunas Divididas"

### Visão Geral do Dashboard

O dashboard foi projetado seguindo princípios de design thinking e análise de negócios, organizado em camadas analíticas que permitem uma navegação intuitiva dos indicadores macro até os detalhes operacionais.

### Principais Análises
              <img src="image/Captura de tela 2025-08-20 215038.png" alt="Detalhes do Dashboard" class="dashboard-image" style="max-width: 100%; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); border: 1px solid rgba(0,0,0,0.05);">
              <p class="img-caption">Visão detalhada das métricas e análises do dashboard interativo</p>
            </div>
            
            <div class="metrics-grid">
              <div class="metric">
                <div class="label">Receita Total</div>
                <div class="value">R$ 21.40 bi</div>
                <div class="subtext">Período analisado</div>
              </div>
              <div class="metric">
                <div class="label">Resultado vs Orçamento</div>
                <div class="value positive">+2.06%</div>
                <div class="subtext">Acima da meta</div>
              </div>
              <div class="metric">
                <div class="label">Crescimento Anual</div>
                <div class="value positive">+1.59%</div>
                <div class="subtext">Comparação YoY</div>
              </div>
            </div>
  
            <div class="alert alert-success" style="margin: 1.5rem 0;">
              <i class="fas fa-chart-line" style="color: var(--success);"></i>
              <div>
                <strong>Destaque de Performance</strong><br>
                O dashboard demonstra um crescimento anual consistente de 1.59% e superação do orçamento em 2.06%, indicando uma trajetória positiva para o negócio.
              </div>
            </div>

            <h4><i class="fas fa-chart-pie"></i> Principais Análises Desenvolvidas</h4>
            
#### 📊 Desempenho Mensal
- Análise comparativa mês a mês entre receita realizada e orçada
- Destaque para sazonalidades e desvios significativos
              
  #### 📅 Comparativo Anual
- Visão comparativa (YoY) que permite identificar tendências e padrões de crescimento ao longo dos anos.
              </div>
              
#### 🌎 Análise Geográfica
- Distribuição de receita por região/UF
- Identificação de mercados-chave e oportunidades de expansão

#### 📊 Performance por Modelo
- Avaliação da eficiência dos diferentes modelos de negócio
- Comparação de desempenho em atingir as metas orçadas
              </div>
              
#### 🏆 Ranking de Lojas
- Identificação das melhores e piores performances por unidade
- Permite ações direcionadas baseadas em dados

#### 📈 Composição da Receita
- Análise da evolução da margem bruta
- Composição de custos ao longo do tempo
              </div>
            </div>
            
> 💡 **Dica de Navegação:** Utilize os filtros interativos para explorar os dados em diferentes níveis de detalhamento e períodos temporais.
          </div>
          
## 3. Métricas de Negócio (DAX)
            
            <p>Foram desenvolvidas medidas DAX avançadas para atender às necessidades analíticas do negócio:</p>
            
            <h4><i class="fas fa-coins"></i> Medidas de Receita</h4>
            <div class="dax-code">
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

// Receita Ano Anterior
Receita Ano Anterior = 
CALCULATE(
    [Receita Total], 
    SAMEPERIODLASTYEAR('Calendario'[Date])
)

// Crescimento Anual %
Crescimento Anual % = 
DIVIDE(
    [Receita Total] - [Receita Ano Anterior], 
    [Receita Ano Anual]
)

// Variação % vs Orçamento
Variação % vs Orçamento = 
DIVIDE(
    [Receita Total] - [Orçamento Receita], 
    [Orçamento Receita]
)

// Receita por Região
Receita por Região = 
CALCULATE(
    [Receita Total], 
    ALLEXCEPT(Lojas, Lojas[regiao])
)

// Receita por Tipo de Loja
Receita por Tipo de Loja = 
CALCULATE(
    [Receita Total], 
    ALLEXCEPT(Lojas, Lojas[tipo_loja])
)

// Receita por Item
Receita por Item = 
CALCULATE(
    [Receita Total], 
    ALLEXCEPT(Campos, Campos[item])
)

// Receita Acumulada
Receita Acumulada = 
CALCULATE(
    [Receita Total], 
    DATESYTD('Calendario'[Date])
)
            </div>
            
            <h4 style="margin-top: 2rem;"><i class="fas fa-chart-line"></i> Medidas de Custo e Rentabilidade</h4>
            <div class="dax-code">
// Custo de Matéria Prima
Custo de Matéria Prima = 
ABS(
    CALCULATE(
        SUM(Fato[valor]), 
        Campos[conta] = "2 MATERIA PRIMA"
    )
)

// Margem Bruta
Margem Bruta = 
[Receita Total] - [Custo de Matéria Prima]

// Margem Bruta %
Margem Bruta % = 
DIVIDE(
    [Margem Bruta], 
    [Receita Total]
)

// Custo por Unidade Vendida
Custo por Unidade Vendida = 
DIVIDE(
    [Custo de Matéria Prima],
    CALCULATE(
        SUM(Fato[quantidade]),
        Campos[conta] = "1 FATURAMENTO"
    )
)
            </div>
            
> **Nota de Otimização:** Todas as medidas foram otimizadas para desempenho, utilizando funções DAX eficientes e boas práticas de modelagem tabular.
            </div>
          </div>
          
## 4. Análise de Resultados e Insights Estratégicos
            
## 📊 Sumário Executivo

A análise revelou crescimento anual positivo de **1.59%**, com a rede superando o orçamento em **2.06%**. No entanto, existem diferenças significativas no desempenho entre diferentes modelos de negócio e regiões.
                
### 📊 Métricas Principais

| Métrica | Valor |
|---------|-------|
| Receita Total | R$ 21.40 bi |
| Resultado vs Orçamento | +2.06% (Acima da meta) |
| Crescimento Anual (YoY) | +1.59% |
            
### ✅ Destaques Positivos

- **Nordeste**: Melhor performance, superando metas com destaque em lojas âncora
- **Modelos "Conceito" e "Buffet"**: Menor participação no faturamento, mas maior eficiência em superar orçamento
- **Junho/2025**: Crescimento expressivo de **+10.9%** (YoY), sinalizando retomada positiva
### ⚠️ Pontos de Atenção

- **Modelo "Restaurante" (R$ 17.09 bi)**: Apesar de representar o maior volume, ficou abaixo do orçamento
- **Modelo "VASTO"**: Apresenta resultado negativo frente ao planejado
- **Custos**: Categoria "2.1 INSUMOS" = 82.78% dos custos totais → precisa de otimização e negociação com fornecedores
            
### 📌 Recomendações Estratégicas
### 1. Otimização de Custos

- Revisão de contratos com fornecedores de insumos
- Implementação de programas de redução de desperdício
- Análise de substituição de itens de alto custo

### 2. Melhoria de Desempenho

- Replicação das melhores práticas dos modelos "Conceito" e "Buffet"
- Análise detalhada das lojas com desempenho abaixo da média
- Treinamento de equipes nas regiões com menor desempenho
### 3. Aprofundamento Analítico

- Investigação das causas do crescimento de junho
- Análise de sazonalidade para melhor planejamento orçamentário
- Segmentação de clientes por perfil de consumo

> **Nota:** Este dashboard foi desenvolvido no Power BI, utilizando boas práticas de modelagem de dados e visualização, garantindo desempenho e usabilidade para tomada de decisão estratégica.
            </div>
👤 *Desenvolvido por Tassio Lucian de Jesus Sales*  
🔒 *Confidencial - Uso exclusivo da Coco Bambu*

## 📊 Análises Principais

### Desempenho Mensal
- Receita vs Orçamento mês a mês
- Destaque para sazonalidade e desvios

### Comparativo Anual (Matriz)
- Receita de um mês comparada ao mesmo mês do ano anterior (YoY same month)

### Performance Geográfica
- Visualização por cidade/UF
- Comparação ao orçamento por região

### Treemap por Modelo de Negócio
- Análise de receita vs eficiência em bater metas

### Evolução de Margem
- Análise da margem bruta ao longo do tempo
- Segmentação por modelo de negócio

### Filtros Principais
- Período (Ano/Mês)
- Região/UF
- Modelo de Negócio
- Comparativo Ano Anterior

## 📈 Composição da Receita (Área Empilhada)
- Evolução da Margem Bruta ao longo do tempo.

## 3. Métricas de Negócio (DAX)

### Medidas de Receita
- Receita Total
- Orçamento Receita
- Receita Ano Anterior
- Crescimento Anual %
- Variação % vs Orçamento
- Receita por Região
- Receita por Tipo de Loja
- Receita por Item
- Receita Acumulada

### Medidas de Custo e Rentabilidade
- Custo de Matéria Prima
- Margem Bruta
- Margem Bruta %
- Custo por Unidade Vendida
```dax
// Medidas de Receita
Receita Total = CALCULATE(SUM(Fato[valor]), Campos[conta] = "1 FATURAMENTO")
Orçamento Receita = CALCULATE(SUM(Fato[valor_orcado]), Campos[conta] = "1 FATURAMENTO")
Receita Ano Anterior = CALCULATE([Receita Total], SAMEPERIODLASTYEAR('Calendario'[Date]))
Crescimento Anual % = DIVIDE([Receita Total] - [Receita Ano Anterior], [Receita Ano Anterior])
Variação % vs Orçamento = DIVIDE([Receita Total] - [Orçamento Receita], [Orçamento Receita])
Receita por Região = CALCULATE([Receita Total], ALLEXCEPT(Lojas, Lojas[regiao]))
Receita por Tipo de Loja = CALCULATE([Receita Total], ALLEXCEPT(Lojas, Lojas[tipo_loja]))
Receita por Item = CALCULATE([Receita Total], ALLEXCEPT(Campos, Campos[item]))
Receita Acumulada = CALCULATE([Receita Total], DATESYTD('Calendario'[Date]))

// Medidas de Custo e Rentabilidade
Custo de Matéria Prima = CALCULATE(SUM(Fato[valor]), Campos[conta] = "2 MATERIA PRIMA") * -1
Margem Bruta = [Receita Total] - [Custo de Matéria Prima]
Margem Bruta % = DIVIDE([Margem Bruta], [Receita Total])
```

## 4. Análise de Resultados e Insights Estratégicos

## 📊 Sumário Executivo

A análise revelou crescimento anual positivo de **1.59%**, com a rede superando o orçamento em **2.06%**. No entanto, existem diferenças significativas no desempenho entre diferentes modelos de negócio e regiões.

## Métricas Principais

| Métrica | Valor |
|---------|-------|
| Receita Total | R$ 21.40 bi |
| Resultado vs Orçamento | +2.06% (Acima da meta) |
| Crescimento Anual (YoY) | +1.59% |

## Conclusão

O dashboard entregue permite um acompanhamento claro, interativo e estratégico, servindo como ferramenta de apoio para a alta gestão da rede Coco Bambu na tomada de decisão, com foco em crescimento sustentável e eficiência operacional.

## 📊 Destaques

### ✅ Destaques Positivos

- **Nordeste**: Melhor performance, superando metas com destaque em lojas âncora
- **Modelos "Conceito" e "Buffet"**: Menor participação no faturamento, mas maior eficiência em superar orçamento
- **Junho/2025**: Crescimento expressivo de **+10.9%** (YoY), sinalizando retomada positiva

### ⚠️ Pontos de Atenção

- **Modelo "Restaurante" (R$ 17.09 bi)**: Apesar de representar o maior volume, ficou abaixo do orçamento
- **Modelo "VASTO"**: Apresenta resultado negativo frente ao planejado
- **Custos**: Categoria "2.1 INSUMOS" = 82.78% dos custos totais → precisa de otimização e negociação com fornecedores

## 📌 Recomendações Estratégicas

### 1. Otimização de Custos

- Revisão de contratos com fornecedores de insumos
- Implementação de programas de redução de desperdício

### 2. Melhoria de Desempenho

- Replicação das melhores práticas dos modelos "Conceito" e "Buffet"
- Análise detalhada das lojas com desempenho abaixo da média
- Treinamento de equipes nas regiões com menor desempenho

### 3. Aprofundamento Analítico

- Investigação das causas do crescimento de junho
- Análise de sazonalidade para melhor planejamento orçamentário

> **Nota:** Este dashboard foi desenvolvido no Power BI, utilizando boas práticas de modelagem de dados e visualização, garantindo desempenho e usabilidade para tomada de decisão estratégica.

---

📅 *Última atualização: 20 de Agosto de 2025*  
👤 *Desenvolvido por Tassio Lucian de Jesus Sales*
