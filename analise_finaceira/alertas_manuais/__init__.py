from flask import Blueprint
from . import filters  # Importa os filtros personalizados

# Criar o blueprint
bp = Blueprint(
    'alertas_manuais',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/alertas_manuais/static'
)

# Alias para compatibilidade com código existente
alertas_manuais_bp = bp
blueprint = bp

def init_app(app):
    """Inicializa a aplicação com o blueprint."""
    # Registrar o blueprint com o prefixo
    app.register_blueprint(bp, url_prefix='/alertas-manuais')
    
    # Registrar os filtros personalizados
    app.jinja_env.filters['format_datetime'] = filters.format_datetime
    app.jinja_env.filters['format_currency'] = filters.format_currency
    
    print(f"Blueprint 'alertas_manuais' registrado com sucesso! Prefixo: /alertas-manuais")
    return bp

# Importar as rotas após a criação do blueprint para evitar importação circular
from . import routes  # noqa

print(f"Módulo alertas_manuais inicializado. Nome do blueprint: {bp.name}")

__all__ = ['bp', 'alertas_manuais_bp', 'blueprint', 'init_app']
