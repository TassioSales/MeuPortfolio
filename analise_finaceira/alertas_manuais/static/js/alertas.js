// Configurações globais
const CONFIG = {
    itensPorPagina: 20,
    ordenacaoPadrao: 'data-desc',
    paginaAtual: 1,
    totalItens: 0,
    totalPaginas: 0,
    filtrosativos: {
        busca: '',
        prioridade: '',
        tipo: '',
        periodo: '',
        status: ''
    }
};

// Elementos da interface
let ELEMENTOS = {};

// Inicializa os elementos da interface
function inicializarElementos() {
    console.log('Iniciando inicialização dos elementos da interface...');
    
    // Elementos principais
    const listaAlertas = document.getElementById('lista-alertas');
    const loadingAlertas = document.getElementById('loading-alertas');
    const nenhumAlerta = document.getElementById('nenhum-alerta');
    const totalAlertas = document.getElementById('total-alertas');
    const alertasativos = document.getElementById('alertas-ativos');
    const valorTotal = document.getElementById('valor-total');
    const searchInput = document.getElementById('searchInput');
    
    // Filtros
    const filtroPrioridade = document.getElementById('filtro-prioridade');
    const filtrotipo = document.getElementById('filtro-tipo');
    const filtroPeriodo = document.getElementById('filtro-periodo');
    const filtroStatus = document.getElementById('filtro-status');
    const limparFiltros = document.getElementById('limpar-filtros');
    
    // Paginação
    const paginacao = document.getElementById('paginacao');
    const totalItens = document.getElementById('total-itens');
    const totalItensFooter = document.getElementById('total-itens-footer');
    const inicioItens = document.getElementById('inicio-itens');
    const fimItens = document.getElementById('fim-itens');
    
    // Modal de exclusão
    const modalExcluirElement = document.getElementById('modalExcluirAlerta');
    const btnConfirmarExclusao = document.getElementById('confirmar-exclusao');
    
    console.log('Elementos encontrados:', {
        listaAlertas: !!listaAlertas,
        loadingAlertas: !!loadingAlertas,
        nenhumAlerta: !!nenhumAlerta,
        totalAlertas: !!totalAlertas,
        alertasativos: !!alertasativos,
        valorTotal: !!valorTotal,
        searchInput: !!searchInput,
        filtroPrioridade: !!filtroPrioridade,
        filtrotipo: !!filtrotipo,
        filtroPeriodo: !!filtroPeriodo,
        filtroStatus: !!filtroStatus,
        limparFiltros: !!limparFiltros,
        paginacao: !!paginacao,
        totalItens: !!totalItens,
        totalItensFooter: !!totalItensFooter,
        inicioItens: !!inicioItens,
        fimItens: !!fimItens,
        modalExcluirElement: !!modalExcluirElement,
        btnConfirmarExclusao: !!btnConfirmarExclusao
    });
    
    if (!btnConfirmarExclusao) {
        console.error('ERRO: Botão de confirmação de exclusão não encontrado no DOM');
        console.log('Procurando por elementos com ID que contenham "confirmar" ou "exclusao":', 
            Array.from(document.querySelectorAll('[id*="confirmar"], [id*="exclusao"]')).map(el => ({
                id: el.id,
                tag: el.tagName,
                className: el.className
            }))
        );
    }
    
    ELEMENTOS = {
        listaAlertas,
        loadingAlertas,
        nenhumAlerta,
        totalAlertas,
        alertasativos,
        valorTotal,
        searchInput,
        filtroPrioridade,
        filtrotipo,
        filtroPeriodo,
        filtroStatus,
        limparFiltros,
        paginacao,
        totalItens,
        totalItensFooter,
        inicioItens,
        fimItens,
        modalExcluirElement,
        modalExcluir: null,
        btnConfirmarExclusao
    };
    
    console.log('Elementos inicializados com sucesso');
}

// Utilitários
const Utils = {
    // Formata uma data no formato brasileiro
    formatarData: (dataString, incluirHora = false) => {
        if (!dataString) return 'N/A';
        
        const data = new Date(dataString);
        if (isNaN(data.getTime())) return 'Data inválida';
        
        const opcoes = { 
            day: '2-digit', 
            month: '2-digit', 
            year: 'numeric' 
        };
        
        if (incluirHora) {
            opcoes.hour = '2-digit';
            opcoes.minute = '2-digit';
        }
        
        return data.toLocaleDateString('pt-BR', opcoes);
    },
    
    // Formata um valor monetário
    formatarMoeda: (valor) => {
        if (valor === null || valor === undefined) return 'R$ 0,00';
        return new Intl.NumberFormat('pt-BR', { 
            style: 'currency', 
            currency: 'BRL' 
        }).format(parseFloat(valor));
    },
    
    // Obtém a classe CSS baseada na prioridade
    getClassePrioridade: (prioridade) => {
        const classes = {
            'alta': 'danger',
            'média': 'warning',
            'media': 'warning',
            'baixa': 'success'
        };
        return classes[prioridade?.toLowerCase()] || 'secondary';
    },
    
    // Obtém o ícone baseado no tipo de alerta
    getIconetipo: (tipo) => {
        const icones = {
            'despesa': 'bi-arrow-up-circle text-danger',
            'receita': 'bi-arrow-down-circle text-success',
            'saldo': 'bi-graph-up text-primary',
            'default': 'bi-bell-fill text-info'
        };
        return icones[tipo?.toLowerCase()] || icones.default;
    },
    
    // Função para debounce (evitar múltiplas chamadas rápidas)
    debounce: (func, wait) => {
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
};

// Função para renderizar os alertas em cards
function renderizarAlertas(alertas) {
    if (!ELEMENTOS.listaAlertas) return;
    
    // Se não houver alertas, mostra mensagem
    if (!alertas || alertas.length === 0) {
        ELEMENTOS.nenhumAlerta.classList.remove('d-none');
        ELEMENTOS.listaAlertas.innerHTML = '';
        
        // Atualiza os contadores para zero
        ELEMENTOS.totalItens.textContent = '0';
        ELEMENTOS.totalItensFooter.textContent = '0';
        ELEMENTOS.inicioItens.textContent = '0';
        ELEMENTOS.fimItens.textContent = '0';
        
        return;
    }
    
    // Esconde a mensagem de nenhum alerta
    ELEMENTOS.nenhumAlerta.classList.add('d-none');
    
    // Calcula os totais
    const totalItens = alertas.length;
    const inicio = (CONFIG.paginaAtual - 1) * CONFIG.itensPorPagina + 1;
    const fim = Math.min(CONFIG.paginaAtual * CONFIG.itensPorPagina, totalItens);
    
    // Atualiza os contadores
    ELEMENTOS.totalItens.textContent = totalItens;
    ELEMENTOS.totalItensFooter.textContent = totalItens;
    ELEMENTOS.inicioItens.textContent = inicio;
    ELEMENTOS.fimItens.textContent = fim;
    
    // Filtra os itens da página atual
    const alertasPaginados = alertas.slice(inicio - 1, fim);
    
    // Limpa a lista de alertas
    ELEMENTOS.listaAlertas.innerHTML = '';
    
    // Adiciona cada alerta como um card
    alertasPaginados.forEach(alerta => {
        const template = document.getElementById('template-card-alerta');
        if (!template) return;
        
        const clone = template.content.cloneNode(true);
        const card = clone.querySelector('.alerta-item');
        
        // Preenche os dados do card
        if (alerta.descricao) {
            const titulo = card.querySelector('.card-title');
            if (titulo) {
                titulo.textContent = alerta.descricao;
                titulo.setAttribute('title', alerta.descricao);
            }
        }
        
        // Descrição detalhada
        if (alerta.descricao_detalhada) {
            const descricao = card.querySelector('.card-text');
            if (descricao) {
                descricao.textContent = alerta.descricao_detalhada;
                descricao.setAttribute('title', alerta.descricao_detalhada);
            }
        }
        
        // Valor
        if (alerta.valor !== undefined) {
            const valorElement = card.querySelector('.valor');
            if (valorElement) {
                valorElement.textContent = Utils.formatarMoeda(alerta.valor);
                valorElement.closest('.meta-item').setAttribute('title', `Valor: ${Utils.formatarMoeda(alerta.valor)}`);
            }
        } else {
            const valorElement = card.querySelector('.valor');
            if (valorElement) {
                valorElement.textContent = 'Não informado';
                valorElement.closest('.meta-item').setAttribute('title', 'Valor não informado');
            }
        }
        
        // Data
        if (alerta.data_vencimento) {
            const dataElement = card.querySelector('.data');
            if (dataElement) {
                dataElement.textContent = Utils.formatarData(alerta.data_vencimento);
                dataElement.closest('.meta-item').setAttribute('title', `Vencimento: ${Utils.formatarData(alerta.data_vencimento)}`);
            }
        } else {
            const dataElement = card.querySelector('.data');
            if (dataElement) {
                dataElement.textContent = 'Sem data';
                dataElement.closest('.meta-item').setAttribute('title', 'Data não informada');
            }
        }
        
        // tipo de alerta
        const tipoAlerta = card.querySelector('#tipo-alerta');
        const iconeContainer = card.querySelector('.alerta-tipo-container');
        const iconeBadge = card.querySelector('.alerta-tipo-container .badge:last-child');
        const iconeMoeda = card.querySelector('.bi-currency-dollar');
        
        if (tipoAlerta && iconeContainer && iconeBadge) {
            const tipoText = alerta.tipo_alerta || 'outro';
            const tipoFormatado = tipoText === 'receita' ? 'Receita' : 
                                tipoText === 'despesa' ? 'Despesa' : 'Outro';
            
            // Limpa classes existentes
            tipoAlerta.className = 'badge';
            iconeBadge.className = 'badge';
            
            // Remove ícone anterior, se existir
            const iconeAnterior = iconeBadge.querySelector('.bi');
            if (iconeAnterior) {
                iconeBadge.removeChild(iconeAnterior);
            }
            
            // Cria o novo ícone
            const icone = document.createElement('i');
            icone.className = 'bi';
            
            // Define classes baseadas no tipo
            if (tipoText === 'receita') {
                // Receita - Verde
                tipoAlerta.classList.add('bg-success', 'text-white');
                iconeBadge.classList.add('bg-success', 'bg-opacity-25', 'text-success');
                icone.classList.add('bi-arrow-up-circle-fill');
            } else if (tipoText === 'despesa') {
                // Despesa - Vermelho
                tipoAlerta.classList.add('bg-danger', 'text-white');
                iconeBadge.classList.add('bg-danger', 'bg-opacity-25', 'text-danger');
                icone.classList.add('bi-arrow-down-circle-fill');
            } else {
                // Outro - Cinza
                tipoAlerta.classList.add('bg-secondary', 'text-white');
                iconeBadge.classList.add('bg-secondary', 'bg-opacity-25', 'text-secondary');
                icone.classList.add('bi-question-circle-fill');
            }
            
            // Adiciona o ícone ao badge
            iconeBadge.appendChild(icone);
            
            // Adiciona borda ao badge do ícone
            iconeBadge.style.border = '1px solid';
            iconeBadge.style.borderColor = 'currentColor';
            
            tipoAlerta.textContent = tipoFormatado;
            tipoAlerta.setAttribute('title', `tipo: ${tipoFormatado}`);
            iconeBadge.setAttribute('title', `tipo: ${tipoFormatado}`);
        }
        
        // Status (badge no canto superior esquerdo)
        const statusBadge = card.querySelector('.badge-status');
        if (statusBadge) {
            const estaativo = alerta.ativo !== undefined ? alerta.ativo : true;
            statusBadge.setAttribute('data-status', estaativo);
            statusBadge.innerHTML = `
                <i class="bi ${estaativo ? 'bi-check-circle-fill' : 'bi-x-circle-fill'}"></i>
                <span class="d-none d-sm-inline">${estaativo ? 'ativo' : 'Inativo'}</span>
            `;
            statusBadge.setAttribute('title', `Alerta ${estaativo ? 'ativo' : 'inativo'}`);
        }
        
        // Prioridade
        const prioridade = card.querySelector('.badge-prioridade');
        if (prioridade) {
            const prioridadeText = alerta.prioridade ? alerta.prioridade.toUpperCase() : 'NÃO DEFINIDA';
            prioridade.textContent = prioridadeText;
            prioridade.setAttribute('data-prioridade', alerta.prioridade?.toLowerCase() || '');
            prioridade.setAttribute('title', `Prioridade: ${prioridadeText}`);
        }
        
        // Valor
        if (alerta.valor_referencia) {
            const valor = card.querySelector('.valor');
            if (valor) valor.textContent = Utils.formatarMoeda(alerta.valor_referencia);
        }
        
        // Data
        if (alerta.criado_em) {
            const data = card.querySelector('.data');
            if (data) data.textContent = Utils.formatarData(alerta.criado_em, true);
        }
        
        // Define os IDs para os botões de ação
        const botoesEditar = card.querySelectorAll('.btn-editar');
        const botoesExcluir = card.querySelectorAll('.btn-excluir');
        
        botoesEditar.forEach(btn => btn.setAttribute('data-id', alerta.id));
        botoesExcluir.forEach(btn => btn.setAttribute('data-id', alerta.id));
        
        // Adiciona o card à lista
        ELEMENTOS.listaAlertas.appendChild(card);
    });
    
    // Atualiza a paginação
    atualizarPaginacao(totalItens);
    
    // Inicializa os tooltips
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.forEach(tooltipTriggerEl => {
            new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
}

// Função para atualizar a paginação
function atualizarPaginacao(totalItens) {
    if (!ELEMENTOS.paginacao) return;
    
    const totalPaginas = Math.ceil(totalItens / CONFIG.itensPorPagina);
    CONFIG.totalPaginas = totalPaginas;
    
    // Se não houver necessidade de paginação, limpa e retorna
    if (totalPaginas <= 1) {
        ELEMENTOS.paginacao.innerHTML = '';
        return;
    }
    
    let paginacaoHTML = '';
    const maxBotoes = 5;
    let inicio = Math.max(1, CONFIG.paginaAtual - Math.floor(maxBotoes / 2));
    let fim = Math.min(totalPaginas, inicio + maxBotoes - 1);
    
    if (fim - inicio + 1 < maxBotoes) {
        inicio = Math.max(1, fim - maxBotoes + 1);
    }
    
    // Botão Anterior
    paginacaoHTML += `
        <li class="page-item ${CONFIG.paginaAtual === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" data-pagina="${CONFIG.paginaAtual - 1}" aria-label="Anterior">
                <span aria-hidden="true">&laquo;</span>
            </a>
        </li>`;
    
    // Primeira página
    if (inicio > 1) {
        paginacaoHTML += `
            <li class="page-item">
                <a class="page-link" href="#" data-pagina="1">1</a>
            </li>`;
        if (inicio > 2) {
            paginacaoHTML += '<li class="page-item disabled"><span class="page-link">...</span></li>';
        }
    }
    
    // Páginas intermediárias
    for (let i = inicio; i <= fim; i++) {
        paginacaoHTML += `
            <li class="page-item ${i === CONFIG.paginaAtual ? 'active' : ''}">
                <a class="page-link" href="#" data-pagina="${i}">${i}</a>
            </li>`;
    }
    
    // Última página
    if (fim < totalPaginas) {
        if (fim < totalPaginas - 1) {
            paginacaoHTML += '<li class="page-item disabled"><span class="page-link">...</span></li>';
        }
        paginacaoHTML += `
            <li class="page-item">
                <a class="page-link" href="#" data-pagina="${totalPaginas}">${totalPaginas}</a>
            </li>`;
    }
    
    // Botão Próximo
    paginacaoHTML += `
        <li class="page-item ${CONFIG.paginaAtual === totalPaginas ? 'disabled' : ''}">
            <a class="page-link" href="#" data-pagina="${CONFIG.paginaAtual + 1}" aria-label="Próximo">
                <span aria-hidden="true">&raquo;</span>
            </a>
        </li>`;
    
    ELEMENTOS.paginacao.innerHTML = paginacaoHTML;
    
    // Adiciona event listeners aos botões de paginação
    document.querySelectorAll('.page-link[data-pagina]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const pagina = parseInt(link.getAttribute('data-pagina'));
            if (pagina >= 1 && pagina <= totalPaginas && pagina !== CONFIG.paginaAtual) {
                CONFIG.paginaAtual = pagina;
                carregarAlertas();
                // Rola para o topo da lista
                ELEMENTOS.listaAlertas.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
}

// Função para carregar os alertas da API
async function carregarAlertas() {
    try {
        // Mostra o indicador de carregamento
        if (ELEMENTOS.loadingAlertas) {
            ELEMENTOS.loadingAlertas.classList.remove('d-none');
        }
        
        // Constrói a URL com os parâmetros de filtro
        const params = new URLSearchParams();
        if (CONFIG.filtrosativos.busca) params.append('busca', CONFIG.filtrosativos.busca);
        if (CONFIG.filtrosativos.prioridade) params.append('prioridade', CONFIG.filtrosativos.prioridade);
        if (CONFIG.filtrosativos.tipo) params.append('tipo', CONFIG.filtrosativos.tipo);
        if (CONFIG.filtrosativos.periodo) params.append('periodo', CONFIG.filtrosativos.periodo);
        if (CONFIG.filtrosativos.status) params.append('status', CONFIG.filtrosativos.status);
        
        // Adiciona parâmetros de paginação
        params.append('pagina', CONFIG.paginaAtual);
        params.append('itens_por_pagina', 20);
        
        // Faz a requisição para a API de alertas
        const resposta = await fetch(`/alertas-manuais/api/alertas?${params.toString()}`);
        
        if (!resposta.ok) {
            throw new Error('Erro ao carregar alertas');
        }
        
        const resultado = await resposta.json();
        
        // Verifica se a resposta tem a estrutura esperada
        if (resultado && resultado.success) {
            // Atualiza o total de itens
            CONFIG.totalItens = resultado.total || 0;
            
            // Atualiza as estatísticas
            if (ELEMENTOS.totalAlertas) {
                ELEMENTOS.totalAlertas.textContent = resultado.total || 0;
                ELEMENTOS.alertasativos.textContent = resultado.ativos || 0;
                ELEMENTOS.valorTotal.textContent = Utils.formatarMoeda(resultado.valor || 0);
            }
            
            // Renderiza os alertas
            renderizarAlertas(resultado.data || []);
            
            // Marca que os dados foram carregados
            document.body.setAttribute('data-loaded', 'true');
        } else {
            throw new Error('Formato de resposta inesperado da API');
        }
        
    } catch (erro) {
        console.error('Erro ao carregar alertas:', erro);
        
        // Exibe mensagem de erro na interface
        if (ELEMENTOS.listaAlertas) {
            ELEMENTOS.listaAlertas.innerHTML = `
                <div class="col-12 text-center py-5 text-danger">
                    <i class="bi bi-exclamation-triangle-fill fs-1"></i>
                    <p class="mt-2 mb-0">Erro ao carregar os alertas.</p>
                    <p class="small text-muted">${erro.message}</p>
                    <button class="btn btn-outline-primary mt-3" onclick="carregarAlertas()">
                        <i class="bi bi-arrow-clockwise me-2"></i>Tentar novamente
                    </button>
                </div>`;
        }
    } finally {
        // Esconde o indicador de carregamento
        if (ELEMENTOS.loadingAlertas) {
            ELEMENTOS.loadingAlertas.classList.add('d-none');
        }
    }
}

// Função para aplicar os filtros
function aplicarFiltros() {
    // Reseta para a primeira página ao aplicar novos filtros
    CONFIG.paginaAtual = 1;
    
    // Atualiza os filtros ativos
    CONFIG.filtrosativos = {
        busca: ELEMENTOS.searchInput ? ELEMENTOS.searchInput.value.trim() : '',
        prioridade: ELEMENTOS.filtroPrioridade ? ELEMENTOS.filtroPrioridade.value : '',
        tipo: ELEMENTOS.filtrotipo ? ELEMENTOS.filtrotipo.value : '',
        periodo: ELEMENTOS.filtroPeriodo ? ELEMENTOS.filtroPeriodo.value : '',
        status: ELEMENTOS.filtroStatus ? ELEMENTOS.filtroStatus.value : ''
    };
    
    // Recarrega os alertas com os novos filtros
    carregarAlertas();
}

// Função para limpar todos os filtros
function limparFiltros() {
    if (ELEMENTOS.searchInput) ELEMENTOS.searchInput.value = '';
    if (ELEMENTOS.filtroPrioridade) ELEMENTOS.filtroPrioridade.value = '';
    if (ELEMENTOS.filtrotipo) ELEMENTOS.filtrotipo.value = '';
    if (ELEMENTOS.filtroPeriodo) ELEMENTOS.filtroPeriodo.value = '';
    if (ELEMENTOS.filtroStatus) ELEMENTOS.filtroStatus.value = '';
    
    aplicarFiltros();
}

// Função para configurar os event listeners dos filtros
function configurarFiltros() {
    // Busca com debounce para evitar muitas requisições
    if (ELEMENTOS.searchInput) {
        const buscaComDebounce = Utils.debounce(() => {
            aplicarFiltros();
        }, 500);
        
        ELEMENTOS.searchInput.addEventListener('input', buscaComDebounce);
    }
    
    // Filtros de seleção
    if (ELEMENTOS.filtroPrioridade) {
        ELEMENTOS.filtroPrioridade.addEventListener('change', aplicarFiltros);
    }
    
    if (ELEMENTOS.filtrotipo) {
        ELEMENTOS.filtrotipo.addEventListener('change', aplicarFiltros);
    }
    
    if (ELEMENTOS.filtroPeriodo) {
        ELEMENTOS.filtroPeriodo.addEventListener('change', aplicarFiltros);
    }
    
    // Filtro de status
    if (ELEMENTOS.filtroStatus) {
        ELEMENTOS.filtroStatus.addEventListener('change', aplicarFiltros);
    }
    
    // Botão para limpar filtros
    if (ELEMENTOS.limparFiltros) {
        ELEMENTOS.limparFiltros.addEventListener('click', (e) => {
            e.preventDefault();
            limparFiltros();
        });
    }
}

// Função para configurar a ordenação
function configurarOrdenacao() {
    const itensOrdenacao = document.querySelectorAll('[data-sort]');
    
    itensOrdenacao.forEach(item => {
        item.addEventListener('click', function() {
            // Remove a classe 'active' de todos os itens
            itensOrdenacao.forEach(i => i.classList.remove('active'));
            
            // Adiciona a classe 'active' ao item clicado
            item.classList.add('active');
            
            // Atualiza a ordenação e recarrega os alertas
            const ordenacao = item.getAttribute('data-sort');
            if (ordenacao) {
                CONFIG.ordenacaoPadrao = ordenacao;
                CONFIG.paginaAtual = 1; // Volta para a primeira página
                carregarAlertas();
            }
        });
    });
}

// Função para configurar o formulário de novo alerta
function setupNovoAlertaForm() {
    const form = document.getElementById('formNovoAlerta');
    if (!form) return;
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Desabilitar botão de envio
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalBtnText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Salvando...';
        
        try {
            // Coletar dados do formulário
            const formData = {
                titulo: form.titulo.value.trim(),
                descricao: form.descricao.value.trim(),
                tipo_alerta: form.tipo_alerta.value, // Adiciona o tipo de alerta
                valor_referencia: form.valor_referencia.value.trim(),
                categoria: form.categoria.value.trim(),
                data_inicio: form.data_inicio.value,
                data_fim: form.data_fim.value,
                prioridade: form.prioridade.value,
                notificar_email: form.notificar_email.checked,
                notificar_app: form.notificar_app.checked,
                status: form.status.value
            };
            
            // Validar dados obrigatórios
            if (!formData.titulo) {
                throw new Error('O título é obrigatório');
            }
            
            if (!formData.valor_referencia) {
                throw new Error('O valor de referência é obrigatório');
            }
            
            // Validar valor numérico
            if (isNaN(parseFloat(formData.valor_referencia))) {
                throw new Error('O valor de referência deve ser um número');
            }
            
            // Validar datas
            if (formData.data_inicio && formData.data_fim && formData.data_inicio > formData.data_fim) {
                throw new Error('A data de início não pode ser posterior à data de término');
            }
            
            // Enviar dados para o servidor
            const url = '/alertas-manuais/novo';
            // Obter o token CSRF do formulário
            const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;
            
            const options = {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken || ''
                },
                credentials: 'same-origin',
                body: JSON.stringify(formData)
            };
            
            console.log('Enviando requisição para:', url);
            console.log('Opções:', options);
            
            const response = await fetch(url, options);
            
            // Verificar se a resposta é JSON
            const contentType = response.headers.get('content-type');
            let data;
            
            if (contentType && contentType.includes('application/json')) {
                data = await response.json();
            } else {
                // Se não for JSON, tentar obter o texto da resposta
                const text = await response.text();
                console.error('Resposta não é JSON:', text);
                throw new Error(`Resposta inesperada do servidor: ${text.substring(0, 200)}`);
            }
            
            if (!response.ok) {
                console.error('Erro na resposta:', data);
                throw new Error(data.mensagem || `Erro ao salvar o alerta: ${response.status} ${response.statusText}`);
            }
            
            // Mostrar mensagem de sucesso
            const toastSucesso = new bootstrap.Toast(document.getElementById('toastSucesso'));
            const toastMensagem = document.querySelector('#toastSucesso .toast-body span');
            toastMensagem.textContent = 'Alerta criado com sucesso!';
            toastSucesso.show();
            
            // Fechar o modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('modalNovoAlerta'));
            modal.hide();
            
            // Limpar o formulário e redefinir os campos de data
            form.reset();
            form.data_inicio.value = '';
            form.data_fim.value = '';
            
            // Recarregar a lista de alertas
            await carregarAlertas();
            
        } catch (erro) {
            console.error('Erro ao salvar alerta:', erro);
            
            // Mostrar mensagem de erro
            const toastErro = new bootstrap.Toast(document.getElementById('toastErro'));
            const toastMensagem = document.querySelector('#toastErro .toast-body span');
            toastMensagem.textContent = erro.message || 'Erro ao salvar o alerta';
            toastErro.show();
            
        } finally {
            // Reativar botão de envio
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnText;
        }
    });
}

// Função para configurar o botão de novo alerta
function setupNovoAlertaButton() {
    const novoAlertaBtn = document.getElementById('novoAlertaBtn');
    if (novoAlertaBtn) {
        novoAlertaBtn.addEventListener('click', function() {
            // Abre o modal de novo alerta
            const modal = new bootstrap.Modal(document.getElementById('modalNovoAlerta'));
            modal.show();
            
            // Foca no primeiro campo do formulário
            const tituloInput = document.getElementById('titulo');
            if (tituloInput) {
                setTimeout(() => {
                    tituloInput.focus();
                }, 500);
            }
        });
    } else {
        console.error('Botão de novo alerta não encontrado');
    }
}

// Função para configurar os eventos de edição e exclusão
document.addEventListener('click', function(event) {
    console.log('Clique detectado no documento');
    
    // Editar alerta
    if (event.target.closest('.btn-editar')) {
        console.log('Botão editar clicado');
        event.preventDefault();
        const btn = event.target.closest('.btn-editar');
        const alertaId = btn.getAttribute('data-id');
        console.log('Editar alerta ID:', alertaId);
        
        // Verificar se o modal existe
        const modalElement = document.getElementById('modalEditarAlerta');
        console.log('Elemento do modal:', modalElement);
        
        if (!modalElement) {
            console.error('Modal de edição não encontrado no DOM');
            return;
        }
        
        // Mostrar o modal de edição
        const modalEditar = new bootstrap.Modal(modalElement);
        console.log('Modal de edição inicializado:', modalEditar);
        
        // Carregar os dados do alerta
        carregarDadosAlerta(alertaId)
            .then(alerta => {
                // Preencher o formulário com os dados do alerta
                console.log('Dados do alerta carregados:', alerta);
                document.getElementById('editar-descricao').value = alerta.descricao || '';
                document.getElementById('editar-tipo').value = alerta.tipo_alerta || 'despesa'; // Define 'despesa' como padrão
                document.getElementById('editar-valor').value = alerta.valor_referencia || '';
                document.getElementById('editar-categoria').value = alerta.categoria || 'outros';
                document.getElementById('editar-data-inicio').value = alerta.data_inicio ? alerta.data_inicio.split('T')[0] : '';
                document.getElementById('editar-data-fim').value = alerta.data_fim ? alerta.data_fim.split('T')[0] : '';
                document.getElementById('editar-prioridade').value = alerta.prioridade || 'media';
                document.getElementById('editar-notificar-email').checked = Boolean(alerta.notificar_email);
                document.getElementById('editar-notificar-app').checked = Boolean(alerta.notificar_app);
                document.getElementById('editar-ativo').checked = Boolean(alerta.ativo);
                
                // Armazenar o ID do alerta no formulário
                document.getElementById('formEditarAlerta').setAttribute('data-id', alertaId);
                
                // Exibir o modal
                modalEditar.show();
            })
            .catch(erro => {
                console.error('Erro ao carregar alerta:', erro);
                mostrarMensagem('Erro ao carregar os dados do alerta. Tente novamente.', 'erro');
            });
    }
    
    // Excluir alerta
    if (event.target.closest('.btn-excluir')) {
        console.log('Botão excluir clicado');
        event.preventDefault();
        const btn = event.target.closest('.btn-excluir');
        const alertaId = btn.getAttribute('data-id');
        console.log('Tentando excluir alerta ID:', alertaId);
        
        console.log('Elementos do modal:', {
            modalExcluir: ELEMENTOS.modalExcluir,
            btnConfirmarExclusao: ELEMENTOS.btnConfirmarExclusao
        });
        
        if (ELEMENTOS.btnConfirmarExclusao) {
            console.log('Atualizando ID do alerta no botão de confirmação');
            // Atualiza o botão de confirmação com o ID do alerta
            ELEMENTOS.btnConfirmarExclusao.setAttribute('data-id', alertaId);
            
            // Abre o modal de confirmação
            if (ELEMENTOS.modalExcluir) {
                console.log('Abrindo modal de confirmação');
                ELEMENTOS.modalExcluir.show();
            } else {
                console.error('Modal de exclusão não inicializado');
            }
        } else {
            console.error('Botão de confirmação não encontrado');
        }
    }
});

// Função para carregar os dados de um alerta
async function carregarDadosAlerta(alertaId) {
    try {
        const response = await fetch(`/alertas-manuais/api/alertas/${alertaId}`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (!response.ok) {
            throw new Error(`Erro ao carregar alerta: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (!data.sucesso) {
            throw new Error(data.mensagem || 'Erro ao carregar alerta');
        }
        
        return data.alerta;
        
    } catch (erro) {
        console.error('Erro ao carregar alerta:', erro);
        throw erro;
    }
}

// Função para exibir mensagens para o usuário
function mostrarMensagem(mensagem, tipo = 'info') {
    console.log(`[${tipo.toUpperCase()}] ${mensagem}`);
    
    // Cria o elemento da mensagem se não existir
    let mensagemDiv = document.getElementById('mensagem-alerta');
    
    if (!mensagemDiv) {
        mensagemDiv = document.createElement('div');
        mensagemDiv.id = 'mensagem-alerta';
        mensagemDiv.style.position = 'fixed';
        mensagemDiv.style.top = '20px';
        mensagemDiv.style.right = '20px';
        mensagemDiv.style.zIndex = '9999';
        mensagemDiv.style.maxWidth = '350px';
        document.body.appendChild(mensagemDiv);
    }
    
    // Define as classes CSS com base no tipo de mensagem
    const classes = {
        'success': 'alert alert-success alert-dismissible fade show',
        'error': 'alert alert-danger alert-dismissible fade show',
        'info': 'alert alert-info alert-dismissible fade show',
        'warning': 'alert alert-warning alert-dismissible fade show'
    };
    
    // Cria o elemento da mensagem
    const alertDiv = document.createElement('div');
    alertDiv.className = classes[tipo] || classes['info'];
    alertDiv.role = 'alert';
    
    // Adiciona o conteúdo da mensagem
    alertDiv.innerHTML = `
        ${mensagem}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Fechar"></button>
    `;
    
    // Adiciona a mensagem ao container
    mensagemDiv.appendChild(alertDiv);
    
    // Remove a mensagem após 5 segundos
    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => {
            if (alertDiv.parentNode === mensagemDiv) {
                mensagemDiv.removeChild(alertDiv);
            }
        }, 300);
    }, 5000);
}

// Função para salvar as alterações de um alerta
async function salvarAlerta(alertaId, dados) {
    try {
        const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;
        
        const response = await fetch(`/alertas-manuais/api/alertas/${alertaId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken || ''
            },
            credentials: 'same-origin',
            body: JSON.stringify(dados)
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.mensagem || `Erro ${response.status}: ${response.statusText}`);
        }
        
        if (!data.sucesso) {
            throw new Error(data.mensagem || 'Erro ao salvar alerta');
        }
        
        return data;
        
    } catch (erro) {
        console.error('Erro ao salvar alerta:', erro);
        throw erro;
    }
}

// Configura o evento de submissão do formulário de edição
document.addEventListener('DOMContentLoaded', function() {
    const formEditar = document.getElementById('formEditarAlerta');
    
    if (!formEditar) {
        console.error('Formulário de edição não encontrado no DOM');
        return;
    }
    
    console.log('Formulário de edição encontrado, adicionando event listener...');
    
    formEditar.addEventListener('submit', async function(event) {
        console.log('Formulário de edição submetido');
        event.preventDefault();
        
        const form = event.target;
        const botaoSalvar = form.querySelector('button[type="submit"]');
        const textoOriginal = botaoSalvar.innerHTML;
        const alertaId = form.getAttribute('data-id');
        
        console.log('ID do alerta a ser editado:', alertaId);
        
        if (!alertaId) {
            console.error('ID do alerta não encontrado no formulário');
            mostrarMensagem('ID do alerta não encontrado', 'erro');
            return;
        }
    
        // Desabilitar o botão para evitar múltiplos cliques
        botaoSalvar.disabled = true;
        botaoSalvar.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Salvando...';
        
        try {
            // Coletar dados do formulário
            const dados = {
                descricao: form.querySelector('#editar-descricao').value.trim(),
                tipo_alerta: form.querySelector('#editar-tipo').value,
                valor_referencia: parseFloat(form.querySelector('#editar-valor').value) || 0,
                categoria: form.querySelector('#editar-categoria').value,
                data_inicio: form.querySelector('#editar-data-inicio').value || null,
                data_fim: form.querySelector('#editar-data-fim').value || null,
                prioridade: form.querySelector('#editar-prioridade').value,
                notificar_email: form.querySelector('#editar-notificar-email').checked,
                notificar_app: form.querySelector('#editar-notificar-app').checked,
                ativo: form.querySelector('#editar-ativo').checked
            };
            
            console.log('Dados do formulário:', dados);
            
            // Validar dados obrigatórios
            if (!dados.descricao) {
                throw new Error('A descrição é obrigatória');
            }
            
            // Enviar dados para o servidor
            console.log('Enviando dados para o servidor...');
            const resultado = await salvarAlerta(alertaId, dados);
            console.log('Resposta do servidor:', resultado);
            
            // Mostrar mensagem de sucesso
            mostrarMensagem('Alerta atualizado com sucesso!', 'sucesso');
            
            // Fechar o modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('modalEditarAlerta'));
            if (modal) {
                modal.hide();
            } else {
                console.error('Não foi possível obter a instância do modal');
                // Tenta fechar o modal de outra forma
                const modalElement = document.getElementById('modalEditarAlerta');
                const bsModal = new bootstrap.Modal(modalElement);
                bsModal.hide();
            }
            
            // Recarregar a lista de alertas
            console.log('Recarregando lista de alertas...');
            await carregarAlertas();
            
        } catch (erro) {
            console.error('Erro ao salvar alerta:', erro);
            mostrarMensagem(erro.message || 'Erro ao salvar alerta. Tente novamente.', 'erro');
        } finally {
            // Restaurar o botão
            botaoSalvar.disabled = false;
            botaoSalvar.innerHTML = textoOriginal;
        }
    });
});

// Configura o evento de confirmação de exclusão
document.addEventListener('DOMContentLoaded', function() {
    console.log('Configurando evento de clique no botão de confirmação de exclusão...');
    
    const btnConfirmar = document.getElementById('confirmar-exclusao');
    
    if (!btnConfirmar) {
        console.error('ERRO: Botão de confirmação não encontrado no DOM');
        return;
    }
    
    console.log('Botão de confirmação encontrado:', btnConfirmar);
    
    // Adiciona um event listener direto ao botão
    btnConfirmar.addEventListener('click', async function() {
        console.log('Botão de confirmação clicado!');
        
        const alertaId = this.getAttribute('data-id');
        console.log('ID do alerta a ser excluído:', alertaId);
        
        if (!alertaId) {
            console.error('Nenhum ID de alerta encontrado no botão de confirmação');
            alert('Erro: ID do alerta não encontrado');
            return;
        }
        
        const botao = this;
        const textoOriginal = botao.innerHTML;
        
        // Desabilita o botão para evitar múltiplos cliques
        botao.disabled = true;
        botao.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Excluindo...';
        
        try {
            console.log('Enviando requisição DELETE para /alertas-manuais/api/alertas/' + alertaId);
            const inicioRequisicao = Date.now();
            
            const response = await fetch(`/alertas-manuais/api/alertas/${alertaId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });
            
            const tempoResposta = Date.now() - inicioRequisicao;
            console.log(`Resposta recebida em ${tempoResposta}ms:`, response.status, response.statusText);
            
            if (!response.ok) {
                console.error('Erro na resposta da API:', response.status, response.statusText);
                let errorMessage = 'Erro ao excluir o alerta';
                
                try {
                    const errorData = await response.json();
                    console.error('Detalhes do erro:', errorData);
                    errorMessage = errorData.message || errorMessage;
                } catch (e) {
                    console.error('Não foi possível analisar a resposta de erro:', e);
                }
                
                throw new Error(errorMessage);
            }
            
            const resultado = await response.json().catch(e => {
                console.error('Erro ao analisar a resposta JSON:', e);
                return { success: false, message: 'Resposta inválida do servidor' };
            });
            
            console.log('Resultado da exclusão:', resultado);
            
            if (resultado && resultado.success) {
                console.log('Exclusão bem-sucedida, fechando o modal');
                
                // Fecha o modal
                if (ELEMENTOS.modalExcluir) {
                    ELEMENTOS.modalExcluir.hide();
                    console.log('Modal fechado com sucesso');
                } else {
                    console.warn('ELEMENTOS.modalExcluir não está disponível, tentando fallback');
                    // Fallback caso não consiga obter a instância do modal
                    const modalElement = document.getElementById('modalExcluirAlerta');
                    if (modalElement) {
                        try {
                            const bsModal = bootstrap.Modal.getInstance(modalElement) || new bootstrap.Modal(modalElement);
                            bsModal.hide();
                            console.log('Modal fechado usando fallback');
                        } catch (e) {
                            console.error('Erro ao fechar o modal com fallback:', e);
                        }
                    } else {
                        console.error('Elemento do modal não encontrado');
                    }
                }
                
                // Recarrega a página para garantir que tudo esteja atualizado
                window.location.reload();
                
                // Mostra mensagem de sucesso
                const toastEl = document.getElementById('toastSucesso');
                if (toastEl) {
                    const toast = new bootstrap.Toast(toastEl);
                    toast.show();
                }
            } else {
                throw new Error(resultado?.message || 'Erro ao excluir o alerta');
            }
        } catch (erro) {
            console.error('Erro ao excluir alerta:', erro);
            
            // Mostra mensagem de erro
            const toastErroEl = document.getElementById('toastErro');
            if (toastErroEl) {
                const toastBody = toastErroEl.querySelector('.toast-body');
                if (toastBody) {
                    toastBody.textContent = `Erro: ${erro.message || 'Não foi possível excluir o alerta'}`;
                }
                const toast = new bootstrap.Toast(toastErroEl);
                toast.show();
            } else {
                alert(`Erro: ${erro.message || 'Não foi possível excluir o alerta'}`);
            }
            
            // Reabilita o botão em caso de erro
            botao.disabled = false;
            botao.innerHTML = textoOriginal;
        }
    });
});

// Captura de erros globais não tratados
window.addEventListener('error', function(event) {
    console.error('Erro não tratado:', event.error || event.message, 'em', event.filename, 'linha', event.lineno);
    return false;
});

// Inicialização quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    try {
        console.log('DOM totalmente carregado, inicializando...');
        
        // Inicializa os elementos da interface
        console.log('Inicializando elementos da interface...');
        inicializarElementos();
        
        // Inicializa o modal de exclusão se o elemento existir
        console.log('Verificando elemento do modal de exclusão...');
        console.log('ELEMENTOS.modalExcluirElement:', ELEMENTOS.modalExcluirElement);
        
        if (ELEMENTOS.modalExcluirElement) {
            console.log('Inicializando modal de exclusão...');
            try {
                ELEMENTOS.modalExcluir = new bootstrap.Modal(ELEMENTOS.modalExcluirElement);
                console.log('Modal de exclusão inicializado com sucesso:', ELEMENTOS.modalExcluir);
                
                // Adiciona um listener para o evento 'shown.bs.modal'
                ELEMENTOS.modalExcluirElement.addEventListener('shown.bs.modal', function () {
                    console.log('Modal de exclusão foi aberto');
                });
                
                // Adiciona um listener para o evento 'hidden.bs.modal'
                ELEMENTOS.modalExcluirElement.addEventListener('hidden.bs.modal', function () {
                    console.log('Modal de exclusão foi fechado');
                });
                
            } catch (e) {
                console.error('Erro ao inicializar o modal de exclusão:', e);
            }
        } else {
            console.error('Elemento do modal de exclusão não encontrado no DOM');
        }
        
        // Configura os filtros
        configurarFiltros();
        
        // Configura a ordenação
        configurarOrdenacao();
        
        // Configura o botão de novo alerta
        setupNovoAlertaButton();
        
        // Configura o formulário de novo alerta
        setupNovoAlertaForm();
        
        // Carrega os alertas iniciais
        carregarAlertas();
        
        // Inicializa tooltips do Bootstrap
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            try {
                const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
                tooltipTriggerList.map(function (tooltipTriggerEl) {
                    try {
                        return new bootstrap.Tooltip(tooltipTriggerEl);
                    } catch (e) {
                        console.error('Erro ao inicializar tooltip:', e);
                        return null;
                    }
                });
            } catch (e) {
                console.error('Erro ao inicializar tooltips:', e);
            }
        } else {
            console.warn('Bootstrap não está disponível para inicialização de tooltips');
        }
    } catch (e) {
        console.error('Erro durante a inicialização do DOM:', e);
    }
});
