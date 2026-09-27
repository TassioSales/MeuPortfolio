# Dashboard, Transações, Empréstimos e Fluxo de Caixa — finanças (Patrimônio)

**Data:** 2026-09-27
**Escopo:** evolução funcional do Django `finanças/` em quatro frentes pedidas pelo usuário — (1) Dashboard, (2) Transações, (3) Empréstimos integrados às despesas/totais, (4) Fluxo de Caixa — mais as correções e fundações necessárias para que essas quatro frentes fiquem corretas.
**Fora de escopo:** investimentos (renda variável/fixa/moedas), metas, auditoria, importação OFX, empacotamento PyInstaller, redesign visual global (mantém Bootstrap 5 + `custom.css` + `static/js/charts.js`).
**Precedente:** `2026-09-08-quality-and-robustness-pass-design.md` (já aplicado — logging, segurança, `json_script`, `charts.js`).

---

## 0. Diagnóstico (estado atual)

Levantado lendo o código e o banco de produção local (`patrimonio.db`, somente leitura): 106 transações (47 crédito, 59 pix), **0 receitas**, 5 recorrências mensais, 31 categorias, 0 contas bancárias, **1 empréstimo ativo** (R$ 52.000, juros simples, 60 parcelas, 0 pagamentos).

### 0.1 Pedidos do usuário → causa raiz

| # | Pedido | Causa raiz no código |
|---|--------|----------------------|
| P1 | "Atividades" deve mostrar os **últimos lançamentos**, não os de maior valor | `views_dashboard.py:59` faz `filter(date__range=mês).order_by("-date")[:5]`. `Transaction` **não tem `created_at`**, então não existe noção de "lançado por último". Como parcelas de cartão e recorrências são pré-criadas com datas futuras, os 5 itens exibidos são os de **data mais tardia do mês** (em geral parcelas grandes que vencem no fim do mês), com desempate arbitrário — daí a impressão de "ordenado por valor". |
| P2 | Somar os empréstimos ao total / às despesas | Empréstimo só vira `Transaction` quando o usuário registra um pagamento manualmente (`loan_make_payment`). Parcelas previstas **nunca** entram em despesas, saldo, relatórios, orçamento, calendário ou fluxo de caixa. O dashboard mostra a dívida em cards separados, desconectados dos totais. O valor recebido (principal) também nunca entra como receita. |
| P3 | Mais gráficos no dashboard | Só existe 1 gráfico (barras receita × despesa, 6 meses). O botão "Últimos 6 meses" (`dashboard.html:163`) é um dropdown sem opções — não faz nada. |
| P4 | Filtros no dashboard | Só navegação mês a mês. Nenhum filtro por categoria, tipo, forma de pagamento, conta ou período maior. |
| P5 | Selecionar uma categoria e ver totais só dela (dashboard e transações) | Transações filtra por categoria, mas **não mostra nenhum total**. O filtro usa `category_id=` exato: selecionar uma categoria pai **ignora as subcategorias**. |
| P6 | KPIs em Transações | Não há nenhum KPI na tela de transações. |
| P7 | Fluxo de caixa mais completo e fácil de entender | Ver 0.2 — a tela tem bugs de cálculo que tornam os números incoerentes, além de não explicar de onde vem cada valor. |

### 0.2 Bugs encontrados (corrigir junto)

**Fluxo de caixa (`views_cashflow.py`, `cash_flow.html`):**
1. **"Saldo Atual" inclui o futuro**: soma *todas* as transações do usuário, inclusive parcelas e recorrências já materializadas até 2028. O saldo "atual" é, na prática, o saldo de março/2028.
2. **Dupla contagem na projeção**: a projeção soma `max(média histórica, recorrentes)` a partir desse "saldo atual" — mas as recorrências e parcelas futuras já estão dentro dele. O mesmo gasto é contado duas vezes.
3. **Média histórica contaminada**: `_monthly_averages` usa `date__gte=cutoff` sem limite superior — os meses futuros (já materializados) entram na média do "histórico".
4. **Linha do tempo duplicada**: o histórico do gráfico percorre todos os meses com transação (inclusive futuros) e a projeção é anexada depois — rótulos como "Out/2026" podem aparecer duas vezes e a projeção começa depois de 2028.
5. **Card "Economia Mensal Estimada"** mostra `proj_income` duas vezes; nunca mostra receita − despesa (`cash_flow.html:32-40`).
6. **Texto duplicado** no alerta de rodapé ("transações recorrentes ativas" repetido, `cash_flow.html:106-108`).
7. **Horizonte**: o seletor só oferece 1–6 meses, a view aceita 1–12.
8. Chart.js carregado duas vezes (já vem do `base.html`; `cash_flow.html:116` carrega de novo). Gráfico não usa `chartTheme()` (quebra no tema escuro).
9. Variável `running` calculada e nunca usada (`views_cashflow.py:92`).

**Dashboard (`views_dashboard.py`):**
10. `timezone.now().date()` com `USE_TZ=True` devolve a data **UTC** — depois das 21h em São Paulo o "hoje" já é amanhã. Mesmo problema em `services.py`, `views_cashflow.py`, `views_loans.py`. Usar `timezone.localdate()`.
11. Gráfico usa `six_months_ago = start - 180 dias` → mostra 7 meses parciais em vez de 6 cheios.
12. "Saldo Total" é o saldo projetado para o **último dia do mês navegado** (inclui lançamentos futuros daquele mês), mas o rótulo não diz isso.
13. Alertas de orçamento sempre usam o mês **real** (`budget_spent_map` usa `today`), mesmo quando o usuário navega para outro mês.
14. Recorrências com descrição vazia geram lançamentos com descrição `" (Recorrente)"` — 5 de 5 recorrências no banco estão assim; na lista aparecem sem título.

**Transações (`views_transactions.py`, `transaction_list.html`):**
15. Filtro de datas recebe string crua (`date__gte=start_date`) — valor inválido derruba a view com `ValidationError` (500).
16. `category` crua em `filter(category_id=...)` — valor não numérico também gera 500.
17. Paginação remonta a querystring à mão em 3 lugares — qualquer filtro novo precisa ser lembrado nos 3.
18. Ordenação fixa por `-date`, sem desempate → paginação instável (itens podem pular/repetir entre páginas).
19. Parcelas de cartão: `total_amount / installments` em `Decimal` gera dízima (ex.: 100/3 = 33,333…) que é arredondada no banco para 33,33 × 3 = 99,99 — **1 centavo some**. A última parcela deve absorver o resto.
20. Editar uma parcela não oferece "aplicar às demais"; excluir uma parcela deixa as outras órfãs (não há vínculo entre elas).

**Empréstimos (`views_loans.py`):**
21. `loan_add_funds` altera `LoanDisbursement` + `Loan` sem `transaction.atomic()`.
22. Pagamento cria uma `Transaction` sem vínculo com o `LoanPayment` — impossível reconciliar, desfazer ou evitar dupla contagem.
23. `float` em todo o cálculo de amortização (juros/saldo) — erros de arredondamento acumulam em 60 parcelas. Usar `Decimal` com `quantize(Decimal("0.01"), ROUND_HALF_UP)`.
24. `LoanListView` roda `_build_schedule` e um `aggregate` **por empréstimo** (N+1).

**Geral:**
25. Aportes em investimento viram `DESPESA` (`Investment.save()`), inflando "despesas" e distorcendo taxa de poupança — dinheiro que foi para a carteira não é gasto.
26. `BankAccount.balance` é um número digitado à mão, totalmente desconectado das transações (`Transaction.account` existe mas nunca altera saldo). Fica registrado aqui; a correção completa (saldo derivado) está fora do escopo — ver §8.

---

## 1. Fundações (modelo de dados + camada de consulta)

Tudo abaixo é pré-requisito das seções 2–5. Migrations aditivas, reversíveis e com backfill.

### 1.1 Novos campos em `Transaction`

| Campo | Tipo | Para quê |
|-------|------|----------|
| `created_at` | `DateTimeField(auto_now_add=True, db_index=True)` | "Últimos lançamentos" (P1). |
| `updated_at` | `DateTimeField(auto_now=True)` | Auditoria / "editado há X". |
| `origin` | `CharField(choices)`, default `MANUAL`, `db_index=True` | Saber de onde veio o lançamento: `MANUAL`, `PARCELA`, `RECORRENTE`, `EMPRESTIMO`, `INVESTIMENTO`, `IMPORTACAO`. Hoje isso só é inferível pelo texto da descrição. |
| `installment_group` | `UUIDField(null=True, db_index=True)` | Liga as N parcelas de uma compra no cartão. |
| `installment_number` / `installment_total` | `PositiveSmallIntegerField(null=True)` | "3/10" estruturado, sem depender do texto. |
| `recurring_source` | `FK(RecurringTransaction, SET_NULL, null=True)` | Liga o lançamento à recorrência que o gerou. |
| `loan` | `FK(Loan, SET_NULL, null=True, related_name="transactions")` | Liga parcelas/recebimento ao empréstimo (P2). |

**Índice composto:** `Index(fields=["user", "date"])` e `Index(fields=["user", "-created_at"])` — todas as telas filtram por usuário + data.

**Backfill (data migration):**
- `created_at` = `datetime.combine(date, time(12, 0))` no fuso local para linhas existentes (a ordem relativa fica pela `id` no desempate). Campo criado `null=True` na migration 1, preenchido na 2, e depois mantido `null=True` por segurança (ordenação usa `F("created_at").desc(nulls_last=True), "-id"`).
- `origin`: heurística uma única vez — descrição termina com `(Recorrente)` → `RECORRENTE`; bate `\((\d+)/(\d+)\)$` com `payment_method=CREDITO` → `PARCELA` (preenche number/total e agrupa por descrição-base + `installment_total` + categoria num `installment_group` novo); tem `investment` reverso → `INVESTIMENTO`; categoria "Pagamento de Empréstimo" → `EMPRESTIMO`; senão `MANUAL`.
- Descrição vazia de recorrente: reescrever para `"<nome da categoria> (Recorrente)"`.

### 1.2 Novos campos em `Category`

| Campo | Tipo | Para quê |
|-------|------|----------|
| `nature` | `CharField(choices)`, default `OPERACIONAL` | `OPERACIONAL` (gasto/receita real), `INVESTIMENTO` (aporte/resgate), `DIVIDA` (parcelas de empréstimo, recebimento de empréstimo). Permite que os KPIs separem "gasto de verdade" de "dinheiro que mudou de lugar" (bug 25) sem perder nada do total. |
| `color` | `CharField(7)`, opcional | Cor estável da categoria nos gráficos (donut/barras não trocam de cor entre telas). Default gerado a partir da paleta de `charts.js`. |

Backfill: "Investimentos" → `INVESTIMENTO`; "Pagamento de Empréstimo" → `DIVIDA`.

### 1.3 Convenção "realizado × previsto"

Não será criado campo de status. Regra única, documentada e aplicada em todas as telas:

- **Realizado** = `date <= hoje` (hoje = `timezone.localdate()`).
- **Previsto** = `date > hoje` (parcelas futuras, recorrências futuras, parcelas de empréstimo futuras).

Toda tela que mostra saldo deixa explícito qual dos dois está exibindo. Lançamentos previstos aparecem com badge "Previsto" na lista.

> Pergunta em aberto Q1 (§9): o usuário quer marcar manualmente "pago / não pago" (ex.: conta vencida e não paga)? Se sim, entra um campo `status` numa fase posterior — a regra por data continua como default.

### 1.4 Camada de consulta compartilhada — `core/analytics.py` (novo)

Hoje cada view monta seu próprio queryset/agregação (dashboard, relatórios, fluxo de caixa, transações, exportações) com regras ligeiramente diferentes. Centralizar:

```python
@dataclass(frozen=True)
class TxFilter:
    start: date | None
    end: date | None
    type: Literal["RECEITA", "DESPESA"] | None
    category_ids: tuple[int, ...]        # já expandido com subcategorias
    payment_methods: tuple[str, ...]
    account_id: int | None
    origins: tuple[str, ...]
    search: str
    min_amount: Decimal | None
    max_amount: Decimal | None
    include_loans: bool = True           # §4
    include_investments: bool = False    # aportes fora de "despesa" por padrão
    realized_only: bool = False

    @classmethod
    def from_request(cls, request, *, default_period="month") -> "TxFilter": ...
    def apply(self, qs: QuerySet[Transaction]) -> QuerySet[Transaction]: ...
    def querystring(self, **overrides) -> str: ...   # para paginação/links
    def previous_period(self) -> "TxFilter": ...       # mesmo tamanho, imediatamente anterior
```

- `from_request` **valida** tudo (datas com `_parse_date`/ISO, ids numéricos pertencentes ao usuário, enums) e descarta silenciosamente o inválido → resolve bugs 15/16.
- Categoria pai expande para `[pai] + subcategorias` (P5). Uma query só (`Category.objects.filter(Q(id__in=ids) | Q(parent_id__in=ids), user=user)`).
- Presets de período: `month` (mês atual/navegado), `last_month`, `3m`, `6m`, `12m`, `ytd`, `year`, `custom`.

Funções puras sobre um queryset filtrado:

```python
def kpis(qs, flt) -> dict            # §3.2 — uma única aggregate() com Sum/Count/Avg/Max filtrados
def by_category(qs, top=8) -> list   # agrupa por categoria-raiz, resto em "Outras"
def by_payment_method(qs) -> list
def monthly_series(user, flt, months=12) -> dict    # meses cheios, inclui meses zerados
def daily_cumulative(qs, start, end) -> list        # gasto acumulado dia a dia
def recent(user, limit=8) -> list    # §2.1 — agrupa parcelas
```

Toda agregação com `Sum(..., filter=Q(...))` numa única ida ao banco sempre que possível (padrão já usado em `_income_expense_totals`).

### 1.5 Utilidades

- `core/dates.py`: `today()` (= `timezone.localdate()`), `add_months(d, n)` (a lógica de "somar 1 mês" está copiada 3 vezes: `services.py`, `views_transactions.py` ×2), `month_bounds(y, m)`, `MONTH_NAMES_PT`/`MONTH_ABBR_PT` (hoje duplicados em `views_dashboard.py` e `views_cashflow.py`).
- `core/money.py`: `q2(x) -> Decimal` (quantize 0,01 HALF_UP) e `split_installments(total, n) -> list[Decimal]` (última parcela absorve o resto — bug 19).
- Trocar todos os `timezone.now().date()` por `dates.today()` (bug 10).

---

## 2. Dashboard

### 2.1 "Atividades" → "Últimos lançamentos" (P1)

- Fonte: `analytics.recent(user, limit=8)` — ordenado por `-created_at, -id`, **independente do mês navegado** (é um feed do que o usuário lançou por último, não um filtro de período).
- **Agrupamento de parcelas**: as N parcelas de um mesmo `installment_group` aparecem como **um** item — "Geladeira · 10x de R$ 250,00 · 1ª em 10/10" — e não 10 itens que empurram todo o resto para fora do feed. Idem para lançamentos de uma mesma importação (`origin=IMPORTACAO` com mesmo `created_at` truncado ao minuto → "32 lançamentos importados").
- Cada item mostra: ícone por tipo/origem, descrição (fallback: nome da categoria), categoria, **data do lançamento** ("hoje", "ontem", "há 3 dias") e **data de competência** quando diferente, valor com sinal, badge "Previsto" se a data for futura.
- Abas no card (sem recarregar página, só alternância de conteúdo já renderizado):
  1. **Recentes** (default) — acima.
  2. **Próximos vencimentos** — lançamentos com `date` entre hoje e hoje+15, ordenados por data asc (inclui parcelas de empréstimo — §4).
  3. **Maiores do período** — top 5 despesas do período filtrado por valor desc (o comportamento que hoje aparece "por acidente", agora explícito e rotulado).
- Link "Ver tudo" leva para `transaction_list?sort=-created_at`.

### 2.2 Barra de filtros do dashboard (P4)

Linha fixa abaixo do título, colapsável no mobile. Tudo via GET (link compartilhável, botão voltar funciona), com o último filtro lembrado em `request.session["dashboard_filter"]` quando o usuário volta sem parâmetros.

| Filtro | Controle | Observação |
|--------|----------|------------|
| Período | Setas ‹ › (mantidas) + seletor de preset (Mês, 3M, 6M, 12M, Ano, Personalizado) | Setas andam pelo tamanho do preset (mês a mês, trimestre a trimestre...). |
| Categoria | Select múltiplo agrupado por pai (optgroup) | Pai inclui subcategorias. |
| Tipo | Todos / Receitas / Despesas | |
| Forma de pagamento | Chips multi-seleção (Pix, Crédito, Débito, Dinheiro) | |
| Conta | Select (só aparece se o usuário tiver contas) | |
| Empréstimos | Toggle "Incluir parcelas de empréstimo" (default **ligado**) | §4. |
| Investimentos | Toggle "Contar aportes como despesa" (default **desligado**) | bug 25. |

- Filtros ativos aparecem como chips removíveis ("Categoria: Alimentação ✕") + "Limpar tudo".
- **Todos** os KPIs e gráficos do dashboard respeitam o filtro, exceto "Últimos lançamentos" (feed) e o card de posição patrimonial (§2.3, sempre global — com nota "não afetado por filtros").

### 2.3 KPIs do dashboard

**Linha 1 — período filtrado** (4 cards, com variação % vs. período anterior equivalente e seta colorida *semântica*: despesa subindo = vermelho, não verde como hoje em `dashboard.html:81-84`):

1. **Receitas** — realizadas; subtexto "+ R$ X previstas" se houver.
2. **Despesas** — realizadas + previstas do período; subtexto quebrando "das quais R$ Y em parcelas de empréstimo · R$ Z em cartão".
3. **Resultado do período** — receitas − despesas, com **taxa de poupança** (% da receita) como subtexto.
4. **Saldo projetado no fim do período** — saldo acumulado até o fim do período (rótulo explícito, bug 12), subtexto "Saldo hoje: R$ …".

**Linha 2 — posição patrimonial** (global, independente de filtro) — resposta direta ao "somar os empréstimos ao total" (P2):

| Card | Cálculo |
|------|---------|
| Saldo em caixa hoje | Σ receitas − Σ despesas com `date <= hoje` |
| Investido | custo total dos investimentos (reusa o que `investment_dashboard` já calcula; valor de mercado se estiver em cache, senão custo) |
| Dívida total | Σ `current_balance` dos empréstimos ativos (+ juros previstos até a quitação em subtexto) |
| **Patrimônio líquido** | caixa + investido − dívida (card destacado, com gradiente, no lugar do "Saldo Total" atual) |

**Linha 3 — indicadores rápidos** (chips pequenos): média diária de gasto no período · maior despesa do período · nº de lançamentos · dias até o fim do mês com "você pode gastar R$ X/dia para fechar no zero" (só no preset Mês corrente) · comprometimento da renda com dívidas (parcelas de empréstimo ÷ receita do mês, com alerta > 30%).

### 2.4 Gráficos do dashboard (P3)

Layout em grade de 12 colunas; todos com `chartTheme()`, `brlTick`, `json_script`, tooltip em BRL, estado vazio ("Sem dados para este filtro") e altura fixa para não pular layout. Cores de categoria vindas de `Category.color`.

| # | Gráfico | Tipo | Dados | Largura |
|---|---------|------|-------|---------|
| G1 | Receitas × Despesas por mês | Barras agrupadas + **linha de resultado** (eixo secundário) | `monthly_series`, 6 ou 12 meses cheios (bug 11); meses futuros com barras hachuradas/transparentes = previsto | 8 |
| G2 | Despesas por categoria | Donut com total no centro; clique numa fatia aplica o filtro de categoria | `by_category(top=8)` | 4 |
| G3 | Gasto acumulado no mês × mês anterior | Duas linhas (atual sólida, anterior tracejada) + linha horizontal de orçamento total, se houver | `daily_cumulative` | 6 |
| G4 | Top categorias × orçamento | Barras horizontais (gasto) com marcador do limite; vermelho se estourou | `by_category` + `Budget` do período navegado (corrige bug 13) | 6 |
| G5 | Evolução do saldo e da dívida | Linha de saldo acumulado + linha de dívida de empréstimos + área de patrimônio líquido, 12 meses | série mensal + saldo do empréstimo reconstruído por `LoanPayment.balance_after`/`LoanDisbursement` | 8 |
| G6 | Formas de pagamento | Barra empilhada 100% ou donut pequeno | `by_payment_method` | 4 |
| G7 | Parcelas futuras comprometidas | Barras por mês (próximos 12 meses) empilhando cartão / recorrentes / empréstimos | lançamentos futuros por `origin` | 12 |

G7 é o gráfico que mais ajuda a "entender" o futuro: mostra quanto da renda dos próximos meses já está comprometido antes de qualquer gasto novo.

### 2.5 Alertas do dashboard

Mantém os de orçamento (≥ 90% / ≥ 100%), agora calculados para o período navegado, e acrescenta:
- Saldo projetado fica negativo em algum dia do mês (vindo do fluxo de caixa §5, com link).
- Parcela de empréstimo vencendo em ≤ 5 dias.
- Recorrência que termina neste mês (`end_date`).
- Máximo 3 alertas visíveis; o resto em "ver mais".

### 2.6 Implementação

- `views_dashboard.py::dashboard` fica fina: monta `TxFilter`, chama `analytics.*`, `loans.position(user)`, e renderiza. Meta: ≤ 12 queries por request (hoje ~10 com só 1 gráfico); medir com `assertNumQueries` no teste.
- Template quebrado em includes: `core/dashboard/_filters.html`, `_kpis.html`, `_position.html`, `_recent.html`, `_charts.html`, `_alerts.html`.
- JS dos gráficos num arquivo estático `static/js/dashboard.js` (usa helpers de `charts.js`), não inline.
- `process_recurring_transactions` continua sendo chamado ao abrir o dashboard, e passa também a chamar `sync_loan_installments(user)` (§4.3).

---

## 3. Transações

### 3.1 Filtros (P5)

Mesma `TxFilter` do dashboard (consistência: o link "ver transações" de um gráfico do dashboard leva exatamente ao mesmo recorte).

- Existentes: busca, período, tipo, categoria.
- Novos: **presets de período** (chips: Este mês, Mês passado, 3 meses, Ano, Tudo), categoria **múltipla com subcategorias**, forma de pagamento, conta, origem (Manual, Parcela, Recorrente, Empréstimo, Investimento, Importação), faixa de valor (mín/máx, com `clean_currency_value`), "Somente previstos / somente realizados".
- **Ordenação** clicável no cabeçalho: data, valor, descrição, lançado em. Sempre com desempate por `-id` (bug 18). Parâmetro `sort=`.
- **Itens por página**: 25 / 50 / 100.
- Paginação via `{{ filter.querystring }}` (bug 17) — um único ponto.
- Filtros avançados em painel colapsável; os básicos (busca, período, categoria, tipo) sempre visíveis.
- Chips de filtros ativos + "Limpar".

### 3.2 KPIs de Transações (P6)

Faixa de cards acima da tabela, **sempre refletindo o filtro atual** (todas as páginas, não só a página visível):

| KPI | Cálculo |
|-----|---------|
| Receitas | Σ RECEITA |
| Despesas | Σ DESPESA |
| Saldo do filtro | receitas − despesas |
| Nº de lançamentos | count (com "x receitas · y despesas") |
| Ticket médio | média por lançamento de despesa |
| Maior lançamento | valor + descrição (link) |
| Média diária | despesas ÷ dias do período |
| Variação vs. período anterior | % sobre as despesas, período de mesmo tamanho imediatamente anterior |

Tudo numa única `aggregate()` (+ 1 para o período anterior).

### 3.3 Painel de categoria selecionada (P5)

Quando **uma** categoria (ou um pai) está filtrada, aparece um painel extra entre os KPIs e a tabela:

- **Total da categoria no período** em destaque, e **% que ela representa** do total de despesas (ou receitas) do mesmo período sem o filtro de categoria.
- **Orçamento** da categoria, se existir: barra de progresso (gasto / limite, restante, projeção de fechamento no ritmo atual).
- **Mini-gráfico**: evolução mensal da categoria nos últimos 12 meses (barras) com linha da média.
- **Quebra por subcategoria** (se for categoria pai): tabela pequena nome · total · %.
- **Quebra por forma de pagamento** da categoria.

Mesmo painel aparece no dashboard quando o filtro de categoria tem exatamente uma categoria (reutiliza o include `core/_category_insight.html`).

### 3.4 Tabela

- Colunas: seleção · data (com badge "Previsto" se futura) · descrição/categoria (com badges "3/10", "Recorrente", "Empréstimo", "Importado") · forma de pagamento · conta · valor · ações.
- **Linha de subtotal** no rodapé da página + total geral do filtro.
- Agrupamento opcional por dia (cabeçalho de dia com subtotal do dia) — toggle "Agrupar por dia".
- Remove o `animation-delay` por linha (com 100 linhas por página a última aparece depois de 10 s).

### 3.5 Ações

- **Parcelas**: ao editar/excluir um lançamento com `installment_group`, perguntar "Só esta / Esta e as próximas / Todas" (bug 20). Mesma coisa para `recurring_source` ("Só esta / Esta e as próximas" — "próximas" também desativa ou ajusta a recorrência).
- **Ações em massa** (além de excluir, que já existe): alterar categoria, alterar forma de pagamento, alterar conta. Sempre `filter(user=request.user, pk__in=ids)`.
- **Exportar o filtro atual** para CSV/XLSX (botão reaproveita `export_csv`/`export_xlsx`, que passam a aceitar `TxFilter`).
- **Duplicar lançamento** (abre o form pré-preenchido com data de hoje).

### 3.6 Formulário de lançamento

- Parcelamento com `split_installments` (bug 19) e preenchendo `origin`, `installment_group`, `installment_number/total`.
- Recorrência preenchendo `recurring_source` e usando `dates.add_months`.
- Categoria agrupada por pai (optgroup) e filtrada pelo tipo escolhido (receita/despesa) via JS.
- Validação: descrição vazia → usar nome da categoria (bug 14).

---

## 4. Empréstimos integrados às despesas e aos totais (P2)

### 4.1 Decisão de design

**Materializar as parcelas previstas do empréstimo como `Transaction` (DESPESA, `origin=EMPRESTIMO`, `loan=<empréstimo>`), da mesma forma que o sistema já faz com parcelas de cartão e recorrências.**

Por quê: é o único jeito de o empréstimo aparecer automaticamente em **todos** os lugares que o usuário olha — despesas do dashboard, filtro por categoria, relatórios, orçamento, calendário, exportações, fluxo de caixa — sem reescrever cada tela com uma exceção "e também some os empréstimos". A alternativa (calcular parcelas "virtuais" na hora em cada tela) espalha a regra por 6+ views e sempre esquece alguma.

O toggle "Incluir parcelas de empréstimo" (§2.2) passa a ser apenas `exclude(origin="EMPRESTIMO")` no `TxFilter`.

### 4.2 Regras

- **Categoria**: todas as parcelas vão para a categoria do sistema "Empréstimos" (`nature=DIVIDA`), criada sob demanda (substitui a atual "Pagamento de Empréstimo" — migration renomeia/mescla). Subcategoria opcional por empréstimo? → Q3.
- **Valor de cada parcela** = linha do cronograma `_build_schedule` (payment + seguro), por modalidade:
  - `PRICE`/`SAC`: parcelas conforme tabela, até `num_installments`.
  - `SIMPLES` (caso real do usuário: R$ 52.000, 60x): juros do mês nas parcelas 1..n-1 + principal na última, exatamente como o cronograma atual calcula.
  - `REDUCAO_SALDO` sem prazo: parcela = pagamento mínimo (juros do mês) + seguro — marcada na descrição como "mínimo".
- **Data** = `due_day` de cada mês a partir do mês seguinte a `start_date` (ajustado ao último dia do mês quando `due_day` > dias do mês).
- **Horizonte**: mesmo teto de 24 meses já usado pelas recorrências (`services.py`), para não gerar 360 linhas de um empréstimo sem prazo; parcelas além do teto aparecem no fluxo de caixa por cálculo (§5), não como linhas.
- **Descrição**: `"<nome do empréstimo> — parcela 7/60"`.

### 4.3 Sincronização — `core/services_loans.py` (novo)

```python
def sync_loan_installments(loan: Loan) -> None:
    """Recria as parcelas PREVISTAS (date > hoje e sem LoanPayment) a partir
    do cronograma atual. Nunca toca em parcelas já pagas."""
```

Chamado (dentro de `transaction.atomic()`):
- ao criar / editar um empréstimo;
- após registrar pagamento;
- após adicionar fundos (`loan_add_funds` — que também ganha `atomic`, bug 21);
- ao desativar/excluir (excluir → apaga parcelas previstas; pagas ficam, com `loan=NULL` via `SET_NULL`);
- no dashboard, de forma barata (só se `loan.updated_at > última sincronização` ou se faltam meses dentro do teto).

Idempotente: rodar duas vezes não duplica (chave lógica `loan_id + installment_number`).

### 4.4 Pagamento reconcilia, não duplica

`loan_make_payment` passa a:
1. Procurar a parcela prevista do empréstimo mais próxima da data de pagamento (mesmo mês).
2. **Converter** essa parcela em realizada: `amount` = valor efetivamente pago, `date` = data do pagamento, descrição com juros/amortização. Se não houver parcela prevista (pagamento extra/antecipado), cria uma nova `Transaction` `origin=EMPRESTIMO`.
3. Gravar `LoanPayment.transaction = <essa transação>` (novo `OneToOneField`, bug 22).
4. Chamar `sync_loan_installments` para recalcular as parcelas seguintes a partir do novo saldo.

Excluir um `LoanPayment` (nova ação na tela de detalhe) reverte: restaura `current_balance` a partir do pagamento anterior, devolve a transação a "prevista" e re-sincroniza.

### 4.5 Entrada do dinheiro (opcional por empréstimo)

Novo campo `Loan.register_income` (bool, default `True` para empréstimos novos, `False` para os já existentes): ao cadastrar, cria uma `Transaction` RECEITA `origin=EMPRESTIMO`, categoria "Empréstimos" (`nature=DIVIDA`), no valor líquido recebido (principal − IOF), na `start_date`. Mesmo para `LoanDisbursement`. Sem isso o saldo fica artificialmente negativo: as parcelas saem mas o dinheiro nunca entrou.

KPIs de "Receitas" do dashboard mostram, por padrão, receitas **operacionais**; a entrada do empréstimo aparece separada no subtexto ("+ R$ 52.000 de empréstimo") para não parecer que o usuário ganhou mais naquele mês.

### 4.6 Tela de empréstimos

- `LoanListView`: sem N+1 (bug 24) — `annotate(total_paid=Sum("payments__amount_paid"))`, cronograma só de 1 linha por empréstimo.
- Nova coluna "Parcela deste mês" e "Próximo vencimento".
- Detalhe: cronograma completo com status por linha (paga / prevista / atrasada), botão "Pagar esta parcela" pré-preenchido.
- Matemática de amortização migrada para `Decimal` (bug 23), mantendo as funções puras e testáveis.

### 4.7 Migração do empréstimo existente

Data migration: para cada `Loan` ativo, rodar `sync_loan_installments` (gera as parcelas previstas do empréstimo de R$ 52.000 a partir de hoje). Transações antigas da categoria "Pagamento de Empréstimo" recebem `origin=EMPRESTIMO` (sem `loan` — não há como saber qual, a não ser que o usuário tenha um só empréstimo; nesse caso vincular).

---

## 5. Fluxo de caixa (P7)

Objetivo: o usuário abre a tela e entende, em 10 segundos, **quanto tem hoje, quanto vai ter no fim de cada mês, e por quê**.

### 5.1 Modelo de cálculo (corrige bugs 1–4)

Para cada mês *M* no horizonte (mês atual + N meses, N = 1..12):

```
Saldo inicial(M)       = saldo realizado até o fim de M-1   (para M = mês atual: saldo em 1º do mês)
+ Entradas certas(M)   = receitas já lançadas com data em M (recorrentes, manuais futuras, entrada de empréstimo)
+ Entradas estimadas(M)= receita variável estimada (ver abaixo) — só se o usuário não tiver receita recorrente cobrindo
− Saídas certas(M)     = despesas já lançadas em M, quebradas em:
                            • Cartão (parcelas)          origin=PARCELA
                            • Fixas (recorrentes)        origin=RECORRENTE
                            • Empréstimos                origin=EMPRESTIMO (+ cálculo além do teto de 24 meses)
                            • Outras já lançadas         MANUAL/IMPORTACAO com data em M
− Saídas estimadas(M)  = gasto variável estimado
= Saldo final(M)
```

- **Mês atual** é tratado de forma híbrida: o que já passou é realizado; do dia de hoje ao fim do mês entram os previstos certos + a parcela proporcional do gasto variável estimado (dias restantes ÷ dias do mês).
- **Gasto variável estimado** = mediana mensal (mais robusta que a média a um mês atípico) das despesas `origin in (MANUAL, IMPORTACAO)`, `nature=OPERACIONAL`, dos últimos 6 meses **realizados e cheios** (nunca meses futuros — bug 3). Com menos de 3 meses de histórico, usa o que houver e mostra aviso "estimativa com pouco histórico".
- **Recorrências além do teto de materialização**: projetadas por data real a partir de `RecurringTransaction` (respeitando `end_date` e frequência), não por "equivalente mensal". Nunca somadas quando já existe a transação materializada (checagem por `recurring_source` + mês) → fim da dupla contagem (bug 2).
- **Saldo "hoje"** = só `date <= hoje` (bug 1).

Tudo implementado em `core/services_cashflow.py::build_forecast(user, horizon, scenario) -> Forecast` (dataclass), sem acesso a `request`, 100% testável. A view só renderiza.

### 5.2 Cenários

Seletor **Pessimista / Base / Otimista**:
- Base: gasto variável = mediana.
- Pessimista: gasto variável = percentil 75 dos 6 meses; receitas estimadas × 0,9.
- Otimista: gasto variável = percentil 25.
Os lançamentos certos (parcelas, fixas, empréstimos) não mudam entre cenários — só a parte estimada. O gráfico principal pode mostrar os três como faixa (banda entre pessimista e otimista, linha base no meio).

### 5.3 Tela

**Cabeçalho**: horizonte (1, 3, 6, 12 meses — bug 7) · cenário · toggle "Incluir empréstimos".

**Cards de resumo** (corrige bug 5):
1. Saldo hoje.
2. Saldo no fim do horizonte (cenário selecionado) com variação.
3. **Menor saldo previsto** — valor e data ("R$ −430 em 10/12"); vermelho se negativo. É a informação mais acionável da tela.
4. Economia mensal média prevista (entradas − saídas) / mês.
5. % da renda já comprometida nos próximos 3 meses (saídas certas ÷ entradas previstas).

**Gráfico principal**: saldo diário do mês atual + saldo de fim de mês dos meses seguintes; realizado em linha sólida, previsto tracejado, banda de cenários, linha zero destacada, marcadores nos dias de vencimento grandes (> 10% da renda). Tooltip mostra os lançamentos do dia.

**Gráfico de composição**: barras empilhadas por mês — saídas por grupo (Cartão, Fixas, Empréstimos, Variável estimado, Outras) contra a linha de entradas. Mostra visualmente *de onde vem* o aperto.

**Tabela mês a mês** (o "extrato do futuro"), uma linha por mês, colunas:

| Mês | Saldo inicial | Entradas | Cartão | Fixas | Empréstimos | Variável (est.) | Outras | Saldo final |
|-----|---------------|----------|--------|-------|-------------|-----------------|--------|-------------|

- Cada linha expansível (`<details>`) lista os lançamentos certos daquele mês (descrição, data, valor), com link para editar.
- Células estimadas em itálico com ícone ⓘ e tooltip "estimado pela mediana dos últimos 6 meses".
- Saldo final negativo em vermelho com ícone de alerta.

**Seção "Como calculamos"** (colapsável, linguagem simples, substitui o alerta de rodapé duplicado — bug 6): explica saldo inicial, o que é "certo" vs. "estimado", de quais meses veio a mediana, e quantos lançamentos entraram em cada grupo.

**Seção "Histórico"**: últimos 6 meses realizados, mesmas colunas — permite comparar "previsto × aconteceu" quando o mês fecha. (Fase posterior: guardar snapshot da previsão para medir acurácia — Q4.)

### 5.4 Técnica

- Remover `<script src=chart.js>` duplicado (bug 8); usar `chartTheme()` e `json_script`.
- JS em `static/js/cashflow.js`.
- Cálculo com `Decimal`; conversão para `float` só no JSON dos gráficos.
- Limite de queries: agrupar por mês/origem numa query (`values("month","origin","type").annotate(Sum)`), 1 query para recorrências, 1 para empréstimos.

---

## 6. Testes

Novos arquivos (padrão atual `core/tests_*.py`, `python manage.py test core`):

| Arquivo | Cobertura mínima |
|---------|------------------|
| `tests_analytics.py` | `TxFilter.from_request` (datas inválidas, id de categoria de outro usuário, presets, expansão de subcategorias); `kpis` (valores exatos, período anterior); `recent` (ordem por `created_at`, agrupamento de parcelas, independente do mês). |
| `tests_dashboard.py` (ampliar) | Atividades mostram o último lançado mesmo com parcelas futuras maiores no mês (**regressão de P1**); filtros aplicam a KPIs; toggle empréstimos; `assertNumQueries`. |
| `tests_transactions.py` (ampliar) | KPIs refletem todas as páginas; painel de categoria com subcategorias e %; ordenação estável; paginação preserva filtros; querystring inválida não gera 500; parcelamento soma exatamente o total (100/3); editar/excluir "esta e as próximas". |
| `tests_loans.py` (novo) | `sync_loan_installments` por modalidade (PRICE, SAC, SIMPLES 60x, REDUCAO_SALDO); idempotência; pagamento reconcilia a parcela prevista (sem duplicar); excluir pagamento reverte; add funds recalcula; parcelas aparecem nas despesas do mês; entrada do empréstimo como receita. |
| `tests_cashflow.py` (novo) | Saldo hoje ignora futuro; sem dupla contagem recorrente materializada × projetada; mediana ignora meses futuros; mês atual híbrido; menor saldo previsto; cenários só alteram a parte estimada; horizonte 12. |
| `tests_migrations.py` (novo) | Backfill de `origin`/`installment_group` a partir de descrições reais ("Geladeira (3/10)", "(Recorrente)"). |

Todas as datas nos testes com "hoje" congelado (patch de `core.dates.today`).

---

## 7. Plano de entrega (fases)

Cada fase é mergeável e deixa o app funcionando.

| Fase | Conteúdo | Resolve |
|------|----------|---------|
| **F1 — Fundações** | §1 inteiro: migrations + backfill, `analytics.py`, `dates.py`, `money.py`, `localdate`. Sem mudança visual além de "Atividades" usando `created_at`. | P1, bugs 10, 14, 19 |
| **F2 — Transações** | §3: `TxFilter` na lista, KPIs, painel de categoria, ordenação, presets, ações de parcelas/recorrências, exportação filtrada. | P5, P6, bugs 15–18, 20 |
| **F3 — Empréstimos** | §4: parcelas materializadas, reconciliação de pagamento, entrada como receita, Decimal, sem N+1. | P2, bugs 21–24 |
| **F4 — Dashboard** | §2: filtros, KPIs novos, posição patrimonial, 7 gráficos, alertas, "Últimos lançamentos" com abas. | P3, P4, P5 (dashboard), bugs 11–13, 25 |
| **F5 — Fluxo de caixa** | §5: `services_cashflow`, cenários, tabela por grupo, gráficos, "como calculamos". | P7, bugs 1–9 |
| **F6 — Acabamento** | Atualizar `finanças/CLAUDE.md` (modelos reais, novos módulos), `MANUAL.md` (como ler o fluxo de caixa, como funcionam as parcelas de empréstimo), revisão de acessibilidade dos novos filtros/gráficos (labels, `aria-*`, contraste no tema escuro). | — |

Ordem pensada para: F1 destrava tudo; F2 e F3 são independentes entre si; F4 depende de F1+F3 (precisa das parcelas de empréstimo para os totais); F5 depende de F1+F3.

**Backup antes de migrar**: F1 e F3 alteram dados de produção (`patrimonio.db`). Rodar `backup.bat` antes de aplicar as migrations e registrar isso no passo a passo da fase.

---

## 8. Recomendações adicionais (não pedidas, fora das fases acima)

Registradas para decisão futura; nenhuma é necessária para P1–P7.

1. **Saldo de contas derivado das transações** (bug 26): `BankAccount.balance` passa a ser saldo inicial + Σ transações da conta; transferências geram par de lançamentos `nature=INVESTIMENTO`-like ("movimentação") que não contam como receita/despesa. Permite "saldo por conta" no dashboard e conciliação com extrato.
2. **Status pago/pendente manual** (Q1) com "contas a pagar vencidas".
3. **Fatura do cartão**: agrupar parcelas por fatura (dia de fechamento/vencimento do cartão) em vez de por data de compra — mostra o valor real que sai da conta em cada mês.
4. **Snapshot mensal da previsão** para comparar previsto × realizado (acurácia do fluxo de caixa).
5. **Regras de categorização automática** na importação (descrição contém "IFOOD" → Alimentação).
6. **Metas ligadas ao fluxo**: aporte mensal planejado de metas entra como saída "Metas" no fluxo de caixa.

---

## 9. Perguntas em aberto

| # | Pergunta | Default adotado se não houver resposta |
|---|----------|----------------------------------------|
| Q1 | Quer marcar manualmente lançamentos como pagos/não pagos? | Não; realizado = data ≤ hoje. |
| Q2 | O valor recebido do empréstimo de R$ 52.000 já existente deve entrar como receita retroativa na data de início? | Não para o existente (`register_income=False`); sim para novos. |
| Q3 | Parcelas de empréstimo numa categoria única "Empréstimos" ou uma subcategoria por empréstimo? | Categoria única; o filtro por empréstimo específico fica em `origin`+`loan` na tela de transações. |
| Q4 | Aportes em investimento devem sair das despesas por padrão? | Sim (toggle desligado); continuam visíveis com o toggle ligado e na tela de investimentos. |
| Q5 | "Últimos lançamentos" deve respeitar o mês navegado ou ser um feed global? | Feed global (o que foi lançado por último, independente do mês). |

---

## 10. Arquivos afetados (estimativa)

**Novos:** `core/analytics.py`, `core/dates.py`, `core/money.py`, `core/services_loans.py`, `core/services_cashflow.py`, `core/migrations/00xx_*` (3–4), `templates/core/dashboard/_*.html` (6), `templates/core/_category_insight.html`, `templates/core/_tx_filters.html`, `static/js/dashboard.js`, `static/js/cashflow.js`, `static/js/transactions.js`, testes (§6).

**Alterados:** `core/models.py`, `core/forms.py`, `core/services.py`, `core/views_dashboard.py`, `core/views_transactions.py`, `core/views_loans.py`, `core/views_cashflow.py`, `core/views_reports.py` (exportações aceitam `TxFilter`), `core/urls.py`, `templates/core/dashboard.html`, `transaction_list.html`, `cash_flow.html`, `loan_list.html`, `loan_detail.html`, `form.html` (parcelas/optgroup), `static/css/custom.css`, `static/js/charts.js` (paleta de categorias, helper de linha tracejada/banda), `finanças/CLAUDE.md`, `MANUAL.md`.
