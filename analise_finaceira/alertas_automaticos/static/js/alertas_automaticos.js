/**
 * Módulo de Gerenciamento de Alertas Automáticos
 * 
 * Este módulo gerencia a interação do usuário com a lista de alertas,
 * incluindo filtros, paginação e marcação de alertas como lidos.
 * 
 * @namespace AlertasAutomaticos
 */

// Módulo principal
const AlertasAutomaticos = (function() {
    // Configurações globais
    const config = {
        selectors: {
            alertaCard: '.alerta-card',
            alertaNaoLido: '.alerta-card.alerta-nao-lido',
            contadorNaoLidos: '#contador-nao-lidos',
            formFiltros: '#form-filtros',
            btnLimparFiltros: '#btn-limpar-filtros',
            tooltip: '[data-bs-toggle="tooltip"]',
            popover: '[data-bs-toggle="popover"]',
            tabelaAlertas: '.tabela-alertas'
        },
        urls: {
            marcarLido: '/alertas-automaticos/{id}/marcar-lido'
        },
        mensagens: {
            erroPadrao: 'Ocorreu um erro inesperado. Por favor, tente novamente.'
        }
    };

    /**
     * Inicializa o módulo
     */
    function init() {
        inicializarTooltips();
        inicializarEventos();
        inicializarDataTable();
    }

    /**
     * Inicializa os tooltips do Bootstrap
     */
    function inicializarTooltips() {
        const tooltipTriggerList = document.querySelectorAll(config.selectors.tooltip);
        if (tooltipTriggerList.length > 0) {
            tooltipTriggerList.forEach(tooltipTriggerEl => {
                new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }
    }

    /**
     * Inicializa os eventos da aplicação
     */
    function inicializarEventos() {
        // Evento de clique nos cards de alerta
        document.querySelectorAll(config.selectors.alertaNaoLido).forEach(card => {
            card.addEventListener('click', handleAlertaClick);
        });

        // Eventos do formulário de filtros
        const formFiltros = document.querySelector(config.selectors.formFiltros);
        if (formFiltros) {
            formFiltros.addEventListener('submit', handleFiltroSubmit);
            
            const btnLimpar = document.querySelector(config.selectors.btnLimparFiltros);
            if (btnLimpar) {
                btnLimpar.addEventListener('click', limparFiltros);
            }
        }
    }

    /**
     * Inicializa o DataTable se estiver disponível
     */
    function inicializarDataTable() {
        if (typeof $.fn.DataTable === 'function') {
            $(config.selectors.tabelaAlertas).DataTable({
                pageLength: 25,
                language: {
                    url: '//cdn.datatables.net/plug-ins/1.10.25/i18n/Portuguese-Brasil.json'
                },
                order: [[0, 'desc']],
                responsive: true,
                dom: '<"table-responsive"t>ip',
                processing: true
            });
        }
    }

    /**
     * Manipula o clique em um alerta
     * @param {Event} event - Objeto de evento
     */
    function handleAlertaClick(event) {
        const card = event.currentTarget;
        const alertaId = card.getAttribute('data-alerta-id');
        
        if (alertaId && card.classList.contains('alerta-nao-lido')) {
            marcarComoLido(alertaId, card);
        }
    }

    /**
     * Marca um alerta como lido
     * @param {string} alertaId - ID do alerta
     * @param {HTMLElement} cardElement - Elemento do card do alerta
     */
    async function marcarComoLido(alertaId, cardElement) {
        if (!alertaId) return;
        
        const url = config.urls.marcarLido.replace('{id}', alertaId);
        
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error('Erro na requisição');
            }

            const data = await response.json();
            
            if (data.success) {
                atualizarEstadoAlerta(cardElement);
                atualizarContadorNaoLidos(-1);
            } else {
                throw new Error(data.message || 'Erro ao marcar alerta como lido');
            }
        } catch (error) {
            console.error('Erro ao marcar alerta como lido:', error);
            showToast('Erro', error.message || config.mensagens.erroPadrao, 'error');
        }
    }

    /**
     * Atualiza o estado visual do alerta para "lido"
     * @param {HTMLElement} cardElement - Elemento do card do alerta
     */
    function atualizarEstadoAlerta(cardElement) {
        if (cardElement) {
            cardElement.classList.remove('alerta-nao-lido');
            cardElement.classList.add('alerta-lido');
            cardElement.removeEventListener('click', handleAlertaClick);
        }
    }

    /**
     * Atualiza o contador de alertas não lidos
     * @param {number} diferenca - Valor a ser adicionado/subtraído do contador
     */
    function atualizarContadorNaoLidos(diferenca) {
        const contadorElement = document.querySelector(config.selectors.contadorNaoLidos);
        if (contadorElement) {
            let contadorAtual = parseInt(contadorElement.textContent) || 0;
            contadorAtual += diferenca;
            contadorElement.textContent = contadorAtual > 0 ? contadorAtual : '';
            contadorElement.style.display = contadorAtual > 0 ? 'inline-block' : 'none';
        }
    }

    /**
     * Manipula o envio do formulário de filtros
     * @param {Event} event - Objeto de evento
     */
    function handleFiltroSubmit(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const params = new URLSearchParams();
        
        // Adiciona apenas os filtros preenchidos
        for (const [key, value] of formData.entries()) {
            if (value) {
                params.append(key, value);
            }
        }
        
        // Redireciona com os parâmetros de filtro
        window.location.href = `${window.location.pathname}?${params.toString()}`;
    }

    /**
     * Limpa os filtros atuais
     */
    function limparFiltros() {
        window.location.href = window.location.pathname;
    }

    /**
     * Exibe uma notificação toast
     * @param {string} titulo - Título da notificação
     * @param {string} mensagem - Mensagem da notificação
     * @param {string} tipo - Tipo de notificação (success, error, info, warning)
     */
    function showToast(titulo, mensagem, tipo = 'info') {
        // Verifica se o Toast do Bootstrap está disponível
        if (typeof bootstrap !== 'undefined' && typeof bootstrap.Toast !== 'undefined') {
            const toastContainer = document.querySelector('.toast-container');
            if (!toastContainer) return;
            
            const toastId = `toast-${Date.now()}`;
            const toastClass = `text-bg-${tipo}`;
            
            const toastHTML = `
                <div id="${toastId}" class="toast ${toastClass}" role="alert" aria-live="assertive" aria-atomic="true">
                    <div class="toast-header">
                        <strong class="me-auto">${titulo}</strong>
                        <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Fechar"></button>
                    </div>
                    <div class="toast-body">
                        ${mensagem}
                    </div>
                </div>
            `;
            
            toastContainer.insertAdjacentHTML('beforeend', toastHTML);
            
            const toastElement = document.getElementById(toastId);
            const toast = new bootstrap.Toast(toastElement, {
                autohide: true,
                delay: 5000
            });
            
            toast.show();
            
            // Remove o toast do DOM após ser escondido
            toastElement.addEventListener('hidden.bs.toast', function() {
                toastElement.remove();
            });
        } else {
            // Fallback para navegadores mais antigos
            alert(`${titulo}: ${mensagem}`);
        }
    }


    /**
     * Executa a análise de alertas
     */
    async function executarAnalise() {
        const overlay = document.getElementById('loading-overlay');
        const btn = document.getElementById('btn-executar-analise');
        const btnHtml = btn.innerHTML;
        
        try {
            // Mostrar overlay de carregamento
            overlay.style.display = 'flex';
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Executando...';
            
            // Executar a análise via fetch
            const response = await fetch('{{ url_for("alertas_automaticos.index") }}?executar_analise=true', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error('Erro na requisição');
            }
            
            const data = await response.json();
            
            if (data.sucesso) {
                showToast('Sucesso', data.mensagem || 'Análise concluída com sucesso!', 'success');
                
                // Recarregar a página após 1,5 segundos
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                throw new Error(data.mensagem || 'Erro ao executar análise');
            }
        } catch (error) {
            console.error('Erro ao executar análise:', error);
            showToast('Erro', error.message || 'Erro ao executar análise', 'error');
        } finally {
            if (overlay && btn) {
                overlay.style.display = 'none';
                btn.disabled = false;
                btn.innerHTML = btnHtml;
            }
        }
    }
    
    /**
     * Limpa todos os alertas
     */
    async function limparAlertas() {
        if (!confirm('Tem certeza que deseja remover TODOS os alertas? Esta ação não pode ser desfeita.')) {
            return;
        }
        
        const btn = document.getElementById('btn-limpar-alertas');
        const btnHtml = btn ? btn.innerHTML : '';
        
        try {
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Removendo...';
            }
            
            // Fazer a requisição para limpar os alertas
            const response = await fetch('{{ url_for("alertas_automaticos.limpar_alertas") }}', {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error('Erro na requisição');
            }
            
            const data = await response.json();
            
            if (data.sucesso) {
                showToast('Sucesso', data.mensagem || 'Alertas removidos com sucesso!', 'success');
                
                // Recarregar a página após 1,5 segundos
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                throw new Error(data.mensagem || 'Erro ao limpar alertas');
            }
        } catch (error) {
            console.error('Erro ao limpar alertas:', error);
            showToast('Erro', error.message || 'Erro ao limpar alertas', 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = btnHtml;
            }
        }
    }

    // API Pública
    return {
        init: init,
        formatarData: formatarData,
        formatarMoeda: formatarMoeda,
        executarAnalise: executarAnalise,
        limparAlertas: limparAlertas
    };
})();

// Inicializa o módulo quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    AlertasAutomaticos.init();
});

/**
 * Formata uma data para o formato brasileiro
 * @param {string} dataString - Data no formato ISO
 * @returns {string} Data formatada
 */
function formatarData(dataString) {
    if (!dataString) return '';
    
    try {
        const data = new Date(dataString);
        if (isNaN(data.getTime())) return '';
        
        return data.toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        });
    } catch (error) {
        console.error('Erro ao formatar data:', error);
        return '';
    }
}

/**
 * Formata um valor monetário
 * @param {number} valor - Valor a ser formatado
 * @param {number} casasDecimais - Número de casas decimais (padrão: 2)
 * @returns {string} Valor formatado como moeda brasileira
 */
function formatarMoeda(valor, casasDecimais = 2) {
    if (valor === null || valor === undefined || isNaN(Number(valor))) {
        return 'R$ 0,00';
    }
    
    const valorNumerico = Number(valor);
    
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL',
        minimumFractionDigits: casasDecimais,
        maximumFractionDigits: casasDecimais
    }).format(valorNumerico);
}

// Exporta as funções para uso global
window.AlertasAutomaticos = AlertasAutomaticos;
