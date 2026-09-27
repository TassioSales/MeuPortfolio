/* Gráficos do dashboard. Dados em <script id="dashboard-data"> (json_script). */
document.addEventListener('DOMContentLoaded', function () {
    applyChartDefaults();
    const data = parseChartJson('dashboard-data', {});
    const { gridColor } = chartTheme();
    const moneyAxis = { beginAtZero: true, grid: { color: gridColor }, ticks: { callback: v => brlTick(v) } };
    const noGrid = { grid: { display: false } };
    const alpha = (hex, a) => {
        const n = parseInt(hex.slice(1), 16);
        return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
    };

    // G1 — receitas × despesas + resultado
    const m = data.monthly;
    if (m && !chartEmptyState('chartMonthly', [m.income, m.expense])) {
        const faded = (color) => m.forecast.map(f => f ? alpha(color, 0.35) : color);
        new Chart(document.getElementById('chartMonthly'), {
            data: {
                labels: m.labels,
                datasets: [
                    { type: 'bar', label: 'Receitas', data: m.income, backgroundColor: faded(CHART_COLORS.income), borderRadius: 6, maxBarThickness: 22, order: 2 },
                    { type: 'bar', label: 'Despesas', data: m.expense, backgroundColor: faded(CHART_COLORS.expense), borderRadius: 6, maxBarThickness: 22, order: 2 },
                    { type: 'line', label: 'Resultado', data: m.net, borderColor: CHART_COLORS.net, backgroundColor: CHART_COLORS.net,
                      tension: 0.3, pointRadius: 3, borderWidth: 2, order: 1,
                      segment: { borderDash: ctx => m.forecast[ctx.p1DataIndex] ? [6, 4] : undefined } },
                ],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: { legend: { position: 'top', align: 'end' } },
                scales: { y: { ...moneyAxis, beginAtZero: false }, x: noGrid },
            },
        });
    }

    // G2 — donut de categorias (clique filtra)
    const c = data.categories;
    if (c && !chartEmptyState('chartCategories', c.values)) {
        const total = c.values.reduce((a, b) => a + b, 0);
        new Chart(document.getElementById('chartCategories'), {
            type: 'doughnut',
            data: { labels: c.labels, datasets: [{ data: c.values, backgroundColor: c.colors, borderWidth: 2, borderColor: 'transparent' }] },
            options: {
                responsive: true, maintainAspectRatio: false, cutout: '68%',
                plugins: {
                    legend: { position: 'bottom', labels: { font: { size: 11 } } },
                    tooltip: { callbacks: { label: ctx => `${ctx.label}: ${brl(ctx.raw)} (${(ctx.raw / total * 100).toFixed(1)}%)` } },
                },
                onClick: (evt, els) => {
                    if (!els.length) return;
                    const id = c.ids[els[0].index];
                    if (!id) return;
                    const base = window.DASHBOARD_CATEGORY_URL || '?';
                    window.location.href = base + (base.length > 1 ? '&' : '') + 'category=' + id;
                },
                onHover: (evt, els) => { evt.native.target.style.cursor = els.length ? 'pointer' : 'default'; },
            },
            plugins: [{
                id: 'centerText',
                afterDraw(chart) {
                    const { ctx, chartArea } = chart;
                    const meta = chart.getDatasetMeta(0);
                    if (!meta.data.length) return;
                    const { x, y } = meta.data[0];
                    ctx.save();
                    ctx.textAlign = 'center';
                    ctx.fillStyle = chartTheme().textColor;
                    ctx.font = '600 11px sans-serif';
                    ctx.fillText('Total', x, y - 10);
                    ctx.font = '800 15px sans-serif';
                    ctx.fillStyle = getComputedStyle(document.body).getPropertyValue('--text-main') || '#0f172a';
                    ctx.fillText(brl(total, 0), x, y + 10);
                    ctx.restore();
                },
            }],
        });
    }

    // G3 — gasto acumulado atual × período anterior
    const cu = data.cumulative;
    if (!cu) {
        chartEmptyState('chartCumulative', [], 'Escolha um período de até 3 meses');
    } else if (!chartEmptyState('chartCumulative', [cu.current.filter(v => v !== null), cu.previous, cu.forecast || []])) {
        const datasets = [
            { label: 'Este período', data: cu.current, borderColor: CHART_COLORS.expense, backgroundColor: alpha(CHART_COLORS.expense, 0.08),
              fill: true, tension: 0.25, pointRadius: 0, borderWidth: 2.5, spanGaps: false },
        ];
        if (cu.forecast) datasets.push({ label: 'Previsto', data: cu.forecast, borderColor: CHART_COLORS.expense, borderDash: [6, 4],
            pointRadius: 0, borderWidth: 2, tension: 0.25 });
        if (cu.previous && cu.previous.length) datasets.push({ label: cu.previous_label || 'Período anterior', data: cu.previous,
            borderColor: CHART_COLORS.other, borderDash: [3, 3], pointRadius: 0, borderWidth: 1.5, tension: 0.25 });
        new Chart(document.getElementById('chartCumulative'), {
            type: 'line',
            data: { labels: cu.labels, datasets },
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: { legend: { position: 'top', align: 'end' } },
                scales: { y: moneyAxis, x: { ...noGrid, ticks: { maxTicksLimit: 10 } } },
            },
        });
    }

    // G7 — comprometido nos próximos 12 meses (empilhado por origem)
    const co = data.committed;
    const committedColors = { PARCELA: CHART_COLORS.card, RECORRENTE: CHART_COLORS.recurring, EMPRESTIMO: CHART_COLORS.loan, OUTROS: CHART_COLORS.other };
    if (co && !chartEmptyState('chartCommitted', co.datasets.map(d => d.data), 'Nada lançado para os próximos meses')) {
        new Chart(document.getElementById('chartCommitted'), {
            type: 'bar',
            data: {
                labels: co.labels,
                datasets: co.datasets.map(d => ({ label: d.label, data: d.data, backgroundColor: committedColors[d.key], borderRadius: 4, maxBarThickness: 36 })),
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { position: 'top', align: 'end' },
                    tooltip: { callbacks: { footer: items => 'Total: ' + brl(items.reduce((a, i) => a + i.raw, 0)) } },
                },
                scales: { x: { ...noGrid, stacked: true }, y: { ...moneyAxis, stacked: true } },
            },
        });
    }

    // G5 — caixa, dívida e patrimônio
    const ev = data.evolution;
    if (ev && !chartEmptyState('chartEvolution', [ev.balance, ev.debt])) {
        const hasDebt = ev.debt.some(v => v > 0);
        const datasets = [
            { label: 'Caixa', data: ev.balance, borderColor: CHART_COLORS.recurring, backgroundColor: alpha(CHART_COLORS.recurring, 0.08), fill: true, tension: 0.3, pointRadius: 2 },
        ];
        if (hasDebt) {
            datasets.push({ label: 'Dívida', data: ev.debt, borderColor: CHART_COLORS.expense, tension: 0.3, pointRadius: 2 });
            datasets.push({ label: 'Caixa − dívida', data: ev.net, borderColor: CHART_COLORS.net, borderDash: [5, 4], tension: 0.3, pointRadius: 0 });
        }
        new Chart(document.getElementById('chartEvolution'), {
            type: 'line',
            data: { labels: ev.labels, datasets },
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: { legend: { position: 'top', align: 'end' } },
                scales: { y: { ...moneyAxis, beginAtZero: false }, x: noGrid },
            },
        });
    }

    // G6 — formas de pagamento
    const p = data.payments;
    if (p && !chartEmptyState('chartPayments', p.values)) {
        new Chart(document.getElementById('chartPayments'), {
            type: 'doughnut',
            data: { labels: p.labels, datasets: [{ data: p.values, backgroundColor: CATEGORY_PALETTE.slice(0, p.values.length), borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, cutout: '60%', plugins: { legend: { position: 'bottom' } } },
        });
    }

    // G4 — orçamento × gasto
    const b = data.budgets;
    if (b && b.length && document.getElementById('chartBudgets')) {
        new Chart(document.getElementById('chartBudgets'), {
            type: 'bar',
            data: {
                labels: b.map(r => r.name),
                datasets: [
                    { label: 'Gasto', data: b.map(r => r.spent), backgroundColor: b.map(r => r.spent > r.limit ? CHART_COLORS.expense : (r.spent > r.limit * 0.8 ? '#f59e0b' : CHART_COLORS.income)), borderRadius: 4, barThickness: 14 },
                    { label: 'Limite', data: b.map(r => r.limit), backgroundColor: alpha('#94a3b8', 0.25), borderRadius: 4, barThickness: 14 },
                ],
            },
            options: {
                indexAxis: 'y', responsive: true, maintainAspectRatio: false,
                plugins: { legend: { position: 'top', align: 'end' } },
                scales: { x: { ...moneyAxis }, y: noGrid },
            },
        });
    }
});
