/**
 * Utility functions for the pesquisa.html page
 */

// Format market cap with BRL prefix
function formatMarketCap(value) {
    if (!value) return 'N/A';
    
    if (value >= 1e12) {
        return `R$ ${(value / 1e12).toFixed(2)}T`;
    } else if (value >= 1e9) {
        return `R$ ${(value / 1e9).toFixed(2)}B`;
    } else if (value >= 1e6) {
        return `R$ ${(value / 1e6).toFixed(2)}M`;
    } else if (value >= 1e3) {
        return `R$ ${(value / 1e3).toFixed(2)}K`;
    } else {
        return `R$ ${value.toFixed(2)}`;
    }
}

// Generate sample chart data for demonstration
function generateSampleChartData() {
    const data = [];
    const now = new Date();
    const oneYearAgo = new Date(now);
    oneYearAgo.setFullYear(now.getFullYear() - 1);
    
    for (let d = new Date(oneYearAgo); d <= now; d.setDate(d.getDate() + 1)) {
        data.push({
            x: new Date(d),
            y: 20 + Math.random() * 20 // Preços entre 20 e 40
        });
    }
    
    return data;
}

// Export functions for use in other files
export {
    formatMarketCap,
    generateSampleChartData
};
