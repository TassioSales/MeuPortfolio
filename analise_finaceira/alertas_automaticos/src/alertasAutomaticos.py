"""
Módulo principal para execução de alertas automáticos.
"""
import os
import sys
from datetime import datetime

# Adiciona o diretório raiz ao path para importar o logger
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger, LogLevel
from .analyse import AnalisadorFinanceiro
from .alert_service import alert_service

# Configura o logger
logger = get_logger('alertas_automaticos')
logger.level(LogLevel.DEBUG)
logger.info("Nível de log configurado para DEBUG")

class GerenciadorAlertas:
    """
    Classe responsável por gerenciar a execução das análises e o salvamento dos alertas.
    """
    
    def __init__(self, db_path=None):
        """
        Inicializa o gerenciador de alertas.
        
        Args:
            db_path: Caminho para o banco de dados SQLite
        """
        self.analisador = AnalisadorFinanceiro(db_path)
        self.alert_service = alert_service
        logger.info("Gerenciador de alertas inicializado.")
    
    def executar_analise(self):
        """
        Executa as análises e salva os alertas no banco de dados.
        """
        try:
            logger.info("Iniciando execução das análises de alertas automáticos.")
            
            # Executa as análises
            alertas = self.analisador.executar_analises()
            
            # Salva os alertas no banco de dados
            alertas_salvos = 0
            for alerta in alertas:
                try:
                    alerta_id = self.alert_service.criar_alerta(alerta)
                    if alerta_id:
                        alertas_salvos += 1
                except Exception as e:
                    logger.error(f"Erro ao salvar alerta: {e}", exc_info=True)
            
            logger.info(f"Processo concluído. {alertas_salvos} alertas foram salvos no banco de dados.")
            return alertas_salvos
            
        except Exception as e:
            logger.error(f"Erro inesperado na execução das análises: {e}", exc_info=True)
            return 0

def main():
    """
    Função principal para execução do script.
    """
    try:
        logger.info("=== INÍCIO DO PROCESSAMENTO DE ALERTAS AUTOMÁTICOS ===")
        
        # Inicializa o gerenciador de alertas
        gerenciador = GerenciadorAlertas()
        
        # Executa as análises
        total_alertas = gerenciador.executar_analise()
        
        logger.info(f"=== PROCESSAMENTO CONCLUÍDO. {total_alertas} ALERTAS GERADOS ===")
        return 0
        
    except Exception as e:
        logger.error(f"Erro fatal durante o processamento: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
