// O gráfico de despesas agora é carregado via imagem na página

document.addEventListener('DOMContentLoaded', function() {
    // Formatar valores monetários
    const formatCurrency = (value) => {
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(value);
    };

    // Formatar data
    const formatDate = (dateString) => {
        const options = { day: '2-digit', month: '2-digit', year: 'numeric' };
        return new Date(dateString).toLocaleDateString('pt-BR', options);
    };

    // Atualizar totais
    const updateTotals = (data) => {
        document.getElementById('total-receitas').textContent = formatCurrency(data.totais.receitas);
        document.getElementById('total-despesas').textContent = formatCurrency(data.totais.despesas);
        document.getElementById('saldo').textContent = formatCurrency(data.totais.saldo);
    };

    // Preencher tabela de transações
    const fillTransactionsTable = (transactions) => {
        const tbody = document.querySelector('#tabela-transacoes tbody');
        tbody.innerHTML = '';

        transactions.forEach(tx => {
            const row = document.createElement('tr');
            row.className = 'fade-in';
            
            const valorClass = tx.valor >= 0 ? 'text-success' : 'text-danger';
            
            row.innerHTML = `
                <td>${formatDate(tx.data)}</td>
                <td>${tx.descricao}</td>
                <td class="${valorClass} fw-bold">${formatCurrency(tx.valor)}</td>
                <td>${tx.categoria || '-'}</td>
            `;
            
            tbody.appendChild(row);
        });
    };


    // Inicializar gráfico de categorias
    let categoriaChart = null;
    const initCategoriaChart = (data) => {
        const ctx = document.getElementById('grafico-categorias').getContext('2d');
        
        // Filtrar apenas categorias com despesas
        const categoriasComDespesas = data.por_categoria.filter(item => item.despesas < 0);
        
        if (categoriaChart) {
            categoriaChart.destroy();
        }

        categoriaChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: categoriasComDespesas.map(item => item.categoria || 'Outros'),
                datasets: [{
                    data: categoriasComDespesas.map(item => Math.abs(item.despesas)),
                    backgroundColor: [
                        '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b', 
                        '#5a5c69', '#858796', '#e83e8c', '#fd7e14', '#20c9a6'
                    ],
                    hoverOffset: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            boxWidth: 12
                        }
                    }
                }
            }
        });
    };

    // Inicializar gráfico de fluxo de caixa
    let fluxoChart = null;
    const initFluxoChart = (transactions) => {
        const ctx = document.getElementById('grafico-fluxo').getContext('2d');
        
        // Agrupar transações por data
        const fluxoPorData = transactions.reduce((acc, tx) => {
            const date = tx.data.split('T')[0];
            if (!acc[date]) {
                acc[date] = { receita: 0, despesa: 0 };
            }
            
            if (tx.tipo === 'Receita') {
                acc[date].receita += parseFloat(tx.valor);
            } else {
                acc[date].despesa += Math.abs(parseFloat(tx.valor));
            }
            
            return acc;
        }, {});
        
        const labels = Object.keys(fluxoPorData).sort();
        const receitas = labels.map(date => fluxoPorData[date].receita);
        const despesas = labels.map(date => fluxoPorData[date].despesa);
        
        if (fluxoChart) {
            fluxoChart.destroy();
        }

        fluxoChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels.map(date => formatDate(date)),
                datasets: [
                    {
                        label: 'Receitas',
                        data: receitas,
                        borderColor: '#1cc88a',
                        backgroundColor: 'rgba(28, 200, 138, 0.1)',
                        tension: 0.3,
                        fill: true
                    },
                    {
                        label: 'Despesas',
                        data: despesas,
                        borderColor: '#e74a3b',
                        backgroundColor: 'rgba(231, 74, 59, 0.1)',
                        tension: 0.3,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: value => formatCurrency(value)
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: context => {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += formatCurrency(context.parsed.y);
                                }
                                return label;
                            }
                        }
                    }
                }
            }
        });
    };

    // Carregar dados iniciais
    const loadData = async () => {
        try {
            // Carregar totais e categorias
            const resSummary = await fetch('/dashboard/api/summary');
            const summaryData = await resSummary.json();
            
            // Carregar transações
            const resTransactions = await fetch('/dashboard/api/transactions');
            const transactionsData = await resTransactions.json();
            
            // Atualizar a interface
            updateTotals(summaryData);
            initCategoriaChart(summaryData);
            fillTransactionsTable(transactionsData);
            initFluxoChart(transactionsData);
            
        } catch (error) {
            console.error('Erro ao carregar dados:', error);
        }
    };

    // O gráfico de despesas agora é carregado via imagem na página

    // Inicializar
    loadData();
});
