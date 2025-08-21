<!DOCTYPE html>
<html>
<head>
<style>
  body {
    font-family: Arial, sans-serif;
    line-height: 1.6;
    max-width: 1000px;
    margin: 0 auto;
    padding: 20px;
    color: #333;
  }
  .header {
    background: #2c3e50;
    color: white;
    padding: 30px;
    border-radius: 8px;
    margin-bottom: 20px;
  }
  h1, h2, h3 {
    color: #2c3e50;
  }
  h1 {
    margin: 0;
    color: white;
  }
  .info-box {
    background: #f8f9fa;
    border-left: 4px solid #3498db;
    padding: 15px;
    margin: 20px 0;
    border-radius: 0 4px 4px 0;
    position: relative;
    overflow: hidden;
  }
  .info-box img {
    transition: transform 0.3s ease;
  }
  .info-box:hover img {
    transform: scale(1.02);
  }
  .metric {
    display: inline-block;
    background: white;
    padding: 15px;
    margin: 10px;
    border-radius: 6px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    min-width: 200px;
  }
  .metric .value {
    font-size: 1.5em;
    font-weight: bold;
    color: #2c3e50;
  }
  .positive {
    color: #27ae60;
  }
  .negative {
    color: #e74c3c;
  }
  .dax-code {
    background: #f5f5f5;
    padding: 15px;
    border-radius: 4px;
    font-family: monospace;
    overflow-x: auto;
  }
  .recommendation {
    background: #e8f4fd;
    padding: 15px;
    border-radius: 4px;
    margin: 15px 0;
    border-left: 4px solid #3498db;
  }
  @media (max-width: 768px) {
    .metric {
      width: 100%;
      margin: 10px 0;
    }
  }
</style>
</head>
<body>

<div class="header">
  <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 300px;">
      <h1>Análise Estratégica de Performance</h1>
      <h2 style="color: #fff; margin-top: 5px;">Coco Bambu</h2>
      <p><strong>Projeto:</strong> Dashboard Estratégico de Análise de Receita e Orçamento</p>
      <p><strong>Candidato(a):</strong> Tassio Lucian de Jesus Sales</p>
      <p><strong>Data:</strong> 20 de Agosto de 2025</p>
    </div>
    <div style="flex: 0 0 auto; margin: 15px 0;">
      <img src="image/Captura de tela 2025-08-20 215011.png" alt="Dashboard Overview" style="max-width: 100%; max-height: 200px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
    </div>
  </div>
</div>

---

<h2>1. Decisões Estratégicas de Modelagem e ETL</h2>

<div class="info-box">
  <h3>Modelagem de Dados</h3>
  <p>A arquitetura do projeto foi desenvolvida com foco em performance, escalabilidade e experiência do usuário final, permitindo que os insights fossem extraídos de forma rápida e intuitiva.</p>
  <ul>
    <li>Implementação de <strong>Esquema Estrela (Star Schema)</strong> com tabela Fato centralizada</li>
    <li>Criação de <strong>Tabela Calendário em DAX</strong> para suportar análises temporais avançadas (comparações YoY, períodos acumulados etc.)</li>
    <li>Relacionamentos otimizados entre tabelas (Campos, Lojas, Calendário e Fato) garantindo consistência</li>
  </ul>

  <h3>Tratamento e Preparação dos Dados (Power Query - ETL)</h3>
  <ul>
    <li><strong>Transformação de Data:</strong> Conversão da coluna <code>mes_ano</code> para data válida</li>
    <li><strong>Tratamento de Nulos:</strong> Valores <code>null</code> em <code>valor</code> e <code>valor_orcado</code> substituídos por <code>0</code></li>
    <li><strong>Enriquecimento Geográfico:</strong> Separação da coluna <code>cidade</code> (formato <code>Cidade-UF</code>) em colunas individuais, habilitando análises regionais e mapas interativos</li>
  </ul>
</div>

---

<h2>2. Arquitetura Visual e Análises Desenvolvidas</h2>

<div class="info-box">
  <h3>Visão Geral do Dashboard</h3>
  <p>O dashboard foi projetado em camadas analíticas, partindo de uma visão macro até insights específicos.</p>
  <div style="text-align: center; margin: 20px 0;">
    <img src="image/Captura de tela 2025-08-20 215038.png" alt="Detalhes do Dashboard" style="max-width: 100%; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
    <p style="font-size: 0.9em; color: #666; margin-top: 8px;">Visão detalhada das métricas e análises do dashboard</p>
  </div>
  
  <div style="display: flex; flex-wrap: wrap; justify-content: space-between;">
    <div class="metric">
      <div class="label">Receita Total</div>
      <div class="value">R$ 21.40 bi</div>
      <div>Período analisado</div>
    </div>
    <div class="metric">
      <div class="label">Resultado vs Orçamento</div>
      <div class="value positive">+2.06%</div>
      <div>Acima da meta</div>
    </div>
    <div class="metric">
      <div class="label">Crescimento Anual</div>
      <div class="value positive">+1.59%</div>
      <div>Comparação YoY</div>
    </div>
  </div>
</div>

<h3>Análises Principais</h3>

<div class="info-box">
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
  <span style="color: #2c3e50; font-weight: bold;">Margem Bruta</span> = [Receita Total] - [Custo de Matéria Prima]<br>
  <span style="color: #2c3e50; font-weight: bold;">Margem Bruta %</span> = DIVIDE([Margem Bruta], [Receita Total])
</div>

<h2>4. Análise de Resultados e Insights Estratégicos</h2>

<div class="info-box">
  <h3>Sumário Executivo</h3>
  <p>A análise revelou crescimento anual positivo de <strong>1.59%</strong>, com a rede superando o orçamento em <strong>2.06%</strong>. No entanto, existem diferenças significativas no desempenho entre diferentes modelos de negócio e regiões.</p>
  
  <div style="display: flex; flex-wrap: wrap; gap: 15px; margin: 15px 0;">
    <div style="flex: 1; min-width: 200px; background: white; padding: 15px; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
      <div style="font-size: 0.9em; color: #7f8c8d;">Receita Total</div>
      <div style="font-size: 1.5em; font-weight: bold;">R$ 21.40 bi</div>
    </div>
    <div style="flex: 1; min-width: 200px; background: white; padding: 15px; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
      <div style="font-size: 0.9em; color: #7f8c8d;">Resultado vs Orçamento</div>
      <div style="font-size: 1.5em; font-weight: bold; color: #27ae60;">+2.06%</div>
      <div style="font-size: 0.8em; color: #7f8c8d;">Acima da meta</div>
    </div>
    <div style="flex: 1; min-width: 200px; background: white; padding: 15px; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
      <div style="font-size: 0.9em; color: #7f8c8d;">Crescimento Anual (YoY)</div>
      <div style="font-size: 1.5em; font-weight: bold; color: #27ae60;">+1.59%</div>
    </div>
  </div>
  
  <div style="margin-top: 20px; background: #f0f8ff; padding: 15px; border-radius: 6px; border-left: 4px solid #3498db;">
    <h4 style="margin-top: 0; color: #2c3e50;">📌 Conclusão</h4>
    <p>O dashboard entregue permite um acompanhamento claro, interativo e estratégico, servindo como ferramenta de apoio para a alta gestão da rede Coco Bambu na tomada de decisão, com foco em crescimento sustentável e eficiência operacional.</p>
  </div>
</div>

<div style="display: flex; flex-wrap: wrap; gap: 20px; margin: 30px 0;">
  <div style="flex: 1; min-width: 300px;">
    <h3>✅ Destaques Positivos</h3>
    <ul>
      <li><strong>Nordeste:</strong> Melhor performance, superando metas com destaque em lojas âncora</li>
      <li><strong>Modelos "Conceito" e "Buffet":</strong> Menor participação no faturamento, mas maior eficiência em superar orçamento</li>
      <li><strong>Junho/2025:</strong> Crescimento expressivo de <strong>+10.9%</strong> (YoY), sinalizando retomada positiva</li>
    </ul>
  </div>
  
  <div style="flex: 1; min-width: 300px;">
    <h3>⚠️ Pontos de Atenção</h3>
    <ul>
      <li><strong>Modelo "Restaurante" (R$ 17.09 bi):</strong> Apesar de representar o maior volume, ficou abaixo do orçamento</li>
      <li><strong>Modelo "VASTO":</strong> Apresenta resultado negativo frente ao planejado</li>
      <li><strong>Custos:</strong> Categoria "2.1 INSUMOS" = 82.78% dos custos totais → precisa de otimização e negociação com fornecedores</li>
    </ul>
  </div>
</div>

<h3>📌 Recomendações Estratégicas</h3>

<div class="recommendation">
  <h4>1. Otimização de Custos</h4>
  <ul>
    <li>Revisão de contratos com fornecedores de insumos</li>
    <li>Implementação de programas de redução de desperdício</li>
  </ul>
</div>

<div class="recommendation">
  <h4>2. Melhoria de Desempenho</h4>
  <ul>
    <li>Replicação das melhores práticas dos modelos "Conceito" e "Buffet"</li>
    <li>Análise detalhada das lojas com desempenho abaixo da média</li>
  </ul>
</div>

<div class="recommendation">
  <h4>3. Aprofundamento Analítico</h4>
  <ul>
    <li>Investigação das causas do crescimento de junho</li>
    <li>Análise de sazonalidade para melhor planejamento orçamentário</li>
  </ul>
</div>

<div style="margin-top: 40px; padding: 15px; background: #f8f9fa; border-radius: 6px; text-align: center; font-size: 0.9em; color: #7f8c8d;">
  <p><strong>Nota:</strong> Este dashboard foi desenvolvido no Power BI, utilizando boas práticas de modelagem de dados e visualização, garantindo desempenho e usabilidade para tomada de decisão estratégica.</p>
</div>

</body>
</html>
