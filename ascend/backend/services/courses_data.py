from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Section:
    heading: str
    body: str
    code: str = ""
    lang: str = "sql"


@dataclass
class Lesson:
    id: str
    title: str
    duration_min: int
    intro: str
    sections: list[Section]
    exercise: str = ""
    takeaway: str = ""


@dataclass
class Module:
    id: str
    title: str
    description: str
    lessons: list[Lesson]


@dataclass
class Course:
    id: str
    title: str
    tagline: str
    description: str
    level: str
    category: str
    duration_hours: int
    skills: list[str]
    color: str
    modules: list[Module]


# ─────────────────────────────────────────────────────────────────────────────
# CURSO 1 — SQL DO ZERO AO AVANÇADO
# ─────────────────────────────────────────────────────────────────────────────
SQL_COURSE = Course(
    id="sql-fundamentals",
    title="SQL: Do Zero ao Avançado",
    tagline="Domine a linguagem mais importante de dados em 20 horas",
    description="Do SELECT básico às window functions e otimização de queries. Aprenda SQL de forma prática com exercícios reais.",
    level="Iniciante → Avançado",
    category="Data",
    duration_hours=20,
    skills=["SQL", "PostgreSQL", "Query Optimization", "Window Functions"],
    color="#00e87a",
    modules=[
        Module("sql-m1", "Fundamentos de Banco de Dados Relacional", "Entenda como os dados são organizados em tabelas e como bancos relacionais funcionam.", [
            Lesson("sql-m1-l1", "O que é um Banco de Dados Relacional?", 15,
                "Bancos de dados relacionais são a espinha dorsal de praticamente todo sistema moderno. Entender sua estrutura é o primeiro passo para trabalhar com dados.",
                [
                    Section("Tabelas, Linhas e Colunas",
                        "Um banco relacional organiza dados em tabelas. Cada tabela tem colunas (atributos) e linhas (registros). Pense numa planilha Excel, mas com superpoderes: consistência garantida, relacionamentos entre tabelas e capacidade de processar milhões de registros.",
                        "-- Exemplo: tabela de clientes\nid | nome          | email              | cidade\n---|---------------|--------------------|----------\n 1 | Ana Silva     | ana@email.com      | São Paulo\n 2 | Carlos Mendes | carlos@email.com   | Rio de Janeiro", "sql"),
                    Section("Chaves Primárias e Estrangeiras",
                        "A chave primária (PRIMARY KEY) identifica unicamente cada linha — como o CPF de uma pessoa. A chave estrangeira (FOREIGN KEY) cria o relacionamento entre tabelas: a tabela de pedidos referencia o id do cliente, garantindo que não existe pedido sem cliente.",
                        "-- Relacionamento entre tabelas\nclientes (id, nome, email)         -- tabela pai\npedidos  (id, cliente_id, valor)   -- tabela filha\n--              ↑\n--   FK referencia clientes.id", "sql"),
                    Section("SGBD: PostgreSQL vs MySQL vs SQLite",
                        "PostgreSQL é o padrão ouro para análise de dados: gratuito, robusto, com excelente suporte a tipos avançados e window functions. MySQL é popular em web apps. SQLite é embutido e ideal para protótipos e apps mobile. Neste curso usaremos sintaxe padrão SQL que funciona em todos.",
                        "-- PostgreSQL: versão\nSELECT version();\n\n-- SQLite: versão\nSELECT sqlite_version();", "sql"),
                ],
                exercise="Desenhe (no papel) o modelo de um banco para uma biblioteca: livros, autores e empréstimos. Quais são as PKs e FKs?",
                takeaway="Bancos relacionais organizam dados em tabelas com relacionamentos explícitos — isso garante consistência e permite consultas poderosas."
            ),
            Lesson("sql-m1-l2", "Seu Primeiro SELECT", 20,
                "O SELECT é a fundação de tudo em SQL. Vamos do mais simples ao uso de filtros e ordenação.",
                [
                    Section("SELECT e FROM",
                        "SELECT especifica quais colunas você quer ver. FROM indica de qual tabela. O asterisco (*) seleciona todas as colunas — útil para explorar, mas evite em produção (traz colunas desnecessárias e quebra quando a tabela muda).",
                        "-- Selecionar tudo\nSELECT * FROM clientes;\n\n-- Selecionar colunas específicas\nSELECT nome, email FROM clientes;\n\n-- Alias para renomear colunas\nSELECT nome AS cliente, email AS contato FROM clientes;", "sql"),
                    Section("WHERE: Filtrando Dados",
                        "WHERE filtra as linhas que atendem a uma condição. Você pode combinar condições com AND, OR e NOT. Use parênteses para deixar a lógica explícita e evitar surpresas.",
                        "-- Clientes de São Paulo\nSELECT * FROM clientes WHERE cidade = 'São Paulo';\n\n-- Múltiplas condições\nSELECT * FROM pedidos\nWHERE valor > 100 AND status = 'aprovado';\n\n-- IN: lista de valores\nSELECT * FROM clientes\nWHERE cidade IN ('São Paulo', 'Rio de Janeiro', 'Curitiba');", "sql"),
                    Section("ORDER BY e LIMIT",
                        "ORDER BY ordena o resultado — ASC (crescente, padrão) ou DESC (decrescente). LIMIT restringe o número de linhas retornadas. Em PostgreSQL, use FETCH FIRST para o padrão SQL.",
                        "-- Top 5 pedidos por valor\nSELECT * FROM pedidos\nORDER BY valor DESC\nLIMIT 5;\n\n-- Paginação: página 2 de 10 registros\nSELECT * FROM produtos\nORDER BY nome\nLIMIT 10 OFFSET 10;", "sql"),
                ],
                exercise="Escreva uma query que busca todos os pedidos com valor acima de R$500, aprovados, ordenados do mais recente ao mais antigo.",
                takeaway="SELECT + WHERE + ORDER BY + LIMIT é o conjunto básico que resolve 80% das consultas do dia a dia."
            ),
            Lesson("sql-m1-l3", "Tipos de Dados e NULL", 18,
                "Escolher o tipo certo de dado afeta performance, espaço e integridade. E entender NULL é crucial para evitar bugs silenciosos.",
                [
                    Section("Principais Tipos de Dados",
                        "INTEGER/BIGINT para números inteiros. DECIMAL/NUMERIC para valores monetários (nunca use FLOAT para dinheiro — perde precisão). VARCHAR(n) para texto variável. DATE, TIMESTAMP para datas. BOOLEAN para verdadeiro/falso. TEXT para textos longos sem limite.",
                        "CREATE TABLE produtos (\n  id         BIGINT PRIMARY KEY,\n  nome       VARCHAR(200) NOT NULL,\n  preco      DECIMAL(10, 2) NOT NULL,  -- 10 dígitos, 2 decimais\n  em_estoque BOOLEAN DEFAULT true,\n  criado_em  TIMESTAMP DEFAULT NOW()\n);", "sql"),
                    Section("NULL: O Valor Ausente",
                        "NULL significa 'valor desconhecido ou ausente' — não é zero, não é string vazia. Comparações com NULL nunca retornam true: NULL = NULL é NULL, não true. Use IS NULL e IS NOT NULL para verificar nulidade. A função COALESCE retorna o primeiro valor não-nulo.",
                        "-- ERRADO: isso nunca retorna linhas!\nSELECT * FROM clientes WHERE telefone = NULL;\n\n-- CERTO\nSELECT * FROM clientes WHERE telefone IS NULL;\n\n-- COALESCE: substitui NULL por um padrão\nSELECT nome, COALESCE(telefone, 'sem telefone') AS contato\nFROM clientes;", "sql"),
                    Section("CAST e Conversão de Tipos",
                        "CAST converte um valor de um tipo para outro. Use quando precisar comparar ou operar tipos diferentes. O operador :: é o atalho do PostgreSQL para CAST.",
                        "-- Converter string para número\nSELECT CAST('42' AS INTEGER);\nSELECT '42'::INTEGER;  -- sintaxe PostgreSQL\n\n-- Formatar data\nSELECT CAST(NOW() AS DATE);\nSELECT TO_CHAR(NOW(), 'DD/MM/YYYY');", "sql"),
                ],
                exercise="Por que nunca devemos usar FLOAT para armazenar preços? Teste: SELECT 0.1 + 0.2 no seu banco e observe o resultado.",
                takeaway="NULL não é zero nem vazio — é a ausência de informação. Sempre trate NULLs explicitamente com IS NULL e COALESCE."
            ),
        ]),
        Module("sql-m2", "Agregações e Agrupamentos", "Aprenda a sumarizar dados com GROUP BY, COUNT, SUM e funções analíticas.", [
            Lesson("sql-m2-l1", "Funções de Agregação", 20,
                "Funções de agregação calculam um único valor a partir de múltiplas linhas. São a base de todo relatório e dashboard.",
                [
                    Section("COUNT, SUM, AVG, MIN, MAX",
                        "COUNT(*) conta todas as linhas incluindo NULLs. COUNT(coluna) conta apenas valores não-nulos. SUM soma valores numéricos. AVG calcula a média. MIN e MAX encontram o menor e maior valor.",
                        "SELECT\n  COUNT(*)          AS total_pedidos,\n  COUNT(desconto)   AS pedidos_com_desconto,  -- ignora NULLs\n  SUM(valor)        AS faturamento_total,\n  AVG(valor)        AS ticket_medio,\n  MIN(valor)        AS menor_pedido,\n  MAX(valor)        AS maior_pedido\nFROM pedidos\nWHERE status = 'aprovado';", "sql"),
                    Section("GROUP BY: Agregando por Categoria",
                        "GROUP BY divide as linhas em grupos e aplica a função de agregação a cada grupo. Toda coluna no SELECT que não é uma função de agregação DEVE estar no GROUP BY.",
                        "-- Faturamento por cidade\nSELECT\n  cidade,\n  COUNT(*)   AS total_clientes,\n  SUM(valor) AS faturamento\nFROM clientes\nJOIN pedidos ON clientes.id = pedidos.cliente_id\nGROUP BY cidade\nORDER BY faturamento DESC;", "sql"),
                    Section("HAVING: Filtrando Grupos",
                        "WHERE filtra linhas antes da agregação. HAVING filtra grupos depois da agregação. A ordem de execução é: FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT.",
                        "-- Cidades com faturamento acima de R$10.000\nSELECT cidade, SUM(valor) AS faturamento\nFROM clientes\nJOIN pedidos ON clientes.id = pedidos.cliente_id\nGROUP BY cidade\nHAVING SUM(valor) > 10000\nORDER BY faturamento DESC;", "sql"),
                ],
                exercise="Qual a diferença entre WHERE e HAVING? Escreva uma query que mostra produtos com mais de 50 vendas e ticket médio acima de R$200.",
                takeaway="A ordem de execução SQL (FROM→WHERE→GROUP BY→HAVING→SELECT→ORDER BY) determina o que pode ser filtrado onde."
            ),
            Lesson("sql-m2-l2", "Window Functions", 25,
                "Window functions são as funções mais poderosas do SQL analítico. Calculam valores sobre uma 'janela' de linhas sem colapsar o resultado como GROUP BY.",
                [
                    Section("ROW_NUMBER, RANK, DENSE_RANK",
                        "ROW_NUMBER atribui um número único a cada linha. RANK dá o mesmo número para empates mas pula o próximo. DENSE_RANK não pula. A cláusula OVER define a janela com PARTITION BY (agrupa) e ORDER BY (ordena dentro do grupo).",
                        "SELECT\n  nome,\n  cidade,\n  valor,\n  ROW_NUMBER() OVER (PARTITION BY cidade ORDER BY valor DESC) AS posicao,\n  RANK()       OVER (PARTITION BY cidade ORDER BY valor DESC) AS rank,\n  DENSE_RANK() OVER (PARTITION BY cidade ORDER BY valor DESC) AS dense_rank\nFROM vendas;", "sql"),
                    Section("LAG, LEAD e Diferenças Temporais",
                        "LAG acessa o valor da linha anterior. LEAD acessa o próximo. São ideais para calcular variação entre períodos (MoM, YoY) sem fazer self-join.",
                        "-- Variação de faturamento mês a mês\nSELECT\n  mes,\n  faturamento,\n  LAG(faturamento) OVER (ORDER BY mes)          AS mes_anterior,\n  faturamento - LAG(faturamento) OVER (ORDER BY mes) AS variacao,\n  ROUND(100.0 * (faturamento - LAG(faturamento) OVER (ORDER BY mes))\n        / LAG(faturamento) OVER (ORDER BY mes), 1) AS variacao_pct\nFROM faturamento_mensal;", "sql"),
                    Section("SUM e AVG como Window Functions",
                        "Qualquer função de agregação pode ser usada como window function com OVER. Isso permite calcular totais acumulados (running total) sem GROUP BY.",
                        "-- Total acumulado de vendas\nSELECT\n  data_venda,\n  valor,\n  SUM(valor) OVER (ORDER BY data_venda) AS acumulado,\n  AVG(valor) OVER (\n    ORDER BY data_venda\n    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW\n  ) AS media_movel_7dias\nFROM vendas;", "sql"),
                ],
                exercise="Escreva uma query que lista os top 3 vendedores por região usando DENSE_RANK e filtra apenas o top 3 de cada região.",
                takeaway="Window functions permitem análises analíticas complexas em uma única query — são o diferencial de um analista de dados avançado."
            ),
            Lesson("sql-m2-l3", "CTEs e Subqueries", 22,
                "CTEs (Common Table Expressions) e subqueries permitem dividir queries complexas em partes legíveis e reutilizáveis.",
                [
                    Section("Subqueries: Query dentro de Query",
                        "Uma subquery é uma query aninhada dentro de outra. Pode aparecer no SELECT (scalar subquery), no FROM (derived table) ou no WHERE (existência ou comparação). Subqueries correlacionadas referenciam a query externa e rodam linha por linha — podem ser lentas.",
                        "-- Subquery no WHERE: clientes que fizeram pedido acima da média\nSELECT nome FROM clientes\nWHERE id IN (\n  SELECT cliente_id FROM pedidos\n  WHERE valor > (SELECT AVG(valor) FROM pedidos)\n);\n\n-- Derived table no FROM\nSELECT cidade, avg_valor\nFROM (\n  SELECT cidade, AVG(valor) AS avg_valor\n  FROM pedidos JOIN clientes ON ...\n  GROUP BY cidade\n) AS resumo_cidades\nWHERE avg_valor > 500;", "sql"),
                    Section("CTEs com WITH",
                        "CTEs tornam queries complexas legíveis. Defina com WITH nome AS (...) antes do SELECT principal. CTEs podem referenciar outras CTEs definidas antes delas no mesmo bloco.",
                        "WITH vendas_aprovadas AS (\n  SELECT * FROM pedidos WHERE status = 'aprovado'\n),\nresultado_por_cliente AS (\n  SELECT\n    cliente_id,\n    COUNT(*)   AS total_pedidos,\n    SUM(valor) AS total_gasto\n  FROM vendas_aprovadas\n  GROUP BY cliente_id\n)\nSELECT\n  c.nome,\n  r.total_pedidos,\n  r.total_gasto\nFROM resultado_por_cliente r\nJOIN clientes c ON c.id = r.cliente_id\nORDER BY r.total_gasto DESC;", "sql"),
                    Section("CTEs Recursivas",
                        "CTEs recursivas permitem consultar hierarquias (organogramas, categorias aninhadas, grafos). Têm uma parte base (âncora) e uma parte recursiva unida com UNION ALL.",
                        "-- Hierarquia de funcionários\nWITH RECURSIVE hierarquia AS (\n  -- âncora: CEO (sem gerente)\n  SELECT id, nome, gerente_id, 0 AS nivel\n  FROM funcionarios WHERE gerente_id IS NULL\n\n  UNION ALL\n\n  -- recursivo: subordinados\n  SELECT f.id, f.nome, f.gerente_id, h.nivel + 1\n  FROM funcionarios f\n  JOIN hierarquia h ON f.gerente_id = h.id\n)\nSELECT nivel, nome FROM hierarquia ORDER BY nivel;", "sql"),
                ],
                exercise="Reescreva uma subquery complexa usando CTE. Qual é mais legível? Quando uma é preferível à outra?",
                takeaway="CTEs são subqueries com nome — tornam código SQL complexo legível e manutenível. Prefira CTEs a subqueries aninhadas."
            ),
        ]),
        Module("sql-m3", "JOINs e Relacionamentos", "Combine dados de múltiplas tabelas com precisão cirúrgica.", [
            Lesson("sql-m3-l1", "INNER, LEFT, RIGHT e FULL JOIN", 25,
                "JOINs combinam linhas de duas ou mais tabelas. Entender qual tipo usar em cada situação é fundamental para obter o resultado correto.",
                [
                    Section("INNER JOIN: Apenas Correspondências",
                        "INNER JOIN retorna apenas linhas que têm correspondência em ambas as tabelas. É o JOIN mais comum. Se um cliente não tem pedido, ele não aparece no resultado.",
                        "-- Pedidos com dados do cliente\nSELECT\n  c.nome,\n  p.id AS pedido_id,\n  p.valor,\n  p.data_pedido\nFROM pedidos p\nINNER JOIN clientes c ON p.cliente_id = c.id\nWHERE p.status = 'aprovado';", "sql"),
                    Section("LEFT JOIN: Todos da Esquerda",
                        "LEFT JOIN retorna todas as linhas da tabela da esquerda, mesmo sem correspondência na direita. Linhas sem match na direita têm NULL nos campos dela. Ideal para encontrar registros 'órfãos'.",
                        "-- Clientes com ou sem pedidos\nSELECT\n  c.nome,\n  COUNT(p.id) AS total_pedidos\nFROM clientes c\nLEFT JOIN pedidos p ON p.cliente_id = c.id\nGROUP BY c.id, c.nome;\n\n-- Clientes SEM nenhum pedido\nSELECT c.nome\nFROM clientes c\nLEFT JOIN pedidos p ON p.cliente_id = c.id\nWHERE p.id IS NULL;", "sql"),
                    Section("Múltiplos JOINs",
                        "Você pode encadear vários JOINs. A ordem importa para performance mas não para resultado. Aliases (c, p, pr) tornam o código legível.",
                        "SELECT\n  c.nome          AS cliente,\n  p.id            AS pedido,\n  pr.nome         AS produto,\n  ip.quantidade,\n  ip.preco_unit\nFROM pedidos p\nJOIN clientes c  ON c.id  = p.cliente_id\nJOIN itens_pedido ip ON ip.pedido_id = p.id\nJOIN produtos pr ON pr.id = ip.produto_id\nWHERE p.data_pedido >= '2024-01-01';", "sql"),
                ],
                exercise="Encontre todos os produtos que nunca foram vendidos usando LEFT JOIN e IS NULL.",
                takeaway="LEFT JOIN com IS NULL na tabela direita é o padrão para encontrar registros sem correspondência — muito mais eficiente que NOT IN com subquery."
            ),
            Lesson("sql-m3-l2", "Otimização de Queries e EXPLAIN", 28,
                "Uma query lenta pode travar seu sistema. Aprenda a diagnosticar e corrigir problemas de performance.",
                [
                    Section("EXPLAIN ANALYZE: Entendendo o Plano de Execução",
                        "EXPLAIN mostra como o banco pretende executar a query. EXPLAIN ANALYZE realmente executa e mostra tempos reais. Os números que mais importam: Seq Scan (varre a tabela inteira — pode ser lento), Index Scan (usa índice — rápido) e o custo total.",
                        "EXPLAIN ANALYZE\nSELECT * FROM pedidos\nWHERE cliente_id = 42 AND status = 'aprovado';\n\n-- Resultado típico:\n-- Seq Scan on pedidos (cost=0.00..1250.00 rows=3 width=64)\n--   Filter: ((cliente_id = 42) AND (status = 'aprovado'))\n-- Planning Time: 0.5 ms\n-- Execution Time: 45.2 ms  ← muito lento para 3 linhas!", "sql"),
                    Section("Índices: A Ferramenta de Performance",
                        "Um índice é uma estrutura de dados separada que o banco mantém para acelerar buscas — como o índice de um livro. CREATE INDEX na(s) coluna(s) mais usadas em WHERE, JOIN e ORDER BY. Mas índices custam espaço e tornam INSERTs/UPDATEs mais lentos.",
                        "-- Criar índice simples\nCREATE INDEX idx_pedidos_cliente ON pedidos(cliente_id);\n\n-- Índice composto (quando filtrar por dois campos juntos)\nCREATE INDEX idx_pedidos_status_data ON pedidos(status, data_pedido);\n\n-- Verificar índices de uma tabela\nSELECT indexname, indexdef\nFROM pg_indexes\nWHERE tablename = 'pedidos';", "sql"),
                    Section("Anti-padrões Comuns de Performance",
                        "SELECT * traz colunas desnecessárias. Funções em colunas de WHERE impedem uso de índices. LIKE '%texto' (começa com %) também não usa índice. N+1 queries (loop de queries) são destruidoras de performance.",
                        "-- RUIM: função na coluna impede índice\nSELECT * FROM pedidos WHERE YEAR(data_pedido) = 2024;\n\n-- BOM: range na coluna usa índice\nSELECT * FROM pedidos\nWHERE data_pedido BETWEEN '2024-01-01' AND '2024-12-31';\n\n-- RUIM: LIKE começa com %\nSELECT * FROM produtos WHERE nome LIKE '%camiseta%';\n-- Use full-text search para isso", "sql"),
                ],
                exercise="Pegue uma query lenta do seu projeto, rode EXPLAIN ANALYZE, identifique o Seq Scan e crie o índice adequado.",
                takeaway="Índices nas colunas usadas em WHERE e JOIN são a solução mais comum para queries lentas — mas meça antes e depois com EXPLAIN ANALYZE."
            ),
            Lesson("sql-m3-l3", "Transações e ACID", 20,
                "Transações garantem que operações críticas sejam atômicas: ou tudo funciona, ou nada acontece.",
                [
                    Section("BEGIN, COMMIT e ROLLBACK",
                        "Uma transação agrupa múltiplas operações. COMMIT persiste tudo. ROLLBACK desfaz tudo. Sem transação explícita, cada comando é auto-committed. SAVEPOINT permite rollback parcial.",
                        "-- Transferência bancária: duas operações devem ser atômicas\nBEGIN;\n\nUPDATE contas SET saldo = saldo - 1000 WHERE id = 1;  -- debita\nUPDATE contas SET saldo = saldo + 1000 WHERE id = 2;  -- credita\n\n-- Se tudo OK\nCOMMIT;\n\n-- Se algo deu errado\n-- ROLLBACK;", "sql"),
                    Section("ACID: As Garantias do Banco",
                        "Atomicidade: tudo ou nada. Consistência: o banco sempre vai de um estado válido a outro válido. Isolamento: transações simultâneas não se interferem. Durabilidade: após COMMIT, os dados sobrevivem a falhas. Esses são os pilares que tornam bancos relacionais confiáveis.",
                        "-- Demonstração de isolamento\n-- Sessão A:\nBEGIN;\nUPDATE produtos SET estoque = estoque - 1 WHERE id = 5;\n-- (ainda não deu COMMIT)\n\n-- Sessão B (ao mesmo tempo):\nSELECT estoque FROM produtos WHERE id = 5;\n-- Ainda vê o valor original (READ COMMITTED)", "sql"),
                    Section("Locks e Deadlocks",
                        "Transações adquirem locks para evitar conflitos. Um deadlock ocorre quando A espera B e B espera A — o banco detecta e mata uma das transações. Para evitar: acesse tabelas sempre na mesma ordem e mantenha transações curtas.",
                        "-- Forçar lock exclusivo (use com cuidado)\nSELECT * FROM produtos WHERE id = 5 FOR UPDATE;\n-- Essa linha agora está locked até o COMMIT/ROLLBACK\n\n-- Lock de tabela inteira (ainda mais cuidado)\nLOCK TABLE pedidos IN EXCLUSIVE MODE;", "sql"),
                ],
                exercise="Implemente uma transferência bancária que verifica saldo suficiente antes de debitar, com ROLLBACK se o saldo for insuficiente.",
                takeaway="Sempre use transações para operações que modificam múltiplas tabelas — ACID é o que diferencia um banco de dados de um arquivo CSV."
            ),
        ]),
        Module("sql-m4", "SQL Avançado e Casos Reais", "Técnicas avançadas usadas por engenheiros de dados seniores.", [
            Lesson("sql-m4-l1", "PIVOT, UNPIVOT e Dados Tabulares Cruzados", 22,
                "Transformar linhas em colunas (e vice-versa) é uma operação frequente em relatórios e dashboards.",
                [
                    Section("Pivot com CASE WHEN",
                        "SQL não tem um operador PIVOT padrão (exceto SQL Server). O padrão universal é usar CASE WHEN dentro de funções de agregação para 'girar' o resultado.",
                        "-- Vendas por mês em colunas\nSELECT\n  produto_id,\n  SUM(CASE WHEN mes = 1 THEN valor END) AS jan,\n  SUM(CASE WHEN mes = 2 THEN valor END) AS fev,\n  SUM(CASE WHEN mes = 3 THEN valor END) AS mar,\n  SUM(valor) AS total_tri\nFROM vendas\nWHERE ano = 2024\nGROUP BY produto_id;", "sql"),
                    Section("UNNEST e Arrays no PostgreSQL",
                        "PostgreSQL suporta colunas do tipo ARRAY. UNNEST transforma um array em linhas — útil para normalizar dados semi-estruturados vindos de APIs ou JSONs.",
                        "-- Expandir tags de um produto\nSELECT id, nome, UNNEST(tags) AS tag\nFROM produtos;\n\n-- JSON: extrair campo\nSELECT\n  id,\n  dados->>'nome' AS nome,\n  (dados->>'preco')::DECIMAL AS preco\nFROM produtos_json;", "sql"),
                    Section("GENERATE_SERIES: Criar Sequências",
                        "GENERATE_SERIES cria uma sequência de valores — perfeito para criar séries temporais com todos os dias/meses, mesmo que não haja dado naquele período.",
                        "-- Série de datas: todos os dias do mês\nSELECT generate_series(\n  '2024-01-01'::DATE,\n  '2024-01-31'::DATE,\n  '1 day'::INTERVAL\n)::DATE AS dia;\n\n-- Completar dias sem venda com zero\nSELECT\n  d.dia,\n  COALESCE(SUM(p.valor), 0) AS faturamento\nFROM generate_series('2024-01-01'::date, '2024-01-31'::date, '1 day') d(dia)\nLEFT JOIN pedidos p ON p.data_pedido::date = d.dia\nGROUP BY d.dia ORDER BY d.dia;", "sql"),
                ],
                exercise="Crie um relatório de vendas que mostra todos os dias de um mês, incluindo dias sem venda (mostrando 0), usando GENERATE_SERIES.",
                takeaway="GENERATE_SERIES é essencial para séries temporais completas — nunca deixe 'buracos' em relatórios por falta de dados naquele dia."
            ),
            Lesson("sql-m4-l2", "Views, Materialized Views e Stored Procedures", 25,
                "Views encapsulam queries complexas. Materialized views cachêam o resultado. Stored procedures executam lógica no banco.",
                [
                    Section("Views: Queries com Nome",
                        "Uma view é uma query salva que se comporta como uma tabela. Simplifica queries repetitivas, encapsula complexidade e pode ser usada para segurança (expor apenas algumas colunas).",
                        "-- Criar view de pedidos enriquecidos\nCREATE VIEW pedidos_completos AS\nSELECT\n  p.id,\n  c.nome AS cliente,\n  p.valor,\n  p.status,\n  p.data_pedido\nFROM pedidos p\nJOIN clientes c ON c.id = p.cliente_id;\n\n-- Usar como tabela normal\nSELECT * FROM pedidos_completos\nWHERE status = 'aprovado' AND data_pedido >= NOW() - INTERVAL '30 days';", "sql"),
                    Section("Materialized Views: Performance com Custo",
                        "Materialized views armazenam o resultado fisicamente. Queries são instantâneas, mas o dado pode ficar desatualizado. Use REFRESH para atualizar. Ideal para relatórios pesados que não precisam de dados em tempo real.",
                        "CREATE MATERIALIZED VIEW relatorio_mensal AS\nSELECT\n  DATE_TRUNC('month', data_pedido) AS mes,\n  COUNT(*) AS total_pedidos,\n  SUM(valor) AS faturamento\nFROM pedidos\nGROUP BY 1;\n\n-- Atualizar (pode ser agendado)\nREFRESH MATERIALIZED VIEW relatorio_mensal;\n\n-- Atualizar sem bloquear leituras\nREFRESH MATERIALIZED VIEW CONCURRENTLY relatorio_mensal;", "sql"),
                    Section("Funções e Stored Procedures",
                        "Funções retornam valores e podem ser usadas em queries. Stored procedures (PROCEDURE) executam lógica e podem fazer COMMIT/ROLLBACK. Use PL/pgSQL para lógica com IF, loops e tratamento de exceção.",
                        "-- Função: calcular desconto\nCREATE OR REPLACE FUNCTION calcular_desconto(valor DECIMAL, pct INT)\nRETURNS DECIMAL AS $$\nBEGIN\n  RETURN valor * (1 - pct / 100.0);\nEND;\n$$ LANGUAGE plpgsql;\n\n-- Usar na query\nSELECT nome, preco, calcular_desconto(preco, 15) AS preco_desconto\nFROM produtos;", "sql"),
                ],
                exercise="Crie uma view 'dashboard_vendas' que mostra, para cada vendedor: total de vendas, ticket médio e ranking por faturamento.",
                takeaway="Views organizam o acesso aos dados. Materialized views trocam atualidade por velocidade — escolha conforme a necessidade do relatório."
            ),
            Lesson("sql-m4-l3", "SQL para Data Engineering", 22,
                "Técnicas SQL usadas em pipelines de dados reais: upsert, particionamento, bulk operations.",
                [
                    Section("UPSERT com INSERT ON CONFLICT",
                        "Upsert significa 'insert ou update se já existe'. No PostgreSQL, use ON CONFLICT DO UPDATE. Fundamental em pipelines de dados onde você reprocessa dados sem duplicar.",
                        "-- Upsert: inserir ou atualizar produto\nINSERT INTO produtos (id, nome, preco, atualizado_em)\nVALUES (1, 'Camiseta', 59.90, NOW())\nON CONFLICT (id) DO UPDATE SET\n  nome         = EXCLUDED.nome,\n  preco        = EXCLUDED.preco,\n  atualizado_em = EXCLUDED.atualizado_em;\n\n-- Ignorar conflito (não atualizar)\nINSERT INTO eventos (id, tipo)\nVALUES (42, 'clique')\nON CONFLICT (id) DO NOTHING;", "sql"),
                    Section("Particionamento de Tabelas",
                        "Tabelas particionadas dividem dados grandes em partes menores (partições) por um critério (data, região). Queries que filtram pela coluna de partição tocam apenas as partições relevantes — drástica melhora de performance.",
                        "-- Criar tabela particionada por mês\nCREATE TABLE eventos (\n  id         BIGINT,\n  tipo       TEXT,\n  criado_em  TIMESTAMP\n) PARTITION BY RANGE (criado_em);\n\n-- Criar partição para jan/2024\nCREATE TABLE eventos_2024_01\n  PARTITION OF eventos\n  FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');", "sql"),
                    Section("COPY e Bulk Import",
                        "Para carregar grandes volumes de dados, o comando COPY é ordens de magnitude mais rápido que múltiplos INSERTs. Em Python, use psycopg2.copy_from() ou COPY com stdin.",
                        "-- Exportar para CSV\nCOPY pedidos TO '/tmp/pedidos.csv' WITH CSV HEADER;\n\n-- Importar de CSV (mais rápido que INSERT)\nCOPY pedidos FROM '/tmp/pedidos.csv' WITH CSV HEADER;\n\n-- Via psql (sem permissão de superusuário)\n\\COPY produtos FROM 'produtos.csv' WITH CSV HEADER;", "sql"),
                ],
                exercise="Crie uma pipeline de carga diária: importe um CSV de pedidos, faça upsert na tabela principal e atualize uma materialized view de relatório.",
                takeaway="UPSERT + particionamento + COPY são as três técnicas SQL que tornam pipelines de dados eficientes em escala."
            ),
        ]),
    ]
)

# ─────────────────────────────────────────────────────────────────────────────
# CURSO 2 — PYTHON PARA ANÁLISE DE DADOS
# ─────────────────────────────────────────────────────────────────────────────
PYTHON_DATA_COURSE = Course(
    id="python-data-analysis",
    title="Python para Análise de Dados",
    tagline="Pandas, visualização e estatística para tomar decisões com dados",
    description="Aprenda a manipular datasets reais com Pandas, criar visualizações profissionais e extrair insights estatísticos com Python.",
    level="Iniciante → Intermediário",
    category="Python",
    duration_hours=25,
    skills=["Python", "Pandas", "NumPy", "Matplotlib", "Seaborn", "Estatística"],
    color="#3b82f6",
    modules=[
        Module("py-m1", "Python Essencial para Dados", "Fundamentos de Python que você precisa para trabalhar com dados.", [
            Lesson("py-m1-l1", "Estruturas de Dados em Python", 20,
                "Listas, dicionários e compreensões são as ferramentas que você usará todos os dias na análise de dados.",
                [
                    Section("Listas e List Comprehensions",
                        "Listas são ordenadas e mutáveis. List comprehensions são a forma Pythônica de criar listas transformando ou filtrando outra iterável — mais rápidas e legíveis que loops for.",
                        "# Lista comum\nvendas = [1200, 850, 2300, 400, 1800]\n\n# List comprehension: filtrar e transformar\nvendas_altas = [v for v in vendas if v > 1000]\n# [1200, 2300, 1800]\n\n# Com transformação\nvendas_mil = [v / 1000 for v in vendas]\n# [1.2, 0.85, 2.3, 0.4, 1.8]\n\n# Aninhada: planilha de mês x produto\nmatriz = [[mes * prod for prod in range(1, 4)] for mes in range(1, 4)]", "python"),
                    Section("Dicionários e Conjuntos",
                        "Dicionários mapeiam chave → valor com acesso O(1). Conjuntos (set) armazenam elementos únicos e suportam operações de união, interseção e diferença — perfeitos para deduplicação.",
                        "# Dicionário de dados\ncliente = {'id': 1, 'nome': 'Ana', 'cidade': 'SP'}\n\n# Dict comprehension\nprecos = {'arroz': 5.5, 'feijao': 7.2, 'macarrao': 3.8}\ncom_taxa = {k: v * 1.12 for k, v in precos.items()}\n\n# Conjuntos para deduplicação\ncidades_vendas = {'SP', 'RJ', 'MG', 'SP', 'RS'}  # SP aparece 1x\ncidades_clientes = {'SP', 'RJ', 'GO'}\n\nem_ambos = cidades_vendas & cidades_clientes  # {'SP', 'RJ'}\napenas_vendas = cidades_vendas - cidades_clientes  # {'MG', 'RS'}", "python"),
                    Section("Funções e Lambda",
                        "Defina funções com def para lógica reutilizável. Lambda cria funções anônimas de uma linha — perfeito para passar como argumento a map, filter e métodos do Pandas.",
                        "def calcular_margem(receita, custo):\n    '''Calcula margem bruta em percentual.'''\n    if receita == 0:\n        return 0\n    return (receita - custo) / receita * 100\n\n# Lambda\ndobrar = lambda x: x * 2\n\n# Usar com map\nprecos = [10, 20, 30]\nprecos_dobro = list(map(lambda x: x * 2, precos))\n\n# Usar com sorted\nclientes.sort(key=lambda c: c['nome'])", "python"),
                ],
                exercise="Crie uma função que recebe uma lista de dicionários (vendas com data, produto, valor) e retorna um dicionário com o faturamento total por produto.",
                takeaway="Dominar listas, dicionários e comprehensions é o pré-requisito para trabalhar com Pandas — elas são a base de toda manipulação de dados em Python."
            ),
            Lesson("py-m1-l2", "NumPy: Computação Numérica", 22,
                "NumPy é a fundação do ecossistema científico Python. Arrays NumPy são 10-100x mais rápidos que listas para operações numéricas.",
                [
                    Section("Arrays e Operações Vetorizadas",
                        "Um ndarray NumPy opera em todos os elementos de uma vez (vetorização) sem precisar de loop — isso é fundamental para performance. Broadcasting permite operar arrays de shapes diferentes.",
                        "import numpy as np\n\n# Criar arrays\nvendas = np.array([1200, 850, 2300, 400, 1800])\ncustos = np.array([800, 600, 1500, 300, 1200])\n\n# Operações vetorizadas (sem loop!)\nlucros = vendas - custos  # array([400, 250, 800, 100, 600])\nmargens = lucros / vendas * 100\n\n# Estatísticas\nprint(f'Média: {vendas.mean():.0f}')\nprint(f'Desvio padrão: {vendas.std():.0f}')\nprint(f'Mediana: {np.median(vendas):.0f}')", "python"),
                    Section("Indexação e Slicing",
                        "Arrays NumPy suportam indexação booleana — filtrar com condições diretamente, sem loops. Slicing funciona como listas mas em múltiplas dimensões.",
                        "import numpy as np\n\nvalores = np.array([100, 250, 50, 800, 150, 30])\n\n# Indexação booleana\nacima_media = valores[valores > valores.mean()]\n# array([250, 800, 150])\n\n# Substituição condicional\nvalores_tratados = np.where(valores < 100, 0, valores)\n# Substitui valores abaixo de 100 por 0\n\n# Array 2D\nmatriz = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])\nprint(matriz[1, :])   # linha 1: [4, 5, 6]\nprint(matriz[:, 2])   # coluna 2: [3, 6, 9]", "python"),
                    Section("Álgebra Linear e Operações Matriciais",
                        "NumPy suporta multiplicação de matrizes, transposição e decomposições — base de modelos de ML. np.linalg contém funções de álgebra linear.",
                        "import numpy as np\n\n# Multiplicação de matrizes\nA = np.array([[1, 2], [3, 4]])\nB = np.array([[5, 6], [7, 8]])\nC = A @ B  # ou np.dot(A, B)\n\n# Transposição\nprint(A.T)\n\n# Gerar dados aleatórios (seed para reprodutibilidade)\nrng = np.random.default_rng(42)\ndados = rng.normal(loc=0, scale=1, size=1000)\nprint(f'Média: {dados.mean():.4f}, Desvio: {dados.std():.4f}')", "python"),
                ],
                exercise="Crie um array NumPy com 100 preços aleatórios entre R$10 e R$500. Calcule média, mediana, desvio padrão e quantos preços estão acima da média.",
                takeaway="NumPy transforma operações que seriam lentos loops Python em operações vetorizadas de C — é a diferença entre segundos e milissegundos."
            ),
            Lesson("py-m1-l3", "Pandas: Introdução ao DataFrame", 25,
                "O DataFrame é a estrutura central da análise de dados em Python. É como uma planilha Excel na memória, mas com superpoderes.",
                [
                    Section("Criar e Carregar DataFrames",
                        "DataFrames podem ser criados de dicionários, listas, arquivos CSV, bancos de dados e APIs. read_csv é a função mais usada no dia a dia.",
                        "import pandas as pd\n\n# De dicionário\ndf = pd.DataFrame({\n    'produto': ['Arroz', 'Feijão', 'Macarrão'],\n    'preco': [5.50, 7.20, 3.80],\n    'estoque': [100, 80, 150]\n})\n\n# De CSV (opções comuns)\ndf = pd.read_csv('vendas.csv',\n    sep=';',              # separador\n    encoding='utf-8',\n    parse_dates=['data'], # converter datas\n    decimal=','           # decimal brasileiro\n)\n\n# Inspecionar\nprint(df.shape)    # (linhas, colunas)\ndf.info()          # tipos e nulls\ndf.describe()      # estatísticas", "python"),
                    Section("Seleção e Filtragem",
                        "iloc seleciona por posição numérica. loc seleciona por label/condição. Máscaras booleanas filtram linhas. Encadeie condições com & (and) e | (or) — não use and/or Python!",
                        "# Selecionar coluna\ndf['produto']         # Series\ndf[['produto', 'preco']]  # DataFrame\n\n# Filtrar linhas\ncaros = df[df['preco'] > 5]\nem_falta = df[df['estoque'] < 50]\n\n# Múltiplas condições (parênteses obrigatórios!)\ndf[(df['preco'] > 5) & (df['estoque'] > 0)]\n\n# loc: label-based\ndf.loc[df['produto'] == 'Arroz', 'preco']\n\n# query: sintaxe mais legível\ndf.query('preco > 5 and estoque > 0')", "python"),
                    Section("Transformação e Novas Colunas",
                        "Crie colunas derivadas com operações vetorizadas. apply() aplica uma função linha a linha (mais lento). assign() cria colunas encadeando operações (estilo funcional).",
                        "# Nova coluna\ndf['valor_total'] = df['preco'] * df['estoque']\n\n# Categorizar com condição\ndf['status'] = pd.cut(\n    df['estoque'],\n    bins=[0, 50, 100, float('inf')],\n    labels=['Crítico', 'Normal', 'Alto']\n)\n\n# apply com função\ndf['nome_upper'] = df['produto'].apply(str.upper)\n\n# assign (encadeável)\ndf = (df\n    .assign(margem=lambda d: (d['preco'] - 2) / d['preco'])\n    .assign(rentavel=lambda d: d['margem'] > 0.3)\n)", "python"),
                ],
                exercise="Carregue um CSV de vendas, calcule o ticket médio por categoria de produto e filtre categorias com faturamento abaixo da média.",
                takeaway="DataFrame é o coração da análise em Python. Domine seleção com loc/iloc, filtragem booleana e criação de colunas derivadas."
            ),
        ]),
        Module("py-m2", "Limpeza e Transformação de Dados", "Dados reais são sujos. Aprenda a tratá-los sistematicamente.", [
            Lesson("py-m2-l1", "Tratamento de Dados Ausentes", 20,
                "Em datasets reais, dados ausentes são a regra, não a exceção. Uma estratégia de tratamento errada pode enviesar toda a análise.",
                [
                    Section("Detectar e Quantificar NaN",
                        "Pandas usa NaN (Not a Number) para valores ausentes em colunas numéricas e None/NaN em outras. isnull() retorna máscara booleana. Calcule a taxa de ausência por coluna para decidir a estratégia.",
                        "import pandas as pd\n\n# Visão geral de valores ausentes\ndf.isnull().sum()              # contagem por coluna\ndf.isnull().mean() * 100       # percentual por coluna\n\n# Visualizar padrão de ausência\nprint(df[df['preco'].isnull()])  # linhas com preco ausente\n\n# Heatmap de nulos (requer seaborn)\nimport seaborn as sns\nimport matplotlib.pyplot as plt\nsns.heatmap(df.isnull(), yticklabels=False, cbar=False)\nplt.show()", "python"),
                    Section("Estratégias de Preenchimento",
                        "Remover linhas (dropna) é simples mas perde dados. Preencher com média/mediana (fillna) é seguro para distribuições simétricas. Forward fill (ffill) funciona bem em séries temporais. Para dados categóricos, crie uma categoria 'Desconhecido'.",
                        "# Remover linhas com qualquer nulo\ndf_limpo = df.dropna()\n\n# Remover apenas se coluna crítica é nula\ndf_limpo = df.dropna(subset=['preco', 'cliente_id'])\n\n# Preencher com mediana (robusto a outliers)\ndf['preco'] = df['preco'].fillna(df['preco'].median())\n\n# Forward fill (séries temporais)\ndf['temperatura'] = df['temperatura'].ffill()\n\n# Categórico: categoria desconhecida\ndf['cidade'] = df['cidade'].fillna('Desconhecido')", "python"),
                    Section("Detecção e Tratamento de Outliers",
                        "Outliers podem ser erros (digitar 99999 em vez de 999) ou valores reais extremos. IQR é robusto: valores fora de 1.5×IQR são suspeitos. Z-score identifica valores além de 3 desvios padrão.",
                        "import numpy as np\n\n# Método IQR\nQ1 = df['valor'].quantile(0.25)\nQ3 = df['valor'].quantile(0.75)\nIQR = Q3 - Q1\n\nlimite_inf = Q1 - 1.5 * IQR\nlimite_sup = Q3 + 1.5 * IQR\n\ndf_sem_outliers = df[df['valor'].between(limite_inf, limite_sup)]\n\n# Z-score\nfrom scipy import stats\nz_scores = np.abs(stats.zscore(df['valor'].dropna()))\ndf_sem_outliers = df[z_scores < 3]", "python"),
                ],
                exercise="Dataset de vendas tem 15% de preços ausentes e 5% de valores negativos (erros). Defina e implemente uma estratégia de tratamento.",
                takeaway="Não existe uma estratégia universal para valores ausentes — a escolha depende do mecanismo que causa a ausência e do impacto no resultado."
            ),
            Lesson("py-m2-l2", "GroupBy e Pivotagem", 22,
                "Agrupar e pivotar dados é a operação mais comum em análise. Pandas torna isso expressivo e eficiente.",
                [
                    Section("GroupBy: Dividir, Aplicar, Combinar",
                        "O padrão Split-Apply-Combine: divide o DataFrame em grupos, aplica uma função a cada grupo, combina os resultados. Você pode aplicar múltiplas funções simultaneamente com agg().",
                        "# Uma função\ndf.groupby('categoria')['valor'].sum()\n\n# Múltiplas funções\nresultado = df.groupby('categoria').agg(\n    total_vendas=('valor', 'sum'),\n    ticket_medio=('valor', 'mean'),\n    num_pedidos=('id', 'count'),\n    maior_pedido=('valor', 'max')\n).reset_index()\n\n# Múltiplas colunas de agrupamento\ndf.groupby(['regiao', 'mes']).agg({'valor': 'sum'})", "python"),
                    Section("Pivot Tables",
                        "pivot_table() cria tabelas cruzadas — equivalente à Tabela Dinâmica do Excel. O resultado tem o índice como linhas e as colunas como colunas da tabela.",
                        "# Vendas por região e mês\ntabela = df.pivot_table(\n    values='valor',\n    index='regiao',\n    columns='mes',\n    aggfunc='sum',\n    fill_value=0\n)\n\nprint(tabela)\n# mes       jan    fev    mar\n# regiao\n# Norte    1200   900   1500\n# Sul      2300  1800   2100\n# Sudeste  4500  3900   5200\n\n# Normalizar por linha (% do total)\ntabela_pct = tabela.div(tabela.sum(axis=1), axis=0) * 100", "python"),
                    Section("merge e join entre DataFrames",
                        "merge() combina DataFrames como um SQL JOIN. Especifique on (coluna de chave), how (inner/left/right/outer). Pandas também tem join() para combinar por índice.",
                        "# Equivalente ao SQL INNER JOIN\ndf_completo = pd.merge(\n    df_pedidos,\n    df_clientes,\n    on='cliente_id',\n    how='left'  # mantém todos os pedidos\n)\n\n# JOIN com chaves com nomes diferentes\npd.merge(\n    df_pedidos,\n    df_clientes,\n    left_on='cli_id',\n    right_on='id',\n    how='inner'\n)\n\n# Concatenar DataFrames (empilhar)\ndf_total = pd.concat([df_jan, df_fev, df_mar], ignore_index=True)", "python"),
                ],
                exercise="Com um DataFrame de vendas (data, vendedor, produto, valor), crie uma tabela dinâmica de faturamento por vendedor × mês, com totais.",
                takeaway="GroupBy + agg() é o duo mais poderoso do Pandas. Domine a sintaxe de agg() nomeado para código legível e profissional."
            ),
            Lesson("py-m2-l3", "Datas e Séries Temporais", 20,
                "Analisar dados ao longo do tempo é uma das tarefas mais comuns. Pandas tem suporte nativo poderoso para datas.",
                [
                    Section("Parsing e Componentes de Data",
                        "parse_dates no read_csv converte strings para datetime automaticamente. to_datetime() converte manualmente. Acesse componentes com .dt: .dt.year, .dt.month, .dt.dayofweek.",
                        "import pandas as pd\n\n# Carregar com datas\ndf = pd.read_csv('vendas.csv', parse_dates=['data_venda'])\n\n# Converter manualmente\ndf['data'] = pd.to_datetime(df['data_str'], format='%d/%m/%Y')\n\n# Extrair componentes\ndf['ano'] = df['data'].dt.year\ndf['mes'] = df['data'].dt.month\ndf['dia_semana'] = df['data'].dt.day_name(locale='pt_BR.UTF-8')\ndf['semana'] = df['data'].dt.isocalendar().week\ndf['trimestre'] = df['data'].dt.quarter", "python"),
                    Section("Resample: Agregação Temporal",
                        "resample() agrupa dados por frequência temporal — como GROUP BY para datas. 'M' é mês, 'W' é semana, 'Q' é trimestre, 'Y' é ano.",
                        "# Faturamento mensal\ndf_mensal = (\n    df.set_index('data')\n    ['valor']\n    .resample('ME')  # Month End\n    .sum()\n    .reset_index()\n)\n\n# Múltiplas métricas por semana\ndf_semanal = (\n    df.set_index('data')\n    .resample('W')\n    .agg({'valor': 'sum', 'id': 'count'})\n    .rename(columns={'id': 'num_pedidos'})\n)", "python"),
                    Section("Rolling: Médias Móveis",
                        "rolling() aplica uma função em uma janela deslizante — perfeito para suavizar séries e calcular médias móveis.",
                        "df = df.set_index('data').sort_index()\n\n# Média móvel de 7 dias\ndf['media_movel_7d'] = df['valor'].rolling(window=7).mean()\n\n# Soma acumulada\ndf['acumulado'] = df['valor'].cumsum()\n\n# Variação percentual dia a dia\ndf['variacao_pct'] = df['valor'].pct_change() * 100\n\n# Preencher NaN inicial da janela\ndf['mm7'] = df['valor'].rolling(7, min_periods=1).mean()", "python"),
                ],
                exercise="Com dados de vendas diárias de um ano, crie: (1) faturamento mensal, (2) média móvel de 30 dias, (3) identifique o mês com maior crescimento MoM.",
                takeaway="resample() é o equivalente do GROUP BY temporal e rolling() calcula janelas deslizantes — dominá-los é essencial para análise de séries temporais."
            ),
        ]),
        Module("py-m3", "Visualização de Dados", "Crie gráficos profissionais que comunicam insights.", [
            Lesson("py-m3-l1", "Matplotlib e Seaborn", 25,
                "Matplotlib é o motor de visualização do Python. Seaborn torna gráficos estatísticos bonitos com poucas linhas de código.",
                [
                    Section("Matplotlib: Controle Total",
                        "Matplotlib usa uma hierarquia Figure → Axes. Figure é a 'tela'. Axes é o gráfico dentro dela. Você pode ter múltiplos Axes (subplots) em uma Figure.",
                        "import matplotlib.pyplot as plt\nimport numpy as np\n\nfig, axes = plt.subplots(1, 2, figsize=(12, 5))\n\n# Gráfico de linha\naxes[0].plot(meses, faturamento, marker='o', color='#00e87a', linewidth=2)\naxes[0].set_title('Faturamento Mensal', fontsize=14, fontweight='bold')\naxes[0].set_xlabel('Mês')\naxes[0].set_ylabel('R$ (mil)')\naxes[0].grid(True, alpha=0.3)\n\n# Gráfico de barras\naxes[1].bar(categorias, valores, color=['#3b82f6', '#8b5cf6', '#f59e0b'])\naxes[1].set_title('Vendas por Categoria')\n\nplt.tight_layout()\nplt.savefig('relatorio.png', dpi=300, bbox_inches='tight')\nplt.show()", "python"),
                    Section("Seaborn: Visualização Estatística",
                        "Seaborn é construído sobre Matplotlib e simplifica gráficos estatísticos. Integra diretamente com DataFrames Pandas.",
                        "import seaborn as sns\nimport matplotlib.pyplot as plt\n\nsns.set_theme(style='darkgrid', palette='husl')\n\nfig, axes = plt.subplots(2, 2, figsize=(14, 10))\n\n# Distribuição\nsns.histplot(df['valor'], kde=True, ax=axes[0, 0])\n\n# Correlação entre variáveis\nsns.scatterplot(data=df, x='preco', y='quantidade', hue='categoria', ax=axes[0, 1])\n\n# Boxplot por categoria\nsns.boxplot(data=df, x='categoria', y='valor', ax=axes[1, 0])\n\n# Mapa de calor de correlação\nsns.heatmap(df.corr(numeric_only=True), annot=True, fmt='.2f', ax=axes[1, 1])\n\nplt.tight_layout()", "python"),
                    Section("Gráficos Interativos com Plotly",
                        "Plotly cria gráficos interativos (hover, zoom, pan) para dashboards web. plotly.express é a API de alto nível — cria gráficos complexos com uma linha.",
                        "import plotly.express as px\n\n# Linha temporal interativa\nfig = px.line(\n    df_mensal, x='mes', y='faturamento',\n    title='Faturamento Mensal 2024',\n    labels={'faturamento': 'R$', 'mes': 'Mês'},\n    color_discrete_sequence=['#00e87a']\n)\nfig.update_layout(template='plotly_dark', height=400)\nfig.show()\n\n# Mapa coroplético\npx.choropleth(\n    df_estados, locations='estado', locationmode='geojson-id',\n    color='faturamento', scope='south america'\n)", "python"),
                ],
                exercise="Com dados de vendas mensais por categoria, crie um dashboard com: linha de faturamento total, barras por categoria e pie chart da participação.",
                takeaway="Matplotlib para controle máximo, Seaborn para gráficos estatísticos rápidos, Plotly para interatividade — escolha a ferramenta certa para cada contexto."
            ),
            Lesson("py-m3-l2", "Análise Exploratória (EDA) Sistemática", 28,
                "EDA é o processo de conhecer um dataset antes de modelar ou reportar. Seguir um processo sistemático evita vieses e surpresas.",
                [
                    Section("Perfil Inicial do Dataset",
                        "Comece sempre com o mesmo roteiro: shape, dtypes, describe(), isnull(), duplicated(). Isso revela a qualidade dos dados antes de qualquer análise.",
                        "def perfil_dataset(df):\n    print(f'Shape: {df.shape}')\n    print(f'\\nTipos:\\n{df.dtypes}')\n    print(f'\\nEstatísticas:\\n{df.describe()}')\n    print(f'\\nNulos:\\n{df.isnull().sum()[df.isnull().sum() > 0]}')\n    print(f'\\nDuplicatas: {df.duplicated().sum()}')\n    return df\n\n# Usar no início de cada análise\ndf = pd.read_csv('dados.csv').pipe(perfil_dataset)", "python"),
                    Section("Análise Univariada e Bivariada",
                        "Univariada: distribução de uma variável por vez (histograma, boxplot, value_counts). Bivariada: relação entre duas variáveis (scatter, groupby + plot, correlação). Sempre diferencie numéricas de categóricas.",
                        "# Univariada: numérica\ndf['valor'].hist(bins=30, figsize=(8, 4))\nprint(df['valor'].describe())\n\n# Univariada: categórica\ndf['status'].value_counts(normalize=True).plot(kind='bar')\n\n# Bivariada: categoria vs numérica\ndf.groupby('categoria')['valor'].mean().plot(kind='barh')\n\n# Bivariada: duas numéricas\nprint(df[['valor', 'quantidade', 'desconto']].corr())", "python"),
                    Section("Comunicar Descobertas",
                        "Uma análise sem comunicação vale zero. Use títulos descritivos (não 'Gráfico 1' — use 'Faturamento cai 30% em julho'), destaque o insight com anotações e mantenha o gráfico simples.",
                        "fig, ax = plt.subplots(figsize=(10, 5))\nax.plot(df['mes'], df['faturamento'])\n\n# Destaque o ponto de queda\nax.annotate(\n    'Queda de 30%\\n(greve de transportes)',\n    xy=(7, df.loc[df['mes']==7, 'faturamento'].values[0]),\n    xytext=(9, df['faturamento'].max() * 0.8),\n    arrowprops={'arrowstyle': '->', 'color': 'red'},\n    color='red', fontsize=10\n)\nax.set_title('Faturamento cai em julho por greve de transportes', fontsize=13)\nax.set_xlabel('')  # remover labels óbvios", "python"),
                ],
                exercise="Faça uma EDA completa de um dataset de sua escolha (Kaggle tem muitos). Documente 5 insights relevantes com gráficos que comunicam claramente.",
                takeaway="EDA é um processo, não um gráfico. Siga sempre o mesmo roteiro: shape → tipos → nulls → distribuições → correlações → insights."
            ),
            Lesson("py-m3-l3", "Estatística para Análise de Dados", 25,
                "Estatística é a linguagem dos dados. Entender distribuições, correlações e testes de hipótese é o que separa analistas de pessoas que olham planilhas.",
                [
                    Section("Distribuições e a Regra 68-95-99.7",
                        "Em uma distribuição normal, 68% dos dados estão a ±1σ, 95% a ±2σ, 99.7% a ±3σ. Use isso para identificar outliers (além de 3σ) e para comunicar variabilidade.",
                        "from scipy import stats\nimport numpy as np\n\n# Verificar normalidade\nstat, p_value = stats.shapiro(df['valor'].dropna())\nprint(f'Shapiro-Wilk: p={p_value:.4f}')\nif p_value > 0.05:\n    print('Distribuição provavelmente normal')\n\n# Intervalo de confiança 95%\nmedia = df['valor'].mean()\nse = stats.sem(df['valor'].dropna())\nic = stats.t.interval(0.95, df=len(df)-1, loc=media, scale=se)\nprint(f'IC 95%: ({ic[0]:.2f}, {ic[1]:.2f})')", "python"),
                    Section("Correlação: Pearson e Spearman",
                        "Correlação de Pearson mede relação linear (-1 a 1). Spearman mede relação monotônica (mais robusta a outliers e distribuições não-normais). Correlação não implica causalidade!",
                        "from scipy import stats\nimport pandas as pd\n\n# Pearson (relação linear)\ncoef, p_valor = stats.pearsonr(df['preco'], df['demanda'])\nprint(f'Pearson r={coef:.3f}, p={p_valor:.4f}')\n\n# Spearman (mais robusto)\ncoef_s, p_s = stats.spearmanr(df['preco'], df['demanda'])\nprint(f'Spearman ρ={coef_s:.3f}, p={p_s:.4f}')\n\n# Matriz de correlação\ncorr_matrix = df[['preco', 'demanda', 'marketing']].corr()\nprint(corr_matrix)", "python"),
                    Section("Testes de Hipótese",
                        "Teste de hipótese: será que a diferença que observamos é real ou é ruído estatístico? H0 (nula): não há diferença. Ha (alternativa): há diferença. p-valor < 0.05 rejeita H0.",
                        "from scipy import stats\n\n# Teste t: médias de dois grupos são diferentes?\ngrupo_a = df[df['campanha'] == 'A']['conversao']\ngrupo_b = df[df['campanha'] == 'B']['conversao']\n\nt_stat, p_valor = stats.ttest_ind(grupo_a, grupo_b)\nprint(f't={t_stat:.3f}, p={p_valor:.4f}')\n\nif p_valor < 0.05:\n    print(f'Diferença estatisticamente significativa!')\n    print(f'Grupo A: {grupo_a.mean():.3f} vs Grupo B: {grupo_b.mean():.3f}')\nelse:\n    print('Sem evidência de diferença real entre os grupos.')", "python"),
                ],
                exercise="A/B test: você tem conversões de duas versões de uma landing page. Use teste t para determinar se a diferença é estatisticamente significativa.",
                takeaway="p-valor não mede a importância prática — mede apenas se a diferença existe. Sempre reporte o tamanho do efeito junto com a significância estatística."
            ),
        ]),
        Module("py-m4", "Projeto Final: Pipeline de Análise", "Integre tudo em um projeto real de ponta a ponta.", [
            Lesson("py-m4-l1", "Pipeline de Dados Automatizado", 28,
                "Um pipeline transforma dados brutos em insights de forma repetível e automatizada.",
                [
                    Section("Estrutura de um Pipeline de Análise",
                        "Todo pipeline tem as etapas: Ingest (carregar), Validate (verificar qualidade), Transform (limpar e enriquecer), Analyze (calcular métricas) e Output (exportar/visualizar). Estruture o código em funções puras para cada etapa.",
                        "# pipeline.py\nimport pandas as pd\nfrom pathlib import Path\n\ndef ingest(caminho: str) -> pd.DataFrame:\n    return pd.read_csv(caminho, parse_dates=['data'], sep=';')\n\ndef validate(df: pd.DataFrame) -> pd.DataFrame:\n    assert df['valor'].notna().all(), 'Valores nulos em valor!'\n    assert (df['valor'] > 0).all(), 'Valores negativos!'\n    return df\n\ndef transform(df: pd.DataFrame) -> pd.DataFrame:\n    return (\n        df\n        .assign(mes=lambda d: d['data'].dt.to_period('M'))\n        .assign(valor_k=lambda d: d['valor'] / 1000)\n        .dropna(subset=['cliente_id'])\n    )\n\ndef analyze(df: pd.DataFrame) -> dict:\n    return {\n        'faturamento_total': df['valor'].sum(),\n        'ticket_medio': df['valor'].mean(),\n        'por_mes': df.groupby('mes')['valor'].sum().to_dict(),\n    }\n\nif __name__ == '__main__':\n    resultado = (\n        ingest('vendas.csv')\n        |> validate\n        |> transform\n        |> analyze\n    )\n    print(resultado)", "python"),
                    Section("Logging e Rastreabilidade",
                        "Um pipeline sem logs é uma caixa preta. Use o módulo logging (ou Loguru) para registrar cada etapa com timestamps, contagem de registros e tempo de processamento.",
                        "from loguru import logger\nimport time\n\ndef ingest(caminho: str) -> pd.DataFrame:\n    inicio = time.time()\n    df = pd.read_csv(caminho)\n    logger.info(f'Carregados {len(df)} registros de {caminho} em {time.time()-inicio:.2f}s')\n    return df\n\ndef validate(df: pd.DataFrame) -> pd.DataFrame:\n    nulos = df.isnull().sum().sum()\n    if nulos > 0:\n        logger.warning(f'{nulos} valores nulos encontrados')\n    duplicatas = df.duplicated().sum()\n    if duplicatas > 0:\n        logger.warning(f'{duplicatas} duplicatas removidas')\n        df = df.drop_duplicates()\n    logger.success(f'Validação concluída: {len(df)} registros válidos')\n    return df", "python"),
                    Section("Exportar Resultados",
                        "Exporte em múltiplos formatos para diferentes audiências: CSV para técnicos, Excel com formatação para gestores, PNG/HTML para apresentações.",
                        "def output(metricas: dict, df: pd.DataFrame, pasta: str = 'output'):\n    from pathlib import Path\n    Path(pasta).mkdir(exist_ok=True)\n\n    # CSV para uso técnico\n    df.to_csv(f'{pasta}/dados_processados.csv', index=False)\n\n    # Excel formatado\n    with pd.ExcelWriter(f'{pasta}/relatorio.xlsx', engine='openpyxl') as w:\n        df.to_excel(w, sheet_name='Dados', index=False)\n        pd.DataFrame(metricas.items(),\n                     columns=['Métrica', 'Valor']).to_excel(w, sheet_name='Resumo')\n\n    # Gráfico\n    import matplotlib.pyplot as plt\n    fig, ax = plt.subplots(figsize=(10, 5))\n    pd.Series(metricas['por_mes']).plot(ax=ax)\n    ax.set_title('Faturamento por Mês')\n    fig.savefig(f'{pasta}/faturamento.png', dpi=150, bbox_inches='tight')\n    logger.success(f'Resultados exportados em /{pasta}/')", "python"),
                ],
                exercise="Implemente o pipeline completo para um dataset de vendas: ingest, validate, transform, analyze e output com Excel e gráfico.",
                takeaway="Um pipeline de análise bem estruturado é código que você pode rodar todo mês com novos dados — invista tempo na estrutura, poupe tempo para sempre."
            ),
            Lesson("py-m4-l2", "Análise de Cohort e Retenção", 30,
                "Análise de cohort mede como grupos de usuários se comportam ao longo do tempo — a métrica mais importante para produtos digitais.",
                [
                    Section("O que é Análise de Cohort",
                        "Um cohort é um grupo definido por um evento compartilhado (mês de cadastro, primeira compra). Análise de cohort rastreia comportamento desse grupo ao longo do tempo. Revela se a retenção está melhorando, piorando ou estável.",
                        "import pandas as pd\nimport numpy as np\n\n# Dados: user_id, data_primeiro_pedido, data_pedido\ndf['cohort_mes'] = df.groupby('user_id')['data'].transform('min').dt.to_period('M')\ndf['pedido_mes'] = df['data'].dt.to_period('M')\ndf['meses_desde_cadastro'] = (\n    df['pedido_mes'] - df['cohort_mes']\n).apply(lambda x: x.n)", "python"),
                    Section("Construir a Tabela de Retenção",
                        "Pivote os dados para criar a matriz de retenção: linhas = cohort (mês de cadastro), colunas = meses desde o cadastro, valores = % de usuários retidos.",
                        "# Contar usuários únicos por cohort e período\ncohort_data = df.groupby(['cohort_mes', 'meses_desde_cadastro']).agg(\n    usuarios=('user_id', 'nunique')\n).reset_index()\n\n# Pivotar\ncohort_pivot = cohort_data.pivot_table(\n    index='cohort_mes',\n    columns='meses_desde_cadastro',\n    values='usuarios'\n)\n\n# Calcular retenção relativa ao mês 0\ncohort_size = cohort_pivot[0]\nretencao = cohort_pivot.divide(cohort_size, axis=0) * 100\n\nprint(retencao.round(1))", "python"),
                    Section("Visualizar o Heatmap de Retenção",
                        "O heatmap de retenção é a visualização padrão: linhas = cohorts, colunas = tempo, cor = % retidos. Verde escuro = boa retenção.",
                        "import seaborn as sns\nimport matplotlib.pyplot as plt\n\nfig, ax = plt.subplots(figsize=(14, 7))\n\nsns.heatmap(\n    retencao,\n    annot=True, fmt='.0f',\n    cmap='YlGn',\n    linewidths=0.5,\n    ax=ax\n)\nax.set_title('Análise de Retenção por Cohort (%)', fontsize=14, pad=12)\nax.set_xlabel('Meses desde o primeiro pedido')\nax.set_ylabel('Cohort (mês de aquisição)')\nplt.tight_layout()\nplt.savefig('retencao_cohort.png', dpi=150)", "python"),
                ],
                exercise="Com dados de pedidos dos últimos 12 meses, construa a análise de cohort completa e identifique qual cohort tem melhor retenção no mês 3.",
                takeaway="Análise de cohort revela tendências que médias gerais escondem — um produto pode ter 50% de retenção média mas estar piorando em cohorts recentes."
            ),
            Lesson("py-m4-l3", "Automação e Agendamento", 20,
                "Transforme sua análise em um relatório que roda sozinho toda semana.",
                [
                    Section("Criar Relatório HTML Automático",
                        "Gere relatórios HTML com tabelas e gráficos incorporados — podem ser enviados por email ou publicados em um servidor.",
                        "import pandas as pd\nfrom jinja2 import Template\n\ntemplate_html = '''\n<html><head><style>\n  table { border-collapse: collapse; width: 100%; }\n  th, td { border: 1px solid #ddd; padding: 8px; }\n  th { background-color: #00e87a; }\n</style></head>\n<body>\n  <h1>Relatório de Vendas — {{ periodo }}</h1>\n  <h2>Faturamento Total: R$ {{ faturamento | number_format(2, ',', '.') }}</h2>\n  {{ tabela | safe }}\n</body></html>\n'''\n\ntabela_html = df.to_html(classes='tabela', index=False)\nhtml = Template(template_html).render(\n    periodo='Janeiro 2024',\n    faturamento=df['valor'].sum(),\n    tabela=tabela_html\n)\nwith open('relatorio.html', 'w') as f:\n    f.write(html)", "python"),
                    Section("Agendamento com schedule",
                        "A biblioteca schedule roda funções em intervalos definidos. Para produção, use cron (Linux/Mac) ou Task Scheduler (Windows).",
                        "import schedule\nimport time\nfrom datetime import datetime\n\ndef gerar_relatorio_diario():\n    print(f'[{datetime.now()}] Gerando relatório...')\n    # seu pipeline aqui\n    print('Relatório gerado!')\n\n# Agendar\nschedule.every().day.at('08:00').do(gerar_relatorio_diario)\nschedule.every().monday.at('09:00').do(gerar_relatorio_semanal)\n\n# Loop\nwhile True:\n    schedule.run_pending()\n    time.sleep(60)  # verificar a cada minuto", "python"),
                    Section("Enviar por Email com smtplib",
                        "Envie o relatório por email automaticamente. Use variáveis de ambiente para credenciais — nunca coloque senhas no código.",
                        "import smtplib\nimport os\nfrom email.mime.multipart import MIMEMultipart\nfrom email.mime.text import MIMEText\nfrom email.mime.base import MIMEBase\nfrom email import encoders\n\ndef enviar_relatorio(destinatarios: list[str], arquivo: str):\n    msg = MIMEMultipart()\n    msg['From'] = os.getenv('EMAIL_FROM')\n    msg['To'] = ', '.join(destinatarios)\n    msg['Subject'] = f'Relatório de Vendas — {datetime.now():%d/%m/%Y}'\n    msg.attach(MIMEText('Segue o relatório em anexo.', 'plain'))\n\n    # Anexar arquivo\n    with open(arquivo, 'rb') as f:\n        part = MIMEBase('application', 'octet-stream')\n        part.set_payload(f.read())\n        encoders.encode_base64(part)\n        part.add_header('Content-Disposition', f'attachment; filename={arquivo}')\n        msg.attach(part)\n\n    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:\n        smtp.login(os.getenv('EMAIL_FROM'), os.getenv('EMAIL_PASS'))\n        smtp.sendmail(msg['From'], destinatarios, msg.as_string())", "python"),
                ],
                exercise="Automatize toda a sua pipeline: rode toda segunda-feira de manhã e envie o relatório Excel por email para uma lista de destinatários.",
                takeaway="Análise que você precisa rodar manualmente toda semana é análise que vai ser esquecida. Automatize desde o primeiro dia."
            ),
        ]),
    ]
)

# ─────────────────────────────────────────────────────────────────────────────
# CATALOG — adicionar todos os cursos aqui
# ─────────────────────────────────────────────────────────────────────────────
COURSES: list[Course] = [SQL_COURSE, PYTHON_DATA_COURSE]
_INDEX: dict[str, Course] = {c.id: c for c in COURSES}


def get_all() -> list[dict]:
    return [
        {
            "id": c.id, "title": c.title, "tagline": c.tagline,
            "description": c.description, "level": c.level,
            "category": c.category, "duration_hours": c.duration_hours,
            "skills": c.skills, "color": c.color,
            "total_modules": len(c.modules),
            "total_lessons": sum(len(m.lessons) for m in c.modules),
        }
        for c in COURSES
    ]


def get_by_id(course_id: str) -> Course | None:
    return _INDEX.get(course_id)


def get_overview(course_id: str) -> dict | None:
    c = _INDEX.get(course_id)
    if not c:
        return None
    return {
        "id": c.id, "title": c.title, "tagline": c.tagline,
        "description": c.description, "level": c.level,
        "category": c.category, "duration_hours": c.duration_hours,
        "skills": c.skills, "color": c.color,
        "modules": [
            {
                "id": m.id, "title": m.title, "description": m.description,
                "lessons": [
                    {"id": l.id, "title": l.title, "duration_min": l.duration_min}
                    for l in m.lessons
                ],
            }
            for m in c.modules
        ],
    }


def get_lesson(course_id: str, lesson_id: str) -> dict | None:
    c = _INDEX.get(course_id)
    if not c:
        return None
    for m in c.modules:
        for l in m.lessons:
            if l.id == lesson_id:
                return {
                    "course_id": course_id,
                    "module_id": m.id,
                    "module_title": m.title,
                    "id": l.id,
                    "title": l.title,
                    "duration_min": l.duration_min,
                    "intro": l.intro,
                    "sections": [{"heading": s.heading, "body": s.body, "code": s.code, "lang": s.lang} for s in l.sections],
                    "exercise": l.exercise,
                    "takeaway": l.takeaway,
                }
    return None
