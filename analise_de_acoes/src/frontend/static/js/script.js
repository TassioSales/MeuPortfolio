/**
 * Main application script
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize components
    initSidebar();
    initTooltips();
    initModals();
    initForms();
    initDataTables();
    
    // Load initial data
    loadDashboardData();
    
    // Set up auto-refresh
    setupAutoRefresh();
    
    // Initialize other components
    initCharts();
    
    // Show welcome message
    setTimeout(() => {
        Utils.showToast('Bem-vindo ao Análise de Ações!', 'success');
    }, 1000);
});

/**
 * Initialize sidebar functionality
 */
function initSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const toggleBtn = document.querySelector('.sidebar-toggle');
    
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            document.body.classList.toggle('sidebar-collapsed');
        });
    }
    
    // Add active class to current page in sidebar
    const currentPath = window.location.pathname.split('/').pop() || 'index.html';
    const navLinks = document.querySelectorAll('.sidebar-nav a');
    
    navLinks.forEach(link => {
        const linkHref = link.getAttribute('href');
        if (linkHref === currentPath || 
            (currentPath === '' && linkHref === 'index.html')) {
            link.parentElement.classList.add('active');
        }
    });
    
    // Mobile menu toggle
    const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('show');
        });
    }
}

/**
 * Initialize tooltips
 */
function initTooltips() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize modals
 */
function initModals() {
    // Close modal when clicking outside
    document.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal')) {
            const modal = bootstrap.Modal.getInstance(event.target);
            if (modal) {
                modal.hide();
            }
        }
    });
    
    // Initialize all modals
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.addEventListener('hidden.bs.modal', function () {
            // Clear form when modal is closed
            const form = this.querySelector('form');
            if (form) {
                form.reset();
            }
        });
    });
}

/**
 * Initialize forms with validation
 */
function initForms() {
    // Add form validation
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
    
    // Handle form submissions with AJAX
    document.addEventListener('submit', function(event) {
        const form = event.target;
        
        // Skip if form doesn't have data-ajax="true"
        if (form.getAttribute('data-ajax') !== 'true') return;
        
        event.preventDefault();
        
        const formData = new FormData(form);
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalBtnText = submitBtn ? submitBtn.innerHTML : '';
        
        // Show loading state
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processando...';
        }
        
        // Send form data
        fetch(form.action, {
            method: form.method,
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw err; });
            }
            return response.json();
        })
        .then(data => {
            // Show success message
            Utils.showToast(data.message || 'Operação realizada com sucesso!', 'success');
            
            // Reset form if needed
            if (form.hasAttribute('data-reset-on-success')) {
                form.reset();
                form.classList.remove('was-validated');
            }
            
            // Close modal if form is in a modal
            const modal = form.closest('.modal');
            if (modal) {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) {
                    bsModal.hide();
                }
            }
            
            // Trigger custom event
            document.dispatchEvent(new CustomEvent('formSuccess', { 
                detail: { form, data } 
            }));
        })
        .catch(error => {
            console.error('Error:', error);
            const errorMessage = error.message || 'Ocorreu um erro ao processar sua solicitação.';
            Utils.showToast(errorMessage, 'error');
        })
        .finally(() => {
            // Reset button state
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
            }
        });
    });
}

/**
 * Initialize DataTables
 */
function initDataTables() {
    const tables = document.querySelectorAll('.datatable');
    
    if (tables.length > 0 && typeof $.fn.DataTable === 'function') {
        tables.forEach(table => {
            $(table).DataTable({
                responsive: true,
                language: {
                    url: '//cdn.datatables.net/plug-ins/1.10.25/i18n/Portuguese-Brasil.json'
                },
                dom: "<'row'<'col-sm-12 col-md-6'l><'col-sm-12 col-md-6'f>>" +
                      "<'row'<'col-sm-12'tr>>" +
                      "<'row'<'col-sm-12 col-md-5'i><'col-sm-12 col-md-7'p>>",
                pageLength: 10,
                order: [],
                columnDefs: [{
                    orderable: false,
                    targets: 'no-sort'
                }]
            });
        });
    }
}

/**
 * Load dashboard data
 */
function loadDashboardData() {
    // Show loading state
    const dashboardCards = document.querySelector('.dashboard-cards');
    if (dashboardCards) {
        dashboardCards.innerHTML = `
            <div class="col-12 text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Carregando...</span>
                </div>
                <p class="mt-2">Carregando dados do dashboard...</p>
            </div>`;
    }
    
    // Simulate API call
    setTimeout(() => {
        // This would be replaced with actual API calls
        updateDashboard({
            portfolioValue: 25450.68,
            profitLoss: 4250.35,
            profitLossPercentage: 12.3,
            assetCount: 8,
            activeAlerts: 3
        });
    }, 1000);
}

/**
 * Update dashboard with data
 */
function updateDashboard(data) {
    const dashboardCards = document.querySelector('.dashboard-cards');
    if (!dashboardCards) return;
    
    dashboardCards.innerHTML = `
        <div class="card">
            <div class="card-header">
                <span class="card-title">Valor Total da Carteira</span>
                <i class="fas fa-wallet"></i>
            </div>
            <div class="card-value">${Utils.formatCurrency(data.portfolioValue)}</div>
            <div class="card-change ${data.profitLossPercentage >= 0 ? 'positive' : 'negative'}">
                <i class="fas fa-${data.profitLossPercentage >= 0 ? 'arrow-up' : 'arrow-down'}"></i> 
                ${Utils.formatPercentage(data.profitLossPercentage)}
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <span class="card-title">Lucro/Prejuízo Total</span>
                <i class="fas fa-chart-line"></i>
            </div>
            <div class="card-value ${data.profitLoss >= 0 ? 'positive' : 'negative'}">
                ${Utils.formatCurrency(data.profitLoss)}
            </div>
            <div class="card-change ${data.profitLossPercentage >= 0 ? 'positive' : 'negative'}">
                <i class="fas fa-${data.profitLossPercentage >= 0 ? 'arrow-up' : 'arrow-down'}"></i> 
                ${Utils.formatPercentage(data.profitLossPercentage)}
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <span class="card-title">Ativos na Carteira</span>
                <i class="fas fa-coins"></i>
            </div>
            <div class="card-value">${data.assetCount}</div>
            <div class="card-change">
                <i class="fas fa-equals"></i> Estável
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <span class="card-title">Alertas Ativos</span>
                <i class="fas fa-bell"></i>
            </div>
            <div class="card-value">${data.activeAlerts}</div>
            <div class="card-change">
                <a href="#">Ver todos</a>
            </div>
        </div>`;
}

/**
 * Set up auto-refresh for dashboard data
 */
function setupAutoRefresh() {
    // Refresh data every 60 seconds
    setInterval(loadDashboardData, 60000);
    
    // Add manual refresh button handler
    const refreshBtn = document.querySelector('.refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function(e) {
            e.preventDefault();
            loadDashboardData();
            Utils.showToast('Dados atualizados', 'success');
        });
    }
}

/**
 * Initialize charts
 */
function initCharts() {
    // This would be replaced with actual chart initialization code
    // For now, we're using the charts initialized in the HTML
}

// Make functions available globally
window.App = {
    initSidebar,
    initTooltips,
    initModals,
    initForms,
    initDataTables,
    loadDashboardData,
    updateDashboard,
    setupAutoRefresh,
    initCharts
};
