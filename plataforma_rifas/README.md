<div align="center">

# 🎟️ Plataforma de Rifas PRO

<p align="center">
  <img src="https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Ticket/3D/ticket_3d.png" width="120" alt="Ticket">
</p>

<h3 align="center">✨ <em>Gerencie rifas de forma profissional, segura e com analytics avançado</em> ✨</h3>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-3776ab?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Streamlit-1.37%2B-ff4b4b?style=flat-square&logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/SQLite-DB-003b57?style=flat-square&logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ed?style=flat-square&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/License-MIT-00d4aa?style=flat-square&logo=opensourceinitiative&logoColor=white" alt="License">
</p>

<p align="center">
  <a href="#-inicio-rapido">
    <img src="https://img.shields.io/badge/🚀-Início_Rápido-00d4aa?style=for-the-badge" alt="Início Rápido">
  </a>
  <a href="#-funcionalidades">
    <img src="https://img.shields.io/badge/🎯-Funcionalidades-ff7000?style=for-the-badge" alt="Funcionalidades">
  </a>
  <a href="#-deploy-com-docker">
    <img src="https://img.shields.io/badge/🐳-Deploy-2496ed?style=for-the-badge" alt="Deploy">
  </a>
</p>

</div>

---

## 🚀 Início Rápido

<table>
<tr>
<td width="33%" align="center">

### 📥 **1. Instalar**
```bash
git clone [repo-url]
cd plataforma_rifas
pip install -r requirements.txt
```
<sub>Python 3.12+ recomendado</sub>

</td>
<td width="33%" align="center">

### 🔐 **2. Iniciar**
```bash
streamlit run app.py
# Acesse: http://localhost:8501
```
<sub>Interface web moderna</sub>

</td>
<td width="33%" align="center">

### 🐳 **3. Docker (opcional)**
```bash
docker compose up --build -d
```
<sub>Pronto para produção</sub>

</td>
</tr>
</table>

> 💡 Para publicar no Docker Hub, veja a seção "Publicar no Docker Hub" mais abaixo.

---

## ✨ Funcionalidades

<table>
<tr>
<td width="50%">

#### 🧩 Multiusuário & Segurança
- Login/cadastro com `bcrypt`
- Rate-limit/lockout após 5 tentativas (10 min)
- Rifas com `owner_id` e bloqueio de operações administrativas para não-donos

#### 🗃️ Persistência Robusta
- Banco `SQLite` como fonte de verdade
- Espelhamento JSON opcional (compatibilidade), controlado por `JSON_MIRROR`
- Backup JSON em um clique (ZIP) via UI

#### 🧾 Vendas & Comprovantes
- Venda com contato (telefone/WhatsApp)
- Cancelar/transferir vendas
- PDFs por comprador (consolidado, valor total, QR opcional, logo)
- Exportação CSV/XLSX com ajuste de fuso horário (`tz_offset_default`)

</td>
<td width="50%">

#### 📊 Analytics Avançado
- KPIs: Vendidos, Arrecadado, Únicos, Sell-through, Meta com progresso
- Período selecionável (24h, 7/30 dias, Tudo, Personalizado)
- Receita por dia e Receita acumulada
- Vendas por dia da semana e por hora (7/14/30)
- Heatmap Dia×Hora (Altair)
- Drill-down por dia (compradores, números, CSV e PDF do dia)

#### 🧱 UX & Operação
- Grade paginada com "Ir para número"
- Reservas com TTL e auto-liberação
- Aparência personalizada (logo, QR, observação padrão)

</td>
</tr>
</table>

---

## 🏗️ Arquitetura

```mermaid
graph TB
    U[👤 Usuário] --> W[🌐 Streamlit UI]
    W --> D[🗃️ db_data_manager]
    D --> DB[(SQLite)]
    D -->|Opcional| J[(JSON Mirror)]
    W --> A[📊 Aba Analytics]
    W --> V[🧾 Vendas/PDF/Export]
    W --> G[⚙️ Gerenciamento]
```

---

## 🛠️ Stack Tecnológico

<table>
<tr>
<td width="33%" align="center">

#### 🐍 Backend
![Python](https://img.shields.io/badge/Python-3.12+-3776ab?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.37+-ff4b4b?style=flat-square&logo=streamlit)
![Loguru](https://img.shields.io/badge/Loguru-0.7+-blue?style=flat-square)

</td>
<td width="33%" align="center">

#### 🗃️ Dados
![SQLite](https://img.shields.io/badge/SQLite-DB-003b57?style=flat-square&logo=sqlite)
![bcrypt](https://img.shields.io/badge/bcrypt-Auth-00bfa5?style=flat-square)

</td>
<td width="33%" align="center">

#### 📊 Visualização & Deploy
![Altair](https://img.shields.io/badge/Altair-5+-red?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ed?style=flat-square&logo=docker)

</td>
</tr>
</table>

---

## 📁 Estrutura do Projeto

```
plataforma_rifas/
├── app.py                     # Aplicação principal
├── modules/
│   ├── ui_components.py       # UI (grid, analytics, drill-down, PDFs)
│   ├── db_data_manager.py     # Regras de negócio + acesso SQLite + JSON backup
│   └── database.py            # Criação de tabelas/índices e conexão
├── data/                      # Banco e (opcional) JSONs/backs
│   └── rifas.db               # SQLite (fonte de verdade)
├── .streamlit/
│   └── config.toml            # Tema e configs do Streamlit
├── requirements.txt           # Dependências (inclui Altair)
├── Dockerfile                 # Imagem da aplicação
├── docker-compose.yml         # Orquestração, volumes e healthcheck
├── logger.py                  # Logging
└── README.md                  # Este arquivo
```

> ℹ️ JSONs legados em `data/*.json`, `data/_backups/`, `data/_reservas/`, `data/_sales/` podem ser removidos após migração para SQLite.

---

## ⚡ Instalação Completa (Manual)

```bash
# 1) Ambiente
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 2) Dependências
pip install -r requirements.txt

# 3) Executar
streamlit run app.py
```

---

## 🎯 Como Usar

1. Selecione/Crie uma rifa na barra lateral (com owner, se logado)
2. Aba "Dashboard & Vendas": venda, reserva e cancelamento
3. Aba "Consultar & Exportar": filtros por período/comprador, CSV/XLSX
4. Aba "📈 Analytics": KPIs, gráficos, heatmap, drill-down e PDF do dia
5. Aba "⚙️ Gerenciamento": configurações, logo/QR/observação, backup JSON e espelhamento JSON

---

## 🐳 Deploy com Docker

### Método Rápido
```bash
docker compose up --build -d
```

### Publicar no Docker Hub
```bash
# Login com Personal Access Token (PAT)
docker logout
docker login -u tassiosales  # cole o PAT no Password

# Build local (usa a tag do compose: tassiosales/plataforma_rifas:latest)
docker compose build

# Push para o Docker Hub
docker compose push

# Alternativa: retag + push manual
docker tag plataforma_rifas-plataforma_rifas:latest tassiosales/plataforma_rifas:latest
docker push tassiosales/plataforma_rifas:latest
```

### Produção puxando do Hub
No `docker-compose.yml`, deixe apenas:
```yaml
image: tassiosales/plataforma_rifas:latest
```
e rode:
```bash
docker compose up -d
```

---

## 🐛 Solução de Problemas

- **401/invalid_token no push**: refaça login com PAT e confirme o repo `tassiosales/plataforma_rifas` público.
- **compose push Skipped**: adicione `image:` no compose (já configurado) ou faça retag manual e `docker push`.
- **Porta 8501 ocupada**: ajuste a porta no compose (ex.: `8502:8501`).
- **Timezone**: ajuste `tz_offset_default` na rifa, e/ou `TZ` no compose.

---

## 🤝 Contribuição

1. Faça fork do projeto
2. Crie uma branch feature/nome
3. Envie PR com descrição clara

---

## 📄 Licença

Licença MIT.

---

<div align="center">

## ⭐ Apoie o Projeto

Se este projeto foi útil, deixe sua ⭐ e compartilhe!

**© 2025 - Plataforma de Rifas PRO**

</div>
