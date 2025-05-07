# Este arquivo torna o diretório um pacote Python
# Permite que os módulos sejam importados corretamente

# Importações dos blueprints
from upload_arq.src import upload_bp
from dashboard_arq.src import dashboard_bp

# Exporta os blueprints para uso no main.py
__all__ = ['upload_bp', 'dashboard_bp']
