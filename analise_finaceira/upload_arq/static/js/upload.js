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
            const allowedExtensions = ['csv', 'pdf'];
            const fileExt = file.name.split('.').pop().toLowerCase();

            fileFeedback.textContent = `Arquivo selecionado: ${file.name} (${fileSize})`;

            // Verifica a extensão do arquivo
            if (!allowedExtensions.includes(fileExt)) {
                fileFeedback.textContent += ` - Extensão inválida. Use apenas .csv ou .pdf`;
                fileFeedback.className = 'form-text text-danger';
                uploadForm.querySelector('button[type="submit"]').disabled = true;
                return;
            }

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
            uploadForm.querySelector('button[type="submit"]').disabled = true;
        }
    });

    // Mostra feedback durante o envio do formulário
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault(); // Impede o envio padrão do formulário
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

        // Envia o formulário via AJAX
        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('file', file);

        fetch('/upload/upload', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value,
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.message || 'Erro desconhecido'); });
            }
            return response.json();
        })
        .then(data => {
            processingAlert.className = 'alert alert-success mt-3';
            processingAlert.innerHTML = `<i class="bi bi-check-circle me-2"></i> ${data.message || 'Arquivo processado com sucesso!'}`;
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        })
        .catch(error => {
            processingAlert.className = 'alert alert-danger mt-3';
            processingAlert.innerHTML = `<i class="bi bi-exclamation-triangle me-2"></i> ${error.message || 'Erro ao processar o arquivo'}`;
            submitButton.disabled = false;
            submitButton.innerHTML = originalButtonText;
            console.error('Erro:', error);
        });
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
    fetch('/upload/upload_history', {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        const tableBody = document.querySelector('#uploadHistoryTable tbody');
        if (tableBody) {
            tableBody.innerHTML = '';
            if (data.data && data.data.length > 0) {
                data.data.forEach(upload => {
                    const row = document.createElement('tr');
                    row.className = 'align-middle';
                    row.innerHTML = `
                        <td class="text-nowrap">${upload.data_upload}</td>
                        <td class="text-nowrap">${upload.nome_arquivo || ''}</td>
                        <td class="text-center">
                            ${upload.status === 'concluido' ? 
                                `${upload.registros_inseridos || 0}/${upload.total_registros || 0}` : 
                                '-'}
                        </td>
                        <td>
                            ${upload.status === 'concluido' ? 
                                '<span class="badge bg-success">Concluído</span>' : 
                                (upload.status === 'erro' ? 
                                    '<span class="badge bg-danger">Erro</span>' : 
                                    '<span class="badge bg-warning">Processando</span>')}
                        </td>
                        <td class="small">${upload.mensagem || ''}</td>
                    `;
                    tableBody.appendChild(row);
                });
            } else {
                tableBody.innerHTML = '<tr><td colspan="5" class="text-center">Nenhum histórico de upload encontrado.</td></tr>';
            }
        }
    })
    .catch(error => console.error('Erro ao atualizar histórico:', error));
}