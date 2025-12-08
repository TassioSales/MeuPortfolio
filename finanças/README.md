<div align="center">

# 💰 Sistema de Gestão Financeira Pessoal

💡 **Controle suas finanças, investimentos e relatórios em um só lugar.**

<p align="center">
  <img src="https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Money%20with%20wings/3D/money_with_wings_3d.png" width="120" alt="Finance Icon">
</p>

<h3 align="center">✨ <em>Organize sua vida financeira com inteligência e simplicidade</em> ✨</h3>
<p align="center"><strong>Desenvolvido com Django 6.0 & Python 3.13 - Versão 2025</strong></p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13-3776ab?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Django-6.0-092E20?style=flat-square&logo=django&logoColor=white" alt="Django">
  <img src="https://img.shields.io/badge/Bootstrap-5-7952B3?style=flat-square&logo=bootstrap&logoColor=white" alt="Bootstrap">
  <img src="https://img.shields.io/badge/Portable-Exe-blue?style=flat-square&logo=windows&logoColor=white" alt="Windows">
  <img src="https://img.shields.io/badge/License-MIT-00d4aa?style=flat-square&logo=opensourceinitiative&logoColor=white" alt="License">
</p>

<p align="center">
  <a href="#-início-rápido">
    <img src="https://img.shields.io/badge/🚀-Início_Rápido-00d4aa?style=for-the-badge" alt="Início Rápido">
  </a>
  <a href="#-funcionalidades">
    <img src="https://img.shields.io/badge/🎯-Funcionalidades-ff7000?style=for-the-badge" alt="Funcionalidades">
  </a>
  <a href="#-instalação">
    <img src="https://img.shields.io/badge/🔧-Instalação-2496ed?style=for-the-badge" alt="Instalação">
  </a>
  <a href="#-tecnologias">
    <img src="https://img.shields.io/badge/🛠️-Tecnologias-9c27b0?style=for-the-badge" alt="Tecnologias">
  </a>
</p>

---

<table>
<tr>
<td align="center" width="25%">
  <img src="https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Chart%20increasing/3D/chart_increasing_3d.png" width="50"><br>
  <strong>Investimentos</strong><br>
  <small>Cotações em Tempo Real</small>
</td>
<td align="center" width="25%">
  <img src="https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Spiral%20calendar/3D/spiral_calendar_3d.png" width="50"><br>
  <strong>Planejamento</strong><br>
  <small>Controle de Gastos</small>
</td>
<td align="center" width="25%">
  <img src="https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Page%20facing%20up/3D/page_facing_up_3d.png" width="50"><br>
  <strong>Relatórios</strong><br>
  <small>Exportação PDF</small>
</td>
<td align="center" width="25%">
  <img src="https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Laptop/3D/laptop_3d.png" width="50"><br>
  <strong>Portátil</strong><br>
  <small>Executável Windows</small>
</td>
</tr>
</table>

</div>

## ✨ Destaques do Projeto

- **Dashboard Interativo**: Visualização clara de receitas, despesas e saldo atual.
- **Gestão de Investimentos**: Acompanhe suas ações com integração ao **Yahoo Finance** (`yfinance`).
- **Relatórios Profissionais**: Gere relatórios detalhados em PDF usando `xhtml2pdf`.
- **Autenticação Segura**: Sistema de login e registro com opção de "Mostrar Senha" e proteção CSRF.
- **Portabilidade Total**: Versão compilada em `.exe` único que não requer instalação de Python.

## 🚀 Início Rápido (Modo Portátil)

A maneira mais fácil de usar o sistema é através do executável portátil.

<table>
<tr>
<td width="50%" align="center">

### 📥 **1. Baixar**
Localize o arquivo `finance_project.exe` na pasta de distribuição.

</td>
<td width="50%" align="center">

### 🖱️ **2. Executar**
Dê um duplo clique no arquivo. O servidor iniciará e o navegador abrirá automaticamente.

</td>
</tr>
</table>

> 💡 **Nota:** Na primeira execução, pode levar alguns segundos para o sistema descompactar os arquivos temporários.

---

## ✨ Funcionalidades Detalhadas

<div align="center">

### 🎯 **O que você pode fazer?**

</div>

<table>
<tr>
<td width="50%">

#### 💰 **Controle Financeiro**
- **CRUD de Transações**: Adicione, edite e remova receitas e despesas.
- **Categorização**: Organize seus gastos por categorias personalizadas.
- **Filtros**: Busque transações por data, tipo ou categoria.

#### 📈 **Módulo de Investimentos**
- **Cotações ao Vivo**: Integração com API para valores atualizados.
- **Carteira**: Visualize a distribuição dos seus ativos.
- **Histórico**: Acompanhe a evolução do seu patrimônio.

</td>
<td width="50%">

#### 🔒 **Segurança & UX**
- **Login/Registro**: Interface amigável com validação de formulários.
- **Visualização de Senha**: Facilidade para digitar senhas complexas.
- **Feedback Visual**: Mensagens de sucesso e erro (Toasts/Alerts).

#### 📄 **Relatórios & Logs**
- **PDF Export**: Baixe relatórios para impressão ou arquivamento.
- **Logging Avançado**: Sistema de logs com `loguru` para monitoramento e debug.

</td>
</tr>
</table>

## ⚡ Automação (Scripts Facilitadores)

Para facilitar o uso, incluímos scripts automáticos (`.bat`) na raiz do projeto. Basta clicar duas vezes:

| Arquivo | Função |
|---------|--------|
| `install.bat` | **Instalação Completa**: Configura Python, cria ambiente virtual e instala dependências. |
| `run.bat` | **Rodar Projeto**: Inicia o servidor local e abre o navegador. |
| `build.bat` | **Criar Executável**: Gera o arquivo `.exe` na pasta `dist`. |
| `populate_data.bat` | **Dados de Exemplo**: Cria usuário teste e transações fictícias. |
| `backup.bat` | **Backup**: Cria um arquivo `.zip` com todo o código do projeto. |

## 🔧 Instalação e Desenvolvimento (Código Fonte)

Se você é desenvolvedor e quer alterar o código, siga estes passos:

### Pré-requisitos
- Python 3.10 ou superior
- Git

### Passo a Passo

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/finance-project.git
cd finance-project

# 2. Crie e ative o ambiente virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure o Banco de Dados
python manage.py migrate

# 5. Crie um Superusuário (Opcional)
python manage.py createsuperuser

# 6. Execute o Servidor
python manage.py runserver
```

**🌐 Acesse:** `http://localhost:8000`

---

## 🛠️ Stack Tecnológico

<div align="center">

### 🎯 **Construído com tecnologias modernas e robustas**

</div>

<table>
<tr>
<td width="33%" align="center">

#### 🐍 **Backend**
![Python](https://img.shields.io/badge/Python-3.13-3776ab?style=flat-square&logo=python)
![Django](https://img.shields.io/badge/Django-6.0-092E20?style=flat-square&logo=django)
![Waitress](https://img.shields.io/badge/Waitress-Server-gray?style=flat-square)

</td>
<td width="33%" align="center">

#### 📊 **Dados & Relatórios**
![SQLite](https://img.shields.io/badge/SQLite-Dev-003B57?style=flat-square&logo=sqlite)
![YFinance](https://img.shields.io/badge/Yahoo-Finance-purple?style=flat-square)
![ReportLab](https://img.shields.io/badge/PDF-Generator-red?style=flat-square)

</td>
<td width="33%" align="center">

#### 🎨 **Frontend & Build**
![Bootstrap](https://img.shields.io/badge/Bootstrap-5-7952B3?style=flat-square&logo=bootstrap)
![PyInstaller](https://img.shields.io/badge/PyInstaller-Build-blue?style=flat-square)
![Inno Setup](https://img.shields.io/badge/Inno-Setup-orange?style=flat-square)

</td>
</tr>
</table>

---

## 📁 Estrutura do Projeto

```
finance_project/
├── 📂 core/                 # Aplicação principal (Views, Models, Forms)
├── 📂 finance_project/      # Configurações do Django (settings.py, urls.py)
├── 📂 templates/            # Arquivos HTML (Dashboard, Login, Relatórios)
├── 📂 static/               # Arquivos CSS, JS e Imagens
├── 📂 logs/                 # Logs da aplicação
├── 📂 dist/                 # Pasta de saída do executável
├── 📄 manage.py             # CLI do Django
├── 📄 run_app.py            # Script de entrada para o executável
├── 📄 finance_project.spec  # Configuração do PyInstaller
├── 📄 setup_script.iss      # Script do instalador Inno Setup
└── 📄 requirements.txt      # Dependências do projeto
```

---

## 🐛 Solução de Problemas Comuns

### ❌ **Erro ao abrir o executável em outro PC**
Se o executável fechar imediatamente, verifique se você copiou o arquivo `finance_project.exe` corretamente. A versão atual possui um tratamento de erro que manterá a janela aberta exibindo o problema.

### ❌ **Banco de Dados não encontrado**
O sistema cria automaticamente um arquivo `db.sqlite3` na mesma pasta do executável se ele não existir. Se você quiser preservar seus dados ao mover o programa, lembre-se de mover o arquivo `db.sqlite3` junto (embora no modo "Arquivo Único", o DB seja extraído temporariamente, para persistência real em modo portátil, recomenda-se o uso do Instalador ou manter o DB externo).

---

## 🤝 Contribuição

1. Faça um **Fork** do projeto
2. Crie uma **Branch** para sua feature (`git checkout -b feature/NovaFeature`)
3. Faça o **Commit** (`git commit -m 'Adicionando nova feature'`)
4. Faça o **Push** (`git push origin feature/NovaFeature`)
5. Abra um **Pull Request**

---

## 📄 Licença

Este projeto está licenciado sob a **Licença MIT**.

---

<div align="center">

**Desenvolvido com ❤️ para organização financeira.**

</div>
