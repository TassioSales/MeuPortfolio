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




  h3 i {
    color: var(--secondary);
    font-size: 1.2em;
  }
  /* Cards & Boxes */
  .card {
    background: white;
    border-radius: var(--border-radius);
    box-shadow: var(--box-shadow);
    padding: 1.75rem;
    margin-bottom: 2rem;
    transition: var(--transition);
    border: 1px solid rgba(0, 0, 0, 0.05);
  }

  .card:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
  }

  .info-box {
    background: white;
    border-left: 4px solid var(--secondary);
    padding: 1.5rem;
    margin: 2rem 0;
    border-radius: 0 var(--border-radius) var(--border-radius) 0;
    position: relative;
    overflow: hidden;
    box-shadow: var(--box-shadow);
    transition: var(--transition);
  }

  .info-box.warning {
    border-left-color: var(--danger);
    background: #fff9f9;
  }

  .info-box.success {
    border-left-color: var(--success);
    background: #f8fff9;
  }

  .info-box i {
    margin-right: 0.75rem;
    font-size: 1.25em;
    color: var(--secondary);
  }

  .info-box img {
    max-width: 100%;
    height: auto;
    border-radius: calc(var(--border-radius) / 2);
    margin: 1.5rem 0;
    display: block;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    transition: var(--transition);
  }

  .info-box:hover img {
    transform: scale(1.01);
    box-shadow: 0 8px 15px rgba(0, 0, 0, 0.15);
  }

  .img-caption {
    text-align: center;
    font-size: 0.9rem;
    color: var(--gray);
    margin-top: 0.5rem;
    font-style: italic;
  }
  /* Metrics Grid */
  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1.5rem;
    margin: 2rem 0;
  }

  .metric {
    background: white;
    padding: 1.5rem;
    border-radius: var(--border-radius);
    box-shadow: var(--box-shadow);
    transition: var(--transition);
    border-top: 4px solid var(--secondary);
    position: relative;
    overflow: hidden;
  }

  .metric:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
  }

  .metric .label {
    font-size: 0.9rem;
    color: var(--gray);
    margin-bottom: 0.5rem;
    font-weight: 500;
  }

  .metric .value {
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--dark);
    margin: 0.5rem 0;
    line-height: 1.2;
  }

  .metric .subtext {
    font-size: 0.85rem;
    color: var(--gray);
  }

  .positive {
    color: var(--success) !important;
  }

  .negative {
    color: var(--danger) !important;
  }

  /* Code Blocks */
  .dax-code {
    background: #f8f9fa;
    padding: 1.5rem;
    border-radius: var(--border-radius);
    font-family: 'Fira Code', 'Consolas', 'Monaco', 'Andale Mono', monospace;
    overflow-x: auto;
    margin: 1.5rem 0;
    border-left: 4px solid var(--secondary);
    font-size: 0.9rem;
    line-height: 1.6;
    color: #333;
    position: relative;
  }

  .dax-code::before {
    content: 'DAX';
    position: absolute;
    top: 0;
    right: 1rem;
    background: var(--secondary);
    color: white;
    padding: 0.25rem 0.75rem;
    font-size: 0.75rem;
    border-radius: 0 0 var(--border-radius) var(--border-radius);
    font-family: 'Roboto', sans-serif;
    font-weight: 500;
  }

  /* Recommendations & Alerts */
  .recommendation {
    background: #f0f7ff;
    padding: 1.5rem;
    border-radius: var(--border-radius);
    margin: 1.5rem 0;
    border-left: 4px solid var(--secondary);
    position: relative;
  }

  .recommendation h4 {
    margin-top: 0;
    color: var(--primary);
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .recommendation h4 i {
    color: var(--secondary);
  }

  .alert {
    padding: 1rem 1.5rem;
    border-radius: var(--border-radius);
    margin: 1.5rem 0;
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    line-height: 1.6;
  }

  .alert i {
    font-size: 1.25rem;
    margin-top: 0.2rem;
  }

  .alert-success {
    background: #f0f9f0;
    border-left: 4px solid var(--success);
    color: #1e7b1e;
  }

  .alert-warning {
    background: #fff8e6;
    border-left: 4px solid #ffc107;
    color: #856404;
  }

  .alert-danger {
    background: #fff0f0;
    border-left: 4px solid var(--danger);
    color: #721c24;
  }
  /* Lists */
  ul, ol {
    padding-left: 1.5rem;
    margin: 1rem 0;
  }

  ul li, ol li {
    margin-bottom: 0.5rem;
    line-height: 1.6;
  }

  ul ul, ol ol {
    margin: 0.5rem 0 0.5rem 1.5rem;
  }

  /* Tables */
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 1.5rem 0;
    font-size: 0.95rem;
    background: white;
    border-radius: var(--border-radius);
    overflow: hidden;
    box-shadow: var(--box-shadow);
  }

  th, td {
    padding: 1rem 1.25rem;
    text-align: left;
    border-bottom: 1px solid var(--light-gray);
  }

  th {
👤 *Desenvolvido por Tassio Lucian de Jesus Sales*

**Candidato(a):** Tassio Lucian de Jesus Sales  
**Data:** 20 de Agosto de 2025

![Dashboard Overview](image/Captura%20de%20tela%202025-08-20%20215011.png)
*Visão geral do dashboard interativo*

## 1. Decisões Estratégicas de Modelagem e ETL

### Modelagem de Dados

A arquitetura do projeto foi desenvolvida com foco em performance, escalabilidade e experiência do usuário final, permitindo que os insights fossem extraídos de forma rápida e intuitiva.

#### Principais Características

- **Estrutura de Dados**: Esquema Estrela (Modelo dimensional otimizado)
- **Tabelas Principais**: 4 (Fato, Dimensões e Calendário)
- **Relacionamentos**: Otimizados (Integridade referencial garantida)
            <h4><i class="fas fa-check-circle"></i> Principais Características</h4>
            <ul style="margin-top: 1rem;">
              <li><strong>Esquema Estrela (Star Schema)</strong> com tabela Fato centralizada para consultas eficientes</li>
              <li><strong>Tabela Calendário em DAX</strong> dinâmica para análises temporais avançadas (YoY, MTD, QTD, YTD)</li>
              <li>Relacionamentos otimizados entre dimensões (Campos, Lojas) e fatos garantindo consistência</li>
              <li>Hierarquias bem definidas para navegação intuitiva (Ano > Mês > Dia)</li>
              <li>Medidas calculadas para métricas de negócio complexas</li>
            </ul>

          </div>
          
          <div class="info-box" style="margin-top: 2rem;">
            <h3><i class="fas fa-tools"></i> Tratamento e Preparação dos Dados (Power Query - ETL)</h3>
            
            <div class="alert alert-info" style="background: #e7f5ff; border-left: 4px solid #4dabf7; color: #0c5460; padding: 1rem; border-radius: 4px; margin: 1.5rem 0;">
              <i class="fas fa-info-circle" style="color: #4dabf7; font-size: 1.2em; margin-right: 0.5rem;"></i>
              <div>
                <strong>Processo ETL Robusto</strong><br>
                Foram implementadas transformações avançadas no Power Query para garantir a qualidade e consistência dos dados.
              </div>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin: 1.5rem 0;">
              <div class="etl-step" style="background: #f8f9fa; padding: 1.25rem; border-radius: 6px; border-left: 4px solid #4dabf7;">
                <h4 style="margin-top: 0; color: #228be6; font-size: 1.1rem;"><i class="far fa-calendar-alt"></i> Transformação de Datas</h4>
                <ul style="margin: 0.5rem 0 0 1.25rem; padding: 0;">
                  <li>Padronização do formato de data</li>
                  <li>Extração de dia, mês, ano, trimestre</li>
                  <li>Criação de hierarquias temporais</li>
                </ul>
              </div>
              
              <div class="etl-step" style="background: #f8f9fa; padding: 1.25rem; border-radius: 6px; border-left: 4px solid #40c057;">
                <h4 style="margin-top: 0; color: #2b8a3e; font-size: 1.1rem;"><i class="fas fa-broom"></i> Limpeza de Dados</h4>
                <ul style="margin: 0.5rem 0 0 1.25rem; padding: 0;">
                  <li>Tratamento de valores nulos</li>
                  <li>Padronização de formatos</li>
                  <li>Validação de consistência</li>
                </ul>
              </div>
              
              <div class="etl-step" style="background: #f8f9fa; padding: 1.25rem; border-radius: 6px; border-left: 4px solid #ffd43b;">
                <h4 style="margin-top: 0; color: #e67700; font-size: 1.1rem;"><i class="fas fa-map-marked-alt"></i> Enriquecimento Geográfico</h4>
                <ul style="margin: 0.5rem 0 0 1.25rem; padding: 0;">
                  <li>Separação de Cidade/UF</li>
                  <li>Agregação por região</li>
                  <li>Preparação para visualizações de mapa</li>
                </ul>
              </div>
            </div>
            
            <h4><i class="fas fa-code"></i> Exemplo de Código Power Query</h4>
            <div class="dax-code">
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
    #"Colunas Divididas" = Table.SplitColumn(Source, "cidade", 
        Splitter.SplitTextByDelimiter("-", QuoteStyle.Csv), {"cidade", "uf"})
in
    #"Colunas Divididas"

        </div>
      </section>

## 2. Arquitetura Visual e Análises Desenvolvidas

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
              
              <div style="background: #f8f9fa; padding: 1.25rem; border-radius: var(--border-radius); border-left: 4px solid #51cf66;">
                <h5 style="margin-top: 0; color: #2c3e50; font-size: 1.1rem;"><i class="fas fa-map-marked-alt" style="color: #51cf66;"></i> Análise Geográfica</h5>
                <p>Distribuição de receita por região/UF, identificando mercados-chave e oportunidades de expansão.</p>
              </div>
              
              <div style="background: #f8f9fa; padding: 1.25rem; border-radius: var(--border-radius); border-left: 4px solid #fcc419;">
                <h5 style="margin-top: 0; color: #2c3e50; font-size: 1.1rem;"><i class="fas fa-sitemap" style="color: #fcc419;"></i> Performance por Modelo</h5>
                <p>Avaliação da eficiência dos diferentes modelos de negócio em atingir as metas orçadas.</p>
              </div>
              
              <div style="background: #f8f9fa; padding: 1.25rem; border-radius: var(--border-radius); border-left: 4px solid #868e96;">
                <h5 style="margin-top: 0; color: #2c3e50; font-size: 1.1rem;"><i class="fas fa-chart-bar" style="color: #868e96;"></i> Ranking de Lojas</h5>
                <p>Identificação das melhores e piores performances por unidade, permitindo ações direcionadas.</p>
              </div>
              
              <div style="background: #f8f9fa; padding: 1.25rem; border-radius: var(--border-radius); border-left: 4px solid #5f3dc4;">
                <h5 style="margin-top: 0; color: #2c3e50; font-size: 1.1rem;"><i class="fas fa-chart-area" style="color: #5f3dc4;"></i> Composição da Receita</h5>
                <p>Análise da evolução da margem bruta e composição de custos ao longo do tempo.</p>
              </div>
            </div>
            
            <div class="alert alert-warning" style="margin: 2rem 0 1rem;">
              <i class="fas fa-lightbulb" style="color: #f59f00;"></i>
              <div>
                <strong>Dica de Navegação</strong><br>
                Utilize os filtros interativos para explorar os dados em diferentes níveis de detalhamento e períodos temporais.
              </div>
            </div>
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
            
> **Nota:**
              <div>
                <strong>Otimização de Performance</strong><br>
                Todas as medidas foram otimizadas para desempenho, utilizando funções DAX eficientes e boas práticas de modelagem tabular.
              </div>
            </div>
          </div>
          
## 4. Análise de Resultados e Insights Estratégicos
            
            <div class="alert" style="background: #f8f9fa; margin: 1.5rem 0; padding: 1.5rem; border-radius: var(--border-radius);">
              <div style="text-align: center;">
                <h4 style="margin-top: 0; color: var(--primary);">Sumário Executivo</h4>
                <p>A análise revelou crescimento anual positivo de <strong>1.59%</strong>, com a rede superando o orçamento em <strong class="positive">2.06%</strong>. No entanto, existem diferenças significativas no desempenho entre diferentes modelos de negócio e regiões.</p>
                
                <div class="metrics-grid" style="margin: 1.5rem auto; max-width: 800px;">
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
              </div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin: 2rem 0;">
              <div class="alert alert-success">
                <i class="fas fa-check-circle"></i>
                <div>
                  <h5 style="margin: 0 0 0.5rem 0;">✅ Destaques Positivos</h5>
                  <ul style="margin: 0; padding-left: 1.25rem;">
                    <li><strong>Nordeste:</strong> Melhor performance, superando metas com destaque em lojas âncora</li>
                    <li><strong>Modelos "Conceito" e "Buffet":</strong> Menor participação no faturamento, mas maior eficiência em superar orçamento</li>
                    <li><strong>Junho/2025:</strong> Crescimento expressivo de <strong>+10.9%</strong> (YoY), sinalizando retomada positiva</li>
                  </ul>
                </div>
              </div>
              
              <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle"></i>
                <div>
                  <h5 style="margin: 0 0 0.5rem 0;">⚠️ Pontos de Atenção</h5>
                  <ul style="margin: 0; padding-left: 1.25rem;">
                    <li><strong>Modelo "Restaurante" (R$ 17.09 bi):</strong> Apesar de representar o maior volume, ficou abaixo do orçamento</li>
                    <li><strong>Modelo "VASTO":</strong> Apresenta resultado negativo frente ao planejado</li>
                    <li><strong>Custos:</strong> Categoria "2.1 INSUMOS" = 82.78% dos custos totais → precisa de otimização e negociação com fornecedores</li>
                  </ul>
                </div>
              </div>
            </div>
            
### 📌 Recomendações Estratégicas
### 1. Otimização de Custos

- Revisão de contratos com fornecedores de insumos
- Implementação de programas de redução de desperdício
                    <li>Análise de substituição de itens de alto custo</li>
                  </ul>
                </div>
                
                <div>
                  <h5 style="margin: 0 0 0.75rem 0; color: var(--primary); font-size: 1rem;">2. Melhoria de Desempenho</h5>
                  <ul style="margin: 0; padding-left: 1.25rem;">
                    <li>Replicação das melhores práticas dos modelos "Conceito" e "Buffet"</li>
                    <li>Análise detalhada das lojas com desempenho abaixo da média</li>
                    <li>Treinamento de equipes nas regiões com menor desempenho</li>
                  </ul>
                </div>
                
                <div>
                  <h5 style="margin: 0 0 0.75rem 0; color: var(--primary); font-size: 1rem;">3. Aprofundamento Analítico</h5>
                  <ul style="margin: 0; padding-left: 1.25rem;">
                    <li>Investigação das causas do crescimento de junho</li>
                    <li>Análise de sazonalidade para melhor planejamento orçamentário</li>
                    <li>Segmentação de clientes por perfil de consumo</li>
                  </ul>
                </div>
              </div>
              
              <div class="alert" style="background: #f8f9fa; margin-top: 1.5rem; padding: 1rem; border-radius: var(--border-radius); font-size: 0.9em;">
                <i class="fas fa-info-circle" style="color: var(--secondary);"></i>
                <strong>Nota:</strong> Este dashboard foi desenvolvido no Power BI, utilizando boas práticas de modelagem de dados e visualização, garantindo desempenho e usabilidade para tomada de decisão estratégica.
              </div>
            </div>
---

📅 *Relatório gerado em 20 de Agosto de 2025*  
👤 *Desenvolvido por Tassio Lucian de Jesus Sales*  
🔒 *Confidencial - Uso exclusivo da Coco Bambu*
  <h4>📊 Desempenho Mensal</h4>
  <p>Receita vs Orçamento mês a mês, destacando sazonalidade e desvios.</p>
  
  <h4>📅 Comparativo Anual (Matriz)</h4>
  <p>Receita de um mês comparada ao mesmo mês do ano anterior (YoY same month).</p>
  
  <h4>🌎 Performance Geográfica</h4>
  <p>Visualização por cidade/UF com comparação ao orçamento.</p>
  
  <h4>📊 Treemap por Modelo de Negócio</h4>
  <p>Receita x Eficiência em bater metas.</p>
  
  <h4>💲 Composição de Custos (Rosca)</h4>
  <p>Estrutura de custos de matéria-prima.</p>
  
  <h4>🏆 Ranking de Lojas (Barras)</h4>
  <p>Top 5 melhores e piores em relação ao orçamento.</p>
  
  <h4>📈 Composição da Receita (Área Empilhada)</h4>
  <p>Evolução da Margem Bruta ao longo do tempo.</p>
</div>

<h2>3. Métricas de Negócio (DAX)</h2>

<div class="dax-code">
  <span style="color: #7f8c8d;">-- Medidas de Receita</span><br>
  <span style="color: #2c3e50; font-weight: bold;">Receita Total</span> = CALCULATE(SUM(Fato[valor]), Campos[conta] = <span style="color: #27ae60;">"1 FATURAMENTO"</span>)<br>
  <span style="color: #2c3e50; font-weight: bold;">Orçamento Receita</span> = CALCULATE(SUM(Fato[valor_orcado]), Campos[conta] = <span style="color: #27ae60;">"1 FATURAMENTO"</span>)<br>
  <span style="color: #2c3e50; font-weight: bold;">Receita Ano Anterior</span> = CALCULATE([Receita Total], SAMEPERIODLASTYEAR('Calendario'[Date]))<br>
  <span style="color: #2c3e50; font-weight: bold;">Crescimento Anual %</span> = DIVIDE([Receita Total] - [Receita Ano Anterior], [Receita Ano Anterior])<br>
  <span style="color: #2c3e50; font-weight: bold;">Variação % vs Orçamento</span> = DIVIDE([Receita Total] - [Orçamento Receita], [Orçamento Receita])<br>
  <span style="color: #2c3e50; font-weight: bold;">Receita por Região</span> = CALCULATE([Receita Total], ALLEXCEPT(Lojas, Lojas[regiao]))<br>
  <span style="color: #2c3e50; font-weight: bold;">Receita por Tipo de Loja</span> = CALCULATE([Receita Total], ALLEXCEPT(Lojas, Lojas[tipo_loja]))<br>
  <span style="color: #2c3e50; font-weight: bold;">Receita por Item</span> = CALCULATE([Receita Total], ALLEXCEPT(Campos, Campos[item]))<br>
  <span style="color: #2c3e50; font-weight: bold;">Receita Acumulada</span> = CALCULATE([Receita Total], DATESYTD('Calendario'[Date]))<br>
  <br>
  <span style="color: #7f8c8d;">-- Medidas de Custo e Rentabilidade</span><br>
  <span style="color: #2c3e50; font-weight: bold;">Custo de Matéria Prima</span> = CALCULATE(SUM(Fato[valor]), Campos[conta] = <span style="color: #27ae60;">"2 MATERIA PRIMA"</span>) * -1<br>
```dax
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

## Destaques

### Destaques Positivos
### ✅ Destaques Positivos

- **Nordeste**: Melhor performance, superando metas com destaque em lojas âncora
- **Modelos "Conceito" e "Buffet"**: Menor participação no faturamento, mas maior eficiência em superar orçamento
- **Junho/2025**: Crescimento expressivo de **+10.9%** (YoY), sinalizando retomada positiva

### ⚠️ Pontos de Atenção

- **Modelo "Restaurante" (R$ 17.09 bi)**: Apesar de representar o maior volume, ficou abaixo do orçamento
- **Modelo "VASTO"**: Apresenta resultado negativo frente ao planejado</li>
- **Custos**: Categoria "2.1 INSUMOS" = 82.78% dos custos totais → precisa de otimização e negociação com fornecedores

## 📌 Recomendações Estratégicas

### 1. Otimização de Custos

-
- Revisão de contratos com fornecedores de insumos
- Implementação de programas de redução de desperdício

### 2. Melhoria de Desempenho

- Replicação das melhores práticas dos modelos "Conceito" e "Buffet"
- Análise detalhada das lojas com desempenho abaixo da média
### 3. Aprofundamento Analítico

- Investigação das causas do crescimento de junho
- Análise de sazonalidade para melhor planejamento orçamentário

> **Nota:** Este dashboard foi desenvolvido no Power BI, utilizando boas práticas de modelagem de dados e visualização, garantindo desempenho e usabilidade para tomada de decisão estratégica.

---

📅 *Última atualização: 20 de Agosto de 2025*  
👤 *Desenvolvido por Tassio Lucian de Jesus Sales*
