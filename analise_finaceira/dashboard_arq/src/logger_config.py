from pathlib import Path
import sys

# Adiciona o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger, RequestContext, log_function

# Configura o logger para o dashboard
dashboard_logger = get_logger("dashboard")

# Configura o contexto da aplicação
RequestContext.set_request_context(
    user_id="sistema",
    module="dashboard"
)
