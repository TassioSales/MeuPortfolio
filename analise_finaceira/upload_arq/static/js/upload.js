document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const fileLabel = document.querySelector('label[for="fileInput"]');
    const fileFeedback = document.createElement('div');
    fileFeedback.className = 'form-text';
    fileInput.parentNode.insertBefore(fileFeedback, fileInput.nextSibling);

    // Atualiza o feedback quando um arquivo é selecionado
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            const file = this.files[0];
            const fileSize = formatFileSize(file.size);
            fileFeedback.textContent = `Arquivo selecionado: ${file.name} (${fileSize})`;
            
            // Verifica o tamanho máximo do arquivo (10MB)
            const maxSize = 10 * 1024 * 1024; // 10MB em bytes
            if (file.size > maxSize) {
                fileFeedback.textContent += ' - Arquivo muito grande (máx. 10MB)';
                fileFeedback.className = 'form-text text-danger';
                uploadForm.querySelector('button[type="submit"]').disabled = true;
            } else {
                fileFeedback.className = 'form-text text-success';
                uploadForm.querySelector('button[type="submit"]').disabled = false;
            }
        } else {
            fileFeedback.textContent = 'Nenhum arquivo selecionado';
            fileFeedback.className = 'form-text';
        }
    });

    // Mostra feedback durante o envio do formulário
    uploadForm.addEventListener('submit', function(e) {
        const submitButton = this.querySelector('button[type="submit"]');
        const originalButtonText = submitButton.innerHTML;
        
        // Desabilita o botão e mostra um spinner
        submitButton.disabled = true;
        submitButton.innerHTML = `
            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            Processando...
        `;
        
        // Mostra mensagem de processamento
        const processingAlert = document.createElement('div');
        processingAlert.className = 'alert alert-info mt-3';
        processingAlert.innerHTML = `
            <i class="bi bi-hourglass-split me-2"></i>
            Processando o arquivo, por favor aguarde...
        `;
        this.parentNode.insertBefore(processingAlert, this.nextSibling);
        
        // Rolar para a mensagem
        processingAlert.scrollIntoView({ behavior: 'smooth' });
        
        // Atualiza a página após 5 segundos (para ver o resultado)
        setTimeout(() => {
            window.location.reload();
        }, 5000);
    });

    // Função para formatar o tamanho do arquivo
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Atualiza a tabela de histórico a cada 30 segundos
    setInterval(updateUploadHistory, 30000);
});

// Função para atualizar a tabela de histórico via AJAX
function updateUploadHistory() {
    fetch('/upload/history')
        .then(response => response.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newTable = doc.querySelector('#uploadHistoryTable');
            if (newTable) {
                const currentTable = document.querySelector('#uploadHistoryTable');
                if (currentTable) {
                    currentTable.innerHTML = newTable.innerHTML;
                }
            }
        })
        .catch(error => console.error('Erro ao atualizar histórico:', error));
}
