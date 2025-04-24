document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('analyzeForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            const textInput = document.getElementById('textInput').value;
            const fileInput = document.getElementById('fileInput').files.length;
            if (!textInput && !fileInput) {
                e.preventDefault();
                alert('Por favor, insira um texto ou selecione um arquivo.');
            }
        });
    }
});