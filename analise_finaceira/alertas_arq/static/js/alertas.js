// alertas.js - Gerenciamento de Alertas

document.addEventListener('DOMContentLoaded', function() {
    // Elementos do DOM
    const formAlerta = document.getElementById('formAlerta');
    const btnCancelar = document.querySelector('.btn-secondary');
    const alertasContainer = document.querySelector('.card:last-child .card-body');
    
    // Inicialização
    carregarAlertas();
    
    // Event Listeners
    if (formAlerta) {
        formAlerta.addEventListener('submit', salvarAlerta);
    }
    
    if (btnCancelar) {
        btnCancelar.addEventListener('click', limparFormulario);
    }
});

// Função para carregar a lista de alertas
function carregarAlertas() {
    const alertasContainer = document.querySelector('.card:last-child .card-body');
    
    fetch('/alertas/api/alertas')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                atualizarListaAlertas(data.data);
            } else {
                mostrarMensagem('Erro ao carregar alertas', 'danger');
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            mostrarMensagem('Erro ao carregar alertas', 'danger');
        });
}

// Função para atualizar a lista de alertas na interface
function atualizarListaAlertas(alertas) {
    const alertasContainer = document.querySelector('.card:last-child .card-body');
    
    if (!alertas || alertas.length === 0) {
        alertasContainer.innerHTML = '<p class="text-muted">Nenhum alerta encontrado.</p>';
        return;
    }
    
    const table = document.createElement('table');
    table.className = 'table table-striped table-hover';
    
    // Cabeçalho da tabela
    const thead = document.createElement('thead');
    thead.className = 'table-light';
    thead.innerHTML = `
        <tr>
            <th>Tipo</th>
            <th>Descrição</th>
            <th>Valor Referência</th>
            <th>Prioridade</th>
            <th>Status</th>
            <th>Ações</th>
        </tr>
    `;
    
    // Corpo da tabela
    const tbody = document.createElement('tbody');
    alertas.forEach(alerta => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${formatarTipoAlerta(alerta.tipo)}</td>
            <td>${alerta.descricao}</td>
            <td>${alerta.valor_referencia ? formatarMoeda(alerta.valor_referencia) : '-'}</td>
            <td><span class="badge bg-${getBadgeClass(alerta.prioridade)}">${formatarPrioridade(alerta.prioridade)}</span></td>
            <td>
                <div class="form-check form-switch">
                    <input class="form-check-input toggle-alerta" type="checkbox" 
                           data-id="${alerta.id}" ${alerta.ativo ? 'checked' : ''}>
                </div>
            </td>
            <td>
                <button class="btn btn-sm btn-outline-primary me-1 editar-alerta" data-id="${alerta.id}">
                    <i class="bi bi-pencil"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger excluir-alerta" data-id="${alerta.id}">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
    
    // Limpa o container e adiciona a tabela
    alertasContainer.innerHTML = '';
    table.appendChild(thead);
    table.appendChild(tbody);
    alertasContainer.appendChild(table);
    
    // Adiciona eventos aos botões
    adicionarEventosBotoes();
}

// Função para adicionar eventos aos botões da lista
function adicionarEventosBotoes() {
    // Toggle status do alerta
    document.querySelectorAll('.toggle-alerta').forEach(toggle => {
        toggle.addEventListener('change', function() {
            const alertaId = this.dataset.id;
            const ativo = this.checked;
            
            fetch(`/alertas/api/alertas/${alertaId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ ativo })
            })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    this.checked = !ativo; // Reverte a mudança em caso de erro
                    mostrarMensagem(data.message || 'Erro ao atualizar status do alerta', 'danger');
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                this.checked = !ativo; // Reverte a mudança em caso de erro
                mostrarMensagem('Erro ao atualizar status do alerta', 'danger');
            });
        });
    });
    
    // Botão editar
    document.querySelectorAll('.editar-alerta').forEach(btn => {
        btn.addEventListener('click', function() {
            const alertaId = this.dataset.id;
            editarAlerta(alertaId);
        });
    });
    
    // Botão excluir
    document.querySelectorAll('.excluir-alerta').forEach(btn => {
        btn.addEventListener('click', function() {
            if (confirm('Tem certeza que deseja excluir este alerta?')) {
                const alertaId = this.dataset.id;
                excluirAlerta(alertaId);
            }
        });
    });
}

// Função para salvar um novo alerta ou atualizar existente
function salvarAlerta(event) {
    event.preventDefault();
    
    const formAlerta = document.getElementById('formAlerta');
    const formData = new FormData(formAlerta);
    const submitBtn = formAlerta.querySelector('button[type="submit"]');
    const alertaId = submitBtn.dataset.id;
    
    const alertaData = {
        tipo: formData.get('tipoAlerta'),
        descricao: formData.get('descricao'),
        valor_referencia: formData.get('valorReferencia') || null,
        categoria: formData.get('categoria') || null,
        data_inicio: formData.get('dataInicio'),
        frequencia: formData.get('frequencia'),
        notificacao_sistema: document.getElementById('notificacao').checked,
        notificacao_email: document.getElementById('email').checked,
        prioridade: formData.get('prioridade'),
        ativo: document.getElementById('ativo').checked
    };
    
    const method = alertaId ? 'PUT' : 'POST';
    const url = alertaId ? `/alertas/api/alertas/${alertaId}` : '/alertas/api/alertas';
    
    // Obtém o token CSRF do cookie
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }
    
    const csrfToken = getCookie('csrf_token');
    
    // Configura os headers da requisição
    const headers = {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': csrfToken || ''
    };
    
    // Adiciona o token CSRF aos dados da requisição
    const dataToSend = {
        ...alertaData,
        csrf_token: csrfToken
    };
    
    // Log dos dados que serão enviados
    console.log('Dados a serem enviados:', dataToSend);
    console.log('Headers da requisição:', headers);
    
    fetch(url, {
        method: method,
        headers: headers,
        body: JSON.stringify(dataToSend),
        credentials: 'include'  // Importante para enviar cookies
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            mostrarMensagem(
                alertaId ? 'Alerta atualizado com sucesso!' : 'Alerta criado com sucesso!', 
                'success'
            );
            limparFormulario();
            carregarAlertas();
        } else {
            mostrarMensagem(data.message || 'Erro ao salvar alerta', 'danger');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        mostrarMensagem('Erro ao salvar alerta', 'danger');
    });
}

// Função para carregar um alerta no formulário para edição
function editarAlerta(alertaId) {
    fetch(`/alertas/api/alertas/${alertaId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const alerta = data.data;
                const formAlerta = document.getElementById('formAlerta');
                
                // Preenche o formulário
                document.getElementById('tipoAlerta').value = alerta.tipo;
                document.getElementById('descricao').value = alerta.descricao;
                document.getElementById('valorReferencia').value = alerta.valor_referencia || '';
                document.getElementById('categoria').value = alerta.categoria || '';
                document.getElementById('dataInicio').value = alerta.data_inicio;
                document.getElementById('frequencia').value = alerta.frequencia;
                document.getElementById('notificacao').checked = alerta.notificacao_sistema;
                document.getElementById('email').checked = alerta.notificacao_email;
                document.getElementById('prioridade').value = alerta.prioridade;
                document.getElementById('ativo').checked = alerta.ativo;
                
                // Atualiza o botão de submit
                const submitBtn = formAlerta.querySelector('button[type="submit"]');
                submitBtn.innerHTML = '<i class="bi bi-save me-1"></i> Atualizar Alerta';
                submitBtn.dataset.id = alerta.id;
                
                // Rola até o formulário
                formAlerta.scrollIntoView({ behavior: 'smooth' });
            } else {
                mostrarMensagem('Erro ao carregar alerta para edição', 'danger');
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            mostrarMensagem('Erro ao carregar alerta para edição', 'danger');
        });
}

// Função para excluir um alerta
function excluirAlerta(alertaId) {
    fetch(`/alertas/api/alertas/${alertaId}`, {
        method: 'DELETE',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            mostrarMensagem('Alerta excluído com sucesso', 'success');
            carregarAlertas();
        } else {
            mostrarMensagem(data.message || 'Erro ao excluir alerta', 'danger');
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        mostrarMensagem('Erro ao excluir alerta', 'danger');
    });
}

// Função para limpar o formulário
function limparFormulario() {
    const formAlerta = document.getElementById('formAlerta');
    formAlerta.reset();
    document.getElementById('dataInicio').value = new Date().toISOString().split('T')[0];
    
    // Reseta o botão de submit
    const submitBtn = formAlerta.querySelector('button[type="submit"]');
    submitBtn.innerHTML = '<i class="bi bi-bell-fill me-1"></i> Criar Alerta';
    delete submitBtn.dataset.id;
}

// Função para exibir mensagens para o usuário
function mostrarMensagem(mensagem, tipo) {
    // Remove mensagens anteriores
    const mensagensAntigas = document.querySelectorAll('.alert-flash');
    mensagensAntigas.forEach(msg => msg.remove());
    
    // Cria a nova mensagem
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${tipo} alert-dismissible fade show alert-flash`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${mensagem}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Insere a mensagem após o título da página
    const titulo = document.querySelector('h1');
    titulo.parentNode.insertBefore(alertDiv, titulo.nextSibling);
}

// Funções auxiliares de formatação
function formatarTipoAlerta(tipo) {
    const tipos = {
        'valor_excedido': 'Valor Excedido',
        'valor_abaixo': 'Valor Abaixo',
        'transacao_suspeita': 'Transação Suspeita',
        'categoria_especifica': 'Categoria Específica'
    };
    return tipos[tipo] || tipo;
}

function formatarPrioridade(prioridade) {
    const prioridades = {
        'baixa': 'Baixa',
        'media': 'Média',
        'alta': 'Alta'
    };
    return prioridades[prioridade] || prioridade;
}

function formatarMoeda(valor) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(valor);
}

function getBadgeClass(prioridade) {
    const classes = {
        'baixa': 'info',
        'media': 'warning',
        'alta': 'danger'
    };
    return classes[prioridade] || 'secondary';
}
