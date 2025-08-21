<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Análise Estratégica de Performance - Coco Bambu</title>
  <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Montserrat:wght@600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
  <style>
  :root {
    --primary: #2c3e50;
    --secondary: #3498db;
    --success: #27ae60;
    --danger: #e74c3c;
    --light: #f8f9fa;
    --dark: #2c3e50;
    --gray: #6c757d;
    --light-gray: #e9ecef;
    --border-radius: 8px;
    --box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    --transition: all 0.3s ease;
  }

  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  body {
    font-family: 'Roboto', sans-serif;
    line-height: 1.7;
    color: #333;
    background-color: #f8f9fa;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }
  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
  }

  .header {
    background: linear-gradient(135deg, var(--primary) 0%, #1a252f 100%);
    color: white;
    padding: 2.5rem 0;
    margin-bottom: 2.5rem;
    border-radius: var(--border-radius);
    overflow: hidden;
    position: relative;
    box-shadow: var(--box-shadow);
  }

  .header::before {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    left: 0;
    background: url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiPjxkZWZzPjxwYXR0ZXJuIGlkPSJwYXR0ZXJuIiB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHBhdHRlcm5Vbml0cz0idXNlclNwYWNlT25Vc2UiIHBhdHRlcm5UcmFuc2Zvcm09InJvdGF0ZSg0NSkiPjxyZWN0IHdpZHRoPSIyMCIgaGVpZ2h0PSIyMCIgZmlsbD0icmdiYSgyNTUsIDI1NSwgMjU1LCAwLjAzKSIvPjwvcGF0dGVybj48L2RlZnM+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0idXJsKCNwYXR0ZXJuKSIvPjwvc3ZnPg==');
    opacity: 0.5;
  }
  h1, h2, h3, h4, h5, h6 {
    font-family: 'Montserrat', sans-serif;
    font-weight: 700;
    color: var(--dark);
    margin-bottom: 1.25rem;
    line-height: 1.3;
  }

  h1 {
    font-size: 2.5rem;
    margin: 0 0 0.5rem 0;
    color: white;
    position: relative;
    display: inline-block;
  }

  h1::after {
    content: '';
    position: absolute;
    bottom: -10px;
    left: 0;
    width: 60px;
    height: 4px;
    background: var(--secondary);
    border-radius: 2px;
  }

  h2 {
    font-size: 1.8rem;
    margin-top: 2.5rem;
    padding-bottom: 0.75rem;
    border-bottom: 2px solid var(--light-gray);
    position: relative;
  }

  h2::after {
    content: '';
    position: absolute;
    bottom: -2px;
    left: 0;
    width: 100px;
    height: 2px;
    background: var(--secondary);
  }

  h3 {
    font-size: 1.4rem;
    margin-top: 2rem;
    color: var(--primary);
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

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
    background: var(--primary);
    color: white;
    font-weight: 500;
    text-transform: uppercase;
    font-size: 0.8rem;
    letter-spacing: 0.5px;
  }

  tr:last-child td {
    border-bottom: none;
  }

  tr:hover {
    background: rgba(0, 0, 0, 0.01);
  }

  /* Responsive Design */
  @media (max-width: 992px) {
    .metrics-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media (max-width: 768px) {
    .metrics-grid {
      grid-template-columns: 1fr;
    }

    .header-content {
      flex-direction: column;
      text-align: center;
    }

    .header-image {
      margin: 1.5rem auto 0;
    }

    h1 {
      font-size: 2rem;
    }

    h2 {
      font-size: 1.6rem;
    }
  }

  @media (max-width: 576px) {
    .container {
      padding: 0 15px;
    }

    .info-box, .card {
      padding: 1.25rem;
    }
  }
</style>
</head>
<body>
  <div class="container">
    <header class="header">
      <div class="header-content" style="position: relative; z-index: 2; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 2rem;">
        <div style="flex: 1; min-width: 300px;">
          <h1>Análise Estratégica de Performance</h1>
          <h2 style="color: rgba(255, 255, 255, 0.9); font-weight: 400; font-size: 1.5rem; margin-bottom: 1.5rem;">Coco Bambu</h2>
          
          <div style="background: rgba(255, 255, 255, 0.1); padding: 1.25rem; border-radius: var(--border-radius); backdrop-filter: blur(5px);">
            <p style="margin: 0.5rem 0; display: flex; align-items: center; gap: 0.5rem;">
              <i class="fas fa-project-diagram" style="width: 20px; text-align: center;"></i>
              <strong>Projeto:</strong> Dashboard Estratégico de Análise de Receita e Orçamento
            </p>
            <p style="margin: 0.5rem 0; display: flex; align-items: center; gap: 0.5rem;">
              <i class="fas fa-user-tie" style="width: 20px; text-align: center;"></i>
              <strong>Candidato(a):</strong> Tassio Lucian de Jesus Sales
            </p>
            <p style="margin: 0.5rem 0; display: flex; align-items: center; gap: 0.5rem;">
              <i class="far fa-calendar-alt" style="width: 20px; text-align: center;"></i>
              <strong>Data:</strong> 20 de Agosto de 2025
            </p>
          </div>
        </div>
        
        <div class="header-image" style="flex: 0 0 auto;">
          <img src="image/Captura de tela 2025-08-20 215011.png" alt="Dashboard Overview" style="max-width: 100%; max-height: 280px; border-radius: var(--border-radius); box-shadow: 0 8px 20px rgba(0,0,0,0.2); border: 3px solid rgba(255, 255, 255, 0.2);">
          <p style="text-align: center; color: rgba(255, 255, 255, 0.8); font-size: 0.85rem; margin-top: 0.75rem;">Visão geral do dashboard interativo</p>
        </div>
      </div>
    </header>

    <main>
      <section id="modelagem">
        <div class="card">
          <h2><i class="fas fa-sitemap"></i> 1. Decisões Estratégicas de Modelagem e ETL</h2>

          <div class="info-box">
            <h3><i class="fas fa-database"></i> Modelagem de Dados</h3>
            <p>A arquitetura do projeto foi desenvolvida com foco em performance, escalabilidade e experiência do usuário final, permitindo que os insights fossem extraídos de forma rápida e intuitiva.</p>
            
            <div class="metrics-grid" style="margin: 1.5rem 0;">
              <div class="metric">
                <div class="label">Estrutura de Dados</div>
                <div class="value">Esquema Estrela</div>
                <div class="subtext">Modelo dimensional otimizado</div>
              </div>
              <div class="metric">
                <div class="label">Tabelas Principais</div>
                <div class="value">4</div>
                <div class="subtext">Fato, Dimensões e Calendário</div>
              </div>
              <div class="metric">
                <div class="label">Relacionamentos</div>
                <div class="value">Otimizados</div>
                <div class="subtext">Integridade referencial garantida</div>
              </div>
            </div>
            
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
          </div>
</div>

        </div>
      </section>

      <section id="arquitetura-visual" style="margin-top: 3rem;">
        <div class="card">
          <h2><i class="fas fa-chart-line"></i> 2. Arquitetura Visual e Análises Desenvolvidas</h2>

          <div class="info-box">
            <h3><i class="fas fa-tachometer-alt"></i> Visão Geral do Dashboard</h3>
            <p>O dashboard foi projetado seguindo princípios de design thinking e análise de negócios, organizado em camadas analíticas que permitem uma navegação intuitiva dos indicadores macro até os detalhes operacionais.</p>
            
            <div style="text-align: center; margin: 2rem 0;">
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
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin: 1.5rem 0;">
              <div style="background: #f8f9fa; padding: 1.25rem; border-radius: var(--border-radius); border-left: 4px solid #4d6bff;">
                <h5 style="margin-top: 0; color: #2c3e50; font-size: 1.1rem;"><i class="fas fa-chart-line" style="color: #4d6bff;"></i> Desempenho Mensal</h5>
                <p>Análise comparativa mês a mês entre receita realizada e orçada, com destaque para sazonalidades e desvios significativos.</p>
              </div>
              
              <div style="background: #f8f9fa; padding: 1.25rem; border-radius: var(--border-radius); border-left: 4px solid #ff6b6b;">
                <h5 style="margin-top: 0; color: #2c3e50; font-size: 1.1rem;"><i class="fas fa-calendar-alt" style="color: #ff6b6b;"></i> Comparativo Anual</h5>
                <p>Visão comparativa (YoY) que permite identificar tendências e padrões de crescimento ao longo dos anos.</p>
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
          
          <div class="info-box" style="margin-top: 2rem;">
            <h3><i class="fas fa-calculator"></i> 3. Métricas de Negócio (DAX)</h3>
            
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
    [Receita Ano Anterior]
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
            
            <div class="alert alert-info" style="margin: 1.5rem 0 0;">
              <i class="fas fa-info-circle"></i>
              <div>
                <strong>Otimização de Performance</strong><br>
                Todas as medidas foram otimizadas para desempenho, utilizando funções DAX eficientes e boas práticas de modelagem tabular.
              </div>
            </div>
          </div>
          
          <div class="info-box success" style="margin-top: 2rem;">
            <h3><i class="fas fa-chart-bar"></i> 4. Análise de Resultados e Insights Estratégicos</h3>
            
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
            
            <div class="recommendation">
              <h4><i class="fas fa-lightbulb"></i> Recomendações Estratégicas</h4>
              
              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-top: 1rem;">
                <div>
                  <h5 style="margin: 0 0 0.75rem 0; color: var(--primary); font-size: 1rem;">1. Otimização de Custos</h5>
                  <ul style="margin: 0; padding-left: 1.25rem;">
                    <li>Revisão de contratos com fornecedores de insumos</li>
                    <li>Implementação de programas de redução de desperdício</li>
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
          </div>
        </div>
      </section>
    </main>
    
    <footer style="text-align: center; margin: 3rem 0 2rem; color: var(--gray); font-size: 0.9rem;">
      <p>Relatório gerado em 20 de Agosto de 2025 | Desenvolvido por Tassio Lucian de Jesus Sales</p>
      <p style="font-size: 0.8em; opacity: 0.8; margin-top: 0.5rem;">Confidencial - Uso exclusivo da Coco Bambu</p>
    </footer>
  </div>
</body>
</html>