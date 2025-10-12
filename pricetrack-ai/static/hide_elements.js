// Função para remover elementos do Streamlit
function removeStreamlitElements() {
    // Remove o menu de três pontos e outros elementos
    const elementsToRemove = [
        // Menu principal
        'div[data-testid="stToolbar"]',
        // Rodapé
        'footer[data-testid="stFooter"]',
        // Botão de deploy
        'div[data-testid="stDeployButton"]',
        // Botão de menu móvel
        'div[data-testid="stToolbar"]',
        // Botão de fechar sidebar
        'div[data-testid="stSidebarCollapseButton"]',
        // Outros elementos que podem aparecer
        'div[data-testid="stDecoration"]',
        'div[data-testid="stStatusWidget"]',
        // Elementos do menu
        '.stApp [data-testid="stToolbar"]',
        '[data-testid="stToolbar"]',
        '[data-testid="stToolbarActions"]',
        '[data-testid="stStatusWidget"]',
        '[data-testid="stDecoration"]',
        '[data-testid="baseButton-header"]',
        '[data-testid="stSidebarNav"]',
        '[data-testid="stSidebarUserContent"]',
        '[data-testid="stSidebarUserContent"] > div:first-child',
        '[data-testid="stSidebarNavItems"]',
        '[data-testid="stSidebarCollapseButton"]'
    ];

    // Remove os elementos
    elementsToRemove.forEach(selector => {
        document.querySelectorAll(selector).forEach(el => {
            if (el) el.remove();
        });
    });

    // Adiciona estilos para garantir que os elementos não sejam exibidos
    const style = document.createElement('style');
    style.innerHTML = `
        .stApp [data-testid="stToolbar"],
        [data-testid="stToolbar"],
        [data-testid="stToolbarActions"],
        [data-testid="stStatusWidget"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        [data-testid="baseButton-header"],
        [data-testid="stSidebarNav"],
        [data-testid="stSidebarUserContent"],
        [data-testid="stSidebarUserContent"] > div:first-child,
        [data-testid="stSidebarNavItems"],
        [data-testid="stSidebarCollapseButton"],
        #MainMenu,
        header,
        footer,
        .stDeployButton,
        #stDecoration {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            width: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            border: none !important;
            position: absolute !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }
    `;
    document.head.appendChild(style);
}

// Executa quando a página carrega
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', removeStreamlitElements);
} else {
    removeStreamlitElements();
}

// Executa novamente após um pequeno atraso para pegar elementos carregados dinamicamente
setTimeout(removeStreamlitElements, 100);
setTimeout(removeStreamlitElements, 500);
setTimeout(removeStreamlitElements, 1000);
setTimeout(removeStreamlitElements, 2000);

// Observa mudanças no DOM para remover elementos que possam aparecer depois
const observer = new MutationObserver(removeStreamlitElements);
observer.observe(document.body, { 
    childList: true, 
    subtree: true,
    attributes: true,
    characterData: true
});
