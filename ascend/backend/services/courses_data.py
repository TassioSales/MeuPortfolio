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
# CURSO 3 — MACHINE LEARNING COM PYTHON
# ─────────────────────────────────────────────────────────────────────────────
ML_COURSE = Course(
    id="machine-learning-python",
    title="Machine Learning com Python",
    tagline="Do conceito ao modelo em produção com scikit-learn e boas práticas",
    description="Aprenda os principais algoritmos de ML, como avaliar modelos corretamente e como colocar um modelo em produção sem quebrar nada.",
    level="Intermediário → Avançado",
    category="Data Science",
    duration_hours=24,
    skills=["Python", "scikit-learn", "Machine Learning", "Feature Engineering", "MLOps"],
    color="#a855f7",
    modules=[
        Module("ml-m1", "Fundamentos de Machine Learning", "Entenda o que é ML de verdade, quando usar e como não cair nas armadilhas mais comuns.", [
            Lesson("ml-m1-l1", "O que é Machine Learning e quando usar", 18,
                "ML não é mágica — é otimização estatística. Saber QUANDO não usar ML é tão importante quanto saber como usar.",
                [
                    Section("Tipos de Aprendizado", "Supervisionado: aprende com exemplos rotulados (classificação, regressão). Não-supervisionado: encontra padrões sem rótulos (clustering, redução de dimensionalidade). Reforço: aprende por tentativa e erro com recompensas. 90% dos problemas de negócio são supervisionados.", "# Taxonomia rápida\n# Supervisionado: entrada X → saída Y conhecida\n# Ex: email (X) → spam/não-spam (Y)\n\n# Não-supervisionado: apenas entrada X\n# Ex: clientes (X) → grupos similares (sem rótulo)\n\n# Reforço: agente → ação → ambiente → recompensa\n# Ex: robô aprendendo a andar", "python"),
                    Section("Quando NÃO usar ML", "Use ML quando: há padrão nos dados, você tem dados suficientes, e a solução exata é desconhecida. NÃO use quando: regras simples resolvem, dados são insuficientes, ou explicabilidade total é obrigatória (alguns setores regulados).", "# Checklist antes de ML:\n# 1. Tenho dados suficientes? (mínimo ~1000 exemplos por classe)\n# 2. Uma regra simples já não resolve?\n# 3. Tenho como validar o modelo?\n# 4. O problema é estável? (distribuição não muda muito)\n\n# Exemplo: prever se cliente vai churn\n# - Regra simples: 'sem login há 30 dias = churn' → testa primeiro!\n# - ML só se a regra simples for insuficiente", "python"),
                    Section("O Pipeline de ML", "Todo projeto de ML segue: Problema → Dados → Features → Modelo → Avaliação → Deploy → Monitoramento. Pular etapas causa falhas em produção.", "from sklearn.pipeline import Pipeline\nfrom sklearn.preprocessing import StandardScaler\nfrom sklearn.linear_model import LogisticRegression\n\n# Pipeline completo: pré-processamento + modelo\npipe = Pipeline([\n    ('scaler', StandardScaler()),\n    ('model', LogisticRegression(max_iter=1000))\n])\n\n# Treinar\npipe.fit(X_train, y_train)\n\n# Avaliar\nprint(f'Acurácia: {pipe.score(X_test, y_test):.3f}')", "python"),
                ],
                exercise="Escolha um problema do seu trabalho. Aplique o checklist: ele realmente precisa de ML ou uma regra simples resolve?",
                takeaway="ML é uma ferramenta — não uma solução universal. A pergunta certa é 'esse problema precisa de ML?' antes de 'qual algoritmo usar?'"
            ),
            Lesson("ml-m1-l2", "Preparação de Dados e Feature Engineering", 25,
                "Lixo entra, lixo sai. 80% do trabalho de ML é preparar dados — é aqui que os modelos ganham ou perdem.",
                [
                    Section("Tratamento de Valores Faltantes", "Nunca delete linhas com NaN sem analisar o padrão. MCAR (falta aleatória): impute pela média/mediana. MAR (falta relacionada): impute por modelo. MNAR (falta não-aleatória): crie feature 'era_nulo'.", "import pandas as pd\nfrom sklearn.impute import SimpleImputer\n\n# Verificar padrão de nulos\nprint(df.isnull().sum())\nprint(df.isnull().mean())  # proporção\n\n# Imputação simples\nimp_mediana = SimpleImputer(strategy='median')\nX['idade'] = imp_mediana.fit_transform(X[['idade']])\n\n# Criar flag de 'era nulo' (preserva informação)\nX['renda_era_nulo'] = X['renda'].isnull().astype(int)\nX['renda'] = X['renda'].fillna(X['renda'].median())", "python"),
                    Section("Encoding de Variáveis Categóricas", "One-Hot Encoding para categorias sem ordem (cidade, cor). Ordinal Encoding para categorias com ordem (baixo/médio/alto). Target Encoding para alta cardinalidade (CEP, produto_id) — mas cuidado com data leakage.", "from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder\nimport pandas as pd\n\n# One-Hot: cria coluna binária por categoria\nohe = OneHotEncoder(sparse_output=False, handle_unknown='ignore')\nX_cat = ohe.fit_transform(X[['cidade', 'plano']])\n\n# Ordinal: preserva ordem\nord = OrdinalEncoder(categories=[['baixo', 'medio', 'alto']])\nX['nivel_encoded'] = ord.fit_transform(X[['nivel']])\n\n# Target encoding (com validação cruzada para evitar leakage)\nfrom category_encoders import TargetEncoder\nte = TargetEncoder(cols=['produto_id'])\nX_train = te.fit_transform(X_train, y_train)\nX_test = te.transform(X_test)", "python"),
                    Section("Feature Engineering: Criar Features Relevantes", "Features derivadas frequentemente superam as originais. Interações, transformações logarítmicas, extração de datas e agrupamentos por cliente são exemplos clássicos.", "import pandas as pd\nimport numpy as np\n\n# Transformação log (distribições assimétricas)\ndf['valor_log'] = np.log1p(df['valor'])  # log1p evita log(0)\n\n# Interação entre features\ndf['valor_por_unidade'] = df['valor_total'] / df['quantidade']\n\n# Extração de datas\ndf['dia_semana'] = df['data'].dt.dayofweek\ndf['mes'] = df['data'].dt.month\ndf['e_fim_de_semana'] = (df['dia_semana'] >= 5).astype(int)\n\n# Agregações por entidade (histórico do cliente)\ndf_agg = df.groupby('cliente_id').agg(\n    n_compras=('pedido_id', 'count'),\n    ticket_medio=('valor', 'mean'),\n    dias_desde_ultima=('data', lambda x: (pd.Timestamp.now() - x.max()).days)\n).reset_index()", "python"),
                ],
                exercise="Pegue um dataset do Kaggle e crie pelo menos 5 features derivadas. Compare o desempenho do modelo com e sem as features novas.",
                takeaway="Feature engineering é onde o conhecimento de negócio vira vantagem competitiva — nenhum algoritmo compensa dados mal preparados."
            ),
            Lesson("ml-m1-l3", "Divisão de Dados e Prevenção de Data Leakage", 20,
                "Data leakage é o erro mais perigoso em ML: o modelo parece ótimo no treino mas falha em produção.",
                [
                    Section("Train/Validation/Test Split", "Nunca avalie no mesmo dado que treinou. Use 70/15/15 ou 80/10/10. O test set só deve ser tocado UMA VEZ — no final. Use validação cruzada para ajuste de hiperparâmetros.", "from sklearn.model_selection import train_test_split\n\n# Divisão estratificada (mantém proporção das classes)\nX_temp, X_test, y_temp, y_test = train_test_split(\n    X, y, test_size=0.15, stratify=y, random_state=42\n)\nX_train, X_val, y_train, y_val = train_test_split(\n    X_temp, y_temp, test_size=0.176, stratify=y_temp, random_state=42\n)  # 0.176 * 0.85 ≈ 0.15 do total\n\nprint(f'Train: {len(X_train)} | Val: {len(X_val)} | Test: {len(X_test)}')", "python"),
                    Section("O que é Data Leakage", "Leakage = usar no treino informação que não estaria disponível em produção. Tipos: target leakage (feature calculada com o alvo), temporal leakage (usar dados futuros), pipeline leakage (fit do scaler no dataset completo).", "# ERRADO: fit do scaler em todos os dados (leakage!)\nscaler = StandardScaler()\nX_scaled = scaler.fit_transform(X)  # usa test set no fit!\nX_train, X_test = train_test_split(X_scaled)\n\n# CERTO: fit apenas no treino\nX_train, X_test = train_test_split(X)\nscaler = StandardScaler()\nX_train = scaler.fit_transform(X_train)  # fit só no treino\nX_test = scaler.transform(X_test)       # apenas transform no test\n\n# AINDA MELHOR: use Pipeline (garante isso automaticamente)\npipe = Pipeline([('scaler', StandardScaler()), ('model', model)])\npipe.fit(X_train, y_train)  # fit interno correto", "python"),
                    Section("Validação Cruzada Correta", "K-Fold simples para dados i.i.d. TimeSeriesSplit para dados temporais — nunca use dados futuros para prever o passado.", "from sklearn.model_selection import cross_val_score, TimeSeriesSplit\n\n# K-Fold padrão (dados não-temporais)\nscores = cross_val_score(pipe, X_train, y_train, cv=5, scoring='roc_auc')\nprint(f'ROC-AUC: {scores.mean():.3f} ± {scores.std():.3f}')\n\n# Time Series Split (dados temporais)\ntscv = TimeSeriesSplit(n_splits=5)\nfor fold, (tr, val) in enumerate(tscv.split(X_train)):\n    pipe.fit(X_train.iloc[tr], y_train.iloc[tr])\n    score = pipe.score(X_train.iloc[val], y_train.iloc[val])\n    print(f'Fold {fold+1}: {score:.3f}')", "python"),
                ],
                exercise="Construa um pipeline completo com StandardScaler + modelo. Verifique com cross_val_score que não há leakage.",
                takeaway="Data leakage faz modelos parecerem milagrosos no notebook e inúteis em produção. Use Pipeline e TimeSeriesSplit para se proteger."
            ),
        ]),
        Module("ml-m2", "Algoritmos Supervisionados", "Os algoritmos mais usados no mercado, quando aplicar cada um e como ajustá-los.", [
            Lesson("ml-m2-l1", "Regressão Logística e Árvores de Decisão", 22,
                "Os dois algoritmos mais interpretáveis — e por isso os mais usados em ambientes regulados.",
                [
                    Section("Regressão Logística", "Regressão logística é um classificador linear que estima probabilidades. Rápido, interpretável, funciona bem com features normalizadas. Use como baseline sempre.", "from sklearn.linear_model import LogisticRegression\nfrom sklearn.metrics import classification_report\n\nmodel = LogisticRegression(C=1.0, max_iter=1000, class_weight='balanced')\nmodel.fit(X_train, y_train)\n\ny_pred = model.predict(X_test)\ny_proba = model.predict_proba(X_test)[:, 1]\n\nprint(classification_report(y_test, y_pred))\n\n# Interpretação dos coeficientes\nimport pandas as pd\ncoefs = pd.Series(model.coef_[0], index=feature_names)\nprint(coefs.sort_values().tail(10))  # top features positivas", "python"),
                    Section("Árvore de Decisão", "Árvores criam regras if/else aprendidas dos dados. Altamente interpretáveis. Propenças a overfitting — controle com max_depth e min_samples_leaf.", "from sklearn.tree import DecisionTreeClassifier, export_text\n\ntree = DecisionTreeClassifier(\n    max_depth=5,\n    min_samples_leaf=20,\n    class_weight='balanced',\n    random_state=42\n)\ntree.fit(X_train, y_train)\n\n# Visualizar as regras\nprint(export_text(tree, feature_names=feature_names, max_depth=3))\n\n# Feature importance\nimport pandas as pd\nfi = pd.Series(tree.feature_importances_, index=feature_names)\nprint(fi.sort_values(ascending=False).head(10))", "python"),
                    Section("Quando Usar Cada Um", "Regressão Logística: dados lineares, explicabilidade obrigatória, baseline rápido. Árvore de Decisão: regras não-lineares simples, relatórios para não-técnicos. Random Forest/XGBoost quando precisar de performance máxima.", "from sklearn.linear_model import LogisticRegression\nfrom sklearn.tree import DecisionTreeClassifier\nfrom sklearn.ensemble import RandomForestClassifier\nfrom sklearn.metrics import roc_auc_score\n\nmodels = {\n    'Logistic Regression': LogisticRegression(max_iter=1000),\n    'Decision Tree': DecisionTreeClassifier(max_depth=5),\n    'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),\n}\n\nfor name, m in models.items():\n    m.fit(X_train, y_train)\n    auc = roc_auc_score(y_test, m.predict_proba(X_test)[:, 1])\n    print(f'{name:25s}: ROC-AUC = {auc:.4f}')", "python"),
                ],
                exercise="Treine os 3 modelos acima no mesmo dataset e compare ROC-AUC, tempo de treino e interpretabilidade.",
                takeaway="Comece sempre com Regressão Logística como baseline. Se não for suficiente, suba para Random Forest. XGBoost/LightGBM para máxima performance."
            ),
            Lesson("ml-m2-l2", "Gradient Boosting: XGBoost e LightGBM", 28,
                "Os algoritmos campeões de competições e o padrão da indústria para dados tabulares.",
                [
                    Section("Como Gradient Boosting Funciona", "Boosting treina modelos sequencialmente — cada novo modelo corrige os erros do anterior. XGBoost e LightGBM são implementações otimizadas que vencem a maioria das competições em dados tabulares.", "# Intuição do Boosting:\n# Modelo 1: prevê [1, 0, 1, 1] → erros: [0, 1, 0, 0]\n# Modelo 2: foca nos erros → prevê erros com peso maior\n# Modelo 3: foca nos erros restantes → ...\n# Final: soma ponderada de todos os modelos\n\nimport xgboost as xgb\n\nmodel = xgb.XGBClassifier(\n    n_estimators=500,\n    learning_rate=0.05,\n    max_depth=6,\n    subsample=0.8,\n    colsample_bytree=0.8,\n    eval_metric='auc',\n    early_stopping_rounds=50,\n    random_state=42\n)\nmodel.fit(\n    X_train, y_train,\n    eval_set=[(X_val, y_val)],\n    verbose=100\n)", "python"),
                    Section("LightGBM: Mais Rápido em Dados Grandes", "LightGBM cresce a árvore leaf-wise (mais profundo) vs. level-wise do XGBoost. É 10-100x mais rápido em datasets grandes. Use LightGBM por padrão, XGBoost quando precisar de maior controle.", "import lightgbm as lgb\n\nmodel = lgb.LGBMClassifier(\n    n_estimators=1000,\n    learning_rate=0.05,\n    num_leaves=31,\n    min_child_samples=20,\n    subsample=0.8,\n    colsample_bytree=0.8,\n    random_state=42\n)\nmodel.fit(\n    X_train, y_train,\n    eval_set=[(X_val, y_val)],\n    callbacks=[lgb.early_stopping(50), lgb.log_evaluation(100)]\n)\n\nprint(f'Best iteration: {model.best_iteration_}')\nprint(f'ROC-AUC: {roc_auc_score(y_test, model.predict_proba(X_test)[:,1]):.4f}')", "python"),
                    Section("Tuning de Hiperparâmetros com Optuna", "Grid search é lento demais para boosting. Use Optuna (busca bayesiana) para encontrar os melhores hiperparâmetros em menos tentativas.", "import optuna\nfrom sklearn.model_selection import cross_val_score\nimport lightgbm as lgb\n\ndef objective(trial):\n    params = {\n        'n_estimators': trial.suggest_int('n_estimators', 100, 1000),\n        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),\n        'num_leaves': trial.suggest_int('num_leaves', 20, 100),\n        'min_child_samples': trial.suggest_int('min_child_samples', 5, 50),\n    }\n    model = lgb.LGBMClassifier(**params, random_state=42)\n    return cross_val_score(model, X_train, y_train, cv=3, scoring='roc_auc').mean()\n\nstudy = optuna.create_study(direction='maximize')\nstudy.optimize(objective, n_trials=50)\nprint('Best params:', study.best_params)", "python"),
                ],
                exercise="Use Optuna para otimizar um LightGBM em um dataset de classificação. Compare com os parâmetros default.",
                takeaway="LightGBM com early stopping é o ponto de partida para dados tabulares. Optuna substitui grid search com muito menos tentativas."
            ),
            Lesson("ml-m2-l3", "Métricas de Avaliação Corretas", 20,
                "Acurácia é a pior métrica para a maioria dos problemas reais. Escolher a métrica errada é escolher o modelo errado.",
                [
                    Section("Classificação: Além da Acurácia", "Em classes desbalanceadas (99% negativo, 1% positivo), um modelo que prevê sempre negativo tem 99% de acurácia — e é inútil. Use Precision, Recall, F1 e ROC-AUC.", "from sklearn.metrics import (\n    classification_report, roc_auc_score,\n    precision_recall_curve, confusion_matrix\n)\nimport matplotlib.pyplot as plt\n\n# Relatório completo\nprint(classification_report(y_test, y_pred, target_names=['Não', 'Sim']))\n\n# ROC-AUC: ranking das probabilidades (threshold-independent)\nauc = roc_auc_score(y_test, y_proba)\nprint(f'ROC-AUC: {auc:.4f}')\n\n# Confusion matrix\ncm = confusion_matrix(y_test, y_pred)\nprint(f'TP={cm[1,1]} FP={cm[0,1]} TN={cm[0,0]} FN={cm[1,0]}')", "python"),
                    Section("Escolher o Threshold Certo", "O threshold padrão é 0.5, mas raramente é o ideal. Defina com base no custo do negócio: falso positivo vs. falso negativo.", "import numpy as np\nfrom sklearn.metrics import precision_recall_curve\n\n# Encontrar threshold ótimo pelo F1\nprecisions, recalls, thresholds = precision_recall_curve(y_test, y_proba)\nf1_scores = 2 * precisions * recalls / (precisions + recalls + 1e-10)\nbest_threshold = thresholds[np.argmax(f1_scores)]\n\nprint(f'Threshold ótimo (F1): {best_threshold:.3f}')\n\n# Aplicar threshold customizado\ny_pred_custom = (y_proba >= best_threshold).astype(int)\nprint(classification_report(y_test, y_pred_custom))", "python"),
                    Section("Regressão: MAE, RMSE e MAPE", "MAE é robusto a outliers. RMSE penaliza erros grandes mais severamente. MAPE é em percentual — útil para comunicar para negócio. R² indica quanto da variância é explicada.", "from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score\nimport numpy as np\n\nmae = mean_absolute_error(y_test, y_pred)\nrmse = np.sqrt(mean_squared_error(y_test, y_pred))\nr2 = r2_score(y_test, y_pred)\n\n# MAPE (cuidado com y=0)\nmape = np.mean(np.abs((y_test - y_pred) / (y_test + 1e-10))) * 100\n\nprint(f'MAE:  {mae:.2f}')\nprint(f'RMSE: {rmse:.2f}')\nprint(f'MAPE: {mape:.1f}%')\nprint(f'R²:   {r2:.4f}')", "python"),
                ],
                exercise="Treine um modelo de churn. Compare os resultados com threshold 0.5, 0.3 e o threshold ótimo pelo F1. Qual dá mais sentido para o negócio?",
                takeaway="A métrica define o que seu modelo otimiza. Sempre alinhe com o negócio: o custo de um falso positivo vs. falso negativo é diferente em cada problema."
            ),
        ]),
        Module("ml-m3", "Modelos em Produção", "Serializar, servir e monitorar modelos — o que separa data scientists de ML engineers.", [
            Lesson("ml-m3-l1", "Serialização e Versionamento de Modelos", 18,
                "Um modelo não commitado no código é um modelo perdido. Aprenda a salvar, versionar e carregar modelos corretamente.",
                [
                    Section("Salvar com joblib e pickle", "joblib é mais eficiente que pickle para arrays NumPy (compressão). Sempre salve o pipeline completo — não só o modelo — para garantir o mesmo pré-processamento.", "import joblib\nfrom sklearn.pipeline import Pipeline\n\n# Salvar pipeline completo\npipe = Pipeline([('scaler', scaler), ('model', model)])\njoblib.dump(pipe, 'model_v1.pkl', compress=3)\nprint('Modelo salvo!')\n\n# Carregar e usar\npipe_loaded = joblib.load('model_v1.pkl')\ny_pred = pipe_loaded.predict(X_new)\n\n# Sempre versione: data + métricas\nimport json\nmetadata = {\n    'versao': 'v1.0',\n    'data_treino': '2024-01-15',\n    'roc_auc_test': 0.847,\n    'features': list(feature_names),\n    'sklearn_version': '1.4.0'\n}\nwith open('model_v1_metadata.json', 'w') as f:\n    json.dump(metadata, f, indent=2)", "python"),
                    Section("MLflow para Rastreamento de Experimentos", "MLflow registra parâmetros, métricas e artefatos de cada experimento. Nunca mais perca qual configuração deu o melhor resultado.", "import mlflow\nimport mlflow.sklearn\n\nmlflow.set_experiment('churn-prediction')\n\nwith mlflow.start_run(run_name='lgbm-v2'):\n    # Logar parâmetros\n    mlflow.log_params({'n_estimators': 500, 'learning_rate': 0.05})\n\n    model.fit(X_train, y_train)\n\n    # Logar métricas\n    auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])\n    mlflow.log_metric('roc_auc', auc)\n\n    # Logar modelo\n    mlflow.sklearn.log_model(model, 'model')\n\n# Abrir UI: mlflow ui", "python"),
                    Section("Feature Store Simples com Parquet", "Antes de MLflow empresarial, salve features calculadas em Parquet — evita recalcular a cada experimento e garante consistência entre treino e inferência.", "import pandas as pd\nfrom pathlib import Path\n\n# Calcular features uma vez\nfeatures_treino = calcular_features(df_treino)\nfeatures_treino.to_parquet('features/treino_2024_01.parquet', index=False)\n\n# Reusar em experimentos\ndf = pd.read_parquet('features/treino_2024_01.parquet')\n\n# Em produção: calcular as mesmas features para novos dados\ndef calcular_features(df: pd.DataFrame) -> pd.DataFrame:\n    return df.assign(\n        valor_log=lambda d: np.log1p(d['valor']),\n        dias_inativo=lambda d: (pd.Timestamp.now() - d['ultima_compra']).dt.days,\n        ticket_medio=lambda d: d['valor_total'] / d['n_compras'].clip(1),\n    )", "python"),
                ],
                exercise="Treine um modelo, salve com joblib e MLflow. Carregue de volta e confirme que as previsões são idênticas.",
                takeaway="Salvar o pipeline completo (não só o modelo) e versionar com metadados é o mínimo para não perder semanas de trabalho."
            ),
            Lesson("ml-m3-l2", "Servir Modelos com FastAPI", 25,
                "Um modelo treinado que não está em produção não gera valor. Construa uma API de inferência robusta.",
                [
                    Section("API de Inferência Básica", "FastAPI + joblib = API de ML em minutos. A estrutura básica recebe features, carrega o modelo e retorna a previsão com probabilidade.", "from fastapi import FastAPI\nfrom pydantic import BaseModel\nimport joblib\nimport numpy as np\n\napp = FastAPI(title='Churn Prediction API')\n\n# Carregar modelo uma vez na inicialização\nmodel = joblib.load('model_v1.pkl')\n\nclass ClienteFeatures(BaseModel):\n    dias_sem_compra: int\n    ticket_medio: float\n    n_compras_90d: int\n    valor_total_12m: float\n\n@app.post('/predict')\ndef predict(cliente: ClienteFeatures):\n    X = np.array([[cliente.dias_sem_compra, cliente.ticket_medio,\n                   cliente.n_compras_90d, cliente.valor_total_12m]])\n    prob = model.predict_proba(X)[0, 1]\n    return {\n        'churn_probability': round(float(prob), 4),\n        'prediction': 'churn' if prob >= 0.35 else 'ativo'\n    }", "python"),
                    Section("Batch Inference para Grandes Volumes", "Para scores diários de toda a base, use batch inference — muito mais eficiente que chamar a API uma vez por cliente.", "import pandas as pd\nimport joblib\nfrom pathlib import Path\n\ndef batch_predict(input_path: str, output_path: str, threshold: float = 0.35):\n    model = joblib.load('model_v1.pkl')\n    df = pd.read_parquet(input_path)\n\n    probas = model.predict_proba(df[FEATURE_COLS])[:, 1]\n    df['churn_prob'] = probas\n    df['churn_pred'] = (probas >= threshold).astype(int)\n    df['risco'] = pd.cut(probas,\n                          bins=[0, 0.2, 0.5, 0.75, 1.0],\n                          labels=['baixo', 'medio', 'alto', 'critico'])\n\n    df.to_parquet(output_path, index=False)\n    print(f'{df.churn_pred.sum()} clientes em risco de churn')\n    return df\n\nbatch_predict('clientes_hoje.parquet', 'scores_hoje.parquet')", "python"),
                    Section("Health Check e Métricas da API", "Uma API de ML sem health check é inoperável em produção. Adicione endpoint de saúde e monitore latência de inferência.", "from fastapi import FastAPI\nfrom prometheus_client import Counter, Histogram, make_asgi_app\nimport time\n\napp = FastAPI()\n\nPREDICT_COUNT = Counter('predictions_total', 'Total predictions')\nLATENCY = Histogram('prediction_latency_seconds', 'Prediction latency')\n\n@app.get('/health')\ndef health():\n    return {'status': 'ok', 'model_version': 'v1.0'}\n\n@app.post('/predict')\ndef predict(features: ClienteFeatures):\n    inicio = time.time()\n    resultado = _fazer_predicao(features)\n    LATENCY.observe(time.time() - inicio)\n    PREDICT_COUNT.inc()\n    return resultado\n\n# Métricas Prometheus em /metrics\napp.mount('/metrics', make_asgi_app())", "python"),
                ],
                exercise="Construa a API completa de churn prediction com FastAPI, incluindo health check e batch endpoint.",
                takeaway="FastAPI é o padrão para servir modelos Python. Sempre carregue o modelo uma vez no startup — nunca dentro do endpoint."
            ),
            Lesson("ml-m3-l3", "Monitoramento de Modelos em Produção", 20,
                "Modelos degradam silenciosamente. Data drift, concept drift e erros de entrada derrubam performance sem alertar ninguém.",
                [
                    Section("Data Drift: Detectar Mudança nas Features", "Data drift = distribuição das features muda. Concept drift = relação X→Y muda. Ambos degradam o modelo. Monitore com testes estatísticos.", "from scipy import stats\nimport pandas as pd\nimport numpy as np\n\ndef detectar_drift(df_referencia: pd.DataFrame, df_producao: pd.DataFrame,\n                   threshold_pvalue: float = 0.05) -> dict:\n    resultados = {}\n    for col in df_referencia.select_dtypes(include=np.number).columns:\n        stat, p = stats.ks_2samp(df_referencia[col].dropna(),\n                                  df_producao[col].dropna())\n        resultados[col] = {\n            'p_value': round(p, 4),\n            'drift_detectado': p < threshold_pvalue\n        }\n    colunas_com_drift = [k for k, v in resultados.items() if v['drift_detectado']]\n    print(f'Drift detectado em: {colunas_com_drift}')\n    return resultados", "python"),
                    Section("Monitorar Performance com Ground Truth Atrasado", "Em churn, o ground truth (cliente churnou?) chega semanas depois. Monitore distribuição de probabilidades como proxy antecipado.", "import pandas as pd\nimport matplotlib.pyplot as plt\n\ndef monitorar_scores(df_scores_historico: pd.DataFrame):\n    # Agrupar por semana\n    df_scores_historico['semana'] = df_scores_historico['data'].dt.isocalendar().week\n\n    stats = df_scores_historico.groupby('semana')['churn_prob'].agg(\n        media='mean', p25=lambda x: x.quantile(0.25), p75=lambda x: x.quantile(0.75)\n    ).reset_index()\n\n    # Plot de tendência\n    fig, ax = plt.subplots(figsize=(10, 4))\n    ax.plot(stats['semana'], stats['media'], label='Média de risco')\n    ax.fill_between(stats['semana'], stats['p25'], stats['p75'], alpha=0.3)\n    ax.axhline(0.35, color='red', linestyle='--', label='Threshold')\n    ax.set_title('Distribuição de scores ao longo do tempo')\n    ax.legend()\n    plt.tight_layout()", "python"),
                    Section("Alertas e Retraining Automático", "Defina gatilhos para retreinar: ROC-AUC cai X%, drift em Y features, ou simplesmente todo mês. Automatize com schedule.", "import schedule\nimport time\nfrom datetime import datetime\n\ndef avaliar_modelo():\n    df_recente = carregar_dados_recentes(dias=30)\n    df_scores = pd.read_parquet('scores_recentes.parquet')\n\n    # Calcular métricas com ground truth disponível\n    df_merged = df_recente.merge(df_scores, on='cliente_id')\n    auc_atual = roc_auc_score(df_merged['churnou'], df_merged['churn_prob'])\n\n    print(f'[{datetime.now()}] ROC-AUC atual: {auc_atual:.4f}')\n\n    if auc_atual < 0.75:  # threshold de degradação\n        print('ALERTA: modelo degradado — iniciando retreino')\n        retreinar_modelo()\n        enviar_alerta_slack('Modelo de churn retreinado automaticamente')\n\nschedule.every().monday.at('06:00').do(avaliar_modelo)\nwhile True:\n    schedule.run_pending()\n    time.sleep(3600)", "python"),
                ],
                exercise="Simule drift mudando a distribuição de uma feature. Detecte com KS test e implemente um alerta automático.",
                takeaway="Modelos sem monitoramento são bombas-relógio. Monitore distribuição de scores semanalmente e tenha gatilho automático de retreino."
            ),
        ]),
        Module("ml-m4", "Projeto Final: Pipeline Completo de ML", "Integre tudo: EDA, features, modelo, API e monitoramento.", [
            Lesson("ml-m4-l1", "Definição do Problema e EDA", 20,
                "Todo projeto começa com uma pergunta de negócio clara. Sem isso, qualquer modelo é solução sem problema.",
                [
                    Section("Canvas de Problema de ML", "Documente: qual decisão o modelo vai informar? Quem usa? Qual métrica de negócio? Qual o custo de erro? Só então pense em algoritmos.", "# Template de Canvas de Problema\ncanvas = {\n    'problema_negocio': 'Identificar clientes em risco de churn 30 dias antes',\n    'decisao_informada': 'Time CS prioriza contato proativo com clientes de alto risco',\n    'metrica_negocio': 'Reduzir churn de 8% para 6% em 6 meses',\n    'metrica_ml': 'ROC-AUC >= 0.80, Recall >= 0.70 (não perder churners)',\n    'custo_falso_positivo': 'Contato desnecessário (baixo custo)',\n    'custo_falso_negativo': 'Perder cliente (alto custo)',\n    'threshold_ideal': 0.30,  # recall alto > precision\n    'frequencia_predicao': 'Batch diário às 06h',\n    'dados_disponiveis': ['transações 24m', 'logs de acesso', 'suporte'],\n    'data_entrega': '2024-03-01'\n}", "python"),
                    Section("EDA Focada no Alvo", "EDA sem foco no alvo é turismo nos dados. Pergunte: qual feature separa melhor churners de não-churners?", "import pandas as pd\nimport matplotlib.pyplot as plt\nimport seaborn as sns\n\n# Distribuição do alvo\nprint(df['churnou'].value_counts(normalize=True))\n\n# Features mais discriminativas\nfor col in ['dias_sem_compra', 'n_contatos_suporte', 'ticket_medio']:\n    fig, ax = plt.subplots(figsize=(8, 4))\n    df.groupby('churnou')[col].plot(kind='density', ax=ax, legend=True)\n    ax.set_title(f'{col} por churn')\n    plt.tight_layout()\n\n# Correlação com alvo\ncorr_alvo = df.corr()['churnou'].sort_values()\nprint(corr_alvo[abs(corr_alvo) > 0.1])", "python"),
                    Section("Baseline Simples", "Antes de qualquer ML, construa um baseline com regras simples. Se ML não superar o baseline significativamente, repense.", "import pandas as pd\nfrom sklearn.metrics import roc_auc_score\n\n# Baseline: dias sem compra > 60 = churn\ndf['baseline_pred'] = (df['dias_sem_compra'] > 60).astype(float)\nauc_baseline = roc_auc_score(df['churnou'], df['baseline_pred'])\nprint(f'Baseline (regra simples): ROC-AUC = {auc_baseline:.4f}')\n\n# Agora compare com ML\n# Se ML não superar baseline em +5pp, o custo pode não se justificar\nprint(f'ML deve superar: {auc_baseline + 0.05:.4f}')", "python"),
                ],
                exercise="Defina um problema de ML do seu contexto usando o Canvas. Construa o baseline e documente o gap esperado.",
                takeaway="'Qual decisão esse modelo vai informar?' é a pergunta mais importante de qualquer projeto de ML."
            ),
            Lesson("ml-m4-l2", "Treino, Avaliação e Registro do Modelo Final", 25,
                "Treine o modelo final com todos os aprendizados do projeto e registre para rastreabilidade total.",
                [
                    Section("Treino Final com Todos os Dados de Desenvolvimento", "Após validação cruzada, treine o modelo final unindo train + validation. Reserve test set apenas para avaliação final — nunca use para ajuste.", "import lightgbm as lgb\nfrom sklearn.pipeline import Pipeline\nimport joblib, json\nfrom datetime import date\n\n# Unir train + val para treino final\nX_dev = pd.concat([X_train, X_val])\ny_dev = pd.concat([y_train, y_val])\n\npipe_final = Pipeline([\n    ('preprocessor', preprocessor),\n    ('model', lgb.LGBMClassifier(**best_params, random_state=42))\n])\npipe_final.fit(X_dev, y_dev)\n\n# Avaliar no test set (única vez!)\nauc_final = roc_auc_score(y_test, pipe_final.predict_proba(X_test)[:, 1])\nprint(f'ROC-AUC FINAL (test set): {auc_final:.4f}')", "python"),
                    Section("Registro Completo do Modelo", "Salve modelo, metadados e um card de modelo — documento que descreve o que o modelo faz, limitações e como usar.", "import joblib, json\nfrom datetime import date\n\njoblib.dump(pipe_final, 'models/churn_v2.0.pkl', compress=3)\n\nmodel_card = {\n    'nome': 'Churn Prediction Model',\n    'versao': '2.0',\n    'data_treino': str(date.today()),\n    'algoritmo': 'LightGBM',\n    'features': list(feature_names),\n    'metricas': {\n        'roc_auc_cv': 0.834,\n        'roc_auc_test': round(auc_final, 4),\n        'threshold': 0.30,\n        'recall_0.30': 0.72,\n        'precision_0.30': 0.45\n    },\n    'limitacoes': [\n        'Treinado com dados Jan-Dez 2023',\n        'Performance pode degradar em campanhas atípicas',\n        'Não usar para clientes com < 3 meses de histórico'\n    ],\n    'responsavel': 'time-ds@empresa.com'\n}\nwith open('models/churn_v2.0_card.json', 'w') as f:\n    json.dump(model_card, f, indent=2, ensure_ascii=False)", "python"),
                    Section("Deploy e Rollback", "Deploy gradual (canary): direcione 10% do tráfego para o novo modelo, monitore, depois suba para 100%. Mantenha o modelo anterior para rollback rápido.", "# Estratégia de deploy canary\nimport random\n\ndef predict_canary(features, canary_fraction=0.10):\n    if random.random() < canary_fraction:\n        # Novo modelo (10% do tráfego)\n        prob = model_v2.predict_proba([features])[0, 1]\n        log_prediction(features, prob, model_version='v2.0')\n    else:\n        # Modelo atual (90% do tráfego)\n        prob = model_v1.predict_proba([features])[0, 1]\n        log_prediction(features, prob, model_version='v1.0')\n    return prob\n\n# Rollback: apenas troque o modelo carregado\n# model_atual = joblib.load('models/churn_v1.0.pkl')  # rollback\nmodel_atual = joblib.load('models/churn_v2.0.pkl')    # novo", "python"),
                ],
                exercise="Complete o pipeline: treino final, model card, salvar com MLflow e escrever o script de deploy com canary.",
                takeaway="Um projeto de ML completo tem: baseline → experimentos rastreados → modelo registrado com card → deploy gradual → monitoramento."
            ),
            Lesson("ml-m4-l3", "Interpretabilidade com SHAP", 22,
                "Explicar por que o modelo tomou uma decisão específica é obrigatório em crédito, saúde e RH.",
                [
                    Section("SHAP Values: Como Funciona", "SHAP (SHapley Additive exPlanations) calcula a contribuição de cada feature para cada previsão individualmente. É o padrão-ouro de explicabilidade.", "import shap\n\n# Calcular SHAP values\nexplainer = shap.TreeExplainer(model)  # rápido para tree-based\nshap_values = explainer.shap_values(X_test)\n\n# Importância global (média do |SHAP|)\nshap.summary_plot(shap_values, X_test, feature_names=feature_names)\n\n# Para classificação binária, use índice 1 (classe positiva)\nif isinstance(shap_values, list):\n    shap_vals = shap_values[1]\nelse:\n    shap_vals = shap_values", "python"),
                    Section("Explicação Individual de uma Previsão", "Para cada cliente, mostre quais features aumentaram ou diminuíram a probabilidade de churn.", "import shap\n\n# Explicar um cliente específico\ncliente_idx = 42\nshap.waterfall_plot(\n    shap.Explanation(\n        values=shap_vals[cliente_idx],\n        base_values=explainer.expected_value,\n        data=X_test.iloc[cliente_idx],\n        feature_names=feature_names\n    )\n)\n\n# Texto para relatório\ncontribuicoes = sorted(\n    zip(feature_names, shap_vals[cliente_idx]),\n    key=lambda x: abs(x[1]), reverse=True\n)\nprint('Principais fatores de risco:')\nfor feat, val in contribuicoes[:5]:\n    direcao = 'aumenta' if val > 0 else 'reduz'\n    print(f'  {feat}: {direcao} risco em {abs(val):.3f}')", "python"),
                    Section("SHAP para Features de Alto Impacto", "O gráfico de dependência SHAP mostra como uma feature específica afeta as previsões — e interações com outras features.", "import shap\nimport matplotlib.pyplot as plt\n\n# Dependência de dias_sem_compra\nshap.dependence_plot(\n    'dias_sem_compra',\n    shap_vals,\n    X_test,\n    feature_names=feature_names,\n    interaction_index='n_contatos_suporte'  # colorido por interação\n)\n\n# Resumo das top features\nshap.summary_plot(\n    shap_vals, X_test,\n    feature_names=feature_names,\n    plot_type='bar',\n    max_display=15\n)", "python"),
                ],
                exercise="Treine um modelo de churn. Use SHAP para identificar as 5 features mais importantes e explique uma previsão individual em linguagem de negócio.",
                takeaway="SHAP transforma um modelo caixa-preta em algo auditável. Em qualquer decisão que afete pessoas, explicabilidade não é opcional."
            ),
        ]),
    ]
)


# ─────────────────────────────────────────────────────────────────────────────
# CURSO 4 — GIT E GITHUB
# ─────────────────────────────────────────────────────────────────────────────
GIT_COURSE = Course(
    id="git-github",
    title="Git e GitHub: Controle de Versão Profissional",
    tagline="Do git init ao pull request em equipe — fluxos reais de trabalho",
    description="Domine Git na linha de comando e GitHub para colaboração. Branches, merges, rebase, pull requests e CI/CD básico.",
    level="Iniciante → Intermediário",
    category="DevOps",
    duration_hours=12,
    skills=["Git", "GitHub", "CI/CD", "Branching", "Code Review"],
    color="#f97316",
    modules=[
        Module("git-m1", "Fundamentos do Git", "Entenda como o Git pensa — snapshots, não diffs — e domine os comandos essenciais.", [
            Lesson("git-m1-l1", "Como o Git Funciona de Verdade", 15,
                "A maioria aprende comandos Git sem entender o modelo. Entender o modelo torna tudo mais fácil.",
                [
                    Section("Snapshots, Não Diffs", "Git salva snapshots do projeto inteiro a cada commit — não a diferença entre arquivos. Isso torna branch e merge baratos. O SHA-1 de cada commit garante integridade: qualquer alteração muda o hash.", "# Ver o conteúdo de um commit (snapshot)\ngit cat-file -p HEAD\n\n# Git armazena 3 tipos de objetos:\n# blob: conteúdo de arquivo\n# tree: diretório (lista de blobs e trees)\n# commit: tree + autor + mensagem + parent\n\n# Exemplo de estrutura interna:\ngit log --oneline --graph --all\ngit show HEAD:src/app.py  # arquivo em um commit específico", "bash"),
                    Section("Os 3 Estados do Git", "Working directory (arquivos modificados) → Staging area (preparados para commit) → Repository (commitados). `git add` move para staging. `git commit` move para repository.", "# Ver em qual estado cada arquivo está\ngit status\n\n# Working directory → Staging\ngit add arquivo.py\ngit add -p  # adicionar por hunks (recomendado)\n\n# Staging → Repository\ngit commit -m \"feat: adicionar validação de CPF\"\n\n# Ver diferenças por estado\ngit diff           # working vs staging\ngit diff --staged  # staging vs último commit", "bash"),
                    Section("Configuração Inicial Correta", "Configure nome, email e editor antes de tudo. Use SSH para autenticação — mais seguro que senha.", "# Configuração global\ngit config --global user.name \"Seu Nome\"\ngit config --global user.email \"seu@email.com\"\ngit config --global core.editor \"code --wait\"  # VS Code\ngit config --global init.defaultBranch main\n\n# Ver configuração\ngit config --list\n\n# Gerar chave SSH\nssh-keygen -t ed25519 -C \"seu@email.com\"\ncat ~/.ssh/id_ed25519.pub  # copiar para GitHub", "bash"),
                ],
                exercise="Configure seu Git com nome, email e chave SSH. Crie um repositório, faça 3 commits e use `git log --oneline --graph` para ver o histórico.",
                takeaway="Git salva snapshots, não diffs. Entender os 3 estados (working/staging/repository) explica 90% dos comandos."
            ),
            Lesson("git-m1-l2", "Branches e Merges", 20,
                "Branch é a feature mais poderosa do Git. É um ponteiro para um commit — criar e destruir é instantâneo.",
                [
                    Section("Criar e Navegar entre Branches", "Branches são ponteiros baratos. Crie uma para cada feature/bug. Nunca trabalhe direto no main.", "# Criar e já mudar para a branch\ngit switch -c feature/cadastro-usuario\n\n# Listar branches\ngit branch       # locais\ngit branch -a    # locais + remotas\n\n# Ver em qual branch está\ngit branch --show-current\n\n# Voltar para main\ngit switch main\n\n# Deletar branch (após merge)\ngit branch -d feature/cadastro-usuario\ngit push origin --delete feature/cadastro-usuario", "bash"),
                    Section("Merge: Fast-Forward e 3-Way", "Fast-forward: histórico linear (sem commit de merge). 3-way merge: quando as branches divergiram — cria um commit de merge. Use `--no-ff` para sempre criar commit de merge e preservar o contexto.", "# Merge simples\ngit switch main\ngit merge feature/cadastro-usuario\n\n# Forçar commit de merge (recomendado para features)\ngit merge --no-ff feature/cadastro-usuario\n\n# Ver histórico com branches\ngit log --oneline --graph --all\n\n# Resolver conflitos\ngit merge feature/x  # conflito!\n# Edite os arquivos com conflito\ngit add arquivo_conflito.py\ngit commit -m \"merge: resolver conflito em cadastro\"", "bash"),
                    Section("Rebase: Histórico Linear", "Rebase reescreve commits da branch como se tivessem sido feitos a partir do estado atual do main. Resulta em histórico linear. Nunca rebase branches compartilhadas.", "# Rebase interativo: limpar commits antes do PR\ngit switch feature/minha-feature\ngit rebase main  # reposicionar commits sobre main\n\n# Rebase interativo: squash de commits\ngit rebase -i HEAD~3  # editar últimos 3 commits\n# pick → squash para juntar commits\n# pick → reword para renomear\n\n# Abortar rebase com problema\ngit rebase --abort", "bash"),
                ],
                exercise="Crie uma feature branch, faça 3 commits (um com erro), use rebase -i para squash e então merge no main com --no-ff.",
                takeaway="Feature branches são o coração do trabalho em equipe. Rebase mantém histórico limpo; merge --no-ff preserva contexto das features."
            ),
            Lesson("git-m1-l3", "Comandos de Recuperação e Inspeção", 18,
                "Git nunca deleta nada de verdade. Aprenda a desfazer qualquer erro.",
                [
                    Section("Desfazer Mudanças com Segurança", "reset --soft preserva staging. reset --mixed preserva working directory. reset --hard descarta tudo — use com cuidado. revert cria um commit que desfaz — seguro para histórico público.", "# Desfazer último commit mas manter arquivos em staging\ngit reset --soft HEAD~1\n\n# Desfazer último commit mas manter no working directory\ngit reset HEAD~1  # --mixed é default\n\n# PERIGOSO: descarta tudo permanentemente\ngit reset --hard HEAD~1\n\n# Seguro para branches públicas: cria commit de reversão\ngit revert HEAD\ngit revert abc1234  # reverter commit específico", "bash"),
                    Section("git stash: Guardar Trabalho Temporariamente", "stash salva mudanças não-commitadas para você trocar de branch sem perder o trabalho.", "# Guardar mudanças atuais\ngit stash push -m \"wip: validação de formulário\"\n\n# Listar stashes\ngit stash list\n\n# Restaurar o mais recente\ngit stash pop\n\n# Restaurar específico\ngit stash apply stash@{2}\n\n# Criar branch a partir de stash\ngit stash branch feature/validacao stash@{0}", "bash"),
                    Section("Investigar o Histórico", "git log, blame e bisect são ferramentas de detetive para entender o que mudou, quando e por quê.", "# Log formatado e útil\ngit log --oneline --graph --all --decorate\ngit log --author=\"Ana\" --since=\"2024-01-01\"\ngit log -p -- src/auth.py  # mudanças em arquivo específico\n\n# Quem escreveu cada linha?\ngit blame -L 10,20 src/auth.py\n\n# Encontrar qual commit introduziu um bug (busca binária)\ngit bisect start\ngit bisect bad              # commit atual tem o bug\ngit bisect good v1.0.0      # versão que funcionava\n# Git vai navegando — você testa e fala good/bad\ngit bisect good  # ou: git bisect bad\ngit bisect reset # ao encontrar o commit culpado", "bash"),
                ],
                exercise="Use git bisect para encontrar qual commit introduziu um bug em um repositório de exemplo. Documente os passos.",
                takeaway="Git nunca perde dados — reflog guarda tudo por 90 dias. `git bisect` encontra bugs em minutos em repositórios com centenas de commits."
            ),
        ]),
        Module("git-m2", "GitHub e Fluxo de Trabalho em Equipe", "Pull Requests, code review e o fluxo Git Flow na prática.", [
            Lesson("git-m2-l1", "Pull Requests e Code Review", 20,
                "Pull Request não é só 'pedir para fazer merge' — é a principal ferramenta de qualidade de código em equipe.",
                [
                    Section("Anatomia de um Bom Pull Request", "PR pequeno é PR que é revisado. PR grande é PR que é aprovado sem leitura. Regra: uma feature, um PR. Máximo 400 linhas.", "# Fluxo completo de PR\ngit switch -c feat/autenticacao-2fa\n\n# Desenvolver, commitar...\ngit push -u origin feat/autenticacao-2fa\n\n# Criar PR via GitHub CLI\ngh pr create \\\n  --title \"feat: adicionar autenticação 2FA\" \\\n  --body \"## O que muda\\n- Adiciona TOTP\\n## Como testar\\n1. ...\" \\\n  --reviewer @colega\n\n# Ver status do PR\ngh pr status\ngh pr checks", "bash"),
                    Section("Como Dar Feedback de Code Review", "Bom feedback: específico, construtivo, explica o porquê. Ruim: 'isso está errado' sem contexto. Use Conventional Comments para clareza.", "# Tipos de comentários (Conventional Comments):\n# question: tenho dúvida sobre esta abordagem\n# suggestion: considere usar X em vez de Y\n# issue: isso vai causar problema porque...\n# nitpick: pequeno detalhe, não bloqueia merge\n# praise: ótima solução aqui!\n\n# Comandos GitHub CLI para review\ngh pr review --comment --body \"Suggestion: usar...\"\ngh pr review --approve\ngh pr review --request-changes --body \"Issue: ...\"", "bash"),
                    Section("Merge Strategies no GitHub", "Merge commit: preserva histórico completo. Squash merge: todos os commits viram um (ótimo para features pequenas). Rebase merge: histórico linear sem commit de merge.", "# Via GitHub CLI\ngh pr merge --merge    # merge commit (--no-ff)\ngh pr merge --squash   # squash todos os commits\ngh pr merge --rebase   # rebase linear\n\n# Limpar branch após merge\ngh pr merge --delete-branch\n\n# Política de merge recomendada:\n# Features: squash merge (histórico limpo no main)\n# Releases: merge commit (preservar contexto)\n# Hotfix: merge commit", "bash"),
                ],
                exercise="Crie um repositório com um colega. Cada um faz uma feature branch, abre PR, dá review no PR do outro e faz merge.",
                takeaway="PRs pequenos e focados são revisados de verdade. PRs grandes são 'aprovados' sem leitura. Tamanho importa mais que qualidade da descrição."
            ),
            Lesson("git-m2-l2", "Git Flow e Estratégias de Branching", 18,
                "Git Flow define quais branches existem e como código flui entre elas — essencial para releases controladas.",
                [
                    Section("Git Flow: Estrutura de Branches", "main: produção estável. develop: integração de features. feature/*: novas funcionalidades. release/*: preparação de release. hotfix/*: correções urgentes em produção.", "# Inicializar Git Flow\ngit flow init\n\n# Feature: develop → feature/* → develop\ngit flow feature start cadastro-pj\ngit flow feature finish cadastro-pj  # merge em develop\n\n# Release: develop → release/* → main + develop\ngit flow release start 1.2.0\n# Bump versão, testes finais...\ngit flow release finish 1.2.0  # cria tag + merge\n\n# Hotfix: main → hotfix/* → main + develop\ngit flow hotfix start fix-autenticacao\ngit flow hotfix finish fix-autenticacao", "bash"),
                    Section("Trunk-Based Development: Alternativa Simples", "TBD: todos commitam direto no main (ou PRs muito curtos). Requer feature flags. Mais rápido que Git Flow, menos overhead. Preferido por times com CI/CD maduro.", "# Trunk-Based: feature flags controlam o que está ativo\nimport os\n\nFEATURE_FLAGS = {\n    'novo_checkout': os.getenv('FF_NOVO_CHECKOUT', 'false') == 'true',\n    'pix_pagamento': os.getenv('FF_PIX', 'false') == 'true',\n}\n\ndef checkout(pedido):\n    if FEATURE_FLAGS['novo_checkout']:\n        return novo_checkout_flow(pedido)  # em desenvolvimento\n    return checkout_legado(pedido)         # estável", "python"),
                    Section("Proteção do Branch Main", "Configure regras no GitHub: exigir PR, mínimo de aprovações, CI passando antes do merge. Nunca force-push no main.", "# Via GitHub CLI\ngh api repos/{owner}/{repo}/branches/main/protection \\\n  --method PUT \\\n  --field required_status_checks='{\"strict\":true,\"contexts\":[\"ci/tests\"]}' \\\n  --field enforce_admins=true \\\n  --field required_pull_request_reviews='{\"required_approving_review_count\":1}'\n\n# .github/CODEOWNERS: quem deve revisar quais arquivos\n# * @time-backend         # tudo por padrão\n# /frontend/ @time-frontend\n# /infra/ @devops", "bash"),
                ],
                exercise="Configure branch protection no seu repositório: PR obrigatório, 1 aprovação mínima, CI deve passar.",
                takeaway="Git Flow para releases controladas, Trunk-Based para velocity máxima. A escolha depende da maturidade do CI/CD do time."
            ),
            Lesson("git-m2-l3", "GitHub Actions: CI/CD Básico", 22,
                "CI/CD automatiza o que você faz manualmente: testes, lint e deploy a cada push.",
                [
                    Section("Primeiro Workflow de CI", "A cada push, roda testes automaticamente. Se quebrar, o PR fica bloqueado. É a rede de segurança do time.", "# .github/workflows/ci.yml\nname: CI\n\non:\n  push:\n    branches: [main, develop]\n  pull_request:\n    branches: [main]\n\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with:\n          python-version: '3.12'\n      - run: pip install -r requirements.txt\n      - run: python -m pytest tests/ -v --tb=short\n      - run: python -m ruff check .\n      - run: python -m mypy src/", "yaml"),
                    Section("Cache de Dependências", "Sem cache, instalar dependências a cada run desperdiça minutos. Cache por hash do requirements.txt é o padrão.", "# .github/workflows/ci.yml\n- name: Cache pip\n  uses: actions/cache@v4\n  with:\n    path: ~/.cache/pip\n    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}\n    restore-keys: |\n      ${{ runner.os }}-pip-\n\n- name: Instalar dependências\n  run: pip install -r requirements.txt\n\n# Para Node.js\n- uses: actions/setup-node@v4\n  with:\n    node-version: '20'\n    cache: 'npm'\n- run: npm ci  # ci é mais rápido e determinístico que install", "yaml"),
                    Section("Deploy Automático no Merge", "Ao fazer merge no main, deploy automático em produção. Use environments para aprovação manual antes do deploy.", "# .github/workflows/deploy.yml\nname: Deploy\n\non:\n  push:\n    branches: [main]\n\njobs:\n  deploy:\n    runs-on: ubuntu-latest\n    environment: production  # exige aprovação manual no GitHub\n    steps:\n      - uses: actions/checkout@v4\n\n      - name: Deploy para servidor\n        env:\n          SSH_KEY: ${{ secrets.SSH_KEY }}\n          SERVER: ${{ secrets.SERVER_HOST }}\n        run: |\n          echo \"$SSH_KEY\" > key.pem\n          chmod 600 key.pem\n          ssh -i key.pem user@$SERVER 'cd /app && git pull && systemctl restart app'", "yaml"),
                ],
                exercise="Configure um workflow de CI que roda pytest + ruff em cada PR. Configure branch protection para bloquear merge se CI falhar.",
                takeaway="CI/CD é o multiplicador de velocidade do time. PR sem testes automáticos é PR que vai quebrar produção."
            ),
        ]),
        Module("git-m3", "Avançado: Submodules, LFS e Hooks", "Recursos para projetos grandes e fluxos de trabalho customizados.", [
            Lesson("git-m3-l1", "Git Hooks: Automatizar Qualidade Local", 15,
                "Hooks rodam scripts antes ou depois de operações Git. Use para garantir qualidade antes mesmo do CI.",
                [
                    Section("pre-commit Hook: Bloquear Commits Ruins", "pre-commit roda antes de cada commit. Se falhar, o commit é cancelado. Use para lint, format e testes rápidos.", "# .git/hooks/pre-commit (criar e dar chmod +x)\n#!/bin/sh\npython -m ruff check . --fix\npython -m black .\ngit add -u  # adicionar correções automáticas\n\n# Ferramenta pre-commit (recomendada):\npip install pre-commit\n\n# .pre-commit-config.yaml\nrepos:\n  - repo: https://github.com/astral-sh/ruff-pre-commit\n    rev: v0.3.0\n    hooks:\n      - id: ruff\n        args: [--fix]\n      - id: ruff-format\n\n  - repo: https://github.com/pre-commit/pre-commit-hooks\n    rev: v4.5.0\n    hooks:\n      - id: no-commit-to-branch\n        args: ['--branch', 'main']", "bash"),
                    Section("commit-msg Hook: Enforçar Conventional Commits", "Conventional Commits (feat:, fix:, docs:) habilitam changelogs automáticos e versionamento semântico.", "#!/bin/sh\n# .git/hooks/commit-msg\nCOMMIT_MSG=$(cat $1)\nPATTERN='^(feat|fix|docs|style|refactor|test|chore)(\\(.+\\))?: .+'\n\nif ! echo \"$COMMIT_MSG\" | grep -qE \"$PATTERN\"; then\n  echo \"Erro: mensagem não segue Conventional Commits\"\n  echo \"Exemplos válidos:\"\n  echo \"  feat: adicionar login com Google\"\n  echo \"  fix(auth): corrigir timeout de sessão\"\n  echo \"  docs: atualizar README\"\n  exit 1\nfi", "bash"),
                    Section("post-merge Hook: Atualizar Dependências Automático", "Após git pull, verificar se requirements mudou e instalar automaticamente.", "#!/bin/sh\n# .git/hooks/post-merge\nCHANGED=$(git diff-tree -r --name-only --no-commit-id ORIG_HEAD HEAD)\n\nif echo \"$CHANGED\" | grep -q 'requirements.txt'; then\n  echo '[hook] requirements.txt mudou — atualizando...'\n  pip install -r requirements.txt\nfi\n\nif echo \"$CHANGED\" | grep -q 'package.json'; then\n  echo '[hook] package.json mudou — rodando npm install...'\n  npm install\nfi", "bash"),
                ],
                exercise="Configure pre-commit com ruff + black e commit-msg para enforçar Conventional Commits. Teste com um commit inválido.",
                takeaway="Hooks de pre-commit evitam que código ruim entre no repositório. São mais rápidos que CI porque rodam localmente."
            ),
            Lesson("git-m3-l2", "Git LFS para Arquivos Grandes", 15,
                "Git não foi feito para binários grandes. LFS (Large File Storage) armazena esses arquivos separadamente.",
                [
                    Section("Configurar LFS", "LFS substitui arquivos grandes por ponteiros leves. O arquivo real fica em storage separado (GitHub, S3, etc.).", "# Instalar LFS\ngit lfs install\n\n# Rastrear tipos de arquivo\ngit lfs track '*.psd'\ngit lfs track '*.pkl'    # modelos ML\ngit lfs track '*.parquet'\ngit lfs track 'data/**'\n\n# .gitattributes é criado automaticamente — commite!\ngit add .gitattributes\ngit commit -m 'chore: configurar Git LFS'\n\n# Ver o que está sendo rastreado\ngit lfs ls-files\ngit lfs status", "bash"),
                    Section("O que NÃO Commitar Nunca", "Secrets, dados de produção, modelos treinados (use MLflow), datasets grandes (use DVC ou S3). Configure .gitignore de forma abrangente.", "# .gitignore essencial para projetos de dados\n.env\n.env.*\n!.env.example\n\n# Dados\ndata/raw/\ndata/processed/\n*.csv\n*.parquet\n*.xlsx\n\n# Modelos (use MLflow/DVC)\nmodels/\n*.pkl\n*.joblib\n\n# Python\n__pycache__/\n*.pyc\n.venv/\nvenv/\n.pytest_cache/\n\n# IDEs\n.vscode/\n.idea/\n\n# OS\n.DS_Store\nThumbs.db", "bash"),
                    Section("DVC: Versionamento de Dados e Modelos", "DVC (Data Version Control) versiona datasets e modelos como o Git versiona código — com rastreamento de linhagem.", "# Instalar e configurar DVC\npip install dvc dvc-s3\ndvc init\n\n# Rastrear dataset\ndvc add data/vendas_2024.parquet\ngit add data/vendas_2024.parquet.dvc .gitignore\ngit commit -m 'data: adicionar dataset de vendas 2024'\n\n# Configurar remote (S3, GCS, etc.)\ndvc remote add -d myremote s3://meu-bucket/dvc\ndvc push  # enviar dados para remote\n\n# Em outro ambiente\ndvc pull  # baixar dados rastreados", "bash"),
                ],
                exercise="Configure LFS para arquivos .pkl e DVC para um dataset CSV. Verifique que o repositório não armazena os binários diretamente.",
                takeaway="Nunca commite dados, modelos ou secrets. Use LFS para binários necessários no repo e DVC para versionamento de dados/modelos."
            ),
            Lesson("git-m3-l3", "Resolução Avançada de Conflitos e Histórico", 18,
                "Conflitos são inevitáveis em times. Saber resolvê-los rápido e limpar histórico são skills que diferenciam seniors.",
                [
                    Section("Resolver Conflitos com Ferramenta Visual", "Conflitos de merge são mais fáceis com uma ferramenta visual. Configure VS Code ou IntelliJ como mergetool.", "# Configurar VS Code como merge tool\ngit config --global merge.tool vscode\ngit config --global mergetool.vscode.cmd 'code --wait $MERGED'\n\n# Usar na resolução de conflito\ngit mergetool\n\n# Conflito no arquivo:\n# <<<<<<< HEAD (nossa versão)\n# nossa mudança\n# =======\n# a mudança deles\n# >>>>>>> feature/x\n\n# Ours vs Theirs\ngit checkout --ours arquivo.py    # manter nossa versão\ngit checkout --theirs arquivo.py  # usar versão deles", "bash"),
                    Section("Limpar Histórico com Interactive Rebase", "Antes de um PR, limpe commits de 'wip' e 'fix' com squash e reword.", "# Editar os últimos 4 commits\ngit rebase -i HEAD~4\n\n# No editor, comandos disponíveis:\n# pick   = manter commit como está\n# reword = manter mas editar mensagem\n# squash = fundir com commit anterior (mantém mensagens)\n# fixup  = fundir com anterior (descarta mensagem)\n# drop   = remover commit completamente\n\n# Exemplo: juntar 3 commits de wip em um só\n# pick abc1234 feat: adicionar cadastro\n# fixup def5678 wip\n# fixup ghi9012 fix typo", "bash"),
                    Section("git reflog: O Histórico Secreto", "reflog guarda TODA movimentação do HEAD — mesmo após reset --hard. É o último recurso para recuperar trabalho perdido.", "# Ver todo o histórico de movimentos\ngit reflog\n\n# Exemplo de output:\n# HEAD@{0}: reset: moving to HEAD~3\n# HEAD@{1}: commit: feat: finalizar cadastro\n# HEAD@{2}: commit: wip: cadastro parcial\n\n# Recuperar commit 'perdido' após reset --hard\ngit checkout HEAD@{1}  # vai para o estado anterior\n# ou:\ngit reset --hard HEAD@{1}  # restaura branch para aquele estado\n\n# Limpar reflog antigo (não faça em repos compartilhados)\ngit reflog expire --expire=90.days.ago --all\ngit gc --prune=90.days.ago", "bash"),
                ],
                exercise="Simule um reset --hard acidental e recupere o trabalho usando git reflog. Pratique interactive rebase para limpar 5 commits de wip.",
                takeaway="reflog é o salvador de trabalho perdido. Interactive rebase é a ferramenta de higiene de histórico. Ambos devem ser reflexo de todo dev sênior."
            ),
        ]),
        Module("git-m4", "Projeto Final: Configurar um Repositório Profissional", "Monte um repositório com todas as boas práticas.", [
            Lesson("git-m4-l1", "Templates e Documentação do Repositório", 15,
                "Um repositório profissional tem README, CONTRIBUTING, templates de PR e issue — tudo que ajuda contribuidores.",
                [
                    Section("README Profissional", "README é a vitrine do projeto. Deve responder: o que é, como rodar, como contribuir, status do projeto.", "# Nome do Projeto\n\n[![CI](https://github.com/org/repo/actions/workflows/ci.yml/badge.svg)](https://github.com/org/repo/actions)\n[![Coverage](https://codecov.io/gh/org/repo/badge.svg)](https://codecov.io/gh/org/repo)\n\n## O que é\nDescrição em 2-3 linhas.\n\n## Como rodar\n```bash\ngit clone https://github.com/org/repo\ncd repo\npython -m venv .venv && source .venv/bin/activate\npip install -r requirements.txt\npython manage.py runserver\n```\n\n## Estrutura\n```\nsrc/        # código fonte\ntests/      # testes\ndocs/       # documentação\n```\n\n## Contribuindo\nVeja [CONTRIBUTING.md](CONTRIBUTING.md)", "markdown"),
                    Section("Templates de Issue e PR", "Templates garantem que issues e PRs chegam com as informações necessárias.", "# .github/ISSUE_TEMPLATE/bug_report.md\n---\nname: Bug Report\nabout: Reporte um bug\n---\n## Descrição do bug\n\n## Como reproduzir\n1. ...\n2. ...\n\n## Comportamento esperado\n\n## Ambiente\n- OS: \n- Python: \n- Branch: \n\n---\n# .github/pull_request_template.md\n## O que muda\n- \n\n## Como testar\n1. \n\n## Checklist\n- [ ] Testes adicionados\n- [ ] Documentação atualizada\n- [ ] Sem secrets no código", "markdown"),
                    Section("Dependabot e Atualizações Automáticas", "Dependabot abre PRs automáticos quando dependências têm vulnerabilidades ou novas versões.", "# .github/dependabot.yml\nversion: 2\nupdates:\n  - package-ecosystem: pip\n    directory: '/'\n    schedule:\n      interval: weekly\n    open-pull-requests-limit: 5\n    groups:\n      dev-dependencies:\n        patterns:\n          - 'pytest*'\n          - 'ruff'\n          - 'mypy'\n\n  - package-ecosystem: github-actions\n    directory: '/'\n    schedule:\n      interval: monthly", "yaml"),
                ],
                exercise="Configure seu repositório com README profissional, templates de PR/issue e Dependabot.",
                takeaway="Um repositório bem documentado atrai contribuidores e facilita onboarding. Invista 2 horas e economize dezenas no futuro."
            ),
            Lesson("git-m4-l2", "Semantic Versioning e Changelogs Automáticos", 15,
                "Semantic Versioning + Conventional Commits = changelogs e tags automáticos sem trabalho manual.",
                [
                    Section("Semantic Versioning", "MAJOR.MINOR.PATCH. MAJOR: breaking change. MINOR: nova feature backward-compatible. PATCH: bugfix.", "# Exemplos de semver:\n# 1.0.0 → lançamento inicial\n# 1.1.0 → nova feature (sem breaking change)\n# 1.1.1 → bugfix\n# 2.0.0 → breaking change na API\n\n# Com Conventional Commits, o bump é automático:\n# feat: → MINOR bump (1.1.0)\n# fix:  → PATCH bump (1.1.1)\n# feat!: ou BREAKING CHANGE → MAJOR bump (2.0.0)\n\n# Criar tag\ngit tag -a v1.2.0 -m 'release: versão 1.2.0'\ngit push origin v1.2.0", "bash"),
                    Section("Changelog Automático com git-cliff", "git-cliff gera CHANGELOG.md automaticamente a partir dos Conventional Commits.", "# Instalar\npip install git-cliff\n\n# Gerar changelog\ngit cliff --output CHANGELOG.md\n\n# cliff.toml\n[changelog]\nheader = '# Changelog'\nbody = '''\n{% for group, commits in commits | group_by(attribute='group') %}\n## {{ group | upper }}\n{% for commit in commits %}\n- {{ commit.message }}\n{% endfor %}\n{% endfor %}\n'''\n\n[git]\nconventional_commits = true\ncommit_parsers = [\n  { message = '^feat', group = 'Features' },\n  { message = '^fix', group = 'Bug Fixes' },\n]", "bash"),
                    Section("Release Automático com GitHub Actions", "A cada tag, o workflow cria automaticamente a release no GitHub com o changelog.", "# .github/workflows/release.yml\nname: Release\n\non:\n  push:\n    tags: ['v*']\n\njobs:\n  release:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n        with:\n          fetch-depth: 0  # necessário para git-cliff\n\n      - name: Gerar changelog\n        uses: orhun/git-cliff-action@v3\n        with:\n          args: --latest\n        id: cliff\n\n      - name: Criar GitHub Release\n        uses: softprops/action-gh-release@v2\n        with:\n          body: ${{ steps.cliff.outputs.content }}\n          generate_release_notes: false", "yaml"),
                ],
                exercise="Configure o workflow completo: Conventional Commits → git-cliff gerando CHANGELOG → GitHub Release automático na tag.",
                takeaway="Conventional Commits + git-cliff + GitHub Actions = releases profissionais sem trabalho manual. Configure uma vez, use para sempre."
            ),
            Lesson("git-m4-l3", "Monorepo: Gerenciar Múltiplos Projetos", 18,
                "Monorepos concentram múltiplos projetos em um repositório — necessário quando times compartilham código.",
                [
                    Section("Estrutura de Monorepo", "Monorepo facilita compartilhamento de código e mudanças atômicas entre projetos. A complexidade é gerenciar CI eficiente.", "monorepo/\n├── packages/\n│   ├── core/          # lógica compartilhada\n│   ├── api/           # backend FastAPI\n│   └── frontend/      # Next.js\n├── tools/\n│   └── scripts/\n├── .github/\n│   └── workflows/\n└── pyproject.toml     # configuração raiz\n\n# Regra de ouro: cada package tem seu próprio\n# requirements.txt, tests/ e pode ser deployado independentemente", "bash"),
                    Section("CI Eficiente: Só Testar o que Mudou", "Em monorepos, rodar todos os testes a cada commit é proibitivo. Use paths filters no GitHub Actions.", "# .github/workflows/ci.yml\njobs:\n  detect-changes:\n    runs-on: ubuntu-latest\n    outputs:\n      api: ${{ steps.filter.outputs.api }}\n      frontend: ${{ steps.filter.outputs.frontend }}\n    steps:\n      - uses: dorny/paths-filter@v3\n        id: filter\n        with:\n          filters: |\n            api:\n              - 'packages/api/**'\n            frontend:\n              - 'packages/frontend/**'\n\n  test-api:\n    needs: detect-changes\n    if: needs.detect-changes.outputs.api == 'true'\n    runs-on: ubuntu-latest\n    steps:\n      - run: cd packages/api && pytest", "yaml"),
                    Section("Sparse Checkout para Monorepos Grandes", "Sparse checkout baixa apenas a parte do monorepo que você precisa — essencial quando o repo tem centenas de GB.", "# Clonar apenas um subdiretório\ngit clone --filter=blob:none --sparse https://github.com/org/monorepo\ncd monorepo\ngit sparse-checkout set packages/api\n\n# Adicionar mais paths\ngit sparse-checkout add packages/core\n\n# Ver o que está configurado\ngit sparse-checkout list", "bash"),
                ],
                exercise="Converta um projeto simples em estrutura de monorepo. Configure CI com paths filter para rodar apenas os testes do que mudou.",
                takeaway="Monorepos escalam bem com CI eficiente (paths filter) e sparse checkout. Sem esses, cada commit testa e baixa tudo desnecessariamente."
            ),
        ]),
    ]
)


# ─────────────────────────────────────────────────────────────────────────────
# CURSO 5 — DOCKER E KUBERNETES
# ─────────────────────────────────────────────────────────────────────────────
DOCKER_COURSE = Course(
    id="docker-kubernetes",
    title="Docker e Kubernetes: Containers na Prática",
    tagline="Empacote, orquestre e escale aplicações com containers",
    description="Do Dockerfile ao cluster Kubernetes. Aprenda a containerizar aplicações, orquestrar serviços com Compose e escalar com K8s.",
    level="Iniciante → Intermediário",
    category="DevOps",
    duration_hours=18,
    skills=["Docker", "Kubernetes", "Docker Compose", "CI/CD", "Infraestrutura"],
    color="#0ea5e9",
    modules=[
        Module("dk-m1", "Docker: Fundamentos", "Entenda containers, imagens e como o Docker funciona internamente.", [
            Lesson("dk-m1-l1", "O que são Containers e por que usar", 15,
                "Containers resolvem o problema clássico 'funciona na minha máquina'. Entenda o que eles são de verdade.",
                [
                    Section("VM vs Container", "VMs virtualizam hardware completo (kernel próprio). Containers compartilham o kernel do host e isolam apenas o processo. Resultado: containers sobem em milissegundos, VMs em minutos. Container não é VM leve — é processo isolado.", "# VM: SO completo isolado\n# Container: processo isolado com namespace/cgroups\n\n# Comparação prática:\n# VM: 512MB RAM mínimo, boot em ~60s\n# Container: ~10MB overhead, boot em <1s\n\n# Ver containers rodando\ndocker ps\n\n# Ver processos dentro do container\ndocker exec -it meu-container ps aux\n\n# O container é apenas um processo no host!\nps aux | grep nginx  # aparece no host também", "bash"),
                    Section("Imagens e Camadas", "Imagem Docker é um conjunto de camadas somente-leitura. Cada instrução no Dockerfile cria uma camada. Camadas são compartilhadas entre imagens — economia de disco.", "# Ver camadas de uma imagem\ndocker history python:3.12-slim\n\n# Inspecionar imagem\ndocker inspect python:3.12-slim\n\n# Camadas do Dockerfile:\n# FROM python:3.12-slim      → camada 1 (base, compartilhada)\n# RUN pip install fastapi    → camada 2 (cache se não mudar)\n# COPY . .                   → camada 3 (muda a cada build)\n# CMD [\"uvicorn\", \"main:app\"] → instrução de execução\n\n# Tamanho das camadas\ndocker images --format 'table {{.Repository}}\\t{{.Size}}'", "bash"),
                    Section("Comandos Essenciais", "Os 10 comandos Docker que você usa todo dia.", "# Ciclo de vida básico\ndocker pull python:3.12-slim        # baixar imagem\ndocker run -it python:3.12-slim sh  # rodar interativo\ndocker run -d -p 8000:8000 minha-api  # rodar em background\ndocker ps                           # containers rodando\ndocker ps -a                        # todos (incluindo parados)\ndocker stop <id>                    # parar gracefully\ndocker rm <id>                      # remover container\ndocker logs -f <id>                 # ver logs em tempo real\ndocker exec -it <id> bash           # entrar no container\ndocker stats                        # uso de recursos", "bash"),
                ],
                exercise="Rode um container Nginx, acesse no browser, inspecione os logs e depois pare e remova o container.",
                takeaway="Container é processo isolado, não VM. Imagens são somente-leitura e compostas de camadas — entender isso explica por que o build é rápido na segunda vez."
            ),
            Lesson("dk-m1-l2", "Dockerfile: Boas Práticas de Build", 22,
                "Um Dockerfile mal escrito resulta em imagens de 2GB que demoram 5 minutos para buildar. Veja como fazer certo.",
                [
                    Section("Estrutura de um Dockerfile Profissional", "Ordem importa: coloque o que muda menos no topo (camadas mais cacheadas). Dependências antes do código fonte.", "# Dockerfile profissional para aplicação Python\nFROM python:3.12-slim AS base\n\n# Variáveis de ambiente para Python\nENV PYTHONUNBUFFERED=1 \\\n    PYTHONDONTWRITEBYTECODE=1 \\\n    PIP_NO_CACHE_DIR=1\n\nWORKDIR /app\n\n# Dependências primeiro (camada cacheada)\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\n\n# Código fonte depois (muda com frequência)\nCOPY . .\n\n# Usuário não-root (segurança)\nRUN useradd -m appuser\nUSER appuser\n\nEXPOSE 8000\nCMD [\"uvicorn\", \"main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]", "dockerfile"),
                    Section("Multi-stage Build: Imagens Menores", "Multi-stage separa o ambiente de build do de produção. Resultado: imagens 5-10x menores.", "# Stage 1: build (tem compiladores, ferramentas)\nFROM python:3.12 AS builder\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install --no-cache-dir --prefix=/install -r requirements.txt\n\n# Stage 2: produção (só o necessário)\nFROM python:3.12-slim AS production\nWORKDIR /app\n\n# Copiar apenas as dependências instaladas\nCOPY --from=builder /install /usr/local\nCOPY . .\n\nRUN useradd -m appuser && chown -R appuser /app\nUSER appuser\n\nCMD [\"uvicorn\", \"main:app\", \"--host\", \"0.0.0.0\"]\n\n# Resultado:\n# Sem multi-stage: ~800MB\n# Com multi-stage: ~150MB", "dockerfile"),
                    Section(".dockerignore: Excluir Arquivos do Contexto", ".dockerignore é tão importante quanto .gitignore. Sem ele, o contexto de build inclui node_modules, .git e arquivos sensíveis.", "# .dockerignore\n.git/\n.venv/\nvenv/\n__pycache__/\n*.pyc\n*.pyo\n.pytest_cache/\n.mypy_cache/\n\n# Dados e modelos pesados\ndata/\nmodels/\n*.pkl\n*.parquet\n\n# Secrets\n.env\n.env.*\n!.env.example\n\n# IDEs\n.vscode/\n.idea/\n\n# Verificar tamanho do contexto antes de buildar\ndocker build --no-cache . 2>&1 | head -5\n# Sending build context to Docker daemon  2.048kB  ← ótimo\n# Sending build context to Docker daemon  500MB    ← problema!", "bash"),
                ],
                exercise="Construa um Dockerfile multi-stage para sua aplicação Python. Compare o tamanho da imagem com e sem multi-stage.",
                takeaway="Ordem das instruções define eficiência do cache. Multi-stage reduz tamanho 5-10x. .dockerignore é obrigatório."
            ),
            Lesson("dk-m1-l3", "Docker Compose: Orquestrar Múltiplos Serviços", 25,
                "Aplicações reais têm múltiplos serviços. Compose define e sobe tudo com um comando.",
                [
                    Section("docker-compose.yml Completo", "Compose define serviços, redes e volumes em YAML. `docker compose up` sobe tudo; `down` derruba.", "# docker-compose.yml\nservices:\n  api:\n    build: .\n    ports:\n      - '8000:8000'\n    environment:\n      - DATABASE_URL=postgresql://user:pass@db:5432/mydb\n      - REDIS_URL=redis://redis:6379\n    depends_on:\n      db:\n        condition: service_healthy\n    volumes:\n      - ./:/app  # hot-reload em dev\n    restart: unless-stopped\n\n  db:\n    image: postgres:16-alpine\n    environment:\n      POSTGRES_USER: user\n      POSTGRES_PASSWORD: pass\n      POSTGRES_DB: mydb\n    volumes:\n      - postgres_data:/var/lib/postgresql/data\n    healthcheck:\n      test: [\"CMD\", \"pg_isready\", \"-U\", \"user\"]\n      interval: 5s\n      retries: 5\n\n  redis:\n    image: redis:7-alpine\n    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru\n\nvolumes:\n  postgres_data:", "yaml"),
                    Section("Profiles: Dev vs Produção", "Profiles permitem serviços diferentes por ambiente — ferramentas de debug só em dev.", "# docker-compose.yml com profiles\nservices:\n  api:\n    build: .\n    # sem profile = sempre ativo\n\n  db:\n    image: postgres:16-alpine\n    # sem profile = sempre ativo\n\n  pgadmin:\n    image: dpage/pgadmin4\n    profiles: [dev]  # só em dev\n    ports:\n      - '5050:80'\n\n  flower:  # monitor de Celery\n    image: mher/flower\n    profiles: [dev]\n\n# Rodar com profile dev:\n# docker compose --profile dev up\n\n# Rodar só produção:\n# docker compose up", "yaml"),
                    Section("Comandos Úteis do Compose", "Os comandos que você usa todo dia em desenvolvimento com Docker Compose.", "# Subir tudo (rebuild se houver mudança)\ndocker compose up --build\n\n# Subir em background\ndocker compose up -d\n\n# Ver logs de um serviço\ndocker compose logs -f api\n\n# Rodar comando em serviço\ndocker compose exec api bash\ndocker compose exec db psql -U user mydb\n\n# Parar sem remover\ndocker compose stop\n\n# Derrubar tudo (mantém volumes)\ndocker compose down\n\n# Derrubar tudo + remover volumes (CUIDADO!)\ndocker compose down -v\n\n# Ver status dos serviços\ndocker compose ps", "bash"),
                ],
                exercise="Crie um docker-compose.yml com FastAPI + PostgreSQL + Redis. Configure healthcheck no banco e dependência correta na API.",
                takeaway="Docker Compose é o ambiente de desenvolvimento padrão. Healthchecks evitam race conditions. Profiles separam ferramentas de dev da produção."
            ),
        ]),
        Module("dk-m2", "Kubernetes: Orquestração em Produção", "Escale containers com Kubernetes — o padrão da indústria para produção.", [
            Lesson("dk-m2-l1", "Conceitos Fundamentais do Kubernetes", 25,
                "K8s parece complexo mas tem uma lógica clara. Entenda os objetos principais e como eles se relacionam.",
                [
                    Section("Arquitetura: Control Plane e Nodes", "Control Plane decide o que rodar. Nodes executam os containers. O conceito central é o loop de reconciliação: K8s compara estado desejado vs atual e corrige.", "# Componentes do Control Plane:\n# - kube-apiserver: API central (kubectl fala com ela)\n# - etcd: banco de dados de estado do cluster\n# - scheduler: decide em qual node cada Pod roda\n# - controller-manager: garante que o estado desejado seja mantido\n\n# Componentes dos Nodes:\n# - kubelet: agente que executa Pods\n# - kube-proxy: gerencia rede entre Pods\n# - container runtime: Docker/containerd\n\n# Ver estado do cluster\nkubectl cluster-info\nkubectl get nodes\nkubectl describe node meu-node", "bash"),
                    Section("Pods, Deployments e Services", "Pod = menor unidade (1+ containers). Deployment = gerencia réplicas de Pods. Service = endpoint estável para acessar os Pods.", "# Pod simples (não use em produção — sem restart automático)\nkubectl run nginx --image=nginx:alpine\n\n# Deployment: gerencia réplicas e rolling updates\nkubectl create deployment api --image=minha-api:1.0 --replicas=3\n\n# Escalar\nkubectl scale deployment api --replicas=5\n\n# Service: expor Deployment\nkubectl expose deployment api --port=8000 --type=ClusterIP\n\n# Ver tudo\nkubectl get pods\nkubectl get deployments\nkubectl get services\n\n# Ver logs\nkubectl logs deployment/api -f\nkubectl exec -it pod/api-abc123 -- bash", "bash"),
                    Section("Manifests YAML: Infrastructure as Code", "Em produção, sempre use arquivos YAML — nunca comandos imperativos. YAML pode ser versionado no Git.", "# deployment.yaml\napiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: api\n  labels:\n    app: api\nspec:\n  replicas: 3\n  selector:\n    matchLabels:\n      app: api\n  template:\n    metadata:\n      labels:\n        app: api\n    spec:\n      containers:\n      - name: api\n        image: minha-api:1.0\n        ports:\n        - containerPort: 8000\n        resources:\n          requests:\n            memory: '128Mi'\n            cpu: '100m'\n          limits:\n            memory: '256Mi'\n            cpu: '500m'\n        readinessProbe:\n          httpGet:\n            path: /health\n            port: 8000\n          initialDelaySeconds: 5\n          periodSeconds: 10", "yaml"),
                ],
                exercise="Suba um cluster local com minikube. Crie um Deployment da sua API com 3 réplicas e exponha com um Service.",
                takeaway="K8s compara estado desejado (YAML) vs atual e corrige automaticamente. Sempre use manifests YAML — nunca comandos imperativos em produção."
            ),
            Lesson("dk-m2-l2", "ConfigMaps, Secrets e Volumes", 20,
                "Nunca bake secrets na imagem. K8s tem mecanismos próprios para configuração e dados sensíveis.",
                [
                    Section("ConfigMaps: Configuração Externalizada", "ConfigMap armazena configuração não-sensível. Pode ser montado como variável de ambiente ou arquivo.", "# Criar ConfigMap\nkubectl create configmap app-config \\\n  --from-literal=DEBUG=false \\\n  --from-literal=LOG_LEVEL=INFO\n\n# Ou via YAML\n# configmap.yaml\napiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: app-config\ndata:\n  DEBUG: 'false'\n  LOG_LEVEL: 'INFO'\n  APP_URL: 'https://api.meusite.com'\n\n# Usar no Deployment\nenvFrom:\n  - configMapRef:\n      name: app-config", "yaml"),
                    Section("Secrets: Dados Sensíveis", "Secrets são base64-encoded (não criptografados por padrão). Em produção, use External Secrets Operator + Vault ou AWS Secrets Manager.", "# Criar Secret\nkubectl create secret generic db-creds \\\n  --from-literal=password=minha-senha-secreta \\\n  --from-literal=user=dbuser\n\n# Usar no Deployment (como env var)\nenv:\n  - name: DB_PASSWORD\n    valueFrom:\n      secretKeyRef:\n        name: db-creds\n        key: password\n\n# Ver secrets (base64)\nkubectl get secret db-creds -o yaml\n\n# IMPORTANTE: nunca commite secrets no YAML!\n# Use .gitignore para secrets.yaml\n# Em produção: Vault, AWS Secrets Manager, etc.", "yaml"),
                    Section("PersistentVolumes para Dados", "Containers são efêmeros — dados morrem com eles. PersistentVolume garante que dados sobrevivam ao restart do Pod.", "# PersistentVolumeClaim\napiVersion: v1\nkind: PersistentVolumeClaim\nmetadata:\n  name: postgres-pvc\nspec:\n  accessModes:\n    - ReadWriteOnce\n  resources:\n    requests:\n      storage: 10Gi\n  storageClassName: standard\n\n# Usar no Pod\nvolumes:\n  - name: postgres-data\n    persistentVolumeClaim:\n      claimName: postgres-pvc\n\ncontainers:\n  - name: postgres\n    image: postgres:16\n    volumeMounts:\n      - name: postgres-data\n        mountPath: /var/lib/postgresql/data", "yaml"),
                ],
                exercise="Configure sua API com ConfigMap para variáveis de ambiente e Secret para credenciais de banco. Nunca hardcode nada.",
                takeaway="Configuração pertence ao ConfigMap. Secrets pertencem ao Secret (e idealmente ao Vault em produção). Nunca na imagem."
            ),
            Lesson("dk-m2-l3", "Rolling Updates, HPA e Ingress", 22,
                "Os 3 recursos que tornam K8s indispensável em produção: deploys sem downtime, autoscaling e roteamento.",
                [
                    Section("Rolling Updates: Deploy sem Downtime", "K8s substitui Pods gradualmente — sempre mantendo réplicas disponíveis. Rollback em segundos se algo der errado.", "# Atualizar imagem (rolling update automático)\nkubectl set image deployment/api api=minha-api:2.0\n\n# Acompanhar rollout\nkubectl rollout status deployment/api\n\n# Rollback imediato\nkubectl rollout undo deployment/api\n\n# Rollback para versão específica\nkubectl rollout history deployment/api\nkubectl rollout undo deployment/api --to-revision=2\n\n# Configurar estratégia no YAML\nstrategy:\n  type: RollingUpdate\n  rollingUpdate:\n    maxSurge: 1        # pods extras durante update\n    maxUnavailable: 0  # nunca deixar réplicas indisponíveis", "bash"),
                    Section("HPA: Autoscaling Horizontal", "HPA aumenta ou diminui réplicas automaticamente baseado em CPU, memória ou métricas customizadas.", "# HPA baseado em CPU\nkubectl autoscale deployment api \\\n  --min=2 --max=10 --cpu-percent=70\n\n# Via YAML (mais controle)\napiVersion: autoscaling/v2\nkind: HorizontalPodAutoscaler\nmetadata:\n  name: api-hpa\nspec:\n  scaleTargetRef:\n    apiVersion: apps/v1\n    kind: Deployment\n    name: api\n  minReplicas: 2\n  maxReplicas: 10\n  metrics:\n  - type: Resource\n    resource:\n      name: cpu\n      target:\n        type: Utilization\n        averageUtilization: 70\n\n# Ver HPA\nkubectl get hpa\nkubectl describe hpa api-hpa", "yaml"),
                    Section("Ingress: Roteamento HTTP", "Ingress expõe múltiplos Services via HTTP/HTTPS com um único Load Balancer — muito mais barato que um LB por Service.", "# Ingress com TLS\napiVersion: networking.k8s.io/v1\nkind: Ingress\nmetadata:\n  name: api-ingress\n  annotations:\n    nginx.ingress.kubernetes.io/rewrite-target: /\n    cert-manager.io/cluster-issuer: letsencrypt-prod\nspec:\n  tls:\n  - hosts:\n    - api.meusite.com\n    secretName: api-tls\n  rules:\n  - host: api.meusite.com\n    http:\n      paths:\n      - path: /\n        pathType: Prefix\n        backend:\n          service:\n            name: api\n            port:\n              number: 8000", "yaml"),
                ],
                exercise="Configure rolling update com maxUnavailable=0 e HPA de 2 a 10 réplicas. Simule carga e observe o autoscaling.",
                takeaway="Rolling updates + HPA + Ingress = a tríade de produção K8s. Com esses 3, sua aplicação escala, atualiza e roteia tráfego automaticamente."
            ),
        ]),
        Module("dk-m3", "Projeto Final: Pipeline Completo", "Do código ao cluster K8s com CI/CD automático.", [
            Lesson("dk-m3-l1", "Build e Push Automático de Imagem", 18,
                "A cada merge no main, a imagem Docker é buildada, testada e enviada ao registry automaticamente.",
                [
                    Section("GitHub Actions: Build e Push", "O workflow padrão: checkout → login no registry → build → test → push com tag semântica.", "# .github/workflows/docker.yml\nname: Docker Build\n\non:\n  push:\n    branches: [main]\n    tags: ['v*']\n\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n\n      - name: Login no Docker Hub\n        uses: docker/login-action@v3\n        with:\n          username: ${{ secrets.DOCKERHUB_USER }}\n          password: ${{ secrets.DOCKERHUB_TOKEN }}\n\n      - name: Build e Push\n        uses: docker/build-push-action@v5\n        with:\n          push: true\n          tags: |\n            usuario/minha-api:latest\n            usuario/minha-api:${{ github.sha }}", "yaml"),
                    Section("Scan de Vulnerabilidades na Imagem", "Nunca suba imagem sem verificar vulnerabilidades. Trivy é gratuito e integra com GitHub Actions.", "# Adicionar ao workflow\n      - name: Scan de segurança\n        uses: aquasecurity/trivy-action@master\n        with:\n          image-ref: 'usuario/minha-api:${{ github.sha }}'\n          format: 'table'\n          exit-code: '1'  # falha se HIGH ou CRITICAL\n          severity: 'HIGH,CRITICAL'\n\n# Rodar localmente\ntrivy image python:3.12-slim\ntrivy image minha-api:latest\n\n# Ver resumo\ntrivy image --severity HIGH,CRITICAL minha-api:latest", "yaml"),
                    Section("Tagging Semântico com GitHub Actions", "Tag da imagem deve refletir a versão — não use só `latest` em produção.", "# Tags automáticas por evento:\n# push main → :latest + :sha-abc1234\n# push v1.2.0 → :1.2.0 + :1.2 + :1 + :latest\n\n      - name: Docker meta\n        uses: docker/metadata-action@v5\n        id: meta\n        with:\n          images: usuario/minha-api\n          tags: |\n            type=semver,pattern={{version}}\n            type=semver,pattern={{major}}.{{minor}}\n            type=sha\n\n      - name: Build e Push\n        uses: docker/build-push-action@v5\n        with:\n          push: true\n          tags: ${{ steps.meta.outputs.tags }}", "yaml"),
                ],
                exercise="Configure o workflow completo: build → scan → push com tag semântica. Verifique as imagens no Docker Hub.",
                takeaway="Nunca suba imagem sem scan de segurança. Tags semânticas permitem rollback preciso — `latest` não é suficiente em produção."
            ),
            Lesson("dk-m3-l2", "Deploy Automático no Kubernetes", 20,
                "Com a imagem publicada, o deploy no cluster deve ser igualmente automático e rastreável.",
                [
                    Section("Atualizar Manifest e Aplicar no Cluster", "O workflow de CD: atualiza a tag no manifest YAML, commita e aplica no cluster via kubectl.", "# .github/workflows/deploy.yml\n      - name: Atualizar tag no manifest\n        run: |\n          sed -i \"s|image: usuario/minha-api:.*|image: usuario/minha-api:${{ github.sha }}|\"\\\n            k8s/deployment.yaml\n\n      - name: Commitar manifest atualizado\n        run: |\n          git config user.email 'ci@github.com'\n          git config user.name 'GitHub Actions'\n          git add k8s/deployment.yaml\n          git commit -m 'ci: atualizar imagem para ${{ github.sha }}'\n          git push\n\n      - name: Deploy no cluster\n        env:\n          KUBECONFIG_DATA: ${{ secrets.KUBECONFIG }}\n        run: |\n          echo \"$KUBECONFIG_DATA\" | base64 -d > kubeconfig\n          KUBECONFIG=kubeconfig kubectl apply -f k8s/\n          kubectl rollout status deployment/api --timeout=120s", "yaml"),
                    Section("GitOps com ArgoCD", "GitOps: o Git é a fonte da verdade. ArgoCD monitora o repo e aplica mudanças automaticamente.", "# Instalar ArgoCD\nkubectl create namespace argocd\nkubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml\n\n# Criar Application\napiVersion: argoproj.io/v1alpha1\nkind: Application\nmetadata:\n  name: minha-api\n  namespace: argocd\nspec:\n  project: default\n  source:\n    repoURL: https://github.com/org/repo\n    targetRevision: main\n    path: k8s/\n  destination:\n    server: https://kubernetes.default.svc\n    namespace: production\n  syncPolicy:\n    automated:\n      prune: true\n      selfHeal: true", "yaml"),
                    Section("Rollback Automático em Falha", "Se o novo deploy falhar o health check, reverta automaticamente.", "# No workflow de CI/CD\n      - name: Verificar saúde após deploy\n        run: |\n          kubectl rollout status deployment/api --timeout=120s || {\n            echo 'Deploy falhou! Iniciando rollback...'\n            kubectl rollout undo deployment/api\n            kubectl rollout status deployment/api\n            exit 1\n          }\n\n# Canary deploy manual:\nkubectl set image deployment/api-canary api=minha-api:nova\nkubectl scale deployment/api-canary --replicas=1\n# Monitorar 10 minutos\n# Se OK: escalar canary e reduzir api-stable\n# Se NOK: kubectl rollout undo deployment/api-canary", "bash"),
                ],
                exercise="Configure um pipeline completo: push no main → build → push imagem → atualizar manifest → deploy no K8s → verificar saúde.",
                takeaway="GitOps com ArgoCD é o estado da arte: Git é a fonte da verdade, o cluster se auto-corrige para corresponder ao YAML commitado."
            ),
            Lesson("dk-m3-l3", "Monitoramento com Prometheus e Grafana", 20,
                "Cluster sem monitoramento é cluster sem visibilidade. Prometheus coleta métricas, Grafana visualiza.",
                [
                    Section("Instalar Prometheus e Grafana com Helm", "Helm é o gerenciador de pacotes do K8s. kube-prometheus-stack instala tudo configurado.", "# Adicionar repositório\nhelm repo add prometheus-community https://prometheus-community.github.io/helm-charts\nhelm repo update\n\n# Instalar kube-prometheus-stack\nhelm install monitoring prometheus-community/kube-prometheus-stack \\\n  --namespace monitoring \\\n  --create-namespace \\\n  --set grafana.adminPassword=minha-senha\n\n# Acessar Grafana\nkubectl port-forward -n monitoring svc/monitoring-grafana 3000:80\n# Login: admin / minha-senha", "bash"),
                    Section("Expor Métricas da Aplicação", "Adicione endpoint /metrics na sua aplicação para que o Prometheus colete automaticamente.", "from fastapi import FastAPI\nfrom prometheus_client import Counter, Histogram, generate_latest\nfrom starlette.responses import Response\nimport time\n\napp = FastAPI()\n\nHTTP_REQUESTS = Counter('http_requests_total', 'Total requests', ['method', 'endpoint', 'status'])\nLATENCY = Histogram('http_latency_seconds', 'Request latency', ['endpoint'])\n\n@app.middleware('http')\nasync def metrics_middleware(request, call_next):\n    inicio = time.time()\n    response = await call_next(request)\n    LATENCY.labels(request.url.path).observe(time.time() - inicio)\n    HTTP_REQUESTS.labels(request.method, request.url.path, response.status_code).inc()\n    return response\n\n@app.get('/metrics')\ndef metrics():\n    return Response(generate_latest(), media_type='text/plain')", "python"),
                    Section("Alertas com AlertManager", "Configure alertas para CPU alta, pods reiniciando ou API com muitos erros 5xx.", "# prometheusrule.yaml\napiVersion: monitoring.coreos.com/v1\nkind: PrometheusRule\nmetadata:\n  name: api-alerts\nspec:\n  groups:\n  - name: api\n    rules:\n    - alert: HighErrorRate\n      expr: |\n        rate(http_requests_total{status=~'5..'}[5m]) /\n        rate(http_requests_total[5m]) > 0.05\n      for: 2m\n      labels:\n        severity: critical\n      annotations:\n        summary: 'Taxa de erro acima de 5%'\n\n    - alert: PodRestartingTooMuch\n      expr: rate(kube_pod_container_status_restarts_total[15m]) > 0\n      for: 5m\n      labels:\n        severity: warning", "yaml"),
                ],
                exercise="Instale Prometheus + Grafana no seu cluster. Adicione /metrics na sua API e configure um alerta de erro 5xx.",
                takeaway="Métricas RED (Rate, Errors, Duration) são o mínimo para qualquer API em produção. Configure alertas antes de precisar deles."
            ),
        ]),
    ]
)


# ─────────────────────────────────────────────────────────────────────────────
# CURSO 6 — APIs REST COM FASTAPI
# ─────────────────────────────────────────────────────────────────────────────
FASTAPI_COURSE = Course(
    id="fastapi-rest-api",
    title="APIs REST com FastAPI",
    tagline="Construa APIs modernas, rápidas e bem documentadas com Python",
    description="FastAPI do zero à produção. Rotas, validação com Pydantic, autenticação JWT, banco de dados async e testes automáticos.",
    level="Iniciante → Avançado",
    category="Backend",
    duration_hours=20,
    skills=["FastAPI", "Python", "REST API", "Pydantic", "SQLAlchemy", "JWT", "Pytest"],
    color="#10b981",
    modules=[
        Module("fa-m1", "Fundamentos do FastAPI", "Entenda por que FastAPI é o framework Python mais rápido e moderno.", [
            Lesson("fa-m1-l1", "Por que FastAPI e como funciona", 15,
                "FastAPI combina velocidade de Go com a produtividade de Python. Entenda a base antes de codar.",
                [
                    Section("FastAPI vs Flask vs Django REST", "FastAPI: async nativo, validação automática, documentação gerada, tipos Python. Flask: minimalista, sem opinião. Django REST: completo mas pesado. Para APIs novas em 2024, FastAPI é a escolha padrão.", "# Instalar\npip install fastapi uvicorn[standard] pydantic\n\n# API mínima funcional\nfrom fastapi import FastAPI\n\napp = FastAPI(title='Minha API', version='1.0.0')\n\n@app.get('/')\ndef root():\n    return {'message': 'API funcionando!'}\n\n@app.get('/health')\ndef health():\n    return {'status': 'ok'}\n\n# Rodar\n# uvicorn main:app --reload", "python"),
                    Section("Type Hints e Documentação Automática", "FastAPI usa type hints do Python para validar dados E gerar documentação Swagger automaticamente.", "from fastapi import FastAPI\nfrom pydantic import BaseModel\nfrom typing import Optional\n\napp = FastAPI()\n\nclass Produto(BaseModel):\n    nome: str\n    preco: float\n    estoque: int = 0\n    descricao: Optional[str] = None\n\n@app.post('/produtos', response_model=Produto, status_code=201)\ndef criar_produto(produto: Produto):\n    # FastAPI valida automaticamente o body\n    # Se preco for string, retorna 422 com detalhe do erro\n    return produto\n\n# Documentação disponível em:\n# http://localhost:8000/docs  (Swagger UI)\n# http://localhost:8000/redoc (ReDoc)", "python"),
                    Section("Path, Query e Body Parameters", "FastAPI distingue automaticamente parâmetros de rota, query string e body pelo tipo.", "from fastapi import FastAPI, Query, Path\nfrom typing import Optional\n\napp = FastAPI()\n\n@app.get('/produtos/{produto_id}')\ndef get_produto(\n    produto_id: int = Path(..., ge=1, description='ID do produto'),\n    incluir_estoque: bool = Query(False),\n    campos: Optional[list[str]] = Query(None),\n):\n    # produto_id: da URL /produtos/42\n    # incluir_estoque: de /produtos/42?incluir_estoque=true\n    # campos: de /produtos/42?campos=nome&campos=preco\n    return {'id': produto_id, 'campos': campos}", "python"),
                ],
                exercise="Crie uma API com 3 endpoints: listar produtos, buscar por ID e criar produto. Use Pydantic para validação.",
                takeaway="FastAPI gera documentação, valida dados e é async por padrão — tudo que Flask e Django REST precisam de extensões para fazer."
            ),
            Lesson("fa-m1-l2", "Pydantic: Validação Avançada", 20,
                "Pydantic é o coração da validação no FastAPI. Validação poderosa com zero código extra.",
                [
                    Section("Modelos Pydantic com Validação", "Validators garantem que dados inválidos nunca chegam no código de negócio.", "from pydantic import BaseModel, Field, field_validator, model_validator\nfrom typing import Optional\nimport re\n\nclass UsuarioCriar(BaseModel):\n    nome: str = Field(..., min_length=2, max_length=100)\n    email: str = Field(..., description='Email válido')\n    senha: str = Field(..., min_length=8)\n    cpf: Optional[str] = None\n\n    @field_validator('email')\n    @classmethod\n    def email_valido(cls, v):\n        if '@' not in v or '.' not in v.split('@')[1]:\n            raise ValueError('Email inválido')\n        return v.lower()\n\n    @field_validator('cpf')\n    @classmethod\n    def cpf_formato(cls, v):\n        if v and not re.match(r'^\\d{11}$', re.sub(r'[.\\-]', '', v)):\n            raise ValueError('CPF deve ter 11 dígitos')\n        return v", "python"),
                    Section("Response Models e Schemas Separados", "Nunca retorne o mesmo modelo que recebe. Crie schemas separados: Create, Update, Response.", "from pydantic import BaseModel\nfrom datetime import datetime\nfrom typing import Optional\n\n# Schema de criação (recebido da API)\nclass ProdutoCreate(BaseModel):\n    nome: str\n    preco: float\n    categoria_id: int\n\n# Schema de atualização (todos opcionais)\nclass ProdutoUpdate(BaseModel):\n    nome: Optional[str] = None\n    preco: Optional[float] = None\n    ativo: Optional[bool] = None\n\n# Schema de resposta (o que a API retorna)\nclass ProdutoResponse(BaseModel):\n    id: int\n    nome: str\n    preco: float\n    ativo: bool\n    criado_em: datetime\n\n    class Config:\n        from_attributes = True  # ler de ORM models", "python"),
                    Section("Pydantic Settings: Configuração Typesafe", "Pydantic lê variáveis de ambiente e valida tipos automaticamente — sem os.getenv() espalhados pelo código.", "from pydantic_settings import BaseSettings\nfrom functools import lru_cache\n\nclass Settings(BaseSettings):\n    app_name: str = 'Minha API'\n    debug: bool = False\n    database_url: str\n    secret_key: str\n    jwt_expire_minutes: int = 30\n    allowed_origins: list[str] = ['http://localhost:3000']\n\n    class Config:\n        env_file = '.env'\n        env_file_encoding = 'utf-8'\n\n@lru_cache\ndef get_settings() -> Settings:\n    return Settings()\n\n# Usar na aplicação\nfrom fastapi import Depends\n\n@app.get('/info')\ndef info(settings: Settings = Depends(get_settings)):\n    return {'app': settings.app_name, 'debug': settings.debug}", "python"),
                ],
                exercise="Implemente schemas separados para criar, atualizar e responder para a entidade Produto. Adicione validação de preço positivo e nome único.",
                takeaway="Schemas separados (Create/Update/Response) evitam expor campos internos e facilitam evolução da API sem breaking changes."
            ),
            Lesson("fa-m1-l3", "Tratamento de Erros e Middleware", 18,
                "APIs profissionais têm erros consistentes e logging estruturado — não stack traces expostos.",
                [
                    Section("HTTPException e Erros Customizados", "Padronize erros com HTTPException. Crie exceções de domínio para manter o código de negócio limpo.", "from fastapi import FastAPI, HTTPException\nfrom fastapi.responses import JSONResponse\nfrom pydantic import BaseModel\n\napp = FastAPI()\n\nclass ErrorResponse(BaseModel):\n    error: str\n    detail: str\n    code: str\n\n# Exceção de domínio\nclass ProdutoNaoEncontrado(Exception):\n    def __init__(self, produto_id: int):\n        self.produto_id = produto_id\n\n# Handler global\n@app.exception_handler(ProdutoNaoEncontrado)\ndef produto_nao_encontrado_handler(request, exc):\n    return JSONResponse(\n        status_code=404,\n        content={'error': 'Produto não encontrado',\n                 'detail': f'ID {exc.produto_id} não existe',\n                 'code': 'PRODUTO_NOT_FOUND'}\n    )\n\n@app.get('/produtos/{id}')\ndef get_produto(id: int):\n    produto = db.get(id)\n    if not produto:\n        raise ProdutoNaoEncontrado(id)  # limpo!", "python"),
                    Section("Middleware de Logging", "Logue cada request com método, path, status e tempo — essencial para debug em produção.", "import time\nimport uuid\nfrom fastapi import FastAPI, Request\nfrom loguru import logger\n\napp = FastAPI()\n\n@app.middleware('http')\nasync def logging_middleware(request: Request, call_next):\n    request_id = str(uuid.uuid4())[:8]\n    inicio = time.time()\n\n    logger.info(f'[{request_id}] {request.method} {request.url.path} started')\n\n    response = await call_next(request)\n\n    duracao = (time.time() - inicio) * 1000\n    logger.info(\n        f'[{request_id}] {request.method} {request.url.path} '\n        f'→ {response.status_code} ({duracao:.1f}ms)'\n    )\n\n    response.headers['X-Request-ID'] = request_id\n    return response", "python"),
                    Section("CORS e Rate Limiting", "Configure CORS para o frontend acessar e rate limiting para evitar abuso.", "from fastapi import FastAPI\nfrom fastapi.middleware.cors import CORSMiddleware\nfrom slowapi import Limiter, _rate_limit_exceeded_handler\nfrom slowapi.util import get_remote_address\nfrom slowapi.errors import RateLimitExceeded\n\napp = FastAPI()\nlimiter = Limiter(key_func=get_remote_address)\napp.state.limiter = limiter\napp.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)\n\n# CORS\napp.add_middleware(\n    CORSMiddleware,\n    allow_origins=['https://meusite.com'],\n    allow_methods=['GET', 'POST', 'PUT', 'DELETE'],\n    allow_headers=['Authorization', 'Content-Type'],\n)\n\n@app.post('/login')\n@limiter.limit('5/minute')  # máximo 5 tentativas por minuto\nasync def login(request: Request, dados: LoginData):\n    return autenticar(dados)", "python"),
                ],
                exercise="Implemente middleware de logging com request ID e tratamento global de exceções com formato de erro consistente.",
                takeaway="APIs sem logging estruturado são impossíveis de debugar em produção. Request ID rastreável é o mínimo para qualquer API."
            ),
        ]),
        Module("fa-m2", "Banco de Dados Async com SQLAlchemy", "Acesso a banco de dados moderno com ORM async.", [
            Lesson("fa-m2-l1", "SQLAlchemy 2.x Async", 25,
                "SQLAlchemy 2.x com modo async é o padrão para FastAPI. Aprenda a configurar corretamente.",
                [
                    Section("Configuração do Banco Async", "AsyncEngine + AsyncSession é a combinação correta para FastAPI. Sessão por request via Depends.", "from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker\nfrom sqlalchemy.orm import DeclarativeBase\nfrom fastapi import Depends\nfrom typing import AsyncGenerator\n\n# Engine\nDATABASE_URL = 'postgresql+asyncpg://user:pass@localhost/mydb'\nengine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)\n\nAsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)\n\nclass Base(DeclarativeBase):\n    pass\n\n# Dependency: sessão por request\nasync def get_db() -> AsyncGenerator[AsyncSession, None]:\n    async with AsyncSessionLocal() as session:\n        try:\n            yield session\n            await session.commit()\n        except Exception:\n            await session.rollback()\n            raise", "python"),
                    Section("Models SQLAlchemy 2.x", "A sintaxe Mapped[] é o padrão moderno — type-safe e sem magic strings.", "from sqlalchemy import String, ForeignKey, Numeric, func\nfrom sqlalchemy.orm import Mapped, mapped_column, relationship\nfrom datetime import datetime\nfrom decimal import Decimal\n\nclass Produto(Base):\n    __tablename__ = 'produtos'\n\n    id: Mapped[int] = mapped_column(primary_key=True)\n    nome: Mapped[str] = mapped_column(String(200), nullable=False)\n    preco: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)\n    ativo: Mapped[bool] = mapped_column(default=True)\n    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())\n    categoria_id: Mapped[int] = mapped_column(ForeignKey('categorias.id'))\n\n    categoria: Mapped['Categoria'] = relationship(back_populates='produtos')", "python"),
                    Section("Queries Async com select()", "SQLAlchemy 2.x usa select() explícito. Sempre carregue relacionamentos explicitamente — evita N+1.", "from sqlalchemy import select\nfrom sqlalchemy.orm import selectinload\nfrom sqlalchemy.ext.asyncio import AsyncSession\n\nasync def get_produto(db: AsyncSession, produto_id: int):\n    result = await db.execute(\n        select(Produto)\n        .where(Produto.id == produto_id)\n        .where(Produto.ativo == True)\n    )\n    return result.scalar_one_or_none()\n\nasync def listar_produtos(db: AsyncSession, skip: int = 0, limit: int = 20):\n    result = await db.execute(\n        select(Produto)\n        .options(selectinload(Produto.categoria))  # evita N+1\n        .order_by(Produto.criado_em.desc())\n        .offset(skip)\n        .limit(limit)\n    )\n    return result.scalars().all()", "python"),
                ],
                exercise="Configure SQLAlchemy async com PostgreSQL. Crie models para Produto e Categoria com relacionamento. Implemente CRUD completo.",
                takeaway="expire_on_commit=False evita erros de sessão fechada. selectinload é obrigatório para relacionamentos — sem ele, cada acesso vira uma query extra."
            ),
            Lesson("fa-m2-l2", "Repository Pattern e Service Layer", 20,
                "Organização que separa acesso a dados da lógica de negócio — o código fica testável e manutenível.",
                [
                    Section("Repository: Abstrair o Banco", "Repository isola queries do SQLAlchemy. Facilita testes e troca de banco no futuro.", "from sqlalchemy.ext.asyncio import AsyncSession\nfrom sqlalchemy import select, func\nfrom app.models import Produto\n\nclass ProdutoRepository:\n    def __init__(self, db: AsyncSession):\n        self.db = db\n\n    async def get_by_id(self, id: int) -> Produto | None:\n        result = await self.db.execute(select(Produto).where(Produto.id == id))\n        return result.scalar_one_or_none()\n\n    async def list(self, skip: int = 0, limit: int = 20) -> list[Produto]:\n        result = await self.db.execute(\n            select(Produto).where(Produto.ativo == True)\n            .order_by(Produto.criado_em.desc())\n            .offset(skip).limit(limit)\n        )\n        return list(result.scalars())\n\n    async def create(self, dados: dict) -> Produto:\n        produto = Produto(**dados)\n        self.db.add(produto)\n        await self.db.flush()  # flush sem commit\n        return produto\n\n    async def count(self) -> int:\n        result = await self.db.execute(select(func.count(Produto.id)))\n        return result.scalar_one()", "python"),
                    Section("Service Layer: Lógica de Negócio", "Service orquestra repositories e aplica regras de negócio. Não deve saber nada de HTTP.", "from app.repositories.produto import ProdutoRepository\nfrom app.schemas.produto import ProdutoCreate, ProdutoUpdate\nfrom app.exceptions import ProdutoNaoEncontrado, NomeJaExiste\n\nclass ProdutoService:\n    def __init__(self, repo: ProdutoRepository):\n        self.repo = repo\n\n    async def criar(self, dados: ProdutoCreate) -> dict:\n        # Regra de negócio: nome único\n        existente = await self.repo.get_by_nome(dados.nome)\n        if existente:\n            raise NomeJaExiste(dados.nome)\n\n        # Regra: preço mínimo\n        if dados.preco < 0.01:\n            raise ValueError('Preço deve ser maior que zero')\n\n        produto = await self.repo.create(dados.model_dump())\n        return produto\n\n    async def atualizar(self, id: int, dados: ProdutoUpdate) -> dict:\n        produto = await self.repo.get_by_id(id)\n        if not produto:\n            raise ProdutoNaoEncontrado(id)\n        return await self.repo.update(id, dados.model_dump(exclude_none=True))", "python"),
                    Section("Dependency Injection no FastAPI", "FastAPI injeta dependências automaticamente. Encadeie Repository → Service → Router limpo.", "from fastapi import APIRouter, Depends, status\nfrom sqlalchemy.ext.asyncio import AsyncSession\nfrom app.database import get_db\nfrom app.repositories.produto import ProdutoRepository\nfrom app.services.produto import ProdutoService\nfrom app.schemas.produto import ProdutoCreate, ProdutoResponse\n\nrouter = APIRouter(prefix='/produtos', tags=['Produtos'])\n\ndef get_produto_service(db: AsyncSession = Depends(get_db)) -> ProdutoService:\n    return ProdutoService(ProdutoRepository(db))\n\n@router.post('/', response_model=ProdutoResponse, status_code=status.HTTP_201_CREATED)\nasync def criar_produto(\n    dados: ProdutoCreate,\n    service: ProdutoService = Depends(get_produto_service)\n):\n    return await service.criar(dados)", "python"),
                ],
                exercise="Implemente o padrão Repository + Service para a entidade Pedido. O Service deve validar estoque antes de confirmar o pedido.",
                takeaway="Repository abstrai o banco, Service abstrai negócio, Router abstrai HTTP. Cada camada tem uma responsabilidade — isso é o que torna o código testável."
            ),
            Lesson("fa-m2-l3", "Migrations com Alembic", 18,
                "Alembic versiona o schema do banco igual o Git versiona código — essencial para times.",
                [
                    Section("Configurar Alembic com SQLAlchemy Async", "Setup inicial do Alembic adaptado para uso com engine assíncrono.", "# Instalar\npip install alembic\n\n# Inicializar\nalembic init alembic\n\n# alembic/env.py — configurar para async\nfrom sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine\nfrom alembic import context\nfrom app.database import DATABASE_URL\nfrom app.models import Base\n\ntarget_metadata = Base.metadata\n\ndef run_migrations_offline():\n    context.configure(url=DATABASE_URL, target_metadata=target_metadata)\n    with context.begin_transaction():\n        context.run_migrations()\n\nasync def run_migrations_online():\n    engine: AsyncEngine = create_async_engine(DATABASE_URL)\n    async with engine.connect() as conn:\n        await conn.run_sync(lambda sync_conn: context.configure(\n            connection=sync_conn, target_metadata=target_metadata\n        ))\n        async with conn.begin():\n            await conn.run_sync(lambda _: context.run_migrations())", "python"),
                    Section("Criar e Aplicar Migrations", "Fluxo diário: modificar model → gerar migration → revisar → aplicar.", "# Gerar migration automática (detecta mudanças nos models)\nalembic revision --autogenerate -m 'add_coluna_descricao_produto'\n\n# SEMPRE revisar o arquivo gerado antes de aplicar!\n# alembic/versions/abc123_add_coluna.py\n\n# Aplicar migrations pendentes\nalembic upgrade head\n\n# Ver histórico\nalembic history\nalembic current\n\n# Reverter última migration (rollback)\nalembic downgrade -1\n\n# Reverter para versão específica\nalembic downgrade abc123\n\n# Ver SQL sem executar\nalembic upgrade head --sql", "bash"),
                    Section("Data Migrations: Transformar Dados", "Algumas mudanças precisam migrar dados, não só schema.", "\"\"\"Migrar telefones para formato internacional\"\"\"\nfrom alembic import op\nimport sqlalchemy as sa\nfrom sqlalchemy.sql import text\n\ndef upgrade() -> None:\n    # 1. Adicionar coluna nova\n    op.add_column('usuarios', sa.Column('telefone_intl', sa.String(20)))\n\n    # 2. Migrar dados\n    conn = op.get_bind()\n    conn.execute(text(\"\"\"\n        UPDATE usuarios\n        SET telefone_intl = '+55' || regexp_replace(telefone, '[^0-9]', '', 'g')\n        WHERE telefone IS NOT NULL\n    \"\"\"))\n\n    # 3. Remover coluna antiga\n    op.drop_column('usuarios', 'telefone')\n    op.alter_column('usuarios', 'telefone_intl', new_column_name='telefone')\n\ndef downgrade() -> None:\n    # Sempre implemente o downgrade!\n    op.add_column('usuarios', sa.Column('telefone_old', sa.String(20)))\n    # ... reverter transformação", "python"),
                ],
                exercise="Crie 3 migrations: adicionar tabela, adicionar coluna e uma data migration que formata dados existentes.",
                takeaway="Sempre implemente o downgrade. Sempre revise o SQL gerado antes de aplicar em produção. Migrations são código — commite no Git."
            ),
        ]),
        Module("fa-m3", "Autenticação JWT e Testes", "Segurança e qualidade — os dois pilares de uma API em produção.", [
            Lesson("fa-m3-l1", "Autenticação JWT Completa", 25,
                "JWT é o padrão para autenticação stateless em APIs. Implemente de forma segura e correta.",
                [
                    Section("Login e Geração de Token", "Nunca armazene senha em plaintext. Use bcrypt para hash. JWT contém claims no payload — não coloque dados sensíveis.", "from datetime import datetime, timedelta\nfrom jose import JWTError, jwt\nfrom passlib.context import CryptContext\nfrom app.config import get_settings\n\npwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')\n\ndef hash_senha(senha: str) -> str:\n    return pwd_context.hash(senha)\n\ndef verificar_senha(senha: str, hash: str) -> bool:\n    return pwd_context.verify(senha, hash)\n\ndef criar_token(data: dict, expire_minutes: int = 30) -> str:\n    settings = get_settings()\n    payload = data.copy()\n    payload['exp'] = datetime.utcnow() + timedelta(minutes=expire_minutes)\n    payload['iat'] = datetime.utcnow()\n    return jwt.encode(payload, settings.secret_key, algorithm='HS256')\n\n@app.post('/auth/login')\nasync def login(form: OAuth2PasswordRequestForm = Depends(), db = Depends(get_db)):\n    usuario = await auth_service.autenticar(db, form.username, form.password)\n    if not usuario:\n        raise HTTPException(status_code=401, detail='Credenciais inválidas')\n    token = criar_token({'sub': str(usuario.id), 'email': usuario.email})\n    return {'access_token': token, 'token_type': 'bearer'}", "python"),
                    Section("Middleware de Autenticação", "get_current_user é injetado como Depends — protege rotas sem repetição de código.", "from fastapi import Depends, HTTPException, status\nfrom fastapi.security import OAuth2PasswordBearer\nfrom jose import JWTError, jwt\n\noauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')\n\nasync def get_current_user(\n    token: str = Depends(oauth2_scheme),\n    db: AsyncSession = Depends(get_db)\n):\n    credentials_exception = HTTPException(\n        status_code=status.HTTP_401_UNAUTHORIZED,\n        detail='Token inválido ou expirado',\n        headers={'WWW-Authenticate': 'Bearer'},\n    )\n    try:\n        payload = jwt.decode(token, settings.secret_key, algorithms=['HS256'])\n        user_id: str = payload.get('sub')\n        if user_id is None:\n            raise credentials_exception\n    except JWTError:\n        raise credentials_exception\n\n    usuario = await user_repo.get_by_id(db, int(user_id))\n    if not usuario or not usuario.ativo:\n        raise credentials_exception\n    return usuario\n\n# Usar em rotas protegidas\n@app.get('/me')\nasync def me(usuario = Depends(get_current_user)):\n    return usuario", "python"),
                    Section("Refresh Token e Logout Seguro", "Access token expira em 15-30min. Refresh token em 7-30 dias. Logout invalida o refresh token.", "import secrets\nfrom app.models import RefreshToken\n\nasync def criar_refresh_token(user_id: int, db: AsyncSession) -> str:\n    token = secrets.token_urlsafe(32)\n    expires = datetime.utcnow() + timedelta(days=30)\n\n    refresh = RefreshToken(user_id=user_id, token=token, expires_at=expires)\n    db.add(refresh)\n    await db.flush()\n    return token\n\n@app.post('/auth/refresh')\nasync def refresh(refresh_token: str, db = Depends(get_db)):\n    token_db = await token_repo.get_valid(db, refresh_token)\n    if not token_db:\n        raise HTTPException(401, 'Refresh token inválido')\n\n    novo_access = criar_token({'sub': str(token_db.user_id)})\n    return {'access_token': novo_access, 'token_type': 'bearer'}\n\n@app.post('/auth/logout')\nasync def logout(refresh_token: str, db = Depends(get_db)):\n    await token_repo.revogar(db, refresh_token)\n    return {'message': 'Logout realizado'}", "python"),
                ],
                exercise="Implemente autenticação completa: registro, login, refresh token e logout. Proteja rotas com Depends(get_current_user).",
                takeaway="Access token curto (15-30min) + refresh token longo (30 dias) é o padrão seguro. Nunca armazene senha ou dados sensíveis no JWT payload."
            ),
            Lesson("fa-m3-l2", "Testes com Pytest e HTTPX", 22,
                "API sem testes é API que vai quebrar em produção. Aprenda a testar endpoints async corretamente.",
                [
                    Section("Configuração de Testes Async", "pytest-asyncio + banco de dados de teste em SQLite em memória — rápido e isolado.", "# conftest.py\nimport pytest\nimport pytest_asyncio\nfrom httpx import AsyncClient, ASGITransport\nfrom sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker\nfrom app.main import app\nfrom app.database import get_db, Base\n\nDATABASE_URL_TEST = 'sqlite+aiosqlite:///:memory:'\n\n@pytest_asyncio.fixture\nasync def db_test():\n    engine = create_async_engine(DATABASE_URL_TEST)\n    async with engine.begin() as conn:\n        await conn.run_sync(Base.metadata.create_all)\n\n    AsyncTestSession = async_sessionmaker(engine, class_=AsyncSession)\n    async with AsyncTestSession() as session:\n        yield session\n\n    async with engine.begin() as conn:\n        await conn.run_sync(Base.metadata.drop_all)\n\n@pytest_asyncio.fixture\nasync def client(db_test):\n    app.dependency_overrides[get_db] = lambda: db_test\n    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as c:\n        yield c\n    app.dependency_overrides.clear()", "python"),
                    Section("Testar Endpoints CRUD", "Teste o happy path e os casos de erro. Cada teste é independente e não depende de estado global.", "import pytest\nfrom httpx import AsyncClient\n\n@pytest.mark.asyncio\nasync def test_criar_produto_sucesso(client: AsyncClient):\n    response = await client.post('/produtos', json={\n        'nome': 'Produto Teste',\n        'preco': 29.90,\n        'categoria_id': 1\n    })\n    assert response.status_code == 201\n    data = response.json()\n    assert data['nome'] == 'Produto Teste'\n    assert data['id'] is not None\n\n@pytest.mark.asyncio\nasync def test_criar_produto_preco_invalido(client: AsyncClient):\n    response = await client.post('/produtos', json={\n        'nome': 'Teste',\n        'preco': -10,  # inválido!\n    })\n    assert response.status_code == 422\n\n@pytest.mark.asyncio\nasync def test_buscar_produto_inexistente(client: AsyncClient):\n    response = await client.get('/produtos/99999')\n    assert response.status_code == 404\n    assert response.json()['code'] == 'PRODUTO_NOT_FOUND'", "python"),
                    Section("Testar Rotas Autenticadas", "Fixtures de usuário autenticado para não repetir login em cada teste.", "import pytest\nfrom httpx import AsyncClient\n\n@pytest.fixture\nasync def token_admin(client: AsyncClient):\n    # Criar usuário\n    await client.post('/auth/registro', json={\n        'email': 'admin@test.com',\n        'senha': 'senha123',\n        'nome': 'Admin Test'\n    })\n    # Login\n    response = await client.post('/auth/login', data={\n        'username': 'admin@test.com',\n        'password': 'senha123'\n    })\n    return response.json()['access_token']\n\n@pytest.mark.asyncio\nasync def test_criar_produto_sem_auth(client: AsyncClient):\n    response = await client.post('/produtos', json={'nome': 'x', 'preco': 10})\n    assert response.status_code == 401\n\n@pytest.mark.asyncio\nasync def test_criar_produto_com_auth(client: AsyncClient, token_admin: str):\n    response = await client.post(\n        '/produtos',\n        json={'nome': 'Produto Auth', 'preco': 10},\n        headers={'Authorization': f'Bearer {token_admin}'}\n    )\n    assert response.status_code == 201", "python"),
                ],
                exercise="Escreva testes para todos os endpoints da sua API: CRUD completo + casos de erro + rotas autenticadas. Meça cobertura com pytest-cov.",
                takeaway="dependency_overrides é o segredo dos testes FastAPI — substitui o banco real por um em memória sem mudar o código de produção."
            ),
            Lesson("fa-m3-l3", "Documentação e Deploy em Produção", 20,
                "API sem documentação não existe para quem vai consumir. Deploy sem processo não escala.",
                [
                    Section("Documentação Rica no FastAPI", "Enriqueça o Swagger automático com exemplos, descrições e agrupamento por tags.", "from fastapi import FastAPI\nfrom pydantic import BaseModel, Field\n\napp = FastAPI(\n    title='API de Produtos',\n    description=''\'\nAPI REST para gerenciamento de produtos.\n\n## Autenticação\nUse `/auth/login` para obter um Bearer token.\n\n## Rate Limiting\nMáximo de 100 requests/minuto por IP.\n''\',\n    version='1.0.0',\n    contact={'name': 'Time Backend', 'email': 'api@empresa.com'},\n    license_info={'name': 'Proprietário'},\n)\n\nclass ProdutoCreate(BaseModel):\n    nome: str = Field(\n        ..., min_length=2, max_length=200,\n        description='Nome do produto',\n        examples=['Notebook Dell XPS 15']\n    )\n    preco: float = Field(\n        ..., gt=0,\n        description='Preço em reais (R$)',\n        examples=[2999.90]\n    )", "python"),
                    Section("Deploy com Docker e Uvicorn", "Em produção, use múltiplos workers Uvicorn atrás do Gunicorn — melhor uso de múltiplos cores.", "# Dockerfile de produção\nFROM python:3.12-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\nRUN useradd -m appuser && chown -R appuser /app\nUSER appuser\n\n# Gunicorn com workers Uvicorn\nCMD [\"gunicorn\", \"main:app\",\n     \"-w\", \"4\",\n     \"-k\", \"uvicorn.workers.UvicornWorker\",\n     \"--bind\", \"0.0.0.0:8000\",\n     \"--timeout\", \"60\",\n     \"--access-logfile\", \"-\"]\n\n# Calcular workers: 2 * CPU_CORES + 1\n# 2 CPUs → 5 workers", "dockerfile"),
                    Section("Health Check e Graceful Shutdown", "Health check correto verifica banco e dependências. Graceful shutdown finaliza requests em andamento.", "from fastapi import FastAPI\nfrom contextlib import asynccontextmanager\nimport asyncpg\n\n@asynccontextmanager\nasync def lifespan(app: FastAPI):\n    # Startup: inicializar pool de conexões\n    app.state.db_pool = await asyncpg.create_pool(DATABASE_URL)\n    print('Banco conectado!')\n    yield\n    # Shutdown: fechar conexões gracefully\n    await app.state.db_pool.close()\n    print('Conexões fechadas.')\n\napp = FastAPI(lifespan=lifespan)\n\n@app.get('/health')\nasync def health(request: Request):\n    try:\n        async with request.app.state.db_pool.acquire() as conn:\n            await conn.fetchval('SELECT 1')\n        return {'status': 'ok', 'database': 'connected'}\n    except Exception as e:\n        raise HTTPException(503, detail=f'Database unavailable: {e}')", "python"),
                ],
                exercise="Adicione documentação rica com exemplos e tags. Configure o Dockerfile de produção com Gunicorn + Uvicorn workers.",
                takeaway="lifespan substitui @app.on_event (deprecado). Gunicorn + Uvicorn workers é a combinação de produção. Health check que verifica o banco realmente funciona."
            ),
        ]),
        Module("fa-m4", "Projeto Final: API Completa", "Construa uma API de e-commerce do zero ao deploy.", [
            Lesson("fa-m4-l1", "Modelagem e Estrutura do Projeto", 20,
                "Boa estrutura de projeto evita dependências circulares e facilita crescimento.",
                [
                    Section("Estrutura de Pastas Profissional", "Separe por camada (models, schemas, services, routers) ou por domínio (produtos, pedidos, auth).", "# Estrutura recomendada (por domínio)\napp/\n├── main.py              # FastAPI app + lifespan\n├── database.py          # engine + sessão\n├── config.py            # settings Pydantic\n├── auth/\n│   ├── models.py\n│   ├── schemas.py\n│   ├── service.py\n│   └── router.py\n├── produtos/\n│   ├── models.py\n│   ├── schemas.py\n│   ├── repository.py\n│   ├── service.py\n│   └── router.py\n├── pedidos/\n│   └── ...\nalembic/\ntests/\n│   ├── conftest.py\n│   ├── test_auth.py\n│   ├── test_produtos.py\n│   └── test_pedidos.py\nDockerfile\ndocker-compose.yml\npyproject.toml", "bash"),
                    Section("main.py: Lifespan e Routers", "Centralize registro de routers e configuração de middleware em main.py.", "from fastapi import FastAPI\nfrom contextlib import asynccontextmanager\nfrom app.database import engine, Base\nfrom app.auth.router import router as auth_router\nfrom app.produtos.router import router as produtos_router\nfrom app.pedidos.router import router as pedidos_router\n\n@asynccontextmanager\nasync def lifespan(app: FastAPI):\n    async with engine.begin() as conn:\n        await conn.run_sync(Base.metadata.create_all)\n    yield\n\napp = FastAPI(\n    title='E-commerce API',\n    version='1.0.0',\n    lifespan=lifespan\n)\n\n# Middlewares\napp.add_middleware(CORSMiddleware, allow_origins=['*'])\n\n# Routers\napp.include_router(auth_router, prefix='/auth', tags=['Auth'])\napp.include_router(produtos_router, prefix='/produtos', tags=['Produtos'])\napp.include_router(pedidos_router, prefix='/pedidos', tags=['Pedidos'])", "python"),
                    Section("pyproject.toml: Configuração Centralizada", "pyproject.toml substitui setup.py, requirements.txt e configs de ferramentas espalhadas.", "[project]\nname = 'ecommerce-api'\nversion = '1.0.0'\nrequires-python = '>=3.12'\ndependencies = [\n    'fastapi>=0.110',\n    'uvicorn[standard]>=0.27',\n    'sqlalchemy>=2.0',\n    'asyncpg>=0.29',\n    'alembic>=1.13',\n    'pydantic-settings>=2.0',\n    'python-jose[cryptography]>=3.3',\n    'passlib[bcrypt]>=1.7',\n]\n\n[project.optional-dependencies]\ndev = ['pytest', 'pytest-asyncio', 'httpx', 'aiosqlite', 'pytest-cov']\n\n[tool.pytest.ini_options]\nasyncio_mode = 'auto'\n\n[tool.ruff]\nline-length = 100\nselect = ['E', 'F', 'I', 'N']", "toml"),
                ],
                exercise="Estruture o projeto completo de e-commerce seguindo a organização por domínio. Configure pyproject.toml com todas as dependências.",
                takeaway="Organização por domínio escala melhor que por camada — cada domínio pode crescer independentemente sem tocar nos outros."
            ),
            Lesson("fa-m4-l2", "Funcionalidades Avançadas", 22,
                "Background tasks, WebSockets e paginação cursor-based para uma API de nível profissional.",
                [
                    Section("Background Tasks: Processar sem Bloquear", "Background tasks executam após a resposta ser enviada — ideal para emails, notificações e cálculos pesados.", "from fastapi import FastAPI, BackgroundTasks\nfrom app.services.email import enviar_email_confirmacao\nfrom app.services.estoque import atualizar_estoque\n\napp = FastAPI()\n\n@app.post('/pedidos', status_code=201)\nasync def criar_pedido(\n    dados: PedidoCreate,\n    bg: BackgroundTasks,\n    db = Depends(get_db),\n    usuario = Depends(get_current_user)\n):\n    pedido = await pedido_service.criar(db, dados, usuario)\n\n    # Executado APÓS a resposta ser enviada\n    bg.add_task(enviar_email_confirmacao, pedido.id, usuario.email)\n    bg.add_task(atualizar_estoque, dados.itens)\n    bg.add_task(gerar_relatorio_diario)  # pode adicionar vários\n\n    return pedido  # responde imediatamente", "python"),
                    Section("Paginação Cursor-Based", "Paginação por offset quebra em grandes volumes (OFFSET 100000 é lento). Cursor-based escala para milhões de registros.", "from fastapi import Query\nfrom pydantic import BaseModel\nfrom typing import Optional, Generic, TypeVar\n\nT = TypeVar('T')\n\nclass PageCursor(BaseModel, Generic[T]):\n    items: list[T]\n    next_cursor: Optional[str] = None\n    has_more: bool\n\n@app.get('/produtos', response_model=PageCursor[ProdutoResponse])\nasync def listar_produtos(\n    limit: int = Query(20, ge=1, le=100),\n    cursor: Optional[str] = None,  # ID do último item\n    db = Depends(get_db)\n):\n    cursor_id = int(cursor) if cursor else None\n    query = select(Produto).where(Produto.ativo == True)\n\n    if cursor_id:\n        query = query.where(Produto.id < cursor_id)\n\n    query = query.order_by(Produto.id.desc()).limit(limit + 1)\n    result = await db.execute(query)\n    items = list(result.scalars())\n\n    has_more = len(items) > limit\n    if has_more:\n        items = items[:limit]\n\n    return PageCursor(\n        items=items,\n        next_cursor=str(items[-1].id) if has_more else None,\n        has_more=has_more\n    )", "python"),
                    Section("Cache com Redis", "Cache de resposta para endpoints lentos — leitura de Redis é 100x mais rápida que query ao banco.", "import json\nfrom fastapi import Depends\nfrom redis.asyncio import Redis\n\nasync def get_redis() -> Redis:\n    return Redis.from_url('redis://localhost', decode_responses=True)\n\n@app.get('/produtos/{id}', response_model=ProdutoResponse)\nasync def get_produto(\n    id: int,\n    db = Depends(get_db),\n    redis: Redis = Depends(get_redis)\n):\n    # Tentar cache primeiro\n    cache_key = f'produto:{id}'\n    cached = await redis.get(cache_key)\n    if cached:\n        return json.loads(cached)\n\n    # Cache miss: buscar no banco\n    produto = await produto_repo.get_by_id(db, id)\n    if not produto:\n        raise HTTPException(404, 'Produto não encontrado')\n\n    # Salvar no cache por 5 minutos\n    await redis.setex(cache_key, 300, json.dumps(produto.model_dump()))\n    return produto", "python"),
                ],
                exercise="Adicione background task para envio de email após criação de pedido e cache Redis nos endpoints de produto mais acessados.",
                takeaway="Background tasks para operações não-críticas na resposta. Cache Redis para leitura frequente. Paginação cursor-based para grandes volumes."
            ),
            Lesson("fa-m4-l3", "CI/CD e Monitoramento da API", 18,
                "Pipeline completo do commit ao deploy com zero downtime.",
                [
                    Section("GitHub Actions: Test + Build + Deploy", "O pipeline completo: testes → lint → build imagem → deploy com health check.", "# .github/workflows/api-deploy.yml\nname: API CI/CD\n\non:\n  push:\n    branches: [main]\n\njobs:\n  test:\n    runs-on: ubuntu-latest\n    services:\n      postgres:\n        image: postgres:16\n        env:\n          POSTGRES_PASSWORD: test\n        options: --health-cmd pg_isready\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with:\n          python-version: '3.12'\n      - run: pip install -e '.[dev]'\n      - run: pytest tests/ --cov=app --cov-report=xml\n      - run: ruff check .\n      - run: mypy app/\n\n  deploy:\n    needs: test\n    runs-on: ubuntu-latest\n    steps:\n      - name: Deploy\n        run: |\n          ssh server 'cd /api && git pull && docker compose up -d --build'\n          sleep 10\n          curl -f http://api.meusite.com/health || exit 1", "yaml"),
                    Section("OpenTelemetry: Tracing Distribuído", "Com microserviços, rastrear uma requisição através de múltiplos serviços é essencial.", "from opentelemetry import trace\nfrom opentelemetry.sdk.trace import TracerProvider\nfrom opentelemetry.sdk.trace.export import BatchSpanProcessor\nfrom opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter\nfrom opentelemetry.instrumentation.fastapi import FastAPIInstrumentor\nfrom opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor\n\n# Configurar tracer\nprovider = TracerProvider()\nprocessor = BatchSpanProcessor(OTLPSpanExporter(endpoint='http://jaeger:4317'))\nprovider.add_span_processor(processor)\ntrace.set_tracer_provider(provider)\n\n# Auto-instrumentar FastAPI e SQLAlchemy\nFastAPIInstrumentor.instrument_app(app)\nSQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)\n\n# Span customizado\ntracer = trace.get_tracer(__name__)\n\nasync def calcular_frete(cep: str, peso: float):\n    with tracer.start_as_current_span('calcular_frete') as span:\n        span.set_attribute('cep', cep)\n        span.set_attribute('peso_kg', peso)\n        resultado = await frete_service.calcular(cep, peso)\n        span.set_attribute('valor_frete', resultado)\n        return resultado", "python"),
                    Section("SLA e Error Budget", "Defina SLOs (Service Level Objectives) e monitore error budget — a prática de SRE para APIs.", "# Prometheus queries para SLO\n\n# SLO: 99.9% das requests em < 500ms\n# Error budget: 0.1% = ~43 minutos/mês de downtime\n\n# Query: taxa de sucesso nas últimas 24h\nrate(http_requests_total{status!~'5..'}[24h]) /\nrate(http_requests_total[24h])\n\n# Query: p99 de latência\nhistogram_quantile(0.99, rate(http_latency_seconds_bucket[5m]))\n\n# Alerta: error budget queimando rápido\nalert: ErrorBudgetBurning\nexpr: |\n  (1 - (\n    rate(http_requests_total{status!~'5..'}[1h]) /\n    rate(http_requests_total[1h])\n  )) > 0.001  # > 10x a taxa normal de erro\nfor: 5m\nseverity: page", "yaml"),
                ],
                exercise="Configure o pipeline CI/CD completo. Adicione OpenTelemetry e defina 3 alertas: latência p99, taxa de erro e disponibilidade.",
                takeaway="CI/CD + tracing distribuído + SLO = API de produção real. Sem esses 3, você gerencia por sorte, não por visibilidade."
            ),
        ]),
    ]
)


# ─────────────────────────────────────────────────────────────────────────────
# CATALOG — adicionar todos os cursos aqui
# ─────────────────────────────────────────────────────────────────────────────
COURSES: list[Course] = [SQL_COURSE, PYTHON_DATA_COURSE, ML_COURSE, GIT_COURSE, DOCKER_COURSE, FASTAPI_COURSE]
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
