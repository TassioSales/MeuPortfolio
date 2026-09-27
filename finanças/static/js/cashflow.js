/* Gráficos do fluxo de caixa. Dados em <script id="cf-data"> (json_script). */
document.addEventListener('DOMContentLoaded', function () {
    applyChartDefaults();
    const d = parseChartJson('cf-data', {});
    const { gridColor } = chartTheme();
    const scenario = window.CF_SCENARIO || 'base';

    // Saldo diário: realizado + cenário selecionado + faixa pessimista↔otimista
    if (d.daily_labels && d.daily_labels.length) {
        const zeroLine = {
            id: 'zeroLine',
            beforeDatasetsDraw(chart) {
                const y = chart.scales.y;
                if (y.min > 0 || y.max < 0) return;
                const { ctx, chartArea } = chart;
                const py = y.getPixelForValue(0);
                ctx.save();
                ctx.strokeStyle = 'rgba(239,68,68,.55)';
                ctx.lineWidth = 1.5;
                ctx.setLineDash([4, 4]);
                ctx.beginPath(); ctx.moveTo(chartArea.left, py); ctx.lineTo(chartArea.right, py); ctx.stroke();
                ctx.restore();
            },
        };
        new Chart(document.getElementById('cfDaily'), {
            type: 'line',
            data: {
                labels: d.daily_labels,
                datasets: [
                    { label: 'Otimista', data: d.scenarios.otimista, borderColor: 'transparent', pointRadius: 0,
                      backgroundColor: 'rgba(99,102,241,.10)', fill: '+1', stepped: false, order: 3 },
                    { label: 'Pessimista', data: d.scenarios.pessimista, borderColor: 'rgba(99,102,241,.25)', borderWidth: 1,
                      pointRadius: 0, fill: false, order: 3 },
                    { label: 'Previsto (' + scenario + ')', data: d.scenarios[scenario], borderColor: '#6366f1', borderDash: [6, 4],
                      borderWidth: 2.5, pointRadius: 0, fill: false, order: 1 },
                    { label: 'Realizado', data: d.real, borderColor: '#10b981', backgroundColor: 'rgba(16,185,129,.08)',
                      borderWidth: 2.5, pointRadius: 0, fill: true, order: 2 },
                ],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { position: 'top', align: 'end' },
                    tooltip: { filter: i => i.raw !== null },
                },
                scales: {
                    y: { grid: { color: gridColor }, ticks: { callback: v => brlTick(v) } },
                    x: { grid: { display: false }, ticks: { maxTicksLimit: 12 } },
                },
            },
            plugins: [zeroLine],
        });
    }

    // Composição das saídas por mês (empilhado) + entradas (linha)
    const comp = d.composition || {};
    const groups = [
        ['card', 'Cartão', CHART_COLORS.card],
        ['fixed', 'Fixas', CHART_COLORS.recurring],
        ['loans', 'Empréstimos', CHART_COLORS.loan],
        ['other', 'Outras', CHART_COLORS.other],
        ['variable', 'Variável (est.)', 'rgba(239,68,68,.45)'],
    ];
    if (!chartEmptyState('cfComposition', [...Object.values(comp), d.income || []])) {
        new Chart(document.getElementById('cfComposition'), {
            data: {
                labels: d.month_labels,
                datasets: [
                    ...groups.filter(([k]) => comp[k] && comp[k].some(v => v)).map(([k, label, color]) => ({
                        type: 'bar', label, data: comp[k], backgroundColor: color, stack: 'out', borderRadius: 3, maxBarThickness: 40,
                    })),
                    { type: 'line', label: 'Entradas', data: d.income, borderColor: CHART_COLORS.income, backgroundColor: CHART_COLORS.income,
                      borderWidth: 2.5, pointRadius: 4, tension: 0.25 },
                ],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: { legend: { position: 'top', align: 'end' } },
                scales: {
                    x: { stacked: true, grid: { display: false } },
                    y: { stacked: true, beginAtZero: true, grid: { color: gridColor }, ticks: { callback: v => brlTick(v) } },
                },
            },
        });
    }
});
