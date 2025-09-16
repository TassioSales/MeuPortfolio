<div align="center">

# 🗺️ Gerador de Roteiros de Viagem com IA

<img src="https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/World%20map/3D/world_map_3d.png" width="100" alt="World Map">

### ✨ *Transforme seus sonhos de viagem em roteiros perfeitos com o poder da Inteligência Artificial* ✨

---

![Python](https://img.shields.io/badge/Python-3.8+-3776ab?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.37+-ff4b4b?style=for-the-badge&logo=streamlit&logoColor=white)
![Mistral AI](https://img.shields.io/badge/Mistral-AI-ff7000?style=for-the-badge&logo=ai&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google-Gemini-4285f4?style=for-the-badge&logo=google&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ed?style=for-the-badge&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-00d4aa?style=for-the-badge&logo=opensourceinitiative&logoColor=white)

[![🚀 Instalação Automática](https://img.shields.io/badge/🚀-Instalação_Automática-00d4aa?style=for-the-badge)](#-instalação-automática)
[![📖 Documentação Completa](https://img.shields.io/badge/📖-Documentação_Completa-4285f4?style=for-the-badge)](#-documentação)
[![🎯 Ver Exemplos](https://img.shields.io/badge/🎯-Ver_Exemplos-ff7000?style=for-the-badge)](#-exemplos-de-uso)
[![🐳 Deploy Docker](https://img.shields.io/badge/🐳-Deploy_Docker-2496ed?style=for-the-badge)](#-deploy-com-docker)

---

**🎯 Crie roteiros de viagem únicos e personalizados usando IA de última geração**  
*Mistral AI • Google Gemini • Interface Moderna • Sistema de Fallback Robusto*

</div>

---

## 📋 Navegação Rápida

<table>
<tr>
<td width="50%">

### 🚀 **Início Rápido**
- [⚡ Instalação Automática](#-instalação-automática)
- [🎯 Como Usar](#-como-usar)
- [🎪 Exemplos de Uso](#-exemplos-de-uso)
- [🐳 Deploy com Docker](#-deploy-com-docker)

### 📚 **Documentação**
- [🎯 Visão Geral](#-visão-geral)
- [✨ Funcionalidades](#-funcionalidades)
- [🏗️ Arquitetura](#-arquitetura)
- [📁 Estrutura do Projeto](#-estrutura-do-projeto)

</td>
<td width="50%">

### 🛠️ **Desenvolvimento**
- [🔧 Configuração Avançada](#-configuração-avançada)
- [📊 API Reference](#-api-reference)
- [🎨 Personalização](#-personalização)
- [🐛 Troubleshooting](#-troubleshooting)

### 🤝 **Comunidade**
- [🤝 Contribuição](#-contribuição)
- [📄 Licença](#-licença)
- [🙏 Agradecimentos](#-agradecimentos)
- [⭐ Apoie o Projeto](#-apoie-o-projeto)

</td>
</tr>
</table>

---

## 🎯 Visão Geral

O **Gerador de Roteiros de Viagem com IA** é uma aplicação web moderna e inteligente que utiliza modelos de linguagem avançados para criar roteiros de viagem personalizados e detalhados. A aplicação combina a facilidade de uso do Streamlit com o poder da inteligência artificial para oferecer uma experiência única de planejamento de viagens.

### 🎪 Características Principais

- **🤖 IA Dupla**: Integração com Mistral AI e Google Gemini
- **🎯 Personalização Avançada**: Perfil detalhado do viajante
- **📅 Flexibilidade de Datas**: Data específica, mês/ano ou IA escolhe
- **🌃 Vida Noturna**: Sugestões detalhadas de bares, festas e eventos
- **📱 Interface Responsiva**: Design moderno e intuitivo
- **🔄 Fallback Inteligente**: Sistema de backup robusto

---

## ✨ Funcionalidades

### 🎨 Interface do Usuário

<table>
<tr>
<td width="50%">

#### 📝 Formulário Inteligente
- **Perfil Detalhado**: Tipo de viagem, faixa etária, número de viajantes
- **Preferências**: Orçamento, ritmo, hospedagem, interesses
- **Configurações Avançadas**: Restrições alimentares, nível de caminhada
- **Datas Flexíveis**: Múltiplas opções de seleção de período

#### 🎯 Seleção de IA
- **Mistral AI**: Modelo principal de alta qualidade
- **Google Gemini**: Fallback confiável
- **Seleção Manual**: Usuário escolhe o modelo preferido
- **Fallback Offline**: Sistema de backup quando APIs falham

</td>
<td width="50%">

#### 📊 Visualização de Resultados
- **Interface em Abas**: Organização clara do conteúdo
- **Visão Geral**: Informações essenciais da viagem
- **Cronograma Detalhado**: Atividades dia a dia
- **Gastronomia**: Pratos típicos e restaurantes
- **Vida Noturna**: Bares, festas e eventos
- **Dicas Práticas**: Mobilidade, comunicação e segurança

</td>
</tr>
</table>

### 🧠 Inteligência Artificial

#### 🤖 Modelos Suportados

| Modelo | Tipo | Características |
|--------|------|-----------------|
| **Mistral Large** | Principal | Alta qualidade, respostas detalhadas |
| **Gemini 2.5 Flash** | Fallback | Rápido e eficiente |
| **Gemini 2.0 Pro** | Alternativo | Balanceado |
| **Gemini 1.5 Pro** | Estável | Versão confiável |

#### 🎯 Personalização Avançada

- **Análise de Perfil**: Considera idade, interesses e restrições
- **Contexto Geográfico**: Adapta sugestões ao destino
- **Sazonalidade**: Considera clima e eventos sazonais
- **Orçamento**: Ajusta recomendações ao nível financeiro

---

## 🏗️ Arquitetura

```mermaid
graph TB
    A[👤 Usuário] --> B[🌐 Streamlit UI]
    B --> C[📝 Formulário]
    C --> D[🧠 Processamento IA]
    
    D --> E{🤖 Modelo Escolhido}
    E -->|Principal| F[🔮 Mistral AI]
    E -->|Fallback| G[💎 Google Gemini]
    E -->|Offline| H[📋 Gerador Local]
    
    F --> I[📊 Parser JSON]
    G --> I
    H --> I
    
    I --> J[🎨 Interface Resultados]
    J --> K[📱 Visualização Final]
    
    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style D fill:#fff3e0
    style I fill:#e8f5e8
    style K fill:#fce4ec
```

### 🔄 Fluxo de Dados

1. **Entrada**: Usuário preenche formulário detalhado
2. **Processamento**: Sistema valida e formata dados
3. **IA**: Modelo selecionado gera roteiro personalizado
4. **Parsing**: Resposta é convertida para JSON estruturado
5. **Apresentação**: Interface organiza e exibe resultados

---

## 🛠️ Tecnologias

### 🐍 Backend

| Tecnologia | Versão | Propósito |
|------------|--------|-----------|
| **Python** | 3.8+ | Linguagem principal |
| **Streamlit** | 1.37+ | Framework web |
| **Requests** | 2.31+ | Chamadas HTTP para APIs |
| **Loguru** | 0.7+ | Sistema de logging |
| **Python-dateutil** | 2.9+ | Manipulação de datas |

### 🤖 Inteligência Artificial

| Serviço | Biblioteca | Uso |
|---------|------------|-----|
| **Mistral AI** | `requests` | API principal |
| **Google Gemini** | `google-genai` | Fallback |
| **Offline** | Template local | Backup final |

### 🎨 Frontend

| Tecnologia | Uso |
|------------|-----|
| **Streamlit Components** | Interface base |
| **CSS Customizado** | Estilização avançada |
| **HTML/Markdown** | Estrutura de conteúdo |
| **Responsive Design** | Adaptação mobile |

---

## 📁 Estrutura do Projeto

<details>
<summary><strong>🗂️ Clique para ver a estrutura completa</strong></summary>

```
gerador_roteiros/
├── 🎯 APLICAÇÃO PRINCIPAL
│   ├── 📄 app.py                      # Interface principal Streamlit (661 linhas)
│   └── 📁 pages/
│       └── 📄 01_Roteiro.py          # Página de resultados com abas
│
├── 🧠 LÓGICA E CONFIGURAÇÃO
│   ├── 📁 utils/
│   │   ├── 📄 __init__.py            # Inicializador do pacote
│   │   └── 📄 prompts.py             # Sistema de prompts para IA
│   ├── 📄 settings.json              # ⭐ Configurações centralizadas
│   └── 📄 examples.py                # ⭐ Exemplos e demonstrações
│
├── ⚙️ CONFIGURAÇÃO E DEPLOY
│   ├── 📄 requirements.txt           # Dependências Python
│   ├── 📄 pyproject.toml            # Configuração moderna do projeto
│   ├── 📄 setup.py                   # ⭐ Script de configuração automática
│   ├── 📄 Dockerfile                # Containerização Docker
│   ├── 📄 docker-compose.yml        # Orquestração de containers
│   └── 📁 .streamlit/
│       ├── 📄 secrets.toml           # Chaves API (não versionado)
│       └── 📄 config.toml            # Configurações Streamlit
│
├── 🔧 DESENVOLVIMENTO
│   ├── 📄 .gitignore                # Exclusões do Git
│   ├── 📄 .pre-commit-config.yaml   # Hooks de qualidade de código
│   └── 📁 .github/
│       └── 📁 workflows/
│           └── 📄 ci.yml            # CI/CD automático
│
├── 📚 DOCUMENTAÇÃO
│   ├── 📄 README.md                 # Este arquivo (documentação completa)
│   └── 📄 LICENSE                   # Licença MIT
│
└── 📁 RUNTIME
    ├── 📁 logs/                      # Logs da aplicação
    │   ├── 📄 app.log               # Log geral
    │   └── 📄 error.log             # Log de erros
    └── 📁 venv/                     # Ambiente virtual Python
```

</details>

### 📋 Descrição dos Arquivos

#### 🎯 Arquivos Principais

- **`app.py`**: Aplicação principal com interface e lógica de negócio
- **`pages/01_Roteiro.py`**: Página de visualização dos resultados
- **`utils/prompts.py`**: Sistema de prompts e formatação de dados

#### ⚙️ Arquivos de Configuração

- **`requirements.txt`**: Dependências Python necessárias
- **`settings.json`**: ⭐ **NOVO** - Configurações centralizadas do projeto
- **`setup.py`**: ⭐ **NOVO** - Script de configuração automática
- **`examples.py`**: ⭐ **NOVO** - Exemplos de uso e demonstrações
- **`.streamlit/secrets.toml`**: Chaves de API (configurar localmente)
- **`logs/`**: Diretório para arquivos de log

---

## ⚡ Instalação Automática

### 🚀 **Método Recomendado - Setup Automático**

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/gerador-roteiros.git
cd gerador_roteiros

# 2. Execute o script de configuração automática
python setup.py
```

**🎉 Pronto! O script `setup.py` fará automaticamente:**
- ✅ Verificação da versão do Python (3.8+)
- ✅ Criação de diretórios necessários
- ✅ Instalação de dependências
- ✅ Configuração de arquivos de exemplo
- ✅ Criação do `.gitignore` e `settings.json`

### 📋 **Pré-requisitos**

- **Python 3.8+** instalado
- **Git** para clonagem do repositório
- **Chaves de API** para Mistral AI e/ou Google Gemini

### 🔧 **Instalação Manual (Alternativa)**

<details>
<summary><strong>Clique para ver instalação manual</strong></summary>

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/gerador-roteiros.git
cd gerador_roteiros

# 2. Crie o ambiente virtual
python -m venv venv

# 3. Ative o ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Instale as dependências
pip install -r requirements.txt

# 5. Configure as chaves de API
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edite o arquivo com suas chaves

# 6. Execute a aplicação
streamlit run app.py
```

</details>

### 🔑 Configuração das Chaves de API

<table>
<tr>
<td width="50%">

#### 🔮 **Mistral AI** (Principal)
1. Acesse [console.mistral.ai](https://console.mistral.ai)
2. Crie uma conta gratuita
3. Gere uma API key
4. Adicione no arquivo `secrets.toml`

</td>
<td width="50%">

#### 💎 **Google Gemini** (Fallback)
1. Acesse [makersuite.google.com](https://makersuite.google.com)
2. Crie um projeto Google Cloud
3. Gere uma API key
4. Adicione no arquivo `secrets.toml`

</td>
</tr>
</table>

### 📝 Exemplo de `secrets.toml`

```toml
# 🔐 Chaves de API - NUNCA commite este arquivo com chaves reais

# Mistral AI (obrigatória)
MISTRAL_API_KEY = "sua_chave_mistral_aqui"

# Google Gemini (opcional, usado como fallback)
GEMINI_API_KEY = "sua_chave_gemini_aqui"

# Configurações opcionais
# DEBUG = false
# LOG_LEVEL = "INFO"
```

> 💡 **Dica**: O arquivo `secrets.toml` é criado automaticamente pelo `setup.py`

---

## 🎯 Como Usar

### 🚀 **Início Rápido**

```bash
# Após a instalação, execute:
streamlit run app.py
```

**🌐 Acesse:** `http://localhost:8501`

### 🎯 **Passo a Passo Detalhado**

#### 1. **🚀 Inicie a Aplicação**
```bash
streamlit run app.py
```
- Interface moderna será carregada no navegador
- Sistema verificará automaticamente as APIs disponíveis

#### 2. **🤖 Configure a IA**
- **Mistral AI**: Modelo principal (recomendado)
- **Google Gemini**: Fallback automático
- Seleção de modelo específico do Gemini

#### 3. **📝 Preencha o Formulário Inteligente**

<table>
<tr>
<td width="50%">

**📍 Informações Básicas**
- Destino principal
- Tipo de data (específica/mês/IA escolhe)
- Duração da viagem

**👥 Perfil dos Viajantes**
- Tipo de viagem (casal, família, etc.)
- Número de viajantes
- Faixa etária
- Presença de crianças

</td>
<td width="50%">

**🎯 Preferências**
- Orçamento (econômico/luxo)
- Ritmo (relaxado/intenso)
- Interesses específicos
- Nível de caminhada

**📝 Detalhes Adicionais**
- Restrições alimentares
- Horários preferidos
- Aversões
- Observações especiais

</td>
</tr>
</table>

#### 4. **Gere o Roteiro**
- Clique em "✨ Gerar Roteiro Personalizado"
- Aguarde o processamento da IA
- Visualize os resultados organizados

#### 5. **🎨 Explore os Resultados**

<table>
<tr>
<td width="20%" align="center">

**📋 Visão Geral**  
*Informações essenciais*

</td>
<td width="20%" align="center">

**🗓️ Cronograma**  
*Atividades dia a dia*

</td>
<td width="20%" align="center">

**🍽️ Gastronomia**  
*Pratos e restaurantes*

</td>
<td width="20%" align="center">

**🌃 Vida Noturna**  
*Bares e eventos*

</td>
<td width="20%" align="center">

**💡 Dicas**  
*Informações práticas*

</td>
</tr>
</table>

### 🎪 Interface de Resultados

A página de resultados é organizada em **abas intuitivas** com:
- 🎨 **Design responsivo** e moderno
- 🌙 **Modo escuro** automático
- 📱 **Adaptação mobile** perfeita
- ⚡ **Navegação fluida** entre seções

---

## 🎪 Exemplos de Uso

### 🎯 **Demonstrações Interativas**

O arquivo `examples.py` contém exemplos prontos para testar:

```bash
# Execute os exemplos
python examples.py
```

**📋 Exemplos Inclusos:**
- 💕 **Viagem Romântica**: Paris para casal
- 👨‍👩‍👧‍👦 **Viagem em Família**: Orlando com crianças
- 🏔️ **Viagem de Aventura**: Nepal para grupo
- 💼 **Viagem de Negócios**: São Paulo executivo

### 🎨 **Personalize seus Exemplos**

```python
# Exemplo de dados personalizados
from examples import exemplo_viagem_romantica
from utils.prompts import format_user_prompt_viagem

# Carregue um exemplo
dados = exemplo_viagem_romantica()

# Modifique conforme necessário
dados['destino'] = 'Santorini, Grécia'
dados['duracao'] = 10

# Gere o prompt
prompt = format_user_prompt_viagem(dados)
print(prompt)
```

---

## 🐳 Deploy com Docker

### 🚀 **Deploy Rápido**

```bash
# Usando Docker Compose (recomendado)
docker-compose up -d

# Ou usando Docker diretamente
docker build -t gerador-roteiros .
docker run -p 8501:8501 gerador-roteiros
```

### ⚙️ **Configuração Docker**

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8501:8501"
    environment:
      - MISTRAL_API_KEY=${MISTRAL_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    volumes:
      - ./logs:/app/logs
```

---

## 🔧 Configuração Avançada

### ⚙️ **Arquivo `settings.json`**

O projeto inclui um sistema de configuração centralizado:

```json
{
  "ai_providers": {
    "default_provider": "mistral",
    "mistral": {
      "model": "mistral-large-latest",
      "temperature": 0.7
    },
    "gemini": {
      "default_model": "gemini-2.5-flash",
      "temperature": 0.7
    }
  },
  "features": {
    "vida_noturna": true,
    "gastronomia": true,
    "export_pdf": false
  }
}
```

### 🎨 **Configurações Avançadas**

#### 🎨 Personalização da Interface

O arquivo `app.py` contém configurações CSS customizáveis:

```python
# Cores principais
--primary-color: #667eea
--secondary-color: #764ba2
--background-color: #f0f2f6

# Modo escuro
[data-theme="dark"] {
    --background-color: #1e1e1e
    --card-background: #2d2d2d
}
```

#### 🤖 Configuração de Modelos

```python
# Modelos disponíveis
MISTRAL_MODELS = ["mistral-large-latest"]
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-pro", "gemini-1.5-pro-latest"]
```

#### 📊 Sistema de Logging

```python
# Configuração de logs
logger.add("logs/app.log", rotation="1 day", retention="7 days", level="INFO")
logger.add("logs/error.log", rotation="1 day", retention="30 days", level="ERROR")
```

### 🔄 Fallback e Recuperação

O sistema possui múltiplas camadas de fallback:

1. **Modelo Principal** → Mistral AI
2. **Modelo Secundário** → Google Gemini
3. **Fallback Offline** → Gerador local

---

## 📊 API Reference

### 🤖 Funções de IA

#### `_call_mistral(user_prompt: str) -> Optional[str]`

Chama a API do Mistral AI para gerar roteiros.

**Parâmetros:**
- `user_prompt`: Prompt formatado com dados do usuário

**Retorna:**
- `str`: Resposta da IA em formato JSON
- `None`: Em caso de erro

#### `_call_gemini(user_prompt: str, model_name: str) -> Optional[str]`

Chama a API do Google Gemini para gerar roteiros.

**Parâmetros:**
- `user_prompt`: Prompt formatado com dados do usuário
- `model_name`: Nome do modelo Gemini a usar

**Retorna:**
- `str`: Resposta da IA em formato JSON
- `None`: Em caso de erro

#### `_parse_json_response(text: str) -> Optional[Dict]`

Converte resposta da IA em estrutura JSON válida.

**Parâmetros:**
- `text`: Texto bruto da resposta da IA

**Retorna:**
- `Dict`: Estrutura JSON parseada
- `None`: Em caso de erro de parsing

### 📝 Funções de Formatação

#### `format_user_prompt_viagem(data: dict) -> str`

Formata dados do usuário em prompt estruturado.

**Parâmetros:**
- `data`: Dicionário com dados do formulário

**Retorna:**
- `str`: Prompt formatado para a IA

---

## 🎨 Personalização

### 🎯 Modificando Prompts

Edite o arquivo `utils/prompts.py` para personalizar:

- **Persona da IA**: Comportamento e tom de voz
- **Estrutura de Resposta**: Formato do JSON de saída
- **Instruções Específicas**: Diretrizes para diferentes tipos de viagem

### 🎨 Customizando Interface

Modifique as variáveis CSS em `app.py`:

```python
# Cores personalizadas
:root {
    --primary-color: #sua_cor_primaria;
    --secondary-color: #sua_cor_secundaria;
}
```

### 🔧 Adicionando Novos Modelos

1. Implemente função de chamada no `app.py`
2. Adicione opção na interface
3. Integre no sistema de fallback

---

## 🐛 Troubleshooting

### ❌ Problemas Comuns

#### **Erro: "Chave API não encontrada"**
```
Solução: Verifique se o arquivo .streamlit/secrets.toml está configurado corretamente
```

#### **Erro: "Módulo não encontrado"**
```
Solução: Ative o ambiente virtual e instale as dependências
pip install -r requirements.txt
```

#### **Erro: "Porta já em uso"**
```
Solução: Use uma porta diferente
streamlit run app.py --server.port 8502
```

#### **Interface não atualiza**
```
Solução: Limpe o cache do navegador ou reinicie a aplicação
```

### 📊 Logs e Debugging

- **Logs gerais**: `logs/app.log`
- **Logs de erro**: `logs/error.log`
- **Debug no terminal**: Execute com `--logger.level debug`

### 🔍 Verificação de Saúde

```bash
# Verificar dependências
pip check

# Verificar logs
tail -f logs/app.log

# Testar APIs
python -c "import requests; print('APIs OK')"
```

---

## 🤝 Contribuição

### 🚀 Como Contribuir

1. **Fork** o repositório
2. **Crie** uma branch para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. **Commit** suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. **Push** para a branch (`git push origin feature/nova-funcionalidade`)
5. **Abra** um Pull Request

### 📋 Guidelines

- **Código**: Siga PEP 8 e boas práticas Python
- **Commits**: Use mensagens descritivas
- **Testes**: Adicione testes para novas funcionalidades
- **Documentação**: Atualize README quando necessário

### 🐛 Reportando Bugs

Use o sistema de Issues do GitHub com:

- **Título** descritivo
- **Descrição** detalhada do problema
- **Passos** para reproduzir
- **Logs** relevantes
- **Screenshots** se aplicável

---

## 📄 Licença

Este projeto está licenciado sob a **MIT License** - veja o arquivo [LICENSE](LICENSE) para detalhes.

### 📜 Resumo da Licença

- ✅ **Uso comercial** permitido
- ✅ **Modificação** permitida
- ✅ **Distribuição** permitida
- ✅ **Uso privado** permitido
- ❌ **Responsabilidade** não garantida

---

## ⭐ Apoie o Projeto

<div align="center">

### 🌟 **Se este projeto foi útil, considere apoiar!** 🌟

[![⭐ GitHub Stars](https://img.shields.io/github/stars/seu-usuario/gerador-roteiros?style=for-the-badge&logo=github&color=yellow)](https://github.com/seu-usuario/gerador-roteiros)
[![🍴 Fork](https://img.shields.io/github/forks/seu-usuario/gerador-roteiros?style=for-the-badge&logo=github&color=blue)](https://github.com/seu-usuario/gerador-roteiros)
[![👁️ Watch](https://img.shields.io/github/watchers/seu-usuario/gerador-roteiros?style=for-the-badge&logo=github&color=green)](https://github.com/seu-usuario/gerador-roteiros)

**💡 Formas de Apoiar:**
- ⭐ Dê uma estrela no GitHub
- 🐛 Reporte bugs e sugestões
- 🤝 Contribua com código
- 📢 Compartilhe com amigos
- 💬 Deixe feedback

</div>

---

## 🙏 Agradecimentos

<table>
<tr>
<td width="25%" align="center">

**🚀 Streamlit**  
*Framework incrível*

</td>
<td width="25%" align="center">

**🔮 Mistral AI**  
*IA de qualidade*

</td>
<td width="25%" align="center">

**💎 Google Gemini**  
*Fallback confiável*

</td>
<td width="25%" align="center">

**🐍 Python Community**  
*Suporte contínuo*

</td>
</tr>
</table>

---

<div align="center">

### 🎯 **Desenvolvido com ❤️ para a comunidade de viajantes** 🎯

**🌍 Explore o mundo com inteligência artificial! 🌍**

---

*📅 Última atualização: Setembro 2025*  
*🏷️ Versão: 1.0.0*  
*📄 Licença: MIT*

**[⬆️ Voltar ao topo](#-gerador-de-roteiros-de-viagem-com-ia)**

</div>
