# Contribuindo para a Plataforma de Rifas PRO

Obrigado por considerar contribuir! Este guia ajuda você a configurar, desenvolver e enviar mudanças com qualidade.

## Requisitos
- Python 3.12+
- Node/Docker (opcional)
- pre-commit (opcional, recomendado)

## Setup do Projeto
```bash
# Clonar
git clone <repo-url>
cd plataforma_rifas

# Ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Dependências
pip install -r requirements.txt

# Hooks (opcional)
pip install pre-commit
pre-commit install

# Executar
streamlit run app.py
```

## Padrões de Código
- Use Black (formatação), isort (imports) e Ruff (lint).
- Não faça push de segredos (use `.streamlit/secrets.toml` localmente, ignore no Git).
- Mantenha logs fora do versionamento (`log/` no `.gitignore`).

## Branches
- Crie branches a partir de `main`/`master`: `feature/minha-feature` ou `fix/issue-123`.

## Pull Requests
- Descreva claramente a motivação e as mudanças.
- Inclua screenshots quando alterar UI.
- Mencione issues relacionadas.

## Teste Manual
- Execute o app e valide:
  - Fluxo de vendas/cancelamento
  - Exportações CSV/XLSX e PDFs
  - Aba Analytics (gráficos e drill-down)
  - Gerenciamento (logo/QR/obs, backup JSON, espelhamento JSON)

## Docker
```bash
docker compose up --build -d
```

## Licença
- Ao contribuir, você concorda com a licença MIT do projeto.
