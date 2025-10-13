<div align="center">

# 🎟️ Sorteador de Rifa PRO

<p align="center">
  <img src="https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Ticket/3D/ticket_3d.png" width="120" alt="Ticket">
</p>

<h3 align="center">✨ <em>Sorteios justos, transparentes e com total controle</em> ✨</h3>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-3776ab?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Streamlit-1.22+-FF4B4B?style=flat-square&logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ed?style=flat-square&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/License-MIT-00d4aa?style=flat-square&logo=opensourceinitiative&logoColor=white" alt="License">
</p>

<p align="center">
  <a href="#-início-rápido">
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
git clone https://github.com/TassioSales/MeuPortfolio.git
cd MeuPortfolio/sorteador_rifa_app
pip install -r requirements.txt
```
<sub>Python 3.8+ recomendado</sub>

</td>
<td width="33%" align="center">

### 🚀 **2. Executar**
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

---

## ✨ Funcionalidades

<table>
<tr>
<td width="50%">

#### 🎲 Sorteio Avançado
- Processamento inteligente de múltiplos formatos
- Suporte a listas, intervalos e números concatenados
- Validação em tempo real de números duplicados
- Filtragem e correção automática de dados

#### 📊 Resultados
- Exibição clara dos vencedores
- Lista completa de participantes
- Exportação para CSV/Excel
- Compartilhamento direto por WhatsApp

</td>
<td width="50%">

#### 🛠️ Facilidades
- Interface intuitiva e responsiva
- Processamento em lote de arquivos
- Suporte a múltiplos formatos de entrada
- Logs detalhados para auditoria
- Totalmente configurável

#### 📱 Multiplataforma
- Acessível de qualquer dispositivo
- Interface adaptável
- Leve e rápido
- Sem necessidade de instalação complexa

</td>
</tr>
</table>

---

## 🛠️ Stack Tecnológico

<table>
<tr>
<td width="33%" align="center">

#### 🐍 Backend
![Python](https://img.shields.io/badge/Python-3.8+-3776ab?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.22+-FF4B4B?style=flat-square&logo=streamlit)
![Pandas](https://img.shields.io/badge/Pandas-1.3+-150458?style=flat-square&logo=pandas)

</td>
<td width="33%" align="center">

#### 📊 Visualização
![Plotly](https://img.shields.io/badge/Plotly-5.0+-3F4F75?style=flat-square&logo=plotly)
![Altair](https://img.shields.io/badge/Altair-4.0+-0099E5?style=flat-square)

</td>
<td width="33%" align="center">

#### 🚀 Deploy
![Docker](https://img.shields.io/badge/Docker-20.10+-2496ed?style=flat-square&logo=docker)
![Docker Compose](https://img.shields.io/badge/Docker_Compose-1.29+-2496ed?style=flat-square&logo=docker)

</td>
</tr>
</table>

---

## 📁 Estrutura do Projeto

```
sorteador_rifa_app/
├── app.py                # Aplicação principal
├── requirements.txt      # Dependências
├── Dockerfile           # Configuração do container
├── docker-compose.yml   # Orquestração
├── data/               # Dados de exemplo
├── modules/            # Módulos adicionais
│   └── assets/         # Recursos visuais
└── README.md           # Documentação
```

---

## 🐳 Deploy com Docker

### Método Rápido
```bash
docker compose up --build -d
```

### Publicar no Docker Hub
```bash
# Login (substitua pelo seu usuário)
docker login -u tassiosales

# Build e push
docker build -t tassiosales/sorteador-rifa .
docker push tassiosales/sorteador-rifa
```

### Variáveis de Ambiente
| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `PORT` | `8501` | Porta da aplicação |
| `TZ` | `America/Sao_Paulo` | Fuso horário |

---

## 🤝 Contribuição

1. Faça fork do projeto
2. Crie sua branch: `git checkout -b feature/nova-funcionalidade`
3. Commit suas alterações: `git commit -m 'Adiciona nova funcionalidade'`
4. Push para a branch: `git push origin feature/nova-funcionalidade`
5. Abra um Pull Request

---

## 📄 Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

<div align="center">

## ⭐ Apoie o Projeto

Se este projeto foi útil, deixe sua ⭐ e compartilhe!

**© 2025 - Sorteador de Rifa PRO**

[![GitHub](https://img.shields.io/badge/GitHub-TassioSales-181717?style=for-the-badge&logo=github)](https://github.com/TassioSales)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Tássio_Sales-0077B5?style=for-the-badge&logo=linkedin)](https://www.linkedin.com/in/tassio-sales-0a2b3c4d/)

</div>
