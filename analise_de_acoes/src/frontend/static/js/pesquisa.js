/**
 * Script principal da página de Pesquisa de Ativos
 * Gerencia a busca, filtragem e exibição de ativos financeiros
 * 
 * Este script utiliza as funções disponíveis no objeto global window.Utils
 * que são carregadas pelo módulo principal em index.js
 */

// Estado da aplicação

// Estado da aplicação
let currentPage = 1;
const itemsPerPage = 10;
let isLoading = false;
let currentSearchParams = {
    query: '',
    market: 'all',
    exchange: 'all',
    sector: 'all',
    sort: 'volume'
};

// Elementos da página
const searchInput = document.getElementById('searchInput');
const marketFilter = document.getElementById('marketFilter');
const exchangeFilter = document.getElementById('exchangeFilter');
const sectorFilter = document.getElementById('sectorFilter');
const sortFilter = document.getElementById('sortFilter');
const assetsGrid = document.getElementById('assetsGrid');
const loadingIndicator = document.getElementById('loadingIndicator');
const noResults = document.getElementById('noResults');
const resultsCount = document.getElementById('resultsCount');

// Inicialização quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Configurar eventos
    setupEventListeners();
    
    // Carregar dados iniciais
    loadAssets();
});

// A função generateSampleChartData está disponível em window.Utils

// Configurar eventos
function setupEventListeners() {
    // Busca ao digitar (com debounce)
    const debouncedSearch = window.Utils?.debounce || function(fn, delay) {
        let timeoutId;
        return function(...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => fn.apply(this, args), delay);
        };
    };
    searchInput.addEventListener('input', debouncedSearch(handleSearch, 500));
    
    // Filtros
    marketFilter.addEventListener('change', handleFilterChange);
    exchangeFilter.addEventListener('change', handleFilterChange);
    sectorFilter.addEventListener('change', handleFilterChange);
    sortFilter.addEventListener('change', handleSortChange);
    
    // Eventos de clique nos cards de ativos
    document.addEventListener('click', function(e) {
        // Verifica se o clique foi em um botão de adicionar à carteira
        if (e.target.closest('.btn-add-to-portfolio')) {
            e.stopPropagation();
            const assetId = e.target.closest('.btn-add-to-portfolio').dataset.assetId;
            showAddToPortfolioModal(assetId);
        }
        
        // Verifica se o clique foi em um card de ativo
        if (e.target.closest('.asset-card') && !e.target.closest('.asset-actions')) {
            const assetId = e.target.closest('.asset-card').dataset.assetId;
            showAssetDetails(assetId);
        }
    });
    
    // Evento de envio do formulário de adicionar à carteira
    const addToPortfolioForm = document.getElementById('addToPortfolioForm');
    if (addToPortfolioForm) {
        addToPortfolioForm.addEventListener('submit', handleAddToPortfolio);
    }
    
    // Evento de envio do formulário de alerta
    const setAlertForm = document.getElementById('setAlertForm');
    if (setAlertForm) {
        setAlertForm.addEventListener('submit', handleSetAlert);
    }
}

// Manipulador de busca
function handleSearch(e) {
    const query = e.target.value.trim().toLowerCase();
    currentSearchParams.query = query;
    currentPage = 1; // Resetar para a primeira página
    loadAssets();
}

// Manipulador de mudança de filtros
function handleFilterChange() {
    currentSearchParams.market = marketFilter.value;
    currentSearchParams.exchange = exchangeFilter.value;
    currentSearchParams.sector = sectorFilter.value;
    currentPage = 1; // Resetar para a primeira página
    loadAssets();
}

// Manipulador de mudança de ordenação
function handleSortChange() {
    currentSearchParams.sort = sortFilter.value;
    loadAssets();
}

// Carregar ativos da API
async function loadAssets() {
    if (isLoading) return;
    
    try {
        isLoading = true;
        showLoading(true);
        
        // Construir URL de busca com parâmetros
        const params = new URLSearchParams({
            q: currentSearchParams.query,
            market: currentSearchParams.market,
            exchange: currentSearchParams.exchange,
            sector: currentSearchParams.sector,
            sort_by: currentSearchParams.sort,
            page: currentPage,
            per_page: itemsPerPage
        });
        
        const url = `/api/assets/search?${params.toString()}`;
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error('Erro ao carregar ativos');
        }
        
        const assets = await response.json();
        
        // Atualizar a interface do usuário
        updateAssetsGrid(assets);
        updateResultsCount(assets.length);
        
    } catch (error) {
        console.error('Erro ao carregar ativos:', error);
        showError('Erro ao carregar ativos. Tente novamente mais tarde.');
    } finally {
        isLoading = false;
        showLoading(false);
    }
}

// Atualizar a grade de ativos
function updateAssetsGrid(assets) {
    if (!assets || assets.length === 0) {
        assetsGrid.innerHTML = `
            <div class="col-12 text-center py-5">
                <i class="fas fa-search fa-3x text-muted mb-3"></i>
                <h4>Nenhum ativo encontrado</h4>
                <p class="text-muted">Tente ajustar os filtros ou buscar por outro termo.</p>
            </div>
        `;
        return;
    }
    
    // Limpar a grade
    assetsGrid.innerHTML = '';
    
    // Adicionar os ativos à grade
    assets.forEach(asset => {
        const assetCard = createAssetCard(asset);
        assetsGrid.appendChild(assetCard);
    });
}

// Criar card de ativo
function createAssetCard(asset) {
    const isPositive = asset.variacao_percentual_24h >= 0;
    const changeClass = isPositive ? 'text-success' : 'text-danger';
    const changeIcon = isPositive ? 'fa-arrow-up' : 'fa-arrow-down';
    
    // Formatar valores monetários
    const priceFormatted = window.Utils?.formatCurrency(asset.price) || `R$ ${asset.price?.toFixed(2) || '0,00'}`;
    const marketCapFormatted = window.Utils?.formatMarketCap ? 
        window.Utils.formatMarketCap(asset.valor_mercado) : 
        `R$ ${asset.valor_mercado?.toLocaleString('pt-BR') || 'N/A'}`;
    const volumeFormatted = window.Utils?.formatNumber ? 
        window.Utils.formatNumber(asset.volume_24h) : 
        asset.volume_24h?.toLocaleString('pt-BR') || '0';
    
    const card = document.createElement('div');
    card.className = 'col-md-6 col-lg-4 mb-4';
    card.innerHTML = `
        <div class="card h-100 asset-card" data-asset-id="${asset.id}">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-3">
                    <div>
                        <h5 class="card-title mb-1">${asset.symbol}</h5>
                        <p class="text-muted small mb-2">${asset.name || 'N/A'}</p>
                    </div>
                    <span class="badge bg-secondary">${asset.bolsa || 'N/A'}</span>
                </div>
                
                <div class="d-flex align-items-center mb-3">
                    <h4 class="mb-0 me-2">${priceFormatted}</h4>
                    <span class="badge ${changeClass} bg-${isPositive ? 'success' : 'danger'}-subtle">
                        <i class="fas ${changeIcon} me-1"></i>
                        ${Math.abs(asset.variacao_percentual_24h || 0).toFixed(2)}%
                    </span>
                </div>
                
                <div class="row g-2 mb-3">
                    <div class="col-6">
                        <div class="small text-muted">Volume (24h)</div>
                        <div>${volumeFormatted}</div>
                    </div>
                    <div class="col-6">
                        <div class="small text-muted">Valor de Mercado</div>
                        <div>${marketCapFormatted}</div>
                    </div>
                    ${asset.dividend_yield ? `
                    <div class="col-6">
                        <div class="small text-muted">Dividend Yield</div>
                        <div>${asset.dividend_yield.toFixed(2)}%</div>
                    </div>` : ''}
                    ${asset.setor ? `
                    <div class="col-6">
                        <div class="small text-muted">Setor</div>
                        <div>${asset.setor}</div>
                    </div>` : ''}
                </div>
                
                <div class="d-flex gap-2 asset-actions">
                    <button class="btn btn-sm btn-outline-primary btn-add-to-portfolio" data-asset-id="${asset.id}">
                        <i class="fas fa-plus me-1"></i> Adicionar
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="showAssetDetails('${asset.id}')">
                        <i class="fas fa-chart-line me-1"></i> Detalhes
                    </button>
                </div>
            </div>
        </div>
    `;
    
    return card;
}

// Mostrar detalhes do ativo no modal
async function showAssetDetails(assetId) {
    try {
        showLoading(true);
        
        // Buscar detalhes do ativo na API
        const response = await fetch(`/api/price/${assetId}`);
        if (!response.ok) {
            throw new Error('Ativo não encontrado');
        }
        
        const asset = await response.json();
        
        // Preencher o modal com os dados do ativo
        document.getElementById('detailSymbol').textContent = asset.symbol;
        document.getElementById('detailName').textContent = asset.name || 'N/A';
        document.getElementById('detailPrice').textContent = formatCurrency(asset.price);
        
        // Atualizar variação
        const changeElement = document.getElementById('detailChange');
        const isPositive = asset.variacao_percentual_24h >= 0;
        changeElement.textContent = `${isPositive ? '+' : ''}${asset.variacao_percentual_24h?.toFixed(2) || '0.00'}%`;
        changeElement.className = `badge bg-${isPositive ? 'success' : 'danger'}-subtle text-${isPositive ? 'success' : 'danger'}`;
        
        // Preencher outras informações
        document.getElementById('detail52wLow').textContent = window.Utils?.formatCurrency ? 
            window.Utils.formatCurrency(asset.min_52s) : 
            `R$ ${asset.min_52s?.toFixed(2) || '0,00'}`;
            
        document.getElementById('detail52wHigh').textContent = window.Utils?.formatCurrency ? 
            window.Utils.formatCurrency(asset.max_52s) : 
            `R$ ${asset.max_52s?.toFixed(2) || '0,00'}`;
            
        document.getElementById('detailVolume').textContent = window.Utils?.formatNumber ? 
            window.Utils.formatNumber(asset.volume_24h) : 
            asset.volume_24h?.toLocaleString('pt-BR') || '0';
            
        document.getElementById('detailMarketCap').textContent = window.Utils?.formatMarketCap ? 
            window.Utils.formatMarketCap(asset.valor_mercado) : 
            `R$ ${asset.valor_mercado?.toLocaleString('pt-BR') || 'N/A'}`;
        
        // Preencher indicadores
        if (asset.pe_ratio) {
            document.getElementById('detailPE').textContent = asset.pe_ratio.toFixed(2);
        }
        
        if (asset.pb_ratio) {
            document.getElementById('detailPB').textContent = asset.pb_ratio.toFixed(2);
        }
        
        if (asset.dividend_yield) {
            document.getElementById('detailDivYield').textContent = `${asset.dividend_yield.toFixed(2)}%`;
        }
        
        if (asset.roe) {
            document.getElementById('detailROE').textContent = `${asset.roe.toFixed(2)}%`;
        }
        
        // Configurar o formulário de adicionar à carteira
        document.getElementById('assetId').value = asset.id;
        document.getElementById('avgPrice').value = asset.price?.toFixed(2) || '0.00';
        
        // Renderizar gráfico
        renderAssetChart(asset);
        
        // Mostrar o modal
        const modal = new bootstrap.Modal(document.getElementById('assetDetailModal'));
        modal.show();
        
    } catch (error) {
        console.error('Erro ao carregar detalhes do ativo:', error);
        showError('Erro ao carregar detalhes do ativo. Tente novamente mais tarde.');
    } finally {
        showLoading(false);
    }
}

// Renderizar gráfico de preços
function renderAssetChart(asset) {
    try {
        const chartElement = document.getElementById('assetDetailChart');
        if (!chartElement) return;
        
        // Limpar o gráfico anterior
        chartElement.innerHTML = '';
        
        // Verificar se há dados históricos
        let chartData = [];
        
        if (asset.historico_precos && Array.isArray(asset.historico_precos)) {
            chartData = asset.historico_precos;
        } else if (typeof asset.historico_precos === 'string') {
            try {
                chartData = JSON.parse(asset.historico_precos);
            } catch (e) {
                console.error('Erro ao analisar histórico de preços:', e);
            }
        }
        
        if (!chartData || chartData.length === 0) {
            chartElement.innerHTML = '<div class="text-center py-4 text-muted">Dados históricos não disponíveis</div>';
            return;
        }
        
        // Preparar dados para o gráfico
        const dates = chartData.map(item => item.date || item.x);
        const prices = chartData.map(item => item.price || item.y);
        
        // Configuração do gráfico
        const options = {
            series: [{
                name: 'Preço',
                data: prices.map((price, index) => ({
                    x: dates[index],
                    y: price
                }))
            }],
            chart: {
                type: 'area',
                height: 250,
                zoom: {
                    enabled: false
                },
                toolbar: {
                    show: false
                },
                sparkline: {
                    enabled: true
                }
            },
            dataLabels: {
                enabled: false
            },
            stroke: {
                curve: 'smooth',
                width: 2
            },
            fill: {
                type: 'gradient',
                gradient: {
                    shadeIntensity: 1,
                    opacityFrom: 0.7,
                    opacityTo: 0.2,
                    stops: [0, 100]
                }
            },
            xaxis: {
                type: 'datetime',
                labels: {
                    show: false
                },
                axisBorder: {
                    show: false
                },
                axisTicks: {
                    show: false
                }
            },
            yaxis: {
                show: false
            },
            grid: {
                show: false,
                padding: {
                    left: 0,
                    right: 0
                }
            },
            tooltip: {
                enabled: true,
                x: {
                    format: 'dd MMM yyyy'
                },
                y: {
                    formatter: function(value) {
                        return 'R$ ' + value.toFixed(2);
                    }
                }
            },
            colors: ['#198754']
        };
        
        // Renderizar o gráfico
        const chart = new ApexCharts(chartElement, options);
        chart.render();
        
    } catch (error) {
        console.error('Erro ao renderizar gráfico:', error);
        const chartElement = document.getElementById('assetDetailChart');
        if (chartElement) {
            chartElement.innerHTML = '<div class="text-center py-4 text-muted">Erro ao carregar o gráfico</div>';
        }
    }
}

// Mostrar modal de adicionar à carteira
function showAddToPortfolioModal(assetId) {
    // Aqui você pode implementar a lógica para mostrar o modal de adicionar à carteira
    // e preencher os campos com os dados do ativo, se necessário
    const modal = new bootstrap.Modal(document.getElementById('addToPortfolioModal'));
    modal.show();
}

// Manipulador de envio do formulário de adicionar à carteira
async function handleAddToPortfolio(e) {
    e.preventDefault();
    
    const form = e.target;
    const formData = new FormData(form);
    const assetId = formData.get('assetId');
    const quantity = parseFloat(formData.get('quantity'));
    const avgPrice = parseFloat(formData.get('avgPrice'));
    
    if (!assetId || isNaN(quantity) || quantity <= 0 || isNaN(avgPrice) || avgPrice <= 0) {
        showError('Por favor, preencha todos os campos corretamente.');
        return;
    }
    
    try {
        showLoading(true);
        
        // Aqui você faria uma chamada à API para adicionar o ativo à carteira
        const response = await fetch('/api/portfolio/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                asset_id: assetId,
                quantity: quantity,
                avg_price: avgPrice
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || 'Erro ao adicionar à carteira');
        }
        
        // Fechar o modal e mostrar mensagem de sucesso
        const modal = bootstrap.Modal.getInstance(document.getElementById('addToPortfolioModal'));
        modal.hide();
        
        showSuccess('Ativo adicionado à carteira com sucesso!');
        
        // Limpar o formulário
        form.reset();
        
    } catch (error) {
        console.error('Erro ao adicionar à carteira:', error);
        showError(error.message || 'Erro ao adicionar à carteira. Tente novamente mais tarde.');
    } finally {
        showLoading(false);
    }
}

// Manipulador de envio do formulário de alerta
async function handleSetAlert(e) {
    e.preventDefault();
    
    const form = e.target;
    const formData = new FormData(form);
    const assetId = formData.get('assetId');
    const alertType = formData.get('alertType');
    const alertValue = parseFloat(formData.get('alertValue'));
    
    if (!assetId || !alertType || isNaN(alertValue) || alertValue <= 0) {
        showError('Por favor, preencha todos os campos corretamente.');
        return;
    }
    
    try {
        showLoading(true);
        
        // Aqui você faria uma chamada à API para configurar o alerta
        const response = await fetch('/api/alerts/set', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                asset_id: assetId,
                alert_type: alertType,
                value: alertValue
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || 'Erro ao configurar alerta');
        }
        
        // Fechar o modal e mostrar mensagem de sucesso
        const modal = bootstrap.Modal.getInstance(document.getElementById('setAlertModal'));
        modal.hide();
        
        showSuccess('Alerta configurado com sucesso!');
        
        // Limpar o formulário
        form.reset();
        
    } catch (error) {
        console.error('Erro ao configurar alerta:', error);
        showError(error.message || 'Erro ao configurar alerta. Tente novamente mais tarde.');
    } finally {
        showLoading(false);
    }
}

// Funções auxiliares

// Atualizar contador de resultados
function updateResultsCount(count) {
    if (resultsCount) {
        resultsCount.textContent = count;
    }
}

// Mostrar/ocultar indicador de carregamento
function showLoading(show) {
    if (window.Utils && typeof window.Utils.showLoading === 'function') {
        window.Utils.showLoading(show ? 'body' : null);
    } else if (loadingIndicator) {
        loadingIndicator.style.display = show ? 'block' : 'none';
        
        if (assetsGrid) {
            assetsGrid.style.opacity = show ? '0.5' : '1';
            assetsGrid.style.pointerEvents = show ? 'none' : 'auto';
        }
    }
}

// Mostrar mensagem de erro
function showError(message) {
    if (window.Utils && typeof window.Utils.showToast === 'function') {
        window.Utils.showToast(message, 'error');
    } else {
        console.error('Erro:', message);
        alert(`Erro: ${message}`);
    }
}

// Mostrar mensagem de sucesso
function showSuccess(message) {
    if (window.Utils && typeof window.Utils.showToast === 'function') {
        window.Utils.showToast(message, 'success');
    } else {
        console.log('Sucesso:', message);
        alert(`Sucesso: ${message}`);
    }
}

// Obter token CSRF
function getCSRFToken() {
    const csrfToken = document.querySelector('meta[name="csrf-token"]');
    return csrfToken ? csrfToken.getAttribute('content') : '';
}
