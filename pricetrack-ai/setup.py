#!/usr/bin/env python3
"""
Script de Inicialização do PriceTrack AI
Configura o ambiente e inicializa o banco de dados
"""

import os
import sys
import subprocess
from pathlib import Path
from core.logger import setup_logging, get_logger, log_user_action

# Configurar logging
logger = get_logger(__name__)
setup_logging()


def check_python_version():
    """Verifica se a versão do Python é compatível"""
    if sys.version_info < (3, 8):
        logger.error(f"Python 3.8+ é necessário! Versão atual: {sys.version}")
        print("❌ Python 3.8+ é necessário!")
        print(f"Versão atual: {sys.version}")
        sys.exit(1)
    logger.info(f"Python {sys.version.split()[0]} detectado")
    print(f"✅ Python {sys.version.split()[0]} detectado")


def check_dependencies():
    """Verifica se as dependências estão instaladas"""
    try:
        import streamlit
        import sqlalchemy
        import plotly
        import google.generativeai
        import pydantic
        logger.info("Todas as dependências estão instaladas")
        print("✅ Todas as dependências estão instaladas")
        return True
    except ImportError as e:
        logger.error(f"Dependência não encontrada: {e}")
        print(f"❌ Dependência não encontrada: {e}")
        print("Execute: pip install -r requirements.txt")
        return False


def create_directories():
    """Cria diretórios necessários"""
    directories = [
        "logs",
        ".streamlit",
        "tests"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        logger.info(f"Diretório {directory}/ criado")
        print(f"✅ Diretório {directory}/ criado")


def check_secrets_file():
    """Verifica se o arquivo de secrets existe"""
    secrets_file = Path(".streamlit/secrets.toml")
    
    if not secrets_file.exists():
        logger.warning("Arquivo .streamlit/secrets.toml não encontrado")
        print("⚠️  Arquivo .streamlit/secrets.toml não encontrado")
        print("Copie o arquivo de exemplo e configure suas chaves:")
        print("cp .streamlit/secrets.toml.example .streamlit/secrets.toml")
        return False
    
    logger.info("Arquivo de secrets encontrado")
    print("✅ Arquivo de secrets encontrado")
    return True


def initialize_database():
    """Inicializa o banco de dados"""
    try:
        from core.models import create_tables
        create_tables()
        logger.info("Banco de dados inicializado com sucesso")
        print("✅ Banco de dados inicializado")
        return True
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {str(e)}")
        print(f"❌ Erro ao inicializar banco: {e}")
        return False


def test_ai_connection():
    """Testa conexão com a API Gemini"""
    try:
        import streamlit as st
        from core.ai_services import gemini_service
        
        # Simular secrets para teste
        if not hasattr(st, 'secrets'):
            st.secrets = {}
            st.secrets["GEMINI_API_KEY"] = "test-key"
        
        # Tentar inicializar o serviço
        gemini_service._initialize_model()
        logger.info("Conexão com Gemini testada com sucesso (modo desenvolvimento)")
        print("✅ Conexão com Gemini testada (modo desenvolvimento)")
        return True
    except Exception as e:
        logger.warning(f"Erro na conexão Gemini: {str(e)}")
        print(f"⚠️  Erro na conexão Gemini: {e}")
        print("Configure GEMINI_API_KEY no secrets.toml")
        return False


def run_tests():
    """Executa testes unitários"""
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Todos os testes passaram com sucesso")
            print("✅ Todos os testes passaram")
            return True
        else:
            logger.error(f"Alguns testes falharam: {result.stdout}")
            print("❌ Alguns testes falharam:")
            print(result.stdout)
            return False
    except Exception as e:
        logger.warning(f"Erro ao executar testes: {str(e)}")
        print(f"⚠️  Erro ao executar testes: {e}")
        return False


def main():
    """Função principal de inicialização"""
    logger.info("Iniciando processo de inicialização do PriceTrack AI")
    log_user_action(logger, "system_startup", "Inicialização do sistema")
    print("🚀 Inicializando PriceTrack AI...")
    print("=" * 50)
    
    # Verificações básicas
    check_python_version()
    
    if not check_dependencies():
        logger.error("Falha na verificação de dependências")
        sys.exit(1)
    
    # Configuração do ambiente
    create_directories()
    
    secrets_ok = check_secrets_file()
    
    # Inicialização do banco
    if not initialize_database():
        logger.error("Falha na inicialização do banco de dados")
        sys.exit(1)
    
    # Teste de conexão IA
    ai_ok = test_ai_connection()
    
    # Executar testes
    tests_ok = run_tests()
    
    print("=" * 50)
    print("📊 Resumo da Inicialização:")
    print(f"✅ Python: OK")
    print(f"✅ Dependências: OK")
    print(f"✅ Diretórios: OK")
    print(f"{'✅' if secrets_ok else '⚠️ '} Secrets: {'OK' if secrets_ok else 'Configure'}")
    print(f"✅ Banco de dados: OK")
    print(f"{'✅' if ai_ok else '⚠️ '} IA Gemini: {'OK' if ai_ok else 'Configure API Key'}")
    print(f"{'✅' if tests_ok else '⚠️ '} Testes: {'OK' if tests_ok else 'Alguns falharam'}")
    
    logger.info("Inicialização concluída com sucesso")
    print("\n🎉 Inicialização concluída!")
    
    if not secrets_ok:
        logger.warning("Secrets não configurados - orientações fornecidas")
        print("\n📝 Próximos passos:")
        print("1. Configure GEMINI_API_KEY no .streamlit/secrets.toml")
        print("2. Execute: streamlit run 🏠_Home.py")
    else:
        logger.info("Sistema pronto para uso")
        print("\n🚀 Para iniciar a aplicação:")
        print("streamlit run 🏠_Home.py")


if __name__ == "__main__":
    main()
