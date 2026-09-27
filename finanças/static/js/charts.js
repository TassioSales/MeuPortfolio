/* Shared Chart.js helpers — theme-aware colors, BRL tick formatting, safe JSON reading. */

function chartTheme() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    return {
        isDark,
        gridColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
        textColor: isDark ? '#94a3b8' : '#64748b',
    };
}

function brlTick(value, decimals = 0) {
    return 'R$ ' + Number(value).toLocaleString('pt-BR', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
    });
}

function parseChartJson(elementId, fallback = []) {
    const el = document.getElementById(elementId);
    if (!el) return fallback;
    try {
        return JSON.parse(el.textContent);
    } catch (e) {
        console.warn(`parseChartJson: failed to parse #${elementId}`, e);
        return fallback;
    }
}

/* Mesma ordem de core/analytics.py → CATEGORY_PALETTE */
const CATEGORY_PALETTE = [
    '#6366f1', '#10b981', '#f59e0b', '#ef4444', '#3b82f6', '#ec4899',
    '#14b8a6', '#8b5cf6', '#f97316', '#84cc16', '#06b6d4', '#a855f7',
];
const CHART_COLORS = {
    income: '#10b981',
    expense: '#ef4444',
    net: '#6366f1',
    loan: '#f59e0b',
    card: '#8b5cf6',
    recurring: '#3b82f6',
    other: '#94a3b8',
};

function brl(value, decimals = 2) {
    return Number(value || 0).toLocaleString('pt-BR', {
        style: 'currency', currency: 'BRL',
        minimumFractionDigits: decimals, maximumFractionDigits: decimals,
    });
}

/* Aplica tema (claro/escuro), fonte e tooltip em BRL a todos os gráficos. */
function applyChartDefaults() {
    if (typeof Chart === 'undefined') return;
    const { gridColor, textColor } = chartTheme();
    Chart.defaults.color = textColor;
    Chart.defaults.borderColor = gridColor;
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily || 'Inter, sans-serif';
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.boxWidth = 8;
    Chart.defaults.plugins.tooltip.callbacks.label = function (ctx) {
        const v = ctx.parsed && typeof ctx.parsed === 'object' ? (ctx.parsed.y ?? ctx.parsed.x ?? ctx.parsed) : ctx.parsed;
        const name = ctx.dataset.label || ctx.label || '';
        return `${name}: ${brl(typeof v === 'number' ? v : ctx.raw)}`;
    };
}

/* Mostra uma mensagem no lugar do canvas quando não há dados. Devolve true se vazio. */
function chartEmptyState(canvasId, values, message = 'Sem dados para este filtro') {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return true;
    const flat = (values || []).flat ? (values || []).flat() : values;
    const hasData = flat && flat.some(v => Number(v) !== 0);
    if (!hasData) {
        const box = document.createElement('div');
        box.className = 'chart-empty';
        box.innerHTML = '<i class="bi bi-bar-chart"></i>';
        const span = document.createElement('span');
        span.textContent = message;
        box.appendChild(span);
        canvas.replaceWith(box);
        return true;
    }
    return false;
}

document.addEventListener('DOMContentLoaded', applyChartDefaults);
