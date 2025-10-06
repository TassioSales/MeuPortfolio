#!/bin/bash
# Script de inicialização rápida para PriceTrack AI

echo "🚀 PriceTrack AI - Inicialização Rápida"
echo "========================================"

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Instale Python 3.8+ primeiro."
    exit 1
fi

echo "✅ Python encontrado: $(python3 --version)"

# Verificar se pip está instalado
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 não encontrado. Instale pip primeiro."
    exit 1
fi

echo "✅ pip encontrado"

# Criar ambiente virtual (opcional)
if [ ! -d "venv" ]; then
    echo "📦 Criando ambiente virtual..."
    python3 -m venv venv
fi

# Ativar ambiente virtual
echo "🔧 Ativando ambiente virtual..."
source venv/bin/activate

# Instalar dependências
echo "📥 Instalando dependências..."
pip install -r requirements.txt

# Criar diretórios necessários
echo "📁 Criando diretórios..."
mkdir -p logs
mkdir -p .streamlit

# Verificar arquivo de secrets
if [ ! -f ".streamlit/secrets.toml" ]; then
    echo "⚠️  Arquivo .streamlit/secrets.toml não encontrado!"
    echo "📝 Copie o arquivo de exemplo e configure suas chaves:"
    echo "   cp .streamlit/secrets.toml.example .streamlit/secrets.toml"
    echo "   nano .streamlit/secrets.toml"
fi

# Executar script de inicialização Python
echo "🔧 Executando inicialização..."
python3 setup.py

echo ""
echo "🎉 Inicialização concluída!"
echo ""
echo "🚀 Para iniciar a aplicação:"
echo "   streamlit run 🏠_Home.py"
echo ""
echo "📖 Para mais informações, consulte o README.md"
