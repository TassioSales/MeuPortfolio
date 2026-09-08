# Passada de qualidade e robustez — finanças (Patrimônio)

**Data:** 2026-09-08
**Escopo:** logging, backend, frontend do projeto Django `finanças/`. Só qualidade/robustez — sem features novas, exceto o redesign pontual da página de login pedido explicitamente pelo usuário.
**Fora de escopo:** cobertura de testes nova para módulos inteiros (só regressão pontual do bug de segurança mais crítico); redesign visual amplo do app (mantém Bootstrap 5 + `custom.css` atuais).

## Contexto

Auditoria feita em duas frentes (backend e frontend) mais revisão direta de `finance_project/settings.py`. O projeto é maior do que o `finanças/CLAUDE.md` documenta (12 modelos, não 6 — `BankAccount`, `Transfer`, `AuditLog`, `Loan`, `LoanDisbursement`, `LoanPayment` foram adicionados depois e não estão na doc).

## 1. Logging

- **Config duplicada** (`finance_project/settings.py:236-274`): o dict `LOGGING` do Django roda em paralelo ao `InterceptHandler` do Loguru → toda mensagem de `django`/`core` sai duplicada (2x no console, gravada em `debug.log` **e** `finance.log`). **Fix:** remover o dict `LOGGING` tradicional; Loguru vira o único sink (stderr + `finance.log`), via `InterceptHandler` capturando o logging padrão do Django.
- **Padronizar em Loguru**: `views_dashboard.py`, `views_accounts.py`, `views_loans.py`, `views_goals.py`, `views_budgets.py`, `views_categories.py` não logam nada hoje; `views_reports.py` e `market_data.py` usam `logging.getLogger("core")` em vez de Loguru. Trocar tudo para `from loguru import logger as log`.
- **Exceções silenciosas**: adicionar `log.warning(...)`/`log.exception(...)` em:
  - `views_investments.py` (linhas ~82-83, 90-91, 98-99, 178-179, 271-272 — bare `except Exception: pass`/fallback silencioso)
  - `views_transactions.py` (~219-220, `import_transactions` pulando linha sem registrar o motivo)
  - `forms.py` (`InvestmentForm.clean()`, `except:` nu na busca do nome via yfinance)
- **Cache sem TTL**: `market_data.get_bcb_series` usa `@lru_cache(maxsize=32)` (dado fica preso por dias no processo de um app desktop). Trocar por `django.core.cache` com timeout (mesmo padrão já usado para tickers). `get_latest_indicator` deve logar quando cai no fallback `0.0`.

## 2. Backend

### Segurança
- `TransactionForm` e `BudgetForm` (`forms.py`) não filtram o queryset de `category` por usuário — vazamento cross-tenant (usuário A pode anexar categoria do usuário B). Fix: escopar por `user` no `__init__`, igual `TransferForm` já faz. **Inclui teste de regressão** cobrindo esse caso.
- `views_settings.py::settings_view` deixa qualquer usuário autenticado reescrever o `.env` compartilhado e mudar o token global do brapi para todos. Fix: restringir a `is_staff`/superuser; tornar a escrita do `.env` atômica (arquivo temporário + rename).
- Upload de OFX/XLSX sem limite de tamanho/tipo antes do parse. Fix: validar tamanho máximo e content-type em `ImportFileForm` antes de `ofxparse`/`openpyxl` processarem o arquivo.
- `finance_project/settings.py:22-30`: `SECRET_KEY` tem fallback hardcoded, `DEBUG` cai em `True` e `ALLOWED_HOSTS` cai em `"*"` quando o `.env` não está configurado — viola a própria convenção do `finanças/CLAUDE.md` ("nunca hardcode SECRET_KEY", "ALLOWED_HOSTS não pode ser `*` em produção"). Fix: manter os defaults permissivos só para `manage.py runserver` (dev), mas em `run_app.py` (modo empacotado/.exe, que é o "modo produção" real deste app) forçar `DEBUG=False` e gerar+persistir uma `SECRET_KEY` aleatória num arquivo local na primeira execução caso não haja uma no `.env`.

### Correção
- `clean_currency_value` aceita valores negativos sem checagem. Fix: adicionar `MinValueValidator(0.01)` (ou equivalente) nos campos monetários que nunca podem ser negativos — `Transaction.amount`, `Budget.limit`, `Goal.target_amount`, `Goal.monthly_target` — via migration aditiva simples; `Goal.current_amount` aceita `MinValueValidator(0)` (pode ser zero, nunca negativo). Nos formulários correspondentes (`TransactionForm`, `BudgetForm`, `GoalForm`), `clean_amount`/`clean_limit`/`clean_target_amount` devem rejeitar valores ≤0 com mensagem de erro amigável, em vez de deixar estourar no `full_clean()` do model.
- `transfer_create` (`views_accounts.py`) e `loan_make_payment` (`views_loans.py`) alteram múltiplas linhas (saldo de duas contas; empréstimo+pagamento+transação+auditoria) sem `transaction.atomic()`. Fix: envolver em `with transaction.atomic():`.

### Performance
- Dashboard (`views_dashboard.py`) faz 6+ `aggregate()` separados mais um loop por orçamento — mesmo padrão problemático em `views_loans.py` (schedule) e `views_reports.py`. Fix: colapsar em `Sum(..., filter=Q(...))` (padrão já correto em outro trecho de `views_reports.py`) e adicionar `select_related("category", "account")` nas list views.

### Limpeza pontual
- `Investment.save()` salva duas vezes na criação (UPDATE extra desnecessário) — ajustar para montar a transação associada antes do único `save()` final.
- `core_extras.py`: `multiply` e `mul` são filtros idênticos — remover um e atualizar templates que usam o removido.

## 3. Frontend

- **XSS**: busca de ticker em `investment_dashboard.html` (~227-245) injeta JSON via `innerHTML` sem escapar. Fix: usar `textContent`/construção de nós DOM em vez de template literal em `innerHTML`.
- **Moeda inconsistente**: várias telas usam `R$ {{ x|floatformat:2 }}` hardcoded em vez do filtro `brl` já existente — `investment_dashboard.html`, `investment_list.html`, `cash_flow.html`, `reports.html`, `reports_pdf.html`, `safe_haven_dashboard.html`. Fix: padronizar tudo em `{{ x|brl }}`.
- **Acessibilidade**: labels sem `for`/`id` correspondente nos formulários de filtro (ex. `transaction_list.html`); modais Bootstrap (`quickAddModal`, `depositModal`) sem `role="dialog"`/`aria-*`. Fix: adicionar os atributos padrão.
- **JS duplicado**: setup de Chart.js copiado em 8+ templates. Fix: extrair `static/js/charts.js` com helper único (cores, tema claro/escuro, opções de grid) e incluir uma vez em `base.html`.
- **JSON frágil**: `JSON.parse('{{ chart_labels|safe }}')` com `.replace(/'/g,'"')` manual quebra com apóstrofo no texto (ex. nome de ativo). Fix: trocar por `{{ chart_labels|json_script:"id" }}` (nativo do Django) em todos os templates com gráfico.
- **Limpeza**: Toastify carregado em toda página mas nunca usado — remover do `base.html`. Pinar versão exata do Chart.js (hoje sem versão). Mover `<style>` inline duplicado (13 templates) para classes utilitárias em `custom.css`.
- **Doc**: `finanças/CLAUDE.md` ainda cita `investment_dashboard.html.bak`, que já foi removido do disco — tirar a referência.

## 4. Página de login (pedido explícito do usuário)

Bug encontrado: `login.html` estende `base.html` inteiro, então um usuário **não autenticado** vê a sidebar completa do app (todos os menus, botão flutuante "+", modal de lançamento rápido) — todos esses links redirecionam pro próprio login, mas a experiência é confusa e feia.

**Fix + redesign:**
- Criar `templates/base_auth.html`: layout mínimo (sem sidebar/FAB/modal), com o mesmo toggle de tema claro/escuro do app, fundo com gradiente sutil usando as cores de marca já definidas em `custom.css`, logo/ícone (`bi-gem`) centralizado.
- `login.html` e `register.html` passam a estender `base_auth.html` em vez de `base.html`.
- Card de login centralizado (glass-card, mesmo estilo visual do resto do app), mantendo o toggle "mostrar senha" já existente e o link para cadastro.
- Sem novas dependências JS/CSS.

## Arquivos afetados (estimativa)

`finance_project/settings.py`, `run_app.py`, `core/forms.py`, `core/models.py`, `core/views_investments.py`, `core/views_transactions.py`, `core/views_accounts.py`, `core/views_loans.py`, `core/views_dashboard.py`, `core/views_reports.py`, `core/views_settings.py`, `core/market_data.py`, `core/templatetags/core_extras.py`, uma migration nova, `templates/base.html`, `templates/base_auth.html` (novo), `templates/registration/login.html`, `templates/registration/register.html`, `templates/core/investment_dashboard.html`, `investment_list.html`, `cash_flow.html`, `reports.html`, `reports_pdf.html`, `safe_haven_dashboard.html`, `transaction_list.html`, `goal_list.html`, `static/css/custom.css`, `static/js/charts.js` (novo), `CLAUDE.md`, mais um arquivo de teste novo para a regressão de segurança.

## Testes

- Novo teste de regressão: usuário A não consegue anexar transação/orçamento à categoria do usuário B (nem via POST direto manipulando o `pk`).
- Rodar `python manage.py test core` no final para garantir que nada quebrou.
- Testar manualmente no navegador: login (novo visual), dashboard, uma tela com gráfico (JSON via `json_script`), import de arquivo grande/inválido (rejeitado), transferência entre contas (atomicidade não é visível diretamente, mas confirmar que o fluxo happy-path continua funcionando).
