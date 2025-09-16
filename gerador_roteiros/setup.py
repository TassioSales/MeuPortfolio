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
    """Cria diretórios necessários apenas se não existirem"""
    directories = ['.streamlit', 'logs', 'pages', 'utils']
    
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ Diretório {directory}/ criado")
        else:
            print(f"📁 Diretório {directory}/ já existe")

def install_dependencies():
    """Instala as dependências do projeto"""
    requirements_file = Path("requirements.txt")
    
    if not requirements_file.exists():
        print("❌ Arquivo requirements.txt não encontrado")
        return False
    
    try:
        print("📦 Instalando dependências...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependências instaladas com sucesso")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao instalar dependências: {e}")
        return False

def create_secrets_file():
    """Cria arquivo de configuração apenas se não existir"""
    secrets_example = Path('.streamlit/secrets.toml.example')
    secrets_file = Path('.streamlit/secrets.toml')
    
    if not secrets_file.exists():
        if secrets_example.exists():
            # Copia o arquivo de exemplo
            try:
                with open(secrets_example, 'r', encoding='utf-8') as src:
                    content = src.read()
                with open(secrets_file, 'w', encoding='utf-8') as dst:
                    dst.write(content)
                print("✅ Arquivo .streamlit/secrets.toml criado")
                print("⚠️  IMPORTANTE: Configure suas chaves de API no arquivo secrets.toml")
            except Exception as e:
                print(f"❌ Erro ao criar secrets.toml: {e}")
                return False
        else:
            # Cria arquivo de exemplo se não existir
            print("📝 Criando arquivo secrets.toml.example...")
            try:
                example_content = """# Chaves de API - Configure suas chaves aqui
# NUNCA commite este arquivo com chaves reais

# Chave da API Mistral (obrigatória)
MISTRAL_API_KEY = "coloque_sua_chave_da_mistral_aqui"

# Chave da API Gemini (opcional, usado como fallback)
GEMINI_API_KEY = "coloque_sua_chave_do_gemini_aqui"

# Configurações opcionais
# DEBUG = false
# LOG_LEVEL = "INFO"
"""
                with open(secrets_example, 'w', encoding='utf-8') as f:
                    f.write(example_content)
                print("✅ Arquivo secrets.toml.example criado")
                
                # Agora cria o arquivo secrets.toml
                with open(secrets_file, 'w', encoding='utf-8') as f:
                    f.write(example_content)
                print("✅ Arquivo .streamlit/secrets.toml criado")
                print("⚠️  IMPORTANTE: Configure suas chaves de API no arquivo secrets.toml")
            except Exception as e:
                print(f"❌ Erro ao criar arquivos de configuração: {e}")
                return False
    else:
        print("✅ Arquivo .streamlit/secrets.toml já existe")
    
    return True

def create_init_files():
    """Cria arquivos __init__.py necessários apenas se não existirem"""
    init_files = [
        'utils/__init__.py'
    ]
    
    for init_file in init_files:
        init_path = Path(init_file)
        if not init_path.exists():
            try:
                init_path.parent.mkdir(parents=True, exist_ok=True)
                with open(init_path, 'w', encoding='utf-8') as f:
                    f.write('"""Pacote utils para o Gerador de Roteiros"""\n')
                print(f"✅ Arquivo {init_file} criado")
            except Exception as e:
                print(f"❌ Erro ao criar {init_file}: {e}")
        else:
            print(f"📄 Arquivo {init_file} já existe")

def create_gitignore():
    """Cria arquivo .gitignore apenas se não existir"""
    gitignore_path = Path('.gitignore')
    
    if not gitignore_path.exists():
        try:
            gitignore_content = """# Arquivos de configuração sensíveis
.streamlit/secrets.toml

# Logs
logs/
*.log

# Ambiente virtual
venv/
env/
.venv/

# Cache Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Streamlit
.streamlit/config.toml

# Temporários
*.tmp
*.temp
"""
            with open(gitignore_path, 'w', encoding='utf-8') as f:
                f.write(gitignore_content)
            print("✅ Arquivo .gitignore criado")
        except Exception as e:
            print(f"❌ Erro ao criar .gitignore: {e}")
    else:
        print("📄 Arquivo .gitignore já existe")

def create_settings_file():
    """Cria arquivo settings.json apenas se não existir"""
    settings_path = Path('settings.json')
    
    if not settings_path.exists():
        try:
            settings_content = """{
  "app": {
    "name": "Gerador de Roteiros de Viagem com IA",
    "version": "1.0.0",
    "description": "Planejador de viagens inteligente que gera roteiros personalizados usando inteligência artificial",
    "author": "Desenvolvedor",
    "license": "MIT"
  },
  "streamlit": {
    "page_title": "Planejador de Viagens IA",
    "page_icon": "🗺️",
    "layout": "wide",
    "initial_sidebar_state": "collapsed",
    "theme": {
      "primaryColor": "#667eea",
      "backgroundColor": "#f6f7f9",
      "secondaryBackgroundColor": "#ffffff",
      "textColor": "#1f2937"
    }
  },
  "ai_providers": {
    "default_provider": "mistral",
    "mistral": {
      "model": "mistral-large-latest",
      "temperature": 0.7,
      "max_tokens": 4000,
      "enabled": true
    },
    "gemini": {
      "models": [
        "gemini-2.5-flash",
        "gemini-2.0-pro",
        "gemini-1.5-pro-latest"
      ],
      "default_model": "gemini-2.5-flash",
      "temperature": 0.7,
      "enabled": true
    },
    "fallback": {
      "enabled": true,
      "offline_mode": true
    }
  },
  "logging": {
    "level": "INFO",
    "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    "rotation": "1 day",
    "retention": "7 days",
    "files": {
      "app_log": "logs/app.log",
      "error_log": "logs/error.log"
    }
  },
  "features": {
    "vida_noturna": true,
    "gastronomia": true,
    "cronograma_detalhado": true,
    "dicas_viagem": true,
    "export_pdf": false,
    "save_history": false,
    "user_ratings": false
  },
  "limits": {
    "max_duration_days": 60,
    "min_duration_days": 1,
    "max_travelers": 20,
    "min_travelers": 1
  },
  "defaults": {
    "duration": 7,
    "travelers": 2,
    "budget": "Intermediário",
    "pace": "Moderado",
    "accommodation": "Hotel 3*",
    "walking_level": "Médio",
    "climate": "Ameno"
  },
  "ui": {
    "show_provider_selection": true,
    "show_advanced_options": true,
    "enable_dark_mode": true,
    "responsive_design": true,
    "animations": true
  },
  "security": {
    "hide_api_keys": true,
    "validate_inputs": true,
    "rate_limiting": false,
    "session_timeout": 3600
  },
  "development": {
    "debug_mode": false,
    "show_prompts": false,
    "mock_ai_responses": false,
    "enable_profiling": false
  }
}"""
            with open(settings_path, 'w', encoding='utf-8') as f:
                f.write(settings_content)
            print("✅ Arquivo settings.json criado")
        except Exception as e:
            print(f"❌ Erro ao criar settings.json: {e}")
    else:
        print("📄 Arquivo settings.json já existe")

def main():
    """Função principal de configuração"""
    print_banner()
    
    print("🔍 Verificando pré-requisitos...")
    if not check_python_version():
        sys.exit(1)
    
    print("\n📁 Criando estrutura de diretórios...")
    create_directories()
    
    print("\n📄 Criando arquivos necessários...")
    create_init_files()
    create_gitignore()
    create_settings_file()
    
    print("\n🔧 Configurando arquivos de API...")
    if not create_secrets_file():
        sys.exit(1)
    
    print("\n📦 Instalando dependências...")
    if not install_dependencies():
        print("⚠️  Aviso: Falha na instalação de dependências. Você pode tentar instalar manualmente:")
        print("   pip install -r requirements.txt")
    
    print("\n" + "="*60)
    print("🎉 CONFIGURAÇÃO CONCLUÍDA COM SUCESSO!")
    print("="*60)
    print("\n📋 PRÓXIMOS PASSOS:")
    print("1. Configure suas chaves de API em .streamlit/secrets.toml")
    print("   - Mistral AI: https://console.mistral.ai")
    print("   - Google Gemini: https://makersuite.google.com")
    print("2. Execute: streamlit run app.py")
    print("3. Acesse: http://localhost:8501")
    print("\n📚 Para mais informações, consulte o README.md")
    print("💡 Dica: Use 'python examples.py' para ver exemplos de uso")
    print("="*60)

if __name__ == "__main__":
    main()
