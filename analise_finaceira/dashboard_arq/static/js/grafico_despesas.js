document.addEventListener('DOMContentLoaded', function() {
    const graficoImg = document.getElementById('grafico-despesas-img');
    const loadingDiv = document.getElementById('loading-grafico');
    const btnAtualizar = document.getElementById('atualizar-grafico');

    // Função para mostrar/ocultar o loading
    function toggleLoading(show) {
        if (show) {
            loadingDiv.style.display = 'block';
            graficoImg.style.display = 'none';
        } else {
            loadingDiv.style.display = 'none';
            graficoImg.style.display = 'block';
        }
    }

    // Função para atualizar o gráfico
    function atualizarGrafico() {
        toggleLoading(true);
        
        // Adiciona um timestamp para evitar cache
        const timestamp = new Date().getTime();
        graficoImg.src = `/dashboard/grafico-despesas?t=${timestamp}`;
    }

    // Evento quando a imagem terminar de carregar
    graficoImg.onload = function() {
        toggleLoading(false);
    };

    // Evento de erro ao carregar a imagem
    graficoImg.onerror = function() {
        toggleLoading(false);
        graficoImg.src = '/static/img/erro.png';
    };

    // Evento do botão de atualizar
    if (btnAtualizar) {
        btnAtualizar.addEventListener('click', function(e) {
            e.preventDefault();
            atualizarGrafico();
        });
    }

    // Esconder o loading inicialmente (será mostrado pelo evento onload)
    toggleLoading(false);
});
