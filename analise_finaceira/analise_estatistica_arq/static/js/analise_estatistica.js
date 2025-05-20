document.getElementById('analiseForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // Limpar mensagens de erro
    document.getElementById('data_inicio_error').textContent = '';
    document.getElementById('data_fim_error').textContent = '';
    document.getElementById('data_inicio_error').style.display = 'none';
    document.getElementById('data_fim_error').style.display = 'none';

    // Validar datas
    const dataInicio = document.getElementById('data_inicio').value;
    const dataFim = document.getElementById('data_fim').value;
    if (!dataInicio) {
        document.getElementById('data_inicio_error').textContent = 'Por favor, selecione uma data inicial.';
        document.getElementById('data_inicio_error').style.display = 'block';
        return;
    }
    if (!dataFim) {
        document.getElementById('data_fim_error').textContent = 'Por favor, selecione uma data final.';
        document.getElementById('data_fim_error').style.display = 'block';
        return;
    }
    if (dataFim < dataInicio) {
        document.getElementById('data_fim_error').textContent = 'A data final não pode ser anterior à data inicial.';
        document.getElementById('data_fim_error').style.display = 'block';
        return;
    }

    // Mostrar spinner
    const spinner = document.getElementById('loading-spinner');
    spinner.style.display = 'block';
    document.getElementById('resultado').innerHTML = '';

    // Coletar dados do formulário
    const formData = new FormData(this);
    const data = {};
    for (let pair of formData.entries()) {
        if (pair[0] === 'tipo_analise') {
            data[pair[0]] = data[pair[0]] || [];
            data[pair[0]].push(pair[1]);
        } else {
            data[pair[0]] = pair[1];
        }
    }

    try {
        const response = await fetch('/analise_estatistica/analise', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
            },
            credentials: 'same-origin',
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error('Erro na requisição: ' + response.statusText);
        }

        const result = await response.json();
        
        let html = '';
        
        // Exibindo análise básica
        if (result.basica) {
            html += `
                <div class="card mb-4 fade-in">
                    <div class="card-body">
                        <h3 class="text-primary">Análise Básica</h3>
                        <table class="table result-table">
                            <tbody>
                                <tr>
                                    <th scope="row">Total de Registros</th>
                                    <td>${result.basica.total_registros}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Período</th>
                                    <td>${result.basica.periodo || 'N/A'}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Total de Ativos</th>
                                    <td>${result.basica.total_ativos}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Ativos com Ganhos</th>
                                    <td>${result.basica.ativos_ganhos}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Ativos com Perdas</th>
                                    <td>${result.basica.ativos_perdas}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }

        // Exibindo estatísticas descritivas
        if (result.descritiva) {
            html += `
                <div class="card mb-4 fade-in">
                    <div class="card-body">
                        <h3 class="text-primary">Estatísticas Descritivas</h3>
                        <table class="table result-table">
                            <tbody>
                                <tr>
                                    <th scope="row">Média de Retorno</th>
                                    <td>${result.descritiva.media_retorno}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Mediana de Retorno</th>
                                    <td>${result.descritiva.mediana_retorno}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Desvio Padrão</th>
                                    <td>${result.descritiva.desvio_padrao}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Máximo</th>
                                    <td>${result.descritiva.maximo}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Mínimo</th>
                                    <td>${result.descritiva.minimo}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Primeiro Quartil</th>
                                    <td>${result.descritiva.quartis.q1}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Terceiro Quartil</th>
                                    <td>${result.descritiva.quartis.q3}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }

        // Exibindo análise de risco
        if (result.risco) {
            html += `
                <div class="card mb-4 fade-in">
                    <div class="card-body">
                        <h3 class="text-primary">Análise de Risco</h3>
                        <table class="table result-table">
                            <tbody>
                                <tr>
                                    <th scope="row">Sharpe Ratio</th>
                                    <td>${result.risco.sharpe}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Sortino Ratio</th>
                                    <td>${result.risco.sortino}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Drawdown Máximo</th>
                                    <td>${result.risco.drawdown_max}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Volatilidade</th>
                                    <td>${result.risco.volatilidade}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Valor em Risco (VaR)</th>
                                    <td>${result.risco.var}</td>
                                </tr>
                                <tr>
                                    <th scope="row">CVaR</th>
                                    <td>${result.risco.cvar}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Probabilidade de Perda</th>
                                    <td>${result.risco.prob_perda}%</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }

        // Exibindo análise temporal
        if (result.temporal) {
            html += `
                <div class="card mb-4 fade-in">
                    <div class="card-body">
                        <h3 class="text-primary">Análise Temporal</h3>
                        <table class="table result-table">
                            <tbody>
                                <tr>
                                    <th scope="row">Melhor Mês</th>
                                    <td>${JSON.stringify(result.temporal.melhor_mes)}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Pior Mês</th>
                                    <td>${JSON.stringify(result.temporal.pior_mes)}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Melhor Ano</th>
                                    <td>${JSON.stringify(result.temporal.melhor_ano)}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Pior Ano</th>
                                    <td>${JSON.stringify(result.temporal.pior_ano)}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Retorno Diário Médio</th>
                                    <td>${result.temporal.retorno_diario}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Retorno Semanal Médio</th>
                                    <td>${result.temporal.retorno_semanal}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Retorno Mensal Médio</th>
                                    <td>${result.temporal.retorno_mensal}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Frequência Diária</th>
                                    <td>${result.temporal.frequencia_diaria}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Frequência Semanal</th>
                                    <td>${result.temporal.frequencia_semanal}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Frequência Mensal</th>
                                    <td>${result.temporal.frequencia_mensal}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }

        // Exibindo análise por ativo
        if (result.ativo) {
            html += `
                <div class="card mb-4 fade-in">
                    <div class="card-body">
                        <h3 class="text-primary">Análise por Ativo</h3>
                        <table class="table result-table">
                            <tbody>
                                <tr>
                                    <th scope="row">Top 5 Ganhadores</th>
                                    <td>${JSON.stringify(result.ativo.top5_ganhadores)}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Top 5 Perdedores</th>
                                    <td>${JSON.stringify(result.ativo.top5_perdedores)}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Distribuição por Tipo</th>
                                    <td>${JSON.stringify(result.ativo.distribuicao_tipo)}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }

        // Exibindo análise de performance
        if (result.performance) {
            html += `
                <div class="card mb-4 fade-in">
                    <div class="card-body">
                        <h3 class="text-primary">Análise de Performance</h3>
                        <table class="table result-table">
                            <tbody>
                                <tr>
                                    <th scope="row">Taxa de Acerto</th>
                                    <td>${result.performance.taxa_acerto}%</td>
                                </tr>
                                <tr>
                                    <th scope="row">Proporção de Ganhos</th>
                                    <td>${result.performance.proporcao_ganhos}%</td>
                                </tr>
                                <tr>
                                    <th scope="row">Proporção de Perdas</th>
                                    <td>${result.performance.proporcao_perdas}%</td>
                                </tr>
                                <tr>
                                    <th scope="row">Retorno Médio Ganhos</th>
                                    <td>${result.performance.retorno_medio_ganhos}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Retorno Médio Perdas</th>
                                    <td>${result.performance.retorno_medio_perdas}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }

        // Exibindo análise de capital
        if (result.capital) {
            html += `
                <div class="card mb-4 fade-in">
                    <div class="card-body">
                        <h3 class="text-primary">Análise de Capital</h3>
                        <table class="table result-table">
                            <tbody>
                                <tr>
                                    <th scope="row">Valor Inicial</th>
                                    <td>${result.capital.valor_inicial}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Valor Final</th>
                                    <td>${result.capital.valor_final}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Retorno Total</th>
                                    <td>${result.capital.retorno_total}%</td>
                                </tr>
                                <tr>
                                    <th scope="row">Drawdown Máximo</th>
                                    <td>${result.capital.drawdown_max}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }

        // Exibindo análise de frequência
        if (result.frequencia) {
            html += `
                <div class="card mb-4 fade-in">
                    <div class="card-body">
                        <h3 class="text-primary">Análise de Frequência</h3>
                        <table class="table result-table">
                            <tbody>
                                <tr>
                                    <th scope="row">Média Diária</th>
                                    <td>${result.frequencia.media_diaria}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Média Semanal</th>
                                    <td>${result.frequencia.media_semanal}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Média Mensal</th>
                                    <td>${result.frequencia.media_mensal}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Horário Mais Comum</th>
                                    <td>${JSON.stringify(result.frequencia.horario_comum)}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Dia da Semana</th>
                                    <td>${JSON.stringify(result.frequencia.dia_semana)}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }

        // Exibindo análise de correlação
        if (result.correlacao) {
            html += `
                <div class="card mb-4 fade-in">
                    <div class="card-body">
                        <h3 class="text-primary">Análise de Correlação</h3>
                        <table class="table result-table">
                            <tbody>
                                <tr>
                                    <th scope="row">Correlação entre Ativos</th>
                                    <td>${JSON.stringify(result.correlacao.ativos)}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Correlação Volume/Preço</th>
                                    <td>${JSON.stringify(result.correlacao.volume_preco)}</td>
                                </tr>
                                <tr>
                                    <th scope="row">Correlação Indicadores</th>
                                    <td>${JSON.stringify(result.correlacao.indicadores)}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }

        if (!result.basica && !result.descritiva && !result.correlacao && !result.volatilidade && !result.rendimento && !result.risco) {
            html = `
                <div class="alert alert-warning fade-in" role="alert">
                    Nenhuma análise disponível para os parâmetros selecionados.
                </div>
            `;
        }

        document.getElementById('resultado').innerHTML = html;
    } catch (error) {
        console.error('Erro:', error);
        document.getElementById('resultado').innerHTML = `
            <div class="alert alert-danger fade-in" role="alert">
                Erro ao processar a análise: ${error.message}. Tente novamente.
            </div>
        `;
    } finally {
        spinner.style.display = 'none';
    }
});