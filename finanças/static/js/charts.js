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
