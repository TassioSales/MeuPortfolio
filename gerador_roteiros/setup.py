#!/usr/bin/env python3
"""
Script de configuração para o Gerador de Roteiros de Viagem com IA
"""

import os
import sys
import subprocess
from pathlib import Path

def print_banner():
    """Exibe o banner de boas-vindas"""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║        🗺️  GERADOR DE ROTEIROS DE VIAGEM COM IA  🗺️        ║
    ║                                                              ║
    ║                    Script de Configuração                    ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

def check_python_version():
    """Verifica se a versão do Python é compatível"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ é necessário. Versão atual:", sys.version)
        return False
    print(f"✅ Python {sys.version.split()[0]} detectado")
    return True

def create_directories():
    """Cria diretórios necessários"""
    directories = ['.streamlit', 'logs', 'pages', 'utils']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Diretório {directory}/ criado")

def install_dependencies():
    """Instala as dependências do projeto"""
    try:
        print("📦 Instalando dependências...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependências instaladas com sucesso")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao instalar dependências: {e}")
        return False

def create_secrets_file():
    """Cria arquivo de configuração de exemplo"""
    secrets_example = Path('.streamlit/secrets.toml.example')
    secrets_file = Path('.streamlit/secrets.toml')
    
    if not secrets_file.exists():
        if secrets_example.exists():
            # Copia o arquivo de exemplo
            with open(secrets_example, 'r', encoding='utf-8') as src:
                content = src.read()
            with open(secrets_file, 'w', encoding='utf-8') as dst:
                dst.write(content)
            print("✅ Arquivo .streamlit/secrets.toml criado")
            print("⚠️  IMPORTANTE: Configure suas chaves de API no arquivo secrets.toml")
        else:
            print("❌ Arquivo secrets.toml.example não encontrado")
            return False
    else:
        print("✅ Arquivo .streamlit/secrets.toml já existe")
    
    return True

def main():
    """Função principal de configuração"""
    print_banner()
    
    print("🔍 Verificando pré-requisitos...")
    if not check_python_version():
        sys.exit(1)
    
    print("\n📁 Criando estrutura de diretórios...")
    create_directories()
    
    print("\n📦 Instalando dependências...")
    if not install_dependencies():
        sys.exit(1)
    
    print("\n🔧 Configurando arquivos...")
    if not create_secrets_file():
        sys.exit(1)
    
    print("\n" + "="*60)
    print("🎉 CONFIGURAÇÃO CONCLUÍDA COM SUCESSO!")
    print("="*60)
    print("\n📋 PRÓXIMOS PASSOS:")
    print("1. Configure suas chaves de API em .streamlit/secrets.toml")
    print("2. Execute: streamlit run app.py")
    print("3. Acesse: http://localhost:8501")
    print("\n📚 Para mais informações, consulte o README.md")
    print("="*60)

if __name__ == "__main__":
    main()
