/**
 * Ponto de entrada principal para os módulos JavaScript
 * Este arquivo é responsável por importar e inicializar todos os módulos necessários
 */

// Importar funções utilitárias
import { 
    formatCurrency, 
    formatNumber, 
    debounce, 
    showToast,
    showLoading,
    hideLoading
} from './utils.js';

// Importar funções específicas da página de pesquisa
import { formatMarketCap, generateSampleChartData } from './pesquisa-utils.js';

// Tornar funções disponíveis globalmente para compatibilidade
window.Utils = {
    formatCurrency,
    formatNumber,
    debounce,
    showToast,
    showLoading,
    hideLoading,
    formatMarketCap,
    generateSampleChartData
};

// Inicializar a aplicação quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    console.log('Aplicação inicializada com sucesso!');
    
    // Mostrar mensagem de boas-vindas
    showToast('Bem-vindo ao Análise de Ações!', 'success');
});
