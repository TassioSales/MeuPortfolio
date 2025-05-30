/**
 * Utility functions for the application
 */

// Format currency
function formatCurrency(value, currency = 'BRL') {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

// Format percentage
function formatPercentage(value, decimals = 2) {
    return `${value > 0 ? '+' : ''}${value.toFixed(decimals)}%`;
}

// Format large numbers
function formatNumber(value, decimals = 0) {
    if (value >= 1000000000) {
        return (value / 1000000000).toFixed(decimals) + 'B';
    }
    if (value >= 1000000) {
        return (value / 1000000).toFixed(decimals) + 'M';
    }
    if (value >= 1000) {
        return (value / 1000).toFixed(decimals) + 'K';
    }
    return value.toFixed(decimals);
}

// Format date
function formatDate(date, format = 'pt-BR') {
    const options = { 
        year: 'numeric', 
        month: '2-digit', 
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    };
    return new Date(date).toLocaleString(format, options);
}

// Get color based on value (positive/negative)
function getValueColor(value) {
    if (value > 0) return 'positive';
    if (value < 0) return 'negative';
    return '';
}

// Debounce function to limit how often a function can be called
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Throttle function to limit the rate at which a function can be called
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Show loading spinner
function showLoading(selector = 'body') {
    const loadingHtml = `
        <div class="loading-overlay">
            <div class="spinner-border text-primary" role="status">
                <span class="sr-only">Carregando...</span>
            </div>
        </div>`;
    
    // Remove any existing loading overlay
    hideLoading();
    
    // Add new loading overlay
    document.querySelector(selector).insertAdjacentHTML('beforeend', loadingHtml);
}

// Hide loading spinner
function hideLoading() {
    const loadingOverlay = document.querySelector('.loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.remove();
    }
}

// Show toast notification
function showToast(message, type = 'info', duration = 5000) {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    const toast = document.createElement('div');
    const toastId = 'toast-' + Date.now();
    
    toast.id = toastId;
    toast.className = `toast show ${type}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="toast-header">
            <strong class="mr-auto">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
            <button type="button" class="ml-2 mb-1 close" data-dismiss="toast" aria-label="Fechar">
                <span aria-hidden="true">&times;</span>
            </button>
        </div>
        <div class="toast-body">
            ${message}
        </div>`;
    
    toastContainer.appendChild(toast);
    
    // Auto dismiss
    const dismissTime = setTimeout(() => {
        const toastElement = document.getElementById(toastId);
        if (toastElement) {
            toastElement.classList.remove('show');
            setTimeout(() => toastElement.remove(), 300);
        }
    }, duration);
    
    // Dismiss on close button click
    const closeButton = toast.querySelector('[data-dismiss="toast"]');
    if (closeButton) {
        closeButton.addEventListener('click', () => {
            clearTimeout(dismissTime);
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        });
    }
    
    return toastId;
}

// Create toast container if it doesn't exist
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
    return container;
}

// Add CSS for loading and toast if not already added
function addUtilityStyles() {
    if (!document.getElementById('utility-styles')) {
        const style = document.createElement('style');
        style.id = 'utility-styles';
        style.textContent = `
            /* Loading overlay */
            .loading-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-color: rgba(0, 0, 0, 0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
            }
            
            .spinner-border {
                width: 3rem;
                height: 3rem;
            }
            
            /* Toast notifications */
            #toast-container {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1100;
                max-width: 350px;
            }
            
            .toast {
                opacity: 0;
                transition: opacity 0.3s ease-in-out;
                margin-bottom: 10px;
                background-color: #2a2a2a;
                color: #fff;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 4px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            }
            
            .toast.show {
                opacity: 1;
            }
            
            .toast-header {
                display: flex;
                align-items: center;
                padding: 0.5rem 1rem;
                background-color: rgba(0, 0, 0, 0.2);
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                color: #fff;
            }
            
            .toast-body {
                padding: 1rem;
            }
            
            .toast .close {
                color: #fff;
                opacity: 0.5;
                background: none;
                border: none;
                font-size: 1.5rem;
                font-weight: 700;
                line-height: 1;
                padding: 0;
                margin-left: auto;
                cursor: pointer;
            }
            
            .toast .close:hover {
                opacity: 1;
            }
            
            /* Toast types */
            .toast.success .toast-header {
                border-left: 4px solid #28a745;
            }
            
            .toast.error .toast-header {
                border-left: 4px solid #dc3545;
            }
            
            .toast.warning .toast-header {
                border-left: 4px solid #ffc107;
            }
            
            .toast.info .toast-header {
                border-left: 4px solid #17a2b8;
            }`;
        
        document.head.appendChild(style);
    }
}

// Initialize utility styles when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    addUtilityStyles();
});

// Export functions
export {
    formatCurrency,
    formatPercentage,
    formatNumber,
    formatDate,
    getValueColor,
    debounce,
    throttle,
    showLoading,
    hideLoading,
    showToast
};

// Manter compatibilidade com código legado
window.Utils = {
    formatCurrency,
    formatPercentage,
    formatNumber,
    formatDate,
    getValueColor,
    debounce,
    throttle,
    showLoading,
    hideLoading,
    showToast
};
