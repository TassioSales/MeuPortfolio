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
# CURSO 7 — DATA ENGINEERING
# ─────────────────────────────────────────────────────────────────────────────
DATA_ENG_COURSE = Course(
    id="data-engineering",
    title="Data Engineering: Pipelines e Warehouses",
    tagline="Construa pipelines de dados confiáveis que alimentam analytics e ML",
    description="Aprenda a arquitetar e implementar pipelines ETL/ELT, Data Warehouses, orquestração com Airflow e processamento com Spark.",
    level="Intermediário → Avançado",
    category="Data",
    duration_hours=22,
    skills=["Python", "Apache Airflow", "Apache Spark", "dbt", "Data Warehouse", "ETL/ELT", "Parquet"],
    color="#f59e0b",
    modules=[
        Module("de-m1", "Fundamentos de Engenharia de Dados", "Entenda o papel do engenheiro de dados e os conceitos que estruturam todo o campo.", [
            Lesson("de-m1-l1", "O que faz um Engenheiro de Dados", 15,
                "Engenheiro de dados é o encanador da empresa: garante que dados fluam do ponto A ao ponto B de forma confiável, na hora certa e com qualidade.",
                [
                    Section("Data Engineer vs Data Scientist vs Analytics Engineer",
                        "Data Engineer: constrói e mantém pipelines e infraestrutura. Data Scientist: modela e analisa. Analytics Engineer (dbt): transforma dados brutos em modelos analíticos. Os três precisam um do outro.",
                        "# Responsabilidades por papel:\n\n# Data Engineer:\n# - Ingestão de dados (APIs, bancos, eventos)\n# - Pipelines ETL/ELT\n# - Data Warehouse / Data Lake\n# - Qualidade e confiabilidade dos dados\n# - Infraestrutura (Airflow, Spark, Kafka)\n\n# Analytics Engineer:\n# - Modelagem dimensional (dbt)\n# - Camadas: staging → intermediate → mart\n# - Documentação e testes de dados\n\n# Data Scientist:\n# - Feature engineering\n# - Treinamento de modelos\n# - Experimentos e análise estatística", "python"),
                    Section("Arquiteturas: Data Warehouse vs Data Lake vs Lakehouse",
                        "Data Warehouse: dados estruturados, schema-on-write, SQL. Data Lake: qualquer formato, schema-on-read, barato. Lakehouse: melhor dos dois — Delta Lake, Apache Iceberg.",
                        "# Data Warehouse (Redshift, BigQuery, Snowflake)\n# Vantagens: SQL padrão, performance, governança\n# Desvantagens: caro para volume alto, só estruturado\n\n# Data Lake (S3, GCS, ADLS)\n# Vantagens: barato, qualquer formato, escala\n# Desvantagens: vira 'data swamp' sem governança\n\n# Lakehouse (Delta Lake, Apache Iceberg, Apache Hudi)\n# Vantagens: ACID transactions no lake, SQL + ML\n# Uso: Databricks Delta Lake é o mais adotado\n\n# Exemplo de estrutura de pastas em um Data Lake:\n# s3://datalake/\n#   raw/          <- dados brutos, nunca modificados\n#   staging/      <- limpeza básica\n#   curated/      <- regras de negócio aplicadas\n#   serving/      <- prontos para consumo (DW, ML)", "bash"),
                    Section("Formatos de Arquivo: Parquet, Avro e Delta",
                        "CSV não tem lugar em pipelines de produção. Parquet é colunar, comprimido e 10-100x mais rápido para analytics.",
                        "import polars as pl\nimport pyarrow as pa\nimport pyarrow.parquet as pq\n\n# Escrever Parquet com compressão\ndf = pl.read_csv('vendas.csv')\ndf.write_parquet('vendas.parquet', compression='snappy')\n\n# Parquet com particionamento (essencial para datasets grandes)\ntabela = pa.Table.from_pandas(df.to_pandas())\npq.write_to_dataset(\n    tabela,\n    root_path='vendas_particionado/',\n    partition_cols=['ano', 'mes']  # s3://lake/vendas/ano=2024/mes=01/\n)\n\n# Ler com filtro de partição (só lê o que precisa)\ndf = pl.read_parquet(\n    'vendas_particionado/',\n    hive_partitioning=True\n).filter(pl.col('ano') == 2024)", "python"),
                ],
                exercise="Compare o tamanho e tempo de leitura de um CSV de 1M linhas vs o mesmo dado em Parquet com e sem particionamento.",
                takeaway="Parquet colunar + compressão Snappy é o padrão de fato para dados analíticos. CSV é aceitável apenas na entrada — nunca na saída de um pipeline."
            ),
            Lesson("de-m1-l2", "ETL vs ELT: Padrões de Ingestão", 20,
                "ETL transforma antes de carregar. ELT carrega bruto e transforma no warehouse. ELT venceu — entenda por quê.",
                [
                    Section("ETL: Extract, Transform, Load",
                        "ETL era o padrão quando armazenamento era caro. Transformar antes de carregar protegia o warehouse de dados sujos. Hoje, com cloud, ELT é mais flexível.",
                        "import pandas as pd\nfrom sqlalchemy import create_engine\n\n# ETL clássico: transformar antes de carregar\ndef extrair(conn_origem):\n    return pd.read_sql('SELECT * FROM vendas WHERE data >= CURRENT_DATE - 1', conn_origem)\n\ndef transformar(df: pd.DataFrame) -> pd.DataFrame:\n    return (\n        df\n        .rename(columns={'dt_venda': 'data_venda', 'vl_total': 'valor'})\n        .assign(\n            valor=lambda d: d['valor'].round(2),\n            data_venda=lambda d: pd.to_datetime(d['data_venda']),\n            mes=lambda d: d['data_venda'].dt.month,\n        )\n        .dropna(subset=['cliente_id', 'valor'])\n        .query('valor > 0')\n    )\n\ndef carregar(df: pd.DataFrame, conn_destino):\n    df.to_sql('fato_vendas', conn_destino, if_exists='append', index=False)\n    print(f'{len(df)} registros carregados')", "python"),
                    Section("ELT com dbt: Transformar no Warehouse",
                        "ELT: extrai bruto, carrega no warehouse, transforma com SQL/dbt. O warehouse faz a transformação — mais barato e mais flexível.",
                        "-- dbt model: models/staging/stg_vendas.sql\n-- Camada staging: apenas limpeza, sem regras de negócio\n\n{{ config(materialized='view') }}\n\nSELECT\n    id_venda                                    AS venda_id,\n    CAST(dt_venda AS DATE)                      AS data_venda,\n    COALESCE(id_cliente, -1)                    AS cliente_id,\n    UPPER(TRIM(status))                         AS status,\n    ROUND(CAST(vl_total AS NUMERIC), 2)         AS valor_total\nFROM {{ source('raw', 'vendas') }}\nWHERE dt_venda >= '2020-01-01'\n  AND vl_total > 0\n\n-- dbt model: models/marts/fct_vendas.sql\n-- Camada mart: regras de negócio aplicadas\n{{ config(materialized='table') }}\n\nSELECT\n    v.venda_id,\n    v.data_venda,\n    d.ano, d.mes, d.trimestre,\n    c.nome_cliente, c.segmento,\n    v.valor_total\nFROM {{ ref('stg_vendas') }} v\nLEFT JOIN {{ ref('dim_datas') }} d ON v.data_venda = d.data\nLEFT JOIN {{ ref('dim_clientes') }} c ON v.cliente_id = c.cliente_id", "sql"),
                    Section("Idempotência: Pipelines que Podem Ser Reexecutados",
                        "Um pipeline idempotente pode rodar N vezes e produzir o mesmo resultado. É o requisito mais importante de qualquer pipeline de produção.",
                        "# Ruim: INSERT simples (duplica dados se rodar 2x)\ndf.to_sql('fato_vendas', engine, if_exists='append')\n\n# Bom: UPSERT (INSERT or UPDATE)\nfrom sqlalchemy.dialects.postgresql import insert\n\ndef upsert(df: pd.DataFrame, engine, tabela: str, pk: list[str]):\n    records = df.to_dict('records')\n    stmt = insert(tabela_obj).values(records)\n    stmt = stmt.on_conflict_do_update(\n        index_elements=pk,\n        set_={col: stmt.excluded[col]\n              for col in df.columns if col not in pk}\n    )\n    with engine.begin() as conn:\n        conn.execute(stmt)\n\n# Melhor ainda: partição por data\n# Deletar partição do dia e reinserir (atomic)\ndef carregar_particao(df: pd.DataFrame, data: str):\n    with engine.begin() as conn:\n        conn.execute(f\"DELETE FROM fato_vendas WHERE data_venda = '{data}'\")\n        df.to_sql('fato_vendas', conn, if_exists='append', index=False)", "python"),
                ],
                exercise="Implemente um pipeline ELT idempotente: extrair de uma API, carregar em Parquet particionado e transformar com SQL.",
                takeaway="Idempotência não é opcional — pipelines falham e precisam ser reexecutados. DELETE + INSERT por partição é o padrão mais simples e confiável."
            ),
            Lesson("de-m1-l3", "Qualidade de Dados: Validação e Monitoramento", 20,
                "Dados ruins geram insights ruins. Validação automatizada é a defesa contra garbage-in garbage-out.",
                [
                    Section("Great Expectations: Testes Declarativos",
                        "Great Expectations valida dados com 'expectations' — regras que os dados devem satisfazer. Falha o pipeline se os dados violarem as regras.",
                        "import great_expectations as gx\n\ncontext = gx.get_context()\n\n# Criar suite de expectations\nsuite = context.add_expectation_suite('vendas_suite')\n\n# Definir expectations\nbatch = context.get_batch({'path': 'vendas.parquet'}, suite)\n\nbatch.expect_column_to_exist('valor_total')\nbatch.expect_column_values_to_not_be_null('cliente_id')\nbatch.expect_column_values_to_be_between('valor_total', min_value=0.01, max_value=1_000_000)\nbatch.expect_column_values_to_be_in_set('status', ['aprovado', 'cancelado', 'pendente'])\nbatch.expect_column_unique_value_count_to_be_between('status', min_value=1, max_value=3)\nbatch.expect_table_row_count_to_be_between(min_value=1000, max_value=10_000_000)\n\n# Rodar validação\nresults = context.run_validation_operator('action_list_operator', [batch])\nif not results['success']:\n    raise ValueError('Dados não passaram na validação!')", "python"),
                    Section("dbt Tests: Qualidade na Transformação",
                        "dbt tem testes embutidos: not_null, unique, accepted_values, relationships. Rodam depois de cada transformação.",
                        "# models/staging/schema.yml\nversion: 2\n\nmodels:\n  - name: stg_vendas\n    description: 'Vendas brutas limpas'\n    columns:\n      - name: venda_id\n        tests:\n          - not_null\n          - unique\n      - name: valor_total\n        tests:\n          - not_null\n          - dbt_utils.accepted_range:\n              min_value: 0.01\n      - name: status\n        tests:\n          - accepted_values:\n              values: ['aprovado', 'cancelado', 'pendente']\n      - name: cliente_id\n        tests:\n          - not_null\n          - relationships:\n              to: ref('dim_clientes')\n              field: cliente_id\n\n# Rodar testes\n# dbt test --select stg_vendas", "yaml"),
                    Section("Data Freshness: Alertas de Atraso",
                        "Dados atrasados são tão prejudiciais quanto dados incorretos. Monitore quando cada tabela foi atualizada.",
                        "-- dbt source freshness\n-- dbt_project.yml / sources.yml\nsources:\n  - name: raw\n    tables:\n      - name: vendas\n        loaded_at_field: updated_at\n        freshness:\n          warn_after: {count: 6, period: hour}\n          error_after: {count: 24, period: hour}\n\n-- Checar freshness\n-- dbt source freshness\n\n-- Query manual de freshness\nSELECT\n    table_name,\n    MAX(updated_at)                         AS ultima_atualizacao,\n    NOW() - MAX(updated_at)                 AS atraso,\n    CASE\n        WHEN NOW() - MAX(updated_at) > INTERVAL '6 hours' THEN 'ALERTA'\n        WHEN NOW() - MAX(updated_at) > INTERVAL '24 hours' THEN 'CRITICO'\n        ELSE 'OK'\n    END AS status\nFROM information_schema.tables t\nJOIN fato_vendas USING (table_name)\nGROUP BY table_name", "sql"),
                ],
                exercise="Configure Great Expectations para validar um dataset de vendas. Integre os testes em um pipeline Airflow — se a validação falhar, o pipeline para.",
                takeaway="Dados sem validação são dados não confiáveis. Valide na entrada (Great Expectations) e na transformação (dbt tests) — não só no final."
            ),
        ]),
        Module("de-m2", "Orquestração com Apache Airflow", "Agende, monitore e reexecute pipelines complexos com DAGs.", [
            Lesson("de-m2-l1", "DAGs e Operadores no Airflow", 25,
                "Airflow define pipelines como grafos acíclicos dirigidos (DAGs). Cada nó é uma tarefa. Aprenda a escrever DAGs profissionais.",
                [
                    Section("Estrutura de uma DAG",
                        "DAG define o fluxo, não executa nada. Tasks definem o trabalho. Dependências definem a ordem.",
                        "from airflow import DAG\nfrom airflow.operators.python import PythonOperator\nfrom airflow.operators.empty import EmptyOperator\nfrom datetime import datetime, timedelta\n\ndefault_args = {\n    'owner': 'data-engineering',\n    'retries': 3,\n    'retry_delay': timedelta(minutes=5),\n    'email_on_failure': True,\n    'email': ['data@empresa.com'],\n}\n\nwith DAG(\n    dag_id='pipeline_vendas_diario',\n    default_args=default_args,\n    schedule='0 6 * * *',  # todo dia às 06:00\n    start_date=datetime(2024, 1, 1),\n    catchup=False,          # não executar datas passadas\n    tags=['vendas', 'producao'],\n    doc_md='Pipeline diário de vendas — extrai do ERP, transforma e carrega no DW.',\n) as dag:\n\n    inicio = EmptyOperator(task_id='inicio')\n    extrair = PythonOperator(task_id='extrair', python_callable=extrair_vendas)\n    validar = PythonOperator(task_id='validar', python_callable=validar_dados)\n    carregar = PythonOperator(task_id='carregar', python_callable=carregar_dw)\n    fim = EmptyOperator(task_id='fim')\n\n    inicio >> extrair >> validar >> carregar >> fim", "python"),
                    Section("TaskFlow API: DAGs Modernas com Decoradores",
                        "TaskFlow API (Airflow 2.x) usa decoradores — código mais limpo, passagem de dados automática via XCom.",
                        "from airflow.decorators import dag, task\nfrom datetime import datetime\nimport pandas as pd\n\n@dag(\n    schedule='@daily',\n    start_date=datetime(2024, 1, 1),\n    catchup=False,\n    tags=['vendas']\n)\ndef pipeline_vendas():\n\n    @task()\n    def extrair() -> dict:\n        df = pd.read_sql('SELECT * FROM vendas WHERE data = CURRENT_DATE - 1', conn)\n        return {'linhas': len(df), 'path': df.to_parquet('/tmp/vendas_raw.parquet')}\n\n    @task()\n    def validar(info: dict) -> dict:\n        df = pd.read_parquet('/tmp/vendas_raw.parquet')\n        assert df['valor'].notna().all(), 'Valores nulos!'\n        assert (df['valor'] > 0).all(), 'Valores negativos!'\n        return {**info, 'validado': True}\n\n    @task()\n    def carregar(info: dict):\n        df = pd.read_parquet('/tmp/vendas_raw.parquet')\n        df.to_sql('fato_vendas', engine, if_exists='append')\n        print(f\"{info['linhas']} linhas carregadas\")\n\n    info = extrair()\n    info_val = validar(info)\n    carregar(info_val)\n\npipeline_vendas()", "python"),
                    Section("Backfill e Reprocessamento",
                        "Airflow permite reprocessar datas passadas — essencial quando uma fonte tinha dados errados.",
                        "# Reprocessar uma data específica\nairflow dags backfill pipeline_vendas_diario \\\n    --start-date 2024-01-15 \\\n    --end-date 2024-01-20\n\n# Limpar execuções com erro para reexecutar\nairflow tasks clear pipeline_vendas_diario \\\n    --start-date 2024-01-15 \\\n    --task-regex 'carregar.*'\n\n# No código: usar {{ ds }} para data de execução\n@task()\ndef extrair(ds=None):  # ds = execution date\n    query = f\"SELECT * FROM vendas WHERE data = '{ds}'\"\n    return pd.read_sql(query, conn).to_dict('records')", "bash"),
                ],
                exercise="Crie uma DAG com TaskFlow API que extrai dados de uma API pública, valida e salva em Parquet. Configure retry e alerta de email.",
                takeaway="catchup=False evita executar todas as datas passadas ao ativar uma DAG. TaskFlow API com decoradores é o padrão moderno do Airflow 2.x."
            ),
            Lesson("de-m2-l2", "Sensors, Hooks e Conexões", 18,
                "Sensors esperam por condições. Hooks abstraem conexões. Conexões centralizam credenciais — a tríade do Airflow profissional.",
                [
                    Section("Sensors: Esperar por Condições",
                        "Sensors pousam a execução até que uma condição seja verdadeira: arquivo no S3, registro no banco, API disponível.",
                        "from airflow.sensors.filesystem import FileSensor\nfrom airflow.providers.amazon.aws.sensors.s3 import S3KeySensor\nfrom airflow.sensors.python import PythonSensor\n\n# Esperar arquivo chegar no S3\naguardar_arquivo = S3KeySensor(\n    task_id='aguardar_arquivo_vendas',\n    bucket_name='meu-bucket',\n    bucket_key='raw/vendas/{{ ds }}/vendas.parquet',\n    poke_interval=300,    # verificar a cada 5 minutos\n    timeout=3600,         # timeout após 1 hora\n    mode='reschedule',    # libera worker enquanto espera\n)\n\n# Sensor customizado: esperar API estar disponível\ndef api_disponivel():\n    import requests\n    r = requests.get('https://api.erp.com/health', timeout=10)\n    return r.status_code == 200\n\naguardar_api = PythonSensor(\n    task_id='aguardar_api',\n    python_callable=api_disponivel,\n    poke_interval=60,\n    mode='reschedule',\n)", "python"),
                    Section("Hooks: Abstrair Conexões",
                        "Hooks encapsulam a lógica de conexão com sistemas externos. Use sempre em vez de hardcodar credenciais.",
                        "from airflow.providers.postgres.hooks.postgres import PostgresHook\nfrom airflow.providers.amazon.aws.hooks.s3 import S3Hook\nfrom airflow.hooks.base import BaseHook\nimport pandas as pd\n\n@task()\ndef extrair_do_banco():\n    # Hook usa a conexão configurada na UI do Airflow\n    hook = PostgresHook(postgres_conn_id='postgres_producao')\n    df = hook.get_pandas_df('SELECT * FROM vendas WHERE data = %(data)s',\n                             parameters={'data': '{{ ds }}'})\n    return df.to_dict('records')\n\n@task()\ndef salvar_no_s3(records: list):\n    import pandas as pd\n    df = pd.DataFrame(records)\n    s3 = S3Hook(aws_conn_id='aws_producao')\n    s3.load_string(\n        string_data=df.to_parquet(),\n        key='processed/vendas/{{ ds }}.parquet',\n        bucket_name='meu-bucket'\n    )", "python"),
                    Section("Gerenciar Conexões com Variáveis",
                        "Centralize credenciais nas Connections do Airflow — nunca hardcode em DAGs. Use Variables para configurações.",
                        "# Criar conexão via CLI\nairflow connections add postgres_producao \\\n    --conn-type postgres \\\n    --conn-host db.empresa.com \\\n    --conn-schema analytics \\\n    --conn-login user \\\n    --conn-password senha \\\n    --conn-port 5432\n\n# Criar variável\nairflow variables set DATA_LAKE_BUCKET meu-bucket-producao\n\n# Usar na DAG\nfrom airflow.models import Variable\n\nbucket = Variable.get('DATA_LAKE_BUCKET')\nconfig = Variable.get('pipeline_config', deserialize_json=True)\n\n# Em produção: usar secrets backend\n# (AWS Secrets Manager, HashiCorp Vault)", "bash"),
                ],
                exercise="Construa uma DAG com: S3Sensor aguardando arquivo → PostgresHook extraindo dados → S3Hook salvando resultado processado.",
                takeaway="mode='reschedule' nos Sensors é obrigatório em produção — libera o worker enquanto espera, evitando starvation do pool."
            ),
            Lesson("de-m2-l3", "Monitoramento e Alertas de Pipeline", 15,
                "Pipeline sem monitoramento é pipeline que falha silenciosamente. Configure alertas antes de precisar.",
                [
                    Section("Callbacks de Sucesso e Falha",
                        "on_failure_callback dispara quando uma task falha. Use para alertas no Slack, PagerDuty ou email.",
                        "from airflow.operators.python import PythonOperator\nfrom datetime import datetime\nimport requests\n\ndef alerta_slack(context):\n    dag_id = context['dag'].dag_id\n    task_id = context['task'].task_id\n    exec_date = context['execution_date']\n    exception = context.get('exception', 'N/A')\n\n    mensagem = (\n        f':red_circle: *FALHA no pipeline*\\n'\n        f'DAG: `{dag_id}`\\n'\n        f'Task: `{task_id}`\\n'\n        f'Data: `{exec_date}`\\n'\n        f'Erro: `{str(exception)[:200]}`'\n    )\n    requests.post(\n        'https://hooks.slack.com/services/XXX/YYY/ZZZ',\n        json={'text': mensagem}\n    )\n\n# Aplicar globalmente na DAG\ndefault_args = {'on_failure_callback': alerta_slack}", "python"),
                    Section("SLA Misses: Alertar Atrasos",
                        "SLA miss dispara quando uma task não conclui no tempo esperado — antes da falha.",
                        "from datetime import timedelta\nfrom airflow import DAG\n\ndef sla_miss_callback(dag, task_list, blocking_task_list, slas, blocking_tis):\n    print(f'SLA MISS: tasks {task_list} atrasadas!')\n    # Enviar alerta...\n\nwith DAG(\n    dag_id='pipeline_critico',\n    sla_miss_callback=sla_miss_callback,\n    default_args={\n        'sla': timedelta(hours=2),  # task deve concluir em 2h\n    }\n) as dag:\n    ...", "python"),
                    Section("Métricas com StatsD e Grafana",
                        "Airflow emite métricas via StatsD — latência, taxa de sucesso e fila de tasks para dashboards Grafana.",
                        "# airflow.cfg\n[metrics]\nstatsd_on = True\nstatsd_host = localhost\nstatsd_port = 8125\nstatsd_prefix = airflow\n\n# Métricas disponíveis:\n# airflow.dag.{dag_id}.duration\n# airflow.task.{dag_id}.{task_id}.duration\n# airflow.task_instance_created\n# airflow.scheduler.tasks.killed_externally\n\n# Query Grafana para taxa de sucesso:\n# summarize(statsd.airflow.task.success, '1h', 'sum') /\n# (summarize(statsd.airflow.task.success, '1h', 'sum') +\n#  summarize(statsd.airflow.task.failed, '1h', 'sum')) * 100", "bash"),
                ],
                exercise="Configure on_failure_callback com alerta no Slack para todas as tasks de uma DAG crítica. Adicione SLA de 3 horas.",
                takeaway="Alertas de falha são o mínimo. SLA misses avisam antes da falha — são a diferença entre resolver às 7h e ser acordado às 3h."
            ),
        ]),
        Module("de-m3", "Spark e Processamento Distribuído", "Processe terabytes com PySpark quando pandas não é suficiente.", [
            Lesson("de-m3-l1", "PySpark: Quando e Como Usar", 22,
                "Spark não é a resposta para todo problema. Entenda quando vale a complexidade e como usá-lo eficientemente.",
                [
                    Section("Pandas vs Polars vs Spark",
                        "Pandas: até ~10GB, single-node, familiar. Polars: até ~100GB, single-node, 5-10x mais rápido. Spark: terabytes, distribuído, necessário acima de 100GB.",
                        "# Regra de bolso:\n# < 1GB:   pandas ou polars — simples\n# 1-100GB: polars — muito mais rápido que pandas\n# > 100GB: PySpark ou Dask\n\n# Polars vs Pandas — mesma operação:\nimport polars as pl\nimport pandas as pd\nimport time\n\n# Polars: lazy evaluation + multi-thread\nt = time.time()\nresult_polars = (\n    pl.scan_parquet('vendas/*.parquet')\n    .filter(pl.col('valor') > 100)\n    .group_by('categoria')\n    .agg(pl.col('valor').sum().alias('total'))\n    .collect()\n)\nprint(f'Polars: {time.time()-t:.2f}s')\n\n# Pandas: single-thread, eager\nt = time.time()\ndf = pd.read_parquet('vendas/*.parquet')\nresult_pandas = df[df.valor > 100].groupby('categoria').valor.sum()\nprint(f'Pandas: {time.time()-t:.2f}s')", "python"),
                    Section("PySpark: Operações Fundamentais",
                        "Spark usa lazy evaluation — o plano de execução é otimizado antes de rodar. transformações vs ações.",
                        "from pyspark.sql import SparkSession\nfrom pyspark.sql import functions as F\n\nspark = SparkSession.builder \\\n    .appName('pipeline-vendas') \\\n    .config('spark.sql.shuffle.partitions', '200') \\\n    .getOrCreate()\n\n# Ler Parquet (lazy — não executa ainda)\ndf = spark.read.parquet('s3://datalake/vendas/')\n\n# Transformações (lazy)\ndf_filtrado = (\n    df\n    .filter(F.col('status') == 'aprovado')\n    .withColumn('mes', F.month('data_venda'))\n    .withColumn('valor_liquido', F.col('valor') * (1 - F.col('desconto')))\n)\n\n# Ação (executa tudo)\nresultado = (\n    df_filtrado\n    .groupBy('mes', 'categoria')\n    .agg(\n        F.sum('valor_liquido').alias('faturamento'),\n        F.count('*').alias('total_pedidos'),\n        F.avg('valor_liquido').alias('ticket_medio')\n    )\n    .orderBy('mes')\n)\n\nresultado.write.mode('overwrite').parquet('s3://datalake/resultado/')", "python"),
                    Section("Otimização: Particionamento e Broadcast",
                        "Shuffle é o maior inimigo da performance no Spark. Evite com bom particionamento e broadcast joins.",
                        "from pyspark.sql import functions as F\nfrom pyspark.sql.functions import broadcast\n\n# Reparticionamento por coluna de join\n# Evita shuffle na query seguinte\ndf_vendas = df_vendas.repartition(200, 'cliente_id')\n\n# Broadcast join: tabela pequena na memória de todos os workers\n# Ideal quando uma tabela é < 100MB\ndf_clientes_pequeno = spark.read.parquet('dim_clientes/')  # 50MB\n\nresultado = df_vendas.join(\n    broadcast(df_clientes_pequeno),  # evita shuffle total\n    on='cliente_id',\n    how='left'\n)\n\n# Ver plano de execução\nresultado.explain(mode='formatted')\n\n# Cache resultado intermediário usado várias vezes\ndf_filtrado.cache()\ndf_filtrado.count()  # materializar cache\n# ... usar df_filtrado múltiplas vezes ...\ndf_filtrado.unpersist()", "python"),
                ],
                exercise="Processe um dataset de 10M linhas com PySpark: filtrar, agregar e salvar particionado por mês. Compare com Polars no mesmo dataset.",
                takeaway="Evite Spark desnecessariamente — Polars resolve 80% dos casos com 10% da complexidade. Use Spark acima de 100GB ou quando precisar de cluster distribuído."
            ),
            Lesson("de-m3-l2", "Delta Lake: ACID no Data Lake", 20,
                "Delta Lake adiciona transações ACID, schema enforcement e time travel ao seu Data Lake.",
                [
                    Section("Por que Delta Lake",
                        "Data Lakes sem ACID sofrem de: leitura durante escrita, dados corrompidos em falha, impossibilidade de rollback. Delta resolve tudo isso.",
                        "from delta import DeltaTable, configure_spark_with_delta_pip\nfrom pyspark.sql import SparkSession\n\nbuilder = SparkSession.builder \\\n    .appName('delta-lake') \\\n    .config('spark.sql.extensions', 'io.delta.sql.DeltaSparkSessionExtension') \\\n    .config('spark.sql.catalog.spark_catalog', 'org.apache.spark.sql.delta.catalog.DeltaCatalog')\n\nspark = configure_spark_with_delta_pip(builder).getOrCreate()\n\n# Escrever em formato Delta (primeira vez)\ndf.write.format('delta').save('s3://datalake/delta/vendas/')\n\n# Escrever incrementalmente (UPSERT/MERGE)\ndelta_table = DeltaTable.forPath(spark, 's3://datalake/delta/vendas/')\n\ndelta_table.alias('alvo').merge(\n    df_novos.alias('novo'),\n    'alvo.venda_id = novo.venda_id'\n).whenMatchedUpdateAll() \\\n .whenNotMatchedInsertAll() \\\n .execute()", "python"),
                    Section("Time Travel: Consultar Dados do Passado",
                        "Delta mantém histórico de todas as versões. Você pode consultar dados como estavam ontem ou reverter para uma versão anterior.",
                        "# Consultar versão anterior\ndf_ontem = spark.read.format('delta') \\\n    .option('versionAsOf', 5) \\\n    .load('s3://datalake/delta/vendas/')\n\n# Por timestamp\ndf_semana_passada = spark.read.format('delta') \\\n    .option('timestampAsOf', '2024-01-08') \\\n    .load('s3://datalake/delta/vendas/')\n\n# Ver histórico\ndelta_table = DeltaTable.forPath(spark, 's3://datalake/delta/vendas/')\ndelta_table.history(10).show(truncate=False)\n\n# Reverter para versão anterior\ndelta_table.restoreToVersion(3)\n\n# Limpar versões antigas (manter últimas 7 dias)\ndelta_table.vacuum(retentionHours=168)", "python"),
                    Section("Schema Evolution e Enforcement",
                        "Delta recusa escrita de dados com schema incompatível (enforcement) mas permite adicionar colunas novas (evolution).",
                        "# Schema enforcement: rejeita coluna incompatível\ntry:\n    df_com_tipo_errado.write \\\n        .format('delta') \\\n        .mode('append') \\\n        .save('s3://datalake/delta/vendas/')\nexcept Exception as e:\n    print(f'Schema inválido: {e}')  # tipo de coluna mudou\n\n# Schema evolution: adicionar nova coluna (opt-in)\ndf_com_nova_coluna.write \\\n    .format('delta') \\\n    .mode('append') \\\n    .option('mergeSchema', 'true') \\\n    .save('s3://datalake/delta/vendas/')\n\n# Ver schema atual\ndelta_table.toDF().printSchema()", "python"),
                ],
                exercise="Converta um pipeline existente para usar Delta Lake. Teste time travel consultando dados de 3 versões atrás e faça rollback.",
                takeaway="Delta Lake é ACID no Data Lake: sem corrupção de dados, com rollback e time travel. Em 2024, é o padrão para Lakehouses em produção."
            ),
            Lesson("de-m3-l3", "dbt: Transformações SQL como Código", 22,
                "dbt transforma SQL em software: versionado, testado e documentado. É a ferramenta mais importante do Analytics Engineer.",
                [
                    Section("Estrutura de Projeto dbt",
                        "dbt organiza transformações em camadas: sources → staging → intermediate → marts. Cada camada tem responsabilidade clara.",
                        "# Estrutura padrão dbt\nmy_project/\n├── dbt_project.yml\n├── profiles.yml\n├── models/\n│   ├── staging/         # limpeza bruta, 1:1 com fonte\n│   │   ├── schema.yml   # documentação + testes\n│   │   └── stg_vendas.sql\n│   ├── intermediate/    # joins e lógica intermediária\n│   │   └── int_vendas_com_clientes.sql\n│   └── marts/           # modelos finais para BI\n│       ├── fct_vendas.sql\n│       └── dim_clientes.sql\n├── tests/               # testes customizados\n├── macros/              # funções reutilizáveis\n└── seeds/               # CSVs estáticos (ex: país/região)\n\n# Comandos essenciais:\n# dbt run          → executa todos os models\n# dbt test         → roda todos os testes\n# dbt docs generate → gera documentação\n# dbt docs serve   → abre documentação no browser", "bash"),
                    Section("Macros e Reutilização de Lógica",
                        "Macros são funções Jinja que evitam repetição de SQL. Fundamental para lógica de negócio usada em múltiplos modelos.",
                        "-- macros/calcular_ticket_medio.sql\n{% macro calcular_ticket_medio(coluna_valor, coluna_qtd) %}\n    CASE\n        WHEN SUM({{ coluna_qtd }}) = 0 THEN 0\n        ELSE SUM({{ coluna_valor }}) / SUM({{ coluna_qtd }})\n    END\n{% endmacro %}\n\n-- models/marts/fct_vendas_resumo.sql\n{{ config(materialized='table') }}\n\nSELECT\n    mes,\n    categoria,\n    SUM(valor)                                          AS faturamento,\n    COUNT(*)                                            AS total_pedidos,\n    {{ calcular_ticket_medio('valor', 'quantidade') }}  AS ticket_medio\nFROM {{ ref('stg_vendas') }}\nGROUP BY mes, categoria\n\n-- Incremental: só processar dados novos\n{{ config(materialized='incremental', unique_key='venda_id') }}\n\nSELECT * FROM {{ ref('stg_vendas') }}\n{% if is_incremental() %}\n    WHERE data_venda > (SELECT MAX(data_venda) FROM {{ this }})\n{% endif %}", "sql"),
                    Section("Orquestrar dbt no Airflow",
                        "dbt + Airflow = pipeline completo: Airflow cuida da orquestração, dbt cuida das transformações SQL.",
                        "from airflow.decorators import dag, task\nfrom airflow.operators.bash import BashOperator\nfrom datetime import datetime\n\n@dag(schedule='@daily', start_date=datetime(2024, 1, 1))\ndef pipeline_dbt():\n\n    @task()\n    def extrair():\n        # Extrai dados brutos para raw layer\n        pass\n\n    # Rodar dbt após extração\n    dbt_run = BashOperator(\n        task_id='dbt_run',\n        bash_command='''\n            cd /opt/dbt/meu_projeto &&\n            dbt run --profiles-dir /opt/dbt --target prod\n        '''\n    )\n\n    dbt_test = BashOperator(\n        task_id='dbt_test',\n        bash_command='''\n            cd /opt/dbt/meu_projeto &&\n            dbt test --profiles-dir /opt/dbt --target prod\n        '''\n    )\n\n    extrair() >> dbt_run >> dbt_test\n\npipeline_dbt()", "python"),
                ],
                exercise="Construa um projeto dbt completo: staging → intermediate → mart para uma fonte de vendas. Adicione testes e gere a documentação.",
                takeaway="dbt é SQL com superpoderes: versionamento, testes, documentação e linhagem automática. É o padrão da indústria para transformações analíticas."
            ),
        ]),
        Module("de-m4", "Projeto Final: Pipeline End-to-End", "Pipeline completo: ingestão → transformação → serving → monitoramento.", [
            Lesson("de-m4-l1", "Arquitetura Medallion: Bronze, Silver, Gold", 18,
                "A arquitetura Medallion organiza dados em camadas de qualidade crescente. É o padrão do Databricks adotado pela indústria.",
                [
                    Section("As 3 Camadas",
                        "Bronze: dados brutos exatamente como chegaram. Silver: limpos e validados. Gold: agregados e prontos para consumo.",
                        "# Arquitetura Medallion no Data Lake\n\n# Bronze: raw, imutável, particionado por ingestão\n# s3://lake/bronze/vendas/ano=2024/mes=01/dia=15/\n# - Dados exatamente como vieram da fonte\n# - Nunca modificar após ingestão\n# - Formato: JSON ou Parquet sem transformação\n\n# Silver: limpo, validado, schema correto\n# s3://lake/silver/vendas/\n# - Nulos tratados, tipos corretos\n# - Deduplicados\n# - Validados (GE ou dbt tests)\n\n# Gold: agregado, pronto para BI e ML\n# s3://lake/gold/fct_vendas_mensal/\n# - Métricas de negócio calculadas\n# - Otimizado para query (particionado por data)\n# - Formato: Delta Lake ou Parquet colunar", "bash"),
                    Section("Pipeline Bronze → Silver",
                        "Processamento da camada bronze para silver: validação, deduplicação e padronização.",
                        "from pyspark.sql import SparkSession, functions as F\nfrom delta import DeltaTable\n\nspark = SparkSession.builder.appName('bronze-to-silver').getOrCreate()\n\ndef bronze_para_silver(data_particao: str):\n    # Ler bronze\n    df_bronze = spark.read.json(\n        f's3://lake/bronze/vendas/data={data_particao}/'\n    )\n\n    # Transformar para silver\n    df_silver = (\n        df_bronze\n        .dropDuplicates(['venda_id'])\n        .filter(F.col('valor').isNotNull())\n        .filter(F.col('valor') > 0)\n        .withColumn('valor', F.round(F.col('valor').cast('decimal(12,2)'), 2))\n        .withColumn('data_venda', F.to_date('data_venda', 'yyyy-MM-dd'))\n        .withColumn('status', F.upper(F.trim('status')))\n        .withColumn('_ingestao_ts', F.current_timestamp())\n    )\n\n    # Salvar em Delta (upsert)\n    DeltaTable.forPath(spark, 's3://lake/silver/vendas/') \\\n        .alias('alvo').merge(df_silver.alias('novo'), 'alvo.venda_id = novo.venda_id') \\\n        .whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()", "python"),
                    Section("Pipeline Silver → Gold",
                        "Da camada silver para gold: aplicar regras de negócio e criar modelos analíticos.",
                        "def silver_para_gold():\n    df_vendas = spark.read.format('delta').load('s3://lake/silver/vendas/')\n    df_clientes = spark.read.format('delta').load('s3://lake/silver/clientes/')\n    df_produtos = spark.read.format('delta').load('s3://lake/silver/produtos/')\n\n    # Modelo analítico: fato de vendas enriquecida\n    fct_vendas = (\n        df_vendas\n        .join(broadcast(df_clientes), 'cliente_id', 'left')\n        .join(broadcast(df_produtos), 'produto_id', 'left')\n        .withColumn('ano', F.year('data_venda'))\n        .withColumn('mes', F.month('data_venda'))\n        .withColumn('trimestre', F.quarter('data_venda'))\n        .select(\n            'venda_id', 'data_venda', 'ano', 'mes', 'trimestre',\n            'cliente_id', 'nome_cliente', 'segmento_cliente',\n            'produto_id', 'nome_produto', 'categoria_produto',\n            'valor', 'quantidade', 'desconto'\n        )\n    )\n\n    fct_vendas.write.format('delta') \\\n        .partitionBy('ano', 'mes') \\\n        .mode('overwrite') \\\n        .option('overwriteSchema', 'true') \\\n        .save('s3://lake/gold/fct_vendas/')", "python"),
                ],
                exercise="Implemente o pipeline completo Bronze → Silver → Gold para uma fonte de vendas. Configure validação de dados em cada transição.",
                takeaway="Bronze nunca muda — é o backup dos dados originais. Silver valida e limpa. Gold agrega e enriquece. Essa separação permite reprocessar qualquer camada sem perder a anterior."
            ),
            Lesson("de-m4-l2", "Streaming com Kafka e Spark Structured Streaming", 22,
                "Pipelines batch processam dados de hora em hora. Streaming processa em segundos — quando latência importa.",
                [
                    Section("Kafka: Fundamentos",
                        "Kafka é um log distribuído de eventos. Producers publicam, Consumers leem na sua própria velocidade. Retenção configuraável garante replay.",
                        "from confluent_kafka import Producer, Consumer\nimport json\n\n# Producer: publicar evento\nproducer = Producer({'bootstrap.servers': 'kafka:9092'})\n\ndef publicar_venda(venda: dict):\n    producer.produce(\n        topic='vendas',\n        key=str(venda['cliente_id']).encode(),\n        value=json.dumps(venda).encode(),\n    )\n    producer.flush()\n\n# Consumer: processar eventos\nconsumer = Consumer({\n    'bootstrap.servers': 'kafka:9092',\n    'group.id': 'pipeline-analytics',\n    'auto.offset.reset': 'earliest',\n})\nconsumer.subscribe(['vendas'])\n\nwhile True:\n    msg = consumer.poll(timeout=1.0)\n    if msg and not msg.error():\n        venda = json.loads(msg.value())\n        processar(venda)\n        consumer.commit()", "python"),
                    Section("Spark Structured Streaming",
                        "Structured Streaming processa streams de Kafka como se fossem tabelas SQL — mesmo código que batch, latência de segundos.",
                        "from pyspark.sql import SparkSession\nfrom pyspark.sql import functions as F\nfrom pyspark.sql.types import StructType, StringType, DoubleType\n\nspark = SparkSession.builder.appName('streaming-vendas').getOrCreate()\n\n# Schema dos eventos\nschema = StructType() \\\n    .add('venda_id', StringType()) \\\n    .add('valor', DoubleType()) \\\n    .add('categoria', StringType()) \\\n    .add('timestamp', StringType())\n\n# Ler do Kafka\ndf_stream = spark.readStream \\\n    .format('kafka') \\\n    .option('kafka.bootstrap.servers', 'kafka:9092') \\\n    .option('subscribe', 'vendas') \\\n    .load() \\\n    .select(F.from_json(F.col('value').cast('string'), schema).alias('data')) \\\n    .select('data.*')\n\n# Agregar por janela de 5 minutos\ndf_agregado = df_stream \\\n    .withColumn('ts', F.to_timestamp('timestamp')) \\\n    .groupBy(F.window('ts', '5 minutes'), 'categoria') \\\n    .agg(F.sum('valor').alias('faturamento'), F.count('*').alias('pedidos'))\n\n# Escrever em Delta\ndf_agregado.writeStream \\\n    .format('delta') \\\n    .outputMode('update') \\\n    .option('checkpointLocation', 's3://lake/checkpoints/vendas/') \\\n    .start('s3://lake/gold/vendas_realtime/')", "python"),
                    Section("Lambda Architecture: Batch + Streaming",
                        "Lambda combina batch (precisão) e streaming (velocidade). Serving layer unifica as duas visões.",
                        "# Lambda Architecture:\n#\n# Batch layer:   processa todos os dados históricos (alta precisão)\n# Speed layer:   processa dados recentes em streaming (baixa latência)\n# Serving layer: une batch + speed para consultas\n\n# Serving layer com DuckDB (unir batch e streaming)\nimport duckdb\n\ncon = duckdb.connect()\n\n# Vista que une batch (Parquet histórico) e streaming (Delta recente)\ncon.execute(\"\"\"\n    CREATE VIEW faturamento_completo AS\n    SELECT categoria, SUM(valor) AS total, 'batch' AS fonte\n    FROM read_parquet('s3://lake/gold/fct_vendas/**/*.parquet')\n    WHERE data_venda < CURRENT_DATE\n    GROUP BY categoria\n\n    UNION ALL\n\n    SELECT categoria, SUM(valor) AS total, 'streaming' AS fonte\n    FROM delta_scan('s3://lake/gold/vendas_realtime/')\n    WHERE window_start >= CURRENT_DATE\n    GROUP BY categoria\n\"\"\")", "python"),
                ],
                exercise="Publique eventos de venda no Kafka com um producer Python. Consuma e agregue com Spark Structured Streaming. Visualize em tempo real.",
                takeaway="Streaming resolve latência, batch resolve precisão. Lambda Architecture combina os dois — serve 99% das necessidades de dados em tempo real."
            ),
            Lesson("de-m4-l3", "DataOps: CI/CD para Pipelines de Dados", 18,
                "Pipelines de dados precisam de CI/CD como qualquer software — testes automatizados, deploy controlado e rollback.",
                [
                    Section("Testar Pipelines de Dados",
                        "Testes unitários para funções de transformação, testes de integração para o pipeline completo.",
                        "import pytest\nimport pandas as pd\nfrom app.pipeline import transformar_vendas, validar_dados\n\ndef test_transformar_vendas_remove_nulos():\n    df = pd.DataFrame({\n        'venda_id': [1, 2, 3],\n        'valor': [100.0, None, 50.0],\n        'cliente_id': [1, 2, None]\n    })\n    resultado = transformar_vendas(df)\n    assert resultado['valor'].notna().all()\n    assert resultado['cliente_id'].notna().all()\n    assert len(resultado) == 1  # só a linha completa\n\ndef test_validar_dados_falha_com_negativos():\n    df = pd.DataFrame({'valor': [-1.0, 100.0]})\n    with pytest.raises(ValueError, match='Valores negativos'):\n        validar_dados(df)\n\ndef test_pipeline_idempotente(tmp_path):\n    df = pd.DataFrame({'venda_id': [1], 'valor': [100.0]})\n    output = str(tmp_path / 'output.parquet')\n\n    executar_pipeline(df, output)  # primeira vez\n    executar_pipeline(df, output)  # segunda vez (idempotente)\n\n    resultado = pd.read_parquet(output)\n    assert len(resultado) == 1  # não duplicou!", "python"),
                    Section("GitHub Actions para DAGs",
                        "Validar DAGs no CI: syntax check, teste unitário e deploy automático para produção.",
                        "# .github/workflows/airflow-ci.yml\nname: Airflow CI\n\non:\n  pull_request:\n    paths: ['dags/**', 'plugins/**']\n\njobs:\n  validate:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n\n      - name: Instalar Airflow\n        run: pip install apache-airflow==2.8.0\n\n      - name: Validar syntax das DAGs\n        run: |\n          for dag in dags/*.py; do\n            python -c \"import importlib.util; \\\n              spec = importlib.util.spec_from_file_location('dag', '$dag'); \\\n              mod = importlib.util.module_from_spec(spec); \\\n              spec.loader.exec_module(mod)\" && \\\n            echo \"OK: $dag\" || { echo \"FALHOU: $dag\"; exit 1; }\n          done\n\n      - name: Testes unitários\n        run: pytest tests/test_dags.py -v\n\n  deploy:\n    needs: validate\n    if: github.ref == 'refs/heads/main'\n    run: aws s3 sync dags/ s3://airflow-bucket/dags/", "yaml"),
                    Section("Controle de Qualidade com Data Contracts",
                        "Data Contracts definem o schema esperado entre produtor e consumidor — como uma API contract, mas para dados.",
                        "# data_contract.yml — contrato entre time de engenharia e analytics\nversion: 1.0\nname: vendas_diarias\nowner: time-engenharia@empresa.com\nconsumers:\n  - time-analytics@empresa.com\n  - time-ml@empresa.com\n\nschema:\n  - field: venda_id\n    type: integer\n    required: true\n    unique: true\n  - field: data_venda\n    type: date\n    required: true\n  - field: valor\n    type: decimal(12,2)\n    required: true\n    min: 0.01\n  - field: status\n    type: string\n    enum: [aprovado, cancelado, pendente]\n\nsla:\n  freshness: 6 hours\n  availability: 99.5%\n  row_count_min: 1000\n\n# Validar contrato com datacontract-cli\n# pip install datacontract-cli\n# datacontract lint data_contract.yml\n# datacontract test data_contract.yml --server producao", "yaml"),
                ],
                exercise="Configure CI/CD completo para seu projeto Airflow: testes automáticos de DAGs, deploy automático no merge e data contracts para as tabelas principais.",
                takeaway="Pipelines de dados são software — precisam de testes, CI/CD e contratos. Data Contracts previnem quebras silenciosas entre times que consomem seus dados."
            ),
        ]),
    ]
)


# ─────────────────────────────────────────────────────────────────────────────
# CURSO 8 — ARQUITETURA DE SISTEMAS
# ─────────────────────────────────────────────────────────────────────────────
ARCH_COURSE = Course(
    id="system-architecture",
    title="Arquitetura de Sistemas: Do Monolito ao Microsserviço",
    tagline="Tome decisões de arquitetura com confiança — trade-offs reais, sem hype",
    description="Padrões arquiteturais, design de APIs, microsserviços, event-driven e como escalar sistemas reais. Foco em trade-offs práticos.",
    level="Intermediário → Avançado",
    category="Arquitetura",
    duration_hours=20,
    skills=["System Design", "Microsserviços", "Event-Driven", "Escalabilidade", "DDD", "CQRS", "API Design"],
    color="#6366f1",
    modules=[
        Module("ar-m1", "Princípios de Design de Software", "Os princípios que separam sistemas fáceis de mudar dos impossíveis de tocar.", [
            Lesson("ar-m1-l1", "SOLID e suas Consequências Práticas", 20,
                "SOLID não é dogma — é um conjunto de heurísticas para tornar código mais manutenível. Entenda o porquê, não apenas o o quê.",
                [
                    Section("S e O: Responsabilidade Única e Aberto/Fechado",
                        "Single Responsibility: uma razão para mudar. Open/Closed: aberto para extensão, fechado para modificação. Violações comuns e como corrigir.",
                        "# Violação de SRP: classe faz tudo\nclass PedidoService:  # Ruim\n    def criar(self, dados): ...\n    def enviar_email(self, pedido): ...  # mistura negócio com infra\n    def gerar_pdf(self, pedido): ...     # mistura negócio com relatório\n    def salvar_banco(self, pedido): ... # mistura negócio com persistência\n\n# Correto: cada classe tem uma responsabilidade\nclass PedidoService:\n    def __init__(self, repo: PedidoRepo, notificador: Notificador):\n        self.repo = repo\n        self.notificador = notificador\n\n    def criar(self, dados: PedidoCreate) -> Pedido:\n        pedido = Pedido(**dados.model_dump())\n        self.repo.salvar(pedido)\n        self.notificador.notificar_criacao(pedido)  # delega\n        return pedido\n\n# Open/Closed: adicionar tipos de desconto sem mudar código existente\nfrom abc import ABC, abstractmethod\n\nclass CalculadorDesconto(ABC):\n    @abstractmethod\n    def calcular(self, valor: float) -> float: ...\n\nclass DescontoVIP(CalculadorDesconto):\n    def calcular(self, valor): return valor * 0.85\n\nclass DescontoBlackFriday(CalculadorDesconto):  # nova regra: zero mudança no código antigo\n    def calcular(self, valor): return valor * 0.60", "python"),
                    Section("L, I e D: Liskov, Interfaces e Inversão de Dependência",
                        "Liskov: subclasses devem ser substituíveis pela base. Interface Segregation: interfaces específicas. Dependency Inversion: dependa de abstrações.",
                        "from abc import ABC, abstractmethod\nfrom typing import Protocol\n\n# Dependency Inversion: depender de abstração, não implementação\nclass EmailSender(Protocol):  # abstração\n    def enviar(self, para: str, assunto: str, corpo: str) -> None: ...\n\nclass SMTPSender:  # implementação concreta\n    def enviar(self, para, assunto, corpo): ...\n\nclass FakeSender:  # implementação de teste\n    def __init__(self):\n        self.enviados = []\n    def enviar(self, para, assunto, corpo):\n        self.enviados.append({'para': para, 'assunto': assunto})\n\nclass PedidoService:\n    def __init__(self, sender: EmailSender):  # depende de abstração!\n        self.sender = sender\n\n    def confirmar(self, pedido):\n        self.sender.enviar(pedido.email, 'Confirmado', f'Pedido {pedido.id}')\n\n# Em teste: injetar FakeSender\n# Em produção: injetar SMTPSender", "python"),
                    Section("Quando NÃO aplicar SOLID",
                        "SOLID tem custo — mais abstrações, mais indireção. Em scripts simples, protótipos e código que muda raramente, SOLID é overhead.",
                        "# Regra prática: aplique SOLID quando\n# 1. O código vai mudar (80% das vezes)\n# 2. Tem múltiplos desenvolvedores\n# 3. É crítico para o negócio\n\n# NÃO aplique quando:\n# - Script de uso único\n# - Protótipo descartável\n# - Módulo sem plano de extensão\n\n# O 'pior' código SOLID:\nclass AbstractEmailStrategyFactory(ABC):  # abstração da abstração da abstração\n    ...\n\n# Simples e suficiente:\ndef enviar_email_confirmacao(pedido_id: int, email: str) -> None:\n    msg = f'Pedido {pedido_id} confirmado!'\n    smtp.sendmail('no-reply@empresa.com', email, msg)\n\n# YAGNI: You Ain't Gonna Need It\n# Não abstraia antes de ter 3 implementações diferentes", "python"),
                ],
                exercise="Refatore uma classe God Object que tem 10 responsabilidades. Separe em classes com SRP e use DI para o email sender.",
                takeaway="SOLID é uma bússola, não uma religião. Aplique quando o custo da abstração é menor que o custo da mudança futura."
            ),
            Lesson("ar-m1-l2", "Domain-Driven Design: Modelar o Negócio em Código", 22,
                "DDD é uma abordagem para sistemas complexos: o código deve refletir o modelo mental do negócio.",
                [
                    Section("Linguagem Ubíqua e Bounded Contexts",
                        "Linguagem Ubíqua: mesmos termos no código e no negócio. Bounded Context: limite onde um modelo é válido — Pedido em Vendas ≠ Pedido em Logística.",
                        "# Linguagem Ubíqua: use termos do negócio no código\n# Ruim:\nclass Order:\n    def process(self): ...   # 'process' não diz nada\n    def update_state(self): ...\n\n# Bom: reflete o vocabulário do negócio\nclass Pedido:\n    def confirmar(self): ...\n    def cancelar(self, motivo: str): ...\n    def solicitar_reembolso(self): ...\n    def marcar_como_entregue(self): ...\n\n# Bounded Contexts: mesmo conceito, modelos diferentes\n# Contexto de Vendas:\nclass Pedido:  # foco em aprovação, valor, cliente\n    numero: int\n    cliente: Cliente\n    valor_total: Decimal\n    status: StatusPedido\n\n# Contexto de Logística:\nclass Remessa:  # foco em endereço, volumes, rastreio\n    pedido_id: int  # só o ID do outro contexto!\n    destino: Endereco\n    volumes: list[Volume]\n    codigo_rastreio: str", "python"),
                    Section("Aggregates e Entities",
                        "Aggregate é a unidade de consistência. Tudo dentro de um aggregate muda junto, em uma única transação. Entities têm identidade. Value Objects são imutáveis.",
                        "from dataclasses import dataclass, field\nfrom decimal import Decimal\nfrom typing import Final\n\n# Value Object: imutável, sem identidade\n@dataclass(frozen=True)\nclass Dinheiro:\n    valor: Decimal\n    moeda: str = 'BRL'\n\n    def __add__(self, outro: 'Dinheiro') -> 'Dinheiro':\n        assert self.moeda == outro.moeda\n        return Dinheiro(self.valor + outro.valor, self.moeda)\n\n# Entity: tem identidade (id)\n@dataclass\nclass ItemPedido:\n    id: int\n    produto_id: int\n    quantidade: int\n    preco_unitario: Dinheiro\n\n    @property\n    def subtotal(self) -> Dinheiro:\n        return Dinheiro(self.preco_unitario.valor * self.quantidade)\n\n# Aggregate Root: ponto de entrada, garante consistência\n@dataclass\nclass Pedido:  # Aggregate Root\n    id: int\n    cliente_id: int\n    itens: list[ItemPedido] = field(default_factory=list)\n    status: str = 'rascunho'\n\n    def adicionar_item(self, produto_id: int, qtd: int, preco: Dinheiro):\n        if self.status != 'rascunho':\n            raise ValueError('Pedido já confirmado')\n        self.itens.append(ItemPedido(len(self.itens)+1, produto_id, qtd, preco))\n\n    @property\n    def total(self) -> Dinheiro:\n        return sum((i.subtotal for i in self.itens), Dinheiro(Decimal('0')))", "python"),
                    Section("Domain Events: Comunicação entre Contextos",
                        "Domain Events representam algo que aconteceu no domínio. São o mecanismo de comunicação entre Bounded Contexts desacoplados.",
                        "from dataclasses import dataclass\nfrom datetime import datetime\nfrom typing import Any\n\n# Domain Event: imutável, passado\n@dataclass(frozen=True)\nclass PedidoConfirmado:\n    pedido_id: int\n    cliente_id: int\n    valor_total: float\n    ocorreu_em: datetime\n\n# Aggregate publica eventos\nclass Pedido:\n    def __init__(self):\n        self._eventos: list[Any] = []\n\n    def confirmar(self):\n        if self.status != 'rascunho':\n            raise ValueError('Pedido já confirmado')\n        self.status = 'confirmado'\n        self._eventos.append(PedidoConfirmado(\n            pedido_id=self.id,\n            cliente_id=self.cliente_id,\n            valor_total=float(self.total.valor),\n            ocorreu_em=datetime.now()\n        ))\n\n    def pop_eventos(self) -> list:\n        eventos, self._eventos = self._eventos, []\n        return eventos\n\n# Handler: outro contexto reage ao evento\nclass LogisticaHandler:\n    def on_pedido_confirmado(self, evento: PedidoConfirmado):\n        remessa = Remessa(pedido_id=evento.pedido_id)\n        self.remessa_repo.salvar(remessa)", "python"),
                ],
                exercise="Modele um domínio de biblioteca: Livro, Exemplar, Empréstimo como Aggregate. Defina os Domain Events e os Bounded Contexts.",
                takeaway="DDD vale a pena em domínios complexos com muitas regras de negócio. Em CRUDs simples, é overhead desnecessário."
            ),
            Lesson("ar-m1-l3", "Clean Architecture e Hexagonal", 18,
                "Clean Architecture separa negócio de infraestrutura. Seu código de domínio não deve depender de Django, FastAPI ou PostgreSQL.",
                [
                    Section("A Regra de Dependência",
                        "Dependências apontam para dentro — do framework para o domínio, nunca ao contrário. O domínio não importa nada de framework.",
                        "# Clean Architecture: camadas\n# Entities (Domain) → Use Cases → Interface Adapters → Frameworks\n# Dependências só apontam para dentro!\n\n# Domain (nenhuma dependência externa)\nclass Pedido:  # puro Python, sem imports de framework\n    def confirmar(self): ...\n\n# Use Case (depende apenas do domínio)\nclass ConfirmarPedidoUseCase:\n    def __init__(self, repo: PedidoRepositoryPort):  # interface!\n        self.repo = repo\n\n    def executar(self, pedido_id: int) -> Pedido:\n        pedido = self.repo.get(pedido_id)\n        pedido.confirmar()\n        self.repo.salvar(pedido)\n        return pedido\n\n# Interface Adapter (implementa a interface do use case)\nclass PedidoRepositorySQLAlchemy:  # depende de SQLAlchemy E do domínio\n    def get(self, id: int) -> Pedido:\n        row = self.session.get(PedidoORM, id)\n        return Pedido(id=row.id, ...)  # converte ORM → Domain\n\n# Framework (FastAPI): chama o use case\n@router.post('/pedidos/{id}/confirmar')\nasync def confirmar(id: int, uc = Depends(get_use_case)):\n    return uc.executar(id)", "python"),
                    Section("Ports and Adapters (Hexagonal)",
                        "Portas são interfaces do domínio. Adaptadores são implementações concretas. O domínio fala só com portas — adaptadores são trocáveis.",
                        "from abc import ABC, abstractmethod\n\n# Port: interface definida pelo domínio\nclass PedidoRepositoryPort(ABC):\n    @abstractmethod\n    def get(self, id: int) -> Pedido: ...\n\n    @abstractmethod\n    def salvar(self, pedido: Pedido) -> None: ...\n\nclass NotificadorPort(ABC):\n    @abstractmethod\n    def notificar_confirmacao(self, pedido: Pedido) -> None: ...\n\n# Adapters: implementações concretas (fora do domínio)\nclass PedidoRepositoryPostgres(PedidoRepositoryPort):\n    def get(self, id): ...  # usa SQLAlchemy\n    def salvar(self, pedido): ...\n\nclass PedidoRepositoryInMemory(PedidoRepositoryPort):  # para testes\n    def __init__(self):\n        self._store = {}\n    def get(self, id): return self._store.get(id)\n    def salvar(self, pedido): self._store[pedido.id] = pedido\n\nclass EmailNotificador(NotificadorPort):\n    def notificar_confirmacao(self, pedido): ...  # usa SMTP", "python"),
                    Section("Quando Usar Clean Architecture",
                        "Clean Architecture tem custo real — mais arquivos, mais indireção. Justifica-se em sistemas complexos, de longa vida e com múltiplas interfaces.",
                        "# Quando vale:\n# - Domínio complexo com muitas regras de negócio\n# - Sistema de longa vida (5+ anos)\n# - Múltiplas interfaces (API, CLI, batch, eventos)\n# - Time grande com especialidades diferentes\n# - Regras de negócio que precisam de testes unitários rápidos\n\n# Quando NÃO vale:\n# - CRUD simples\n# - API que só persiste e retorna dados\n# - Protótipo ou MVP\n# - Time pequeno (1-2 devs)\n\n# Alternativa pragmática: 'Screaming Architecture'\n# Organize por funcionalidade de negócio, não por camada técnica:\n# vendas/ (models.py, views.py, services.py)\n# estoque/\n# financeiro/\n# Melhor que models/ views/ services/ misturados", "python"),
                ],
                exercise="Implemente um caso de uso de confirmação de pedido com Clean Architecture: domain entity, use case, port e dois adapters (Postgres e InMemory).",
                takeaway="A regra de ouro: o domínio não importa nada de infra. Se você consegue testar o use case sem banco de dados, está no caminho certo."
            ),
        ]),
        Module("ar-m2", "Padrões Arquiteturais", "Os padrões que resolvem problemas recorrentes em sistemas distribuídos.", [
            Lesson("ar-m2-l1", "CQRS e Event Sourcing", 22,
                "CQRS separa reads de writes. Event Sourcing armazena eventos em vez de estado. Poderosos juntos, perigosos mal aplicados.",
                [
                    Section("CQRS: Separar Leitura de Escrita",
                        "Command Query Responsibility Segregation: um lado escreve (commands), outro lê (queries). Permite otimizar cada lado independentemente.",
                        "from dataclasses import dataclass\nfrom abc import ABC, abstractmethod\n\n# Command: intenção de mudar estado\n@dataclass(frozen=True)\nclass ConfirmarPedidoCommand:\n    pedido_id: int\n    usuario_id: int\n\n# Query: leitura sem efeito colateral\n@dataclass(frozen=True)\nclass BuscarPedidoQuery:\n    pedido_id: int\n\n# Command Handler: escreve no banco normalizado\nclass ConfirmarPedidoHandler:\n    def handle(self, cmd: ConfirmarPedidoCommand):\n        pedido = self.repo.get(cmd.pedido_id)\n        pedido.confirmar()\n        self.repo.salvar(pedido)\n        self.event_bus.publish(PedidoConfirmado(pedido.id))\n\n# Query Handler: lê de view desnormalizada (otimizada para display)\nclass BuscarPedidoHandler:\n    def handle(self, query: BuscarPedidoQuery) -> dict:\n        # Lê de uma view ou tabela desnormalizada\n        return self.read_db.execute(\n            'SELECT p.*, c.nome_cliente, SUM(i.valor) as total '\n            'FROM pedidos p JOIN clientes c ... WHERE p.id = ?',\n            [query.pedido_id]\n        ).fetchone()", "python"),
                    Section("Event Sourcing: O Log é o Estado",
                        "Em vez de salvar o estado atual, salve todos os eventos que chegaram ao estado atual. O estado é reconstruído aplicando os eventos.",
                        "from dataclasses import dataclass\nfrom datetime import datetime\nfrom typing import Any\n\n# Eventos imutáveis\n@dataclass(frozen=True)\nclass PedidoCriado:\n    pedido_id: int\n    cliente_id: int\n    ocorreu_em: datetime\n\n@dataclass(frozen=True)\nclass ItemAdicionado:\n    pedido_id: int\n    produto_id: int\n    quantidade: int\n    preco: float\n    ocorreu_em: datetime\n\n# Aggregate reconstrói estado a partir dos eventos\nclass Pedido:\n    def __init__(self, pedido_id: int):\n        self.id = pedido_id\n        self.itens = []\n        self.status = None\n\n    def apply(self, evento: Any):\n        if isinstance(evento, PedidoCriado):\n            self.cliente_id = evento.cliente_id\n            self.status = 'criado'\n        elif isinstance(evento, ItemAdicionado):\n            self.itens.append({'produto': evento.produto_id, 'qtd': evento.quantidade})\n\n    @classmethod\n    def from_events(cls, pedido_id: int, eventos: list) -> 'Pedido':\n        pedido = cls(pedido_id)\n        for evento in eventos:\n            pedido.apply(evento)\n        return pedido", "python"),
                    Section("Quando usar (e quando não usar) CQRS/ES",
                        "CQRS e Event Sourcing têm custo alto de complexidade. Use apenas quando os benefícios superam esse custo.",
                        "# CQRS vale quando:\n# - Leitura e escrita têm padrões de carga muito diferentes\n# - Modelo de leitura é muito diferente do de escrita\n# - Você precisa de múltiplas 'visões' dos mesmos dados\n\n# Event Sourcing vale quando:\n# - Auditoria completa é obrigatória (fintech, healthcare)\n# - Você precisa 'viajar no tempo' (reconstruir estado em qualquer ponto)\n# - Replay de eventos é necessário (criar novas projeções)\n\n# CUIDADO:\n# - Eventual consistency pode confundir usuários\n# - Debugging é mais difícil\n# - Queries simples ficam complicadas\n# - A maioria dos sistemas NÃO precisa de Event Sourcing\n\n# Alternativa mais simples: audit log\n# Tabela de auditoria com created_at, updated_at, changed_by, old_value, new_value\n# Resolve 80% dos casos de auditoria sem a complexidade do ES", "python"),
                ],
                exercise="Implemente CQRS para um sistema de pedidos: command handler que escreve em banco normalizado e query handler que lê de view desnormalizada.",
                takeaway="CQRS sem Event Sourcing é muito mais simples e resolve a maioria dos casos. Event Sourcing é para auditoria total e replay de eventos — use raramente."
            ),
            Lesson("ar-m2-l2", "Microsserviços: Trade-offs Reais", 22,
                "Microsserviços não são a solução para tudo. Entenda os trade-offs antes de decompor seu monolito.",
                [
                    Section("Monolito Modulado: O Melhor dos Dois Mundos",
                        "Antes de microsserviços, tente um monolito bem modularizado. É 80% dos benefícios com 20% da complexidade.",
                        "# Monolito Modulado: módulos com fronteiras claras\n# Regra: módulos só se comunicam por interfaces públicas\n\n# vendas/__init__.py (interface pública do módulo)\nfrom .service import VendasService\nfrom .schemas import PedidoCreate, PedidoResponse\n__all__ = ['VendasService', 'PedidoCreate', 'PedidoResponse']\n\n# estoque/__init__.py\nfrom .service import EstoqueService\n__all__ = ['EstoqueService']\n\n# PROIBIDO: estoque importar diretamente de vendas internals\n# from vendas.models import PedidoORM  ← ERRADO!\n\n# CORRETO: comunicação pela interface pública\nfrom vendas import VendasService\n\n# Benefícios:\n# - Deploy simples (único processo)\n# - Transações ACID\n# - Sem latência de rede entre módulos\n# - Fácil de refatorar\n# - Pode extrair para microsserviço depois, se necessário", "python"),
                    Section("Quando Extrair para Microsserviço",
                        "Extraia quando o módulo tem: escala diferente, time diferente, deploy independente necessário, ou tecnologia diferente.",
                        "# Sinais para extrair um microsserviço:\n# 1. Escala diferente: serviço de busca precisa de 20 instâncias,\n#    checkout precisa de 2\n# 2. Time independente: time de ML quer deploy sem depender do time de backend\n# 3. Tecnologia diferente: processamento de imagem precisa de C++/GPU\n# 4. Falha isolada: se o serviço de recomendação cair,\n#    o checkout deve continuar funcionando\n\n# NÃO extraia quando:\n# - O módulo precisa de transação ACID com outro módulo\n# - É usado por um único serviço\n# - O time não tem expertise em sistemas distribuídos\n# - O problema é código ruim, não escala\n\n# Regra de Sam Newman: 'Don't start with microservices'\n# Comece com monolito. Extraia quando sentir a dor real.", "python"),
                    Section("Comunicação entre Microsserviços",
                        "Síncrono (REST/gRPC): resposta imediata, acoplamento temporal. Assíncrono (Kafka/RabbitMQ): desacoplado, mais complexo. Escolha com critério.",
                        "# Síncrono (REST): use quando precisa da resposta para continuar\nimport httpx\n\nasync def verificar_estoque(produto_id: int, qtd: int) -> bool:\n    async with httpx.AsyncClient(timeout=5.0) as client:\n        r = await client.get(\n            f'http://estoque-service/produtos/{produto_id}/disponibilidade',\n            params={'quantidade': qtd}\n        )\n        return r.json()['disponivel']\n\n# Circuit Breaker: evitar cascata de falhas\nfrom tenacity import retry, stop_after_attempt, wait_exponential\n\n@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))\nasync def verificar_estoque_com_retry(produto_id, qtd):\n    return await verificar_estoque(produto_id, qtd)\n\n# Assíncrono (Kafka): use quando não precisa da resposta\n# Pedido confirmado → publica evento → Estoque reage → Logística reage\nproducer.produce('pedidos', key=str(pedido_id), value=json.dumps(evento))", "python"),
                ],
                exercise="Modele um sistema de e-commerce. Defina quais módulos ficam no monolito e quais viram microsserviços — justifique cada decisão.",
                takeaway="Microsserviços multiplicam a complexidade operacional. Comece com monolito modularizado. Extraia quando sentir a dor real de escala ou autonomia de time."
            ),
            Lesson("ar-m2-l3", "Resiliência: Circuit Breaker, Retry e Bulkhead", 20,
                "Sistemas distribuídos falham parcialmente. Resiliência é projetar para funcionar degradado.",
                [
                    Section("Circuit Breaker: Parar de Bater em Porta Fechada",
                        "Circuit Breaker monitora falhas e para de chamar um serviço temporariamente quando está falhando — evita cascata.",
                        "import time\nfrom enum import Enum\n\nclass Estado(Enum):\n    FECHADO = 'fechado'    # funcionando normalmente\n    ABERTO = 'aberto'      # falhando: rejeita chamadas\n    MEIO_ABERTO = 'meio_aberto'  # testando se voltou\n\nclass CircuitBreaker:\n    def __init__(self, limite_falhas=5, timeout_s=60):\n        self.limite = limite_falhas\n        self.timeout = timeout_s\n        self.falhas = 0\n        self.estado = Estado.FECHADO\n        self.ultima_falha = None\n\n    def chamar(self, func, *args, **kwargs):\n        if self.estado == Estado.ABERTO:\n            if time.time() - self.ultima_falha > self.timeout:\n                self.estado = Estado.MEIO_ABERTO\n            else:\n                raise Exception('Circuit Breaker ABERTO — serviço indisponível')\n\n        try:\n            resultado = func(*args, **kwargs)\n            self.falhas = 0\n            self.estado = Estado.FECHADO\n            return resultado\n        except Exception as e:\n            self.falhas += 1\n            self.ultima_falha = time.time()\n            if self.falhas >= self.limite:\n                self.estado = Estado.ABERTO\n            raise", "python"),
                    Section("Retry com Exponential Backoff e Jitter",
                        "Retry ingênuo (retry imediato) pode derrubar um serviço que está se recuperando. Exponential backoff + jitter distribui a carga.",
                        "import asyncio\nimport random\nfrom tenacity import (\n    retry, stop_after_attempt,\n    wait_exponential, wait_random,\n    retry_if_exception_type\n)\nimport httpx\n\n# Tenacity: retry profissional\n@retry(\n    stop=stop_after_attempt(4),\n    wait=wait_exponential(multiplier=1, min=1, max=30) + wait_random(0, 2),\n    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),\n    reraise=True\n)\nasync def chamar_api_externa(url: str) -> dict:\n    async with httpx.AsyncClient(timeout=10) as client:\n        r = await client.get(url)\n        r.raise_for_status()\n        return r.json()\n\n# Delays com jitter: 1s, ~2s, ~4s, ~8s (com variação aleatória)\n# Sem jitter: 1s, 2s, 4s, 8s (todos retentam no mesmo segundo = thundering herd)", "python"),
                    Section("Bulkhead: Isolar Falhas por Compartimento",
                        "Bulkhead separa pools de recursos. Se um serviço lento consume todas as threads, outros serviços não são afetados.",
                        "import asyncio\nfrom asyncio import Semaphore\n\n# Bulkhead com Semaphore: limitar concorrência por serviço\nclass BulkheadClient:\n    def __init__(self, max_concurrent: int = 10):\n        self.semaphore = Semaphore(max_concurrent)\n\n    async def get(self, url: str) -> dict:\n        async with self.semaphore:  # máximo 10 chamadas simultâneas\n            async with httpx.AsyncClient(timeout=5.0) as client:\n                r = await client.get(url)\n                return r.json()\n\n# Pool separado por serviço\nestoque_client = BulkheadClient(max_concurrent=10)\npagamento_client = BulkheadClient(max_concurrent=5)  # mais restrito\n\n# Se estoque travar, pagamento não é afetado\nasync def processar_pedido(pedido):\n    estoque_ok = await estoque_client.get(f'/estoque/{pedido.produto_id}')\n    if estoque_ok:\n        resultado = await pagamento_client.get(f'/pagamento/processar')\n        return resultado", "python"),
                ],
                exercise="Implemente um cliente HTTP com Circuit Breaker + Retry exponencial + Bulkhead. Simule falhas e observe o comportamento de cada mecanismo.",
                takeaway="Circuit Breaker evita cascata. Retry com jitter evita thundering herd. Bulkhead isola falhas. Os três juntos são o padrão de resiliência para microsserviços."
            ),
        ]),
        Module("ar-m3", "Escalabilidade e Performance", "Como sistemas escalam de 100 para 10 milhões de usuários.", [
            Lesson("ar-m3-l1", "Estratégias de Cache", 20,
                "Cache é o multiplicador de performance mais poderoso. Cada camada tem seu papel.",
                [
                    Section("Camadas de Cache",
                        "Browser → CDN → Reverse Proxy (Nginx) → Application Cache (Redis) → Database Cache. Cada camada tem hit rate e latência diferentes.",
                        "# Camadas de cache e latências típicas:\n# L1 (CPU cache):      1ns\n# L2 (RAM):            100ns\n# Redis local:         0.5ms\n# Redis remoto:        1ms\n# SSD (banco):         100ms\n# HDD:                 10ms (seek) + throughput\n# Rede (outro DC):     30ms\n\n# Application Cache com Redis\nimport redis\nimport json\nfrom functools import wraps\n\nr = redis.Redis(host='localhost', decode_responses=True)\n\ndef cache(ttl_seconds: int = 300):\n    def decorator(func):\n        @wraps(func)\n        async def wrapper(*args, **kwargs):\n            key = f'{func.__name__}:{args}:{kwargs}'\n            cached = r.get(key)\n            if cached:\n                return json.loads(cached)  # HIT\n            result = await func(*args, **kwargs)  # MISS\n            r.setex(key, ttl_seconds, json.dumps(result))\n            return result\n        return wrapper\n    return decorator\n\n@cache(ttl=60)\nasync def get_produto(produto_id: int) -> dict:\n    return await db.fetch_one(f'SELECT * FROM produtos WHERE id = {produto_id}')", "python"),
                    Section("Estratégias: Cache-Aside, Write-Through, Write-Behind",
                        "Cache-Aside (Lazy): aplicação gerencia o cache. Write-Through: escreve no cache e banco simultaneamente. Write-Behind: escreve no cache, banco assíncrono.",
                        "# Cache-Aside (mais comum)\nasync def get_usuario(user_id: int):\n    cached = await redis.get(f'user:{user_id}')\n    if cached:\n        return json.loads(cached)  # cache hit\n    usuario = await db.get(user_id)  # cache miss\n    await redis.setex(f'user:{user_id}', 300, json.dumps(usuario))\n    return usuario\n\nasync def atualizar_usuario(user_id: int, dados: dict):\n    await db.update(user_id, dados)\n    await redis.delete(f'user:{user_id}')  # invalidar cache\n\n# Write-Through: sempre consistente, mais lento na escrita\nasync def salvar_produto(produto: dict):\n    await db.save(produto)              # 1. banco\n    await redis.set(f'prod:{produto[\"id\"]}', json.dumps(produto))  # 2. cache\n\n# Problema do cache: thundering herd\n# Solução: probabilistic early expiration\nimport random, math\ndef deve_recomputar(ttl_restante, beta=1.0):\n    return -ttl_restante - beta * math.log(random.random()) < 0", "python"),
                    Section("Cache Invalidation: O Problema Difícil",
                        "'Há apenas dois problemas difíceis em ciências da computação: invalidação de cache e naming things.' — Phil Karlton",
                        "# Estratégias de invalidação:\n\n# 1. TTL (Time-To-Live): mais simples, aceita staleness\nawait redis.setex('config', 300, json.dumps(config))  # expira em 5min\n\n# 2. Event-based: invalida quando dado muda\nasync def on_produto_atualizado(evento: ProdutoAtualizado):\n    await redis.delete(f'produto:{evento.produto_id}')\n    await redis.delete('produtos:lista')  # invalidar listas também!\n\n# 3. Versioning: nunca invalida, só versiona\nasync def get_produto_v(produto_id: int, version: int):\n    key = f'produto:{produto_id}:v{version}'\n    cached = await redis.get(key)\n    if not cached:\n        produto = await db.get(produto_id)\n        await redis.setex(key, 3600, json.dumps(produto))\n    return json.loads(cached)\n\n# Cache Tags: invalidar grupo de chaves\n# ex: ao atualizar categoria, invalidar todos os produtos da categoria\nawait redis.sadd(f'tag:categoria:{cat_id}', f'produto:{prod_id}')\n# invalidar:\nkeys = await redis.smembers(f'tag:categoria:{cat_id}')\nawait redis.delete(*keys)", "python"),
                ],
                exercise="Implemente cache-aside com Redis para o endpoint de produto mais acessado. Meça o p99 de latência com e sem cache.",
                takeaway="Cache é o antibiótico da performance — resolve quase tudo mas tem efeitos colaterais (staleness, invalidação). Use com critério e sempre meça o hit rate."
            ),
            Lesson("ar-m3-l2", "Database Sharding e Replicação", 18,
                "Quando um único banco não aguentar a carga, escalabilidade horizontal é a resposta.",
                [
                    Section("Replicação: Primary-Replica",
                        "Primary recebe writes. Replicas recebem reads. A maioria das aplicações tem 10x mais reads que writes — réplicas de leitura multiplicam capacidade.",
                        "# SQLAlchemy com múltiplos bancos\nfrom sqlalchemy.ext.asyncio import create_async_engine, AsyncSession\nfrom sqlalchemy.orm import sessionmaker\nimport random\n\n# Engines separadas\nwrite_engine = create_async_engine('postgresql+asyncpg://primary/db')\nread_engines = [\n    create_async_engine('postgresql+asyncpg://replica1/db'),\n    create_async_engine('postgresql+asyncpg://replica2/db'),\n]\n\ndef get_read_engine():\n    return random.choice(read_engines)  # round-robin simples\n\n# Dependency injection por tipo de operação\nasync def get_write_db() -> AsyncSession:\n    async with AsyncSession(write_engine) as s:\n        yield s\n\nasync def get_read_db() -> AsyncSession:\n    async with AsyncSession(get_read_engine()) as s:\n        yield s\n\n# Router:\n@app.get('/produtos')           # leitura\nasync def listar(db = Depends(get_read_db)): ...\n\n@app.post('/produtos')          # escrita\nasync def criar(db = Depends(get_write_db)): ...", "python"),
                    Section("Sharding: Particionar Dados Horizontalmente",
                        "Sharding divide os dados em múltiplos bancos por uma shard key. Resolve limites de volume que réplicas não resolvem.",
                        "import hashlib\n\nNUM_SHARDS = 4\nSHARD_CONNECTIONS = {\n    0: 'postgresql+asyncpg://shard0/db',\n    1: 'postgresql+asyncpg://shard1/db',\n    2: 'postgresql+asyncpg://shard2/db',\n    3: 'postgresql+asyncpg://shard3/db',\n}\n\ndef get_shard(shard_key: str) -> int:\n    # Hash consistente: mesmo key sempre vai para mesmo shard\n    return int(hashlib.md5(shard_key.encode()).hexdigest(), 16) % NUM_SHARDS\n\ndef get_engine_for_user(user_id: str):\n    shard = get_shard(user_id)\n    return engines[shard]\n\n# Problema: queries cross-shard são caras\n# 'Buscar todos os pedidos do Brasil' requer query em todos os shards\n# Solução: escolher shard key com sabedoria (user_id, tenant_id)\n\n# Reshard sem downtime é extremamente difícil\n# Planeje a shard key com cuidado desde o início!", "python"),
                    Section("CQRS com Read Models Desnormalizados",
                        "Para escalar reads sem sharding, crie tabelas desnormalizadas otimizadas para consulta — atualizadas por eventos.",
                        "# Read Model: tabela desnormalizada para query rápida\n# Atualizada por eventos — sem joins na hora da leitura\n\n# Tabela de escrita (normalizada):\n# pedidos(id, cliente_id, data, status)\n# itens_pedido(id, pedido_id, produto_id, qtd, preco)\n\n# Read Model (desnormalizada, otimizada para dashboard):\nCREATE TABLE pedidos_view (\n    pedido_id INT PRIMARY KEY,\n    cliente_nome VARCHAR(200),\n    cliente_email VARCHAR(200),\n    data_pedido DATE,\n    total_itens INT,\n    valor_total DECIMAL(12,2),\n    status VARCHAR(50),\n    ultimo_produto VARCHAR(200)\n);\nCREATE INDEX ON pedidos_view(data_pedido, status);\n\n-- Atualizar read model via trigger ou evento\n-- Event handler:\nasync def on_pedido_confirmado(evento):\n    await read_db.execute(\n        'INSERT INTO pedidos_view ... ON CONFLICT DO UPDATE SET ...',\n        {...}\n    )", "sql"),
                ],
                exercise="Configure primary-replica com SQLAlchemy. Roteie queries de leitura para réplica e escrita para primary. Meça o throughput antes e depois.",
                takeaway="Réplicas de leitura resolvem 90% dos problemas de escala de banco. Sharding é o último recurso — o custo de manutenção é muito alto."
            ),
            Lesson("ar-m3-l3", "System Design: Como Arquitetar Sistemas do Zero", 22,
                "System Design é a habilidade de transformar requisitos vagos em arquitetura concreta. Aprenda o framework.",
                [
                    Section("Framework de System Design",
                        "Toda entrevista ou projeto de arquitetura segue a mesma estrutura. Domine o processo antes de pensar em tecnologia.",
                        "# Framework em 6 etapas:\n\n# 1. CLARIFICAR requisitos (5 min)\n# - Quantos usuários? (100, 1M, 1B?)\n# - Leitura vs escrita (10:1? 100:1?)\n# - Consistência ou disponibilidade? (CAP theorem)\n# - Latência aceitável? (10ms? 500ms?)\n# - Escala geográfica? (1 região, global?)\n\n# 2. ESTIMAR escala\n# 1M usuários, 10 req/usuário/dia = 10M req/dia\n# = ~115 req/s (médio) = ~500 req/s (pico)\n# Armazenamento: 10M req * 1KB = 10GB/dia = 3.6TB/ano\n\n# 3. DESENHAR arquitetura de alto nível\n# Load Balancer → API Servers → Cache → Database\n\n# 4. DETALHAR componentes críticos\n# Qual banco? (SQL vs NoSQL)\n# Como o cache funciona?\n# Como escalar o componente gargalo?\n\n# 5. IDENTIFICAR gargalos e trade-offs\n# 6. MONITORAMENTO e observabilidade", "python"),
                    Section("Design de um URL Shortener",
                        "Exemplo clássico: projetar bit.ly do zero. Veja o raciocínio completo.",
                        "# Requisitos:\n# - 100M URLs criadas/dia\n# - 10B cliques/dia (100:1 read:write)\n# - URL curta de 7 caracteres\n# - Redirecionamento < 10ms\n\n# Estimativas:\n# Writes: 100M/dia = 1.160/s\n# Reads:  10B/dia  = 115.700/s\n# Armazenamento: 100M * 500B = 50GB/dia\n\n# Geração de ID curto:\nimport base62  # pip install pybase62\nimport random\n\ndef gerar_codigo() -> str:\n    # 7 chars base62 = 62^7 = 3.5 trilhões de combinações\n    numero = random.randint(0, 62**7)\n    return base62.encode(numero).zfill(7)\n\n# Arquitetura:\n# Write path: API → Redis (dedup) → DB (PostgreSQL)\n# Read path:  DNS → CDN (cache 24h) → Redis (cache 1h) → DB\n\n# Por que CDN? 80% dos clicks acontecem nas primeiras horas\n# CDN elimina chamada ao servidor para links populares", "python"),
                    Section("CAP Theorem na Prática",
                        "CAP: Consistency, Availability, Partition Tolerance. Em sistemas distribuídos, só dá para garantir 2 dos 3. Entenda o que seu sistema precisa.",
                        "# CAP Theorem:\n# P (Partition Tolerance): rede pode falhar — SEMPRE deve ser tolerado\n# Logo a escolha real é: CP ou AP\n\n# CP (Consistency + Partition Tolerance):\n# - Prefere consistência: rejeita requests se não puder garantir dado atualizado\n# - Exemplos: HBase, Zookeeper, etcd\n# - Use quando: banco financeiro, inventário (não pode oversell)\n\n# AP (Availability + Partition Tolerance):\n# - Prefere disponibilidade: pode retornar dado desatualizado\n# - Exemplos: Cassandra, DynamoDB (eventual consistency)\n# - Use quando: timeline de redes sociais, analytics, catálogo de produtos\n\n# PACELC: extensão do CAP\n# Sem partição: Latency vs Consistency\n# Com partição: Availability vs Consistency\n\n# Exemplo prático:\n# Pedido de compra → CP (não pode perder o pedido)\n# Feed de notícias → AP (ok se demorar 1s para atualizar)\n# Contagem de likes → AP (eventual consistency aceitável)", "python"),
                ],
                exercise="Arquitete um sistema de chat em tempo real para 10M usuários. Estime escala, defina componentes e justifique as escolhas de CP vs AP.",
                takeaway="System Design não tem resposta certa — tem trade-offs justificados. O framework é: clarificar → estimar → desenhar → detalhar → identificar gargalos."
            ),
        ]),
        Module("ar-m4", "Projeto Final: Arquitetar um Sistema Real", "Aplique todos os conceitos em um sistema completo.", [
            Lesson("ar-m4-l1", "API Gateway e BFF Pattern", 18,
                "API Gateway centraliza cross-cutting concerns. BFF otimiza a API para cada tipo de cliente.",
                [
                    Section("API Gateway: Uma Entrada, Múltiplos Serviços",
                        "API Gateway cuida de: autenticação, rate limiting, logging, roteamento e transformação — sem poluir os microsserviços.",
                        "# Nginx como API Gateway básico\n# nginx.conf\nupstream api_service {\n    server api1:8000;\n    server api2:8000;\n    server api3:8000;\n}\n\nupstream auth_service {\n    server auth:8001;\n}\n\nserver {\n    listen 80;\n\n    # Rate limiting\n    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;\n\n    location /api/v1/ {\n        limit_req zone=api burst=20;\n        proxy_pass http://api_service;\n\n        # Adicionar headers de contexto\n        proxy_set_header X-Request-ID $request_id;\n        proxy_set_header X-Real-IP $remote_addr;\n    }\n\n    location /auth/ {\n        proxy_pass http://auth_service;\n    }\n}", "bash"),
                    Section("BFF: Backend for Frontend",
                        "BFF cria uma API otimizada para cada tipo de cliente — mobile precisa de menos dados que o web admin.",
                        "from fastapi import FastAPI, Depends\nimport httpx\n\n# BFF Mobile: resposta compacta (menos dados, menos banda)\nmobile_bff = FastAPI(title='Mobile BFF')\n\n@mobile_bff.get('/home')\nasync def home_mobile(usuario_id: int):\n    async with httpx.AsyncClient() as client:\n        # Uma chamada agrega dados de 3 microsserviços\n        perfil, pedidos, ofertas = await asyncio.gather(\n            client.get(f'http://usuarios/{usuario_id}/resumo'),\n            client.get(f'http://pedidos/{usuario_id}/recentes?limit=3'),\n            client.get(f'http://marketing/ofertas?limit=2'),\n        )\n    return {\n        'nome': perfil.json()['nome'],  # só nome, sem foto\n        'ultimos_pedidos': pedidos.json(),\n        'ofertas': ofertas.json(),\n    }\n\n# BFF Web Admin: resposta completa\nadmin_bff = FastAPI(title='Admin BFF')\n\n@admin_bff.get('/pedidos/{id}')\nasync def pedido_admin(id: int):\n    # Traz tudo: histórico, logs, dados completos\n    ...", "python"),
                    Section("Service Mesh com Istio",
                        "Service Mesh gerencia comunicação entre microsserviços: mTLS, circuit breaking, observabilidade — sem código na aplicação.",
                        "# Istio VirtualService: roteamento avançado\napiVersion: networking.istio.io/v1alpha3\nkind: VirtualService\nmetadata:\n  name: api-vs\nspec:\n  hosts:\n  - api\n  http:\n  # Canary: 10% do tráfego para v2\n  - route:\n    - destination:\n        host: api\n        subset: v1\n      weight: 90\n    - destination:\n        host: api\n        subset: v2\n      weight: 10\n\n---\n# DestinationRule: circuit breaking automático\napiVersion: networking.istio.io/v1alpha3\nkind: DestinationRule\nmetadata:\n  name: api-dr\nspec:\n  host: api\n  trafficPolicy:\n    outlierDetection:\n      consecutiveErrors: 5\n      interval: 30s\n      baseEjectionTime: 60s", "yaml"),
                ],
                exercise="Implemente um BFF para mobile e outro para web admin, cada um agregando dados de 3 microsserviços diferentes com respostas otimizadas.",
                takeaway="BFF resolve o problema de over-fetching (mobile recebe dados demais) e under-fetching (precisa de múltiplas chamadas). API Gateway centraliza cross-cutting concerns."
            ),
            Lesson("ar-m4-l2", "Observabilidade: Logs, Métricas e Traces", 20,
                "Os três pilares da observabilidade: saber o que está acontecendo no sistema em qualquer momento.",
                [
                    Section("Logging Estruturado",
                        "Logs em JSON com contexto (request_id, user_id, trace_id) são consultáveis. Logs em texto livre são inúteis em escala.",
                        "import structlog\nfrom fastapi import Request\n\n# Configurar structlog\nstructlog.configure(\n    processors=[\n        structlog.processors.TimeStamper(fmt='iso'),\n        structlog.processors.add_log_level,\n        structlog.processors.JSONRenderer(),\n    ]\n)\n\nlogger = structlog.get_logger()\n\n# Middleware: adicionar contexto a todos os logs\n@app.middleware('http')\nasync def logging_middleware(request: Request, call_next):\n    log = logger.bind(\n        request_id=request.headers.get('X-Request-ID'),\n        method=request.method,\n        path=request.url.path,\n        user_agent=request.headers.get('User-Agent')\n    )\n    log.info('request_started')\n    response = await call_next(request)\n    log.info('request_finished', status=response.status_code)\n    return response\n\n# Log de negócio com contexto\nlogger.info('pedido_confirmado',\n    pedido_id=pedido.id,\n    valor=float(pedido.total),\n    cliente_id=pedido.cliente_id\n)", "python"),
                    Section("Os 4 Golden Signals",
                        "Google SRE define 4 métricas que cobrem todos os sistemas: Latency, Traffic, Errors, Saturation.",
                        "from prometheus_client import Counter, Histogram, Gauge\n\n# Latency: tempo de resposta\nLATENCY = Histogram(\n    'http_request_duration_seconds',\n    'Request duration',\n    ['method', 'endpoint'],\n    buckets=[.005, .01, .025, .05, .1, .25, .5, 1, 2.5]\n)\n\n# Traffic: volume de requests\nTRAFFIC = Counter(\n    'http_requests_total',\n    'Total requests',\n    ['method', 'endpoint', 'status']\n)\n\n# Errors: taxa de erros\n# (derivada do Traffic com status >= 500)\n\n# Saturation: uso de recursos\nDB_POOL_SIZE = Gauge('db_pool_size', 'DB connection pool size')\nDB_POOL_USED = Gauge('db_pool_used', 'DB connections in use')\n\n# SLO: 99.9% das requests em < 500ms\n# Alerta: se p99 > 400ms por 5 minutos → page", "python"),
                    Section("Distributed Tracing com OpenTelemetry",
                        "Trace rastreia uma request através de múltiplos serviços. Essencial para debugar em microsserviços.",
                        "from opentelemetry import trace\nfrom opentelemetry.sdk.trace import TracerProvider\nfrom opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter\nfrom opentelemetry.instrumentation.fastapi import FastAPIInstrumentor\nfrom opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor\n\n# Setup\nprovider = TracerProvider()\nprovider.add_span_processor(\n    BatchSpanProcessor(OTLPSpanExporter(endpoint='http://jaeger:4317'))\n)\ntrace.set_tracer_provider(provider)\n\n# Auto-instrumentar (zero código extra)\nFastAPIInstrumentor.instrument_app(app)\nHTTPXClientInstrumentor().instrument()  # propaga trace_id em chamadas HTTP\n\n# Span manual para operações importantes\ntracer = trace.get_tracer(__name__)\n\nasync def processar_pagamento(pedido_id: int, valor: float):\n    with tracer.start_as_current_span('processar_pagamento') as span:\n        span.set_attribute('pedido.id', pedido_id)\n        span.set_attribute('pagamento.valor', valor)\n        resultado = await gateway_pagamento.cobrar(valor)\n        span.set_attribute('pagamento.status', resultado.status)\n        return resultado", "python"),
                ],
                exercise="Configure os 4 Golden Signals com Prometheus. Adicione logging estruturado com request_id e OpenTelemetry para traces distribuídos.",
                takeaway="Sem os 3 pilares (logs + métricas + traces) você é cego em produção. Logs explicam o quê, métricas mostram o quanto, traces mostram o onde."
            ),
            Lesson("ar-m4-l3", "ADR: Documentar Decisões de Arquitetura", 15,
                "Architecture Decision Records documentam por que uma decisão foi tomada — o ativo mais valioso de longa duração de um sistema.",
                [
                    Section("O que é um ADR e por que escrever",
                        "ADR responde: qual era o contexto? quais opções foram consideradas? qual foi escolhida e por quê? quais são as consequências?",
                        "# Template ADR (Markdown)\n# docs/adr/001-banco-de-dados-principal.md\n\n# ADR 001: Escolha do Banco de Dados Principal\n\n## Status\nAceito\n\n## Contexto\nPrecisamos escolher o banco para o sistema de pedidos.\nEstimamos 500 writes/s e 5000 reads/s no pico.\nO time tem expertise em PostgreSQL e SQL.\n\n## Opções Consideradas\n1. **PostgreSQL** — SQL padrão, ACID, extensions ricas\n2. **MongoDB** — Flexibilidade de schema, horizontal scaling\n3. **DynamoDB** — Serverless, escala infinita, custo por uso\n\n## Decisão\nPostgreSQL com réplicas de leitura.\n\n## Justificativa\n- Equipe já tem expertise → menor risco\n- ACID necessário para transações de pagamento\n- 5000 reads/s resolvido com réplicas — sem necessidade de NoSQL\n- Extensions: pgvector para futuro ML, TimescaleDB para métricas\n\n## Consequências\n- Positivas: consistência, SQL padrão, ecossistema maduro\n- Negativas: escala horizontal mais complexa que Dynamo\n- Riscos: reshard manual se crescer acima de 10TB", "markdown"),
                    Section("Quando Escrever um ADR",
                        "Escreva quando a decisão é: difícil de reverter, impacta múltiplos times, ou tem trade-offs não óbvios.",
                        "# Decisões que merecem ADR:\n# - Escolha de banco de dados ou message broker\n# - Arquitetura de autenticação (JWT vs sessão vs OAuth)\n# - Estratégia de versionamento de API\n# - Monolito vs microsserviços\n# - Linguagem ou framework principal\n# - Estratégia de cache\n\n# Decisões que NÃO precisam de ADR:\n# - Qual biblioteca de logging usar\n# - Formatação de código\n# - Nomes de variáveis\n\n# Ferramentas:\n# adr-tools: CLI para criar e listar ADRs\n# pip install adr-tools\n\n# Criar novo ADR:\n# adr new 'Escolha do message broker'\n# → docs/adr/002-message-broker.md\n\n# Listar ADRs:\n# adr list", "bash"),
                    Section("RFC: Request for Comments para Decisões Grandes",
                        "Para decisões grandes que afetam múltiplos times, RFC permite coletar feedback antes de decidir.",
                        "# Template RFC\n# docs/rfc/rfc-001-migracao-para-microsservicos.md\n\n# RFC 001: Migração para Microsserviços\n\n## Resumo\nPropomos decompor o monolito em 5 microsserviços ao longo de 12 meses.\n\n## Motivação\n- Deploy acoplado causa janelas de 4 horas\n- Time de ML quer autonomia de deploy\n- Módulo de pagamento precisa de PCI DSS isolado\n\n## Proposta Detalhada\n### Fase 1 (Meses 1-3): Extrair Autenticação\n- Auth separado primeiro: menos risk, mais ganho\n- Strangler Fig Pattern: proxy intercepta requests\n\n### Fase 2 (Meses 4-6): Extrair Pagamentos\n...\n\n## Alternativas Consideradas\n- Monolito modularizado — descartado porque...\n- Migração big-bang — descartada porque...\n\n## Perguntas Abertas\n- Como gerenciar transações cross-service?\n- Qual service mesh usar?\n\n## Revisor Responsável: @lead-architect\n## Prazo para feedback: 2024-02-15", "markdown"),
                ],
                exercise="Escreva 3 ADRs para decisões reais de um sistema que você está construindo. Inclua contexto, opções, decisão e consequências.",
                takeaway="ADRs são cartas para o futuro — explicam por que, não apenas o quê. Em 2 anos, quando alguém perguntar 'por que usamos PostgreSQL?', o ADR responde."
            ),
        ]),
    ]
)


# ─────────────────────────────────────────────────────────────────────────────
# CURSO 9 — AWS CLOUD FUNDAMENTOS
# ─────────────────────────────────────────────────────────────────────────────
AWS_COURSE = Course(
    id="aws-cloud-fundamentos",
    title="AWS Cloud: Do Zero ao Deploy em Produção",
    tagline="Domine os serviços AWS essenciais e suba aplicações reais na nuvem",
    description="Aprenda os serviços AWS mais usados na prática: compute, storage, banco de dados, rede, serverless, IAM e monitoramento. Foco em aplicações reais.",
    level="Iniciante → Intermediário",
    category="Cloud",
    duration_hours=20,
    skills=["AWS", "EC2", "S3", "RDS", "Lambda", "IAM", "VPC", "CloudFormation", "Terraform"],
    color="#f97316",
    modules=[
        Module("aws-m1", "Fundamentos: IAM, VPC e Compute", "Os blocos fundamentais que toda aplicação AWS usa.", [
            Lesson("aws-m1-l1", "IAM: Identidade e Controle de Acesso", 18,
                "IAM é a fundação de segurança da AWS. Tudo começa aqui — sem entender IAM, você não entende AWS.",
                [
                    Section("Users, Groups, Roles e Policies",
                        "User: pessoa ou serviço. Group: conjunto de users. Role: identidade temporária assumida por serviço. Policy: documento JSON que define permissões.",
                        "# Criar policy de acesso apenas a um bucket S3\naws iam create-policy \\\n    --policy-name MeuBucketReadOnly \\\n    --policy-document '{\n        \"Version\": \"2012-10-17\",\n        \"Statement\": [{\n            \"Effect\": \"Allow\",\n            \"Action\": [\"s3:GetObject\", \"s3:ListBucket\"],\n            \"Resource\": [\n                \"arn:aws:s3:::meu-bucket\",\n                \"arn:aws:s3:::meu-bucket/*\"\n            ]\n        }]\n    }'\n\n# Criar role para EC2 acessar S3 sem credenciais hardcoded\naws iam create-role \\\n    --role-name EC2S3ReadRole \\\n    --assume-role-policy-document '{\n        \"Version\": \"2012-10-17\",\n        \"Statement\": [{\n            \"Effect\": \"Allow\",\n            \"Principal\": {\"Service\": \"ec2.amazonaws.com\"},\n            \"Action\": \"sts:AssumeRole\"\n        }]\n    }'\n\naws iam attach-role-policy \\\n    --role-name EC2S3ReadRole \\\n    --policy-arn arn:aws:iam::123456789:policy/MeuBucketReadOnly", "bash"),
                    Section("Least Privilege: Nunca use root ou AdministratorAccess",
                        "Root é para criar a conta e nunca mais. AdministratorAccess em produção é malpractice. Sempre menor privilégio necessário.",
                        "# Ruim: usar root account no dia a dia\n# Ruim: AdministratorAccess para aplicação\n# Bom: policy específica para o que a aplicação precisa\n\n# Verificar permissões excessivas com Access Analyzer\naws accessanalyzer list-findings \\\n    --analyzer-arn arn:aws:access-analyzer:us-east-1:123:analyzer/meu-analyzer\n\n# Simular acesso antes de criar resource (Policy Simulator)\naws iam simulate-principal-policy \\\n    --policy-source-arn arn:aws:iam::123:user/meu-usuario \\\n    --action-names s3:DeleteObject \\\n    --resource-arns arn:aws:s3:::meu-bucket/*\n\n# Regra: SCP (Service Control Policy) na org bloqueia\n# criação de recursos fora de us-east-1 e sa-east-1\n# Garante conformidade mesmo se dev errar a região", "bash"),
                    Section("Python com Boto3: Autenticação sem Credenciais Hardcoded",
                        "Nunca coloque access keys no código. Use roles em EC2/Lambda, profiles locais ou environment variables.",
                        "import boto3\n\n# Em EC2/Lambda: boto3 pega credenciais da role automaticamente\ns3 = boto3.client('s3')  # sem credencial explícita!\n\n# Local: use AWS profiles (~/.aws/credentials)\ns3 = boto3.Session(profile_name='meu-perfil-dev').client('s3')\n\n# Listar objetos de um bucket\ndef listar_arquivos(bucket: str, prefix: str = '') -> list[str]:\n    paginator = s3.get_paginator('list_objects_v2')\n    arquivos = []\n    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):\n        for obj in page.get('Contents', []):\n            arquivos.append(obj['Key'])\n    return arquivos\n\n# Upload com metadados\ndef upload_parquet(df, bucket: str, key: str):\n    import io\n    buffer = io.BytesIO()\n    df.to_parquet(buffer)\n    s3.put_object(\n        Bucket=bucket,\n        Key=key,\n        Body=buffer.getvalue(),\n        ContentType='application/octet-stream',\n        Metadata={'criado-por': 'pipeline-vendas', 'versao': '2'}\n    )", "python"),
                ],
                exercise="Crie um IAM user com acesso apenas a S3, um role para EC2 e teste com Boto3 sem credenciais hardcoded.",
                takeaway="IAM Role > IAM User para serviços. Nunca hardcode access keys. Least privilege não é paranoia — é profissionalismo."
            ),
            Lesson("aws-m1-l2", "VPC: Rede Privada na AWS", 20,
                "VPC é sua rede privada na AWS. Sem entender subnets, security groups e routing, você não sabe onde seus serviços estão.",
                [
                    Section("VPC, Subnets, Internet Gateway e NAT",
                        "Public subnet: tem rota para Internet Gateway. Private subnet: sem acesso direto à internet, usa NAT Gateway para saída.",
                        "# Criar VPC com subnets via Terraform\nresource \"aws_vpc\" \"main\" {\n  cidr_block           = \"10.0.0.0/16\"\n  enable_dns_hostnames = true\n  tags = { Name = \"minha-vpc\" }\n}\n\nresource \"aws_subnet\" \"public\" {\n  vpc_id                  = aws_vpc.main.id\n  cidr_block              = \"10.0.1.0/24\"\n  availability_zone       = \"us-east-1a\"\n  map_public_ip_on_launch = true\n  tags = { Name = \"public-subnet\" }\n}\n\nresource \"aws_subnet\" \"private\" {\n  vpc_id            = aws_vpc.main.id\n  cidr_block        = \"10.0.2.0/24\"\n  availability_zone = \"us-east-1a\"\n  tags = { Name = \"private-subnet\" }\n}\n\nresource \"aws_internet_gateway\" \"igw\" {\n  vpc_id = aws_vpc.main.id\n}\n\n# NAT Gateway: permite private subnet acessar internet\nresource \"aws_nat_gateway\" \"nat\" {\n  allocation_id = aws_eip.nat.id\n  subnet_id     = aws_subnet.public.id\n}", "hcl"),
                    Section("Security Groups vs NACLs",
                        "Security Group: firewall stateful no nível do recurso. NACL: stateless no nível da subnet. Use SG para 99% dos casos.",
                        "resource \"aws_security_group\" \"app\" {\n  name   = \"app-sg\"\n  vpc_id = aws_vpc.main.id\n\n  ingress {\n    from_port       = 8000\n    to_port         = 8000\n    protocol        = \"tcp\"\n    security_groups = [aws_security_group.alb.id]\n  }\n\n  egress {\n    from_port   = 0\n    to_port     = 0\n    protocol    = \"-1\"\n    cidr_blocks = [\"0.0.0.0/0\"]\n  }\n}\n\nresource \"aws_security_group\" \"db\" {\n  ingress {\n    from_port       = 5432\n    to_port         = 5432\n    protocol        = \"tcp\"\n    security_groups = [aws_security_group.app.id]\n  }\n}", "hcl"),
                    Section("VPC Endpoints: Acesso Privado a Serviços AWS",
                        "VPC Endpoint permite acessar S3, DynamoDB e outros serviços sem passar pela internet pública — mais seguro e sem custo de NAT.",
                        "# S3 Gateway Endpoint (gratuito!)\nresource \"aws_vpc_endpoint\" \"s3\" {\n  vpc_id       = aws_vpc.main.id\n  service_name = \"com.amazonaws.us-east-1.s3\"\n  vpc_endpoint_type = \"Gateway\"\n  route_table_ids = [aws_route_table.private.id]\n}\n\n# Interface Endpoint para Secrets Manager\nresource \"aws_vpc_endpoint\" \"secrets\" {\n  vpc_id              = aws_vpc.main.id\n  service_name        = \"com.amazonaws.us-east-1.secretsmanager\"\n  vpc_endpoint_type   = \"Interface\"\n  subnet_ids          = [aws_subnet.private.id]\n  security_group_ids  = [aws_security_group.endpoint.id]\n  private_dns_enabled = true\n}", "hcl"),
                ],
                exercise="Crie uma VPC com subnets pública e privada. Coloque uma EC2 na private subnet, acesse o S3 via VPC Endpoint sem NAT.",
                takeaway="Banco de dados sempre em private subnet. Load Balancer em public. VPC Endpoint para S3 economiza NAT Gateway e elimina tráfego público."
            ),
            Lesson("aws-m1-l3", "EC2: Compute na AWS", 20,
                "EC2 é o bloco de compute mais flexível da AWS. Aprenda a escolher o tipo certo, configurar e automatizar.",
                [
                    Section("Tipos de Instância e Quando Usar",
                        "t3: propósito geral burstable. m6i: steady state. c6i: compute-intensivo. r6i: memory-intensivo. Spot economiza 90% para batch.",
                        "# Tipos mais usados:\n# t3.micro / t3.small: dev/staging, CPU burstable\n# t3.medium / t3.large: apps pequenas de produção\n# m6i.large: apps web com carga constante\n# c6i.xlarge: processamento de dados, APIs high-throughput\n# r6i.large: banco de dados in-memory, caches grandes\n\n# Spot para pipeline de dados:\nresource \"aws_spot_instance_request\" \"pipeline\" {\n  ami           = data.aws_ami.amazon_linux.id\n  instance_type = \"c6i.4xlarge\"\n  spot_price    = \"0.20\"\n  user_data     = base64encode(file(\"startup.sh\"))\n}", "hcl"),
                    Section("User Data e Instance Profile: Bootstrap sem SSH",
                        "User Data executa na inicialização. Instance Profile injeta credenciais. Juntos eliminam acesso manual via SSH.",
                        "#!/bin/bash\nset -euxo pipefail\n\nyum update -y && yum install -y python3.11 git\n\ngit clone https://github.com/minha-org/minha-api.git /opt/app\ncd /opt/app && pip3.11 install -r requirements.txt\n\n# Buscar secret sem credenciais hardcoded (usa a role da EC2)\nDATABASE_URL=$(aws secretsmanager get-secret-value \\\n    --secret-id prod/myapp/database \\\n    --query SecretString --output text | jq -r .url)\n\nexport DATABASE_URL\n\ncat > /etc/systemd/system/myapp.service <<EOF\n[Unit]\nDescription=MyApp FastAPI\n[Service]\nExecStart=/usr/bin/python3.11 -m uvicorn app.main:app --host 0.0.0.0 --port 8000\nRestart=always\nEOF\n\nsystemctl enable myapp && systemctl start myapp", "bash"),
                    Section("Auto Scaling Group: Escala Automática",
                        "ASG adiciona e remove instâncias baseado em métricas. Com ALB, distribui tráfego automaticamente.",
                        "resource \"aws_autoscaling_group\" \"app\" {\n  min_size            = 2\n  max_size            = 10\n  desired_capacity    = 2\n  vpc_zone_identifier = [aws_subnet.private_a.id, aws_subnet.private_b.id]\n\n  launch_template {\n    id      = aws_launch_template.app.id\n    version = \"$Latest\"\n  }\n\n  target_group_arns = [aws_lb_target_group.app.arn]\n  health_check_type = \"ELB\"\n}\n\n# Escalar quando CPU > 70%\nresource \"aws_autoscaling_policy\" \"cpu\" {\n  policy_type            = \"TargetTrackingScaling\"\n  autoscaling_group_name = aws_autoscaling_group.app.name\n  target_tracking_configuration {\n    predefined_metric_specification {\n      predefined_metric_type = \"ASGAverageCPUUtilization\"\n    }\n    target_value = 70.0\n  }\n}", "hcl"),
                ],
                exercise="Crie um ASG com Launch Template, User Data que instala e inicia uma FastAPI, e política de auto-scaling por CPU.",
                takeaway="User Data + Instance Profile = EC2 que se configura sozinha sem SSH. ASG + ALB = escala automática sem downtime."
            ),
        ]),
        Module("aws-m2", "Storage, Banco de Dados e Serverless", "Os serviços mais usados em aplicações reais.", [
            Lesson("aws-m2-l1", "S3: Object Storage para Tudo", 15,
                "S3 é o serviço mais versátil da AWS. Aprenda além do básico: lifecycle, replication e presigned URLs.",
                [
                    Section("S3 Lifecycle e Storage Classes",
                        "S3 Standard: acesso frequente. IA: 40% mais barato. Glacier: centavos/GB. Lifecycle automatiza a transição.",
                        "import boto3\n\ns3 = boto3.client('s3')\n\ns3.put_bucket_lifecycle_configuration(\n    Bucket='meu-datalake',\n    LifecycleConfiguration={\n        'Rules': [{\n            'ID': 'mover-dados-antigos',\n            'Status': 'Enabled',\n            'Filter': {'Prefix': 'raw/'},\n            'Transitions': [\n                {'Days': 30,  'StorageClass': 'STANDARD_IA'},\n                {'Days': 90,  'StorageClass': 'GLACIER'},\n                {'Days': 365, 'StorageClass': 'DEEP_ARCHIVE'},\n            ],\n        }]\n    }\n)\n\n# Presigned URL: acesso temporário sem expor credenciais\ndef gerar_url_download(bucket: str, key: str, expira_em: int = 3600) -> str:\n    return s3.generate_presigned_url(\n        'get_object',\n        Params={'Bucket': bucket, 'Key': key},\n        ExpiresIn=expira_em\n    )", "python"),
                    Section("S3 Event Notifications: Reagir a Uploads",
                        "S3 aciona Lambda quando um objeto é criado. Base de pipelines event-driven.",
                        "resource \"aws_s3_bucket_notification\" \"pipeline\" {\n  bucket = aws_s3_bucket.datalake.id\n\n  lambda_function {\n    lambda_function_arn = aws_lambda_function.processar.arn\n    events              = [\"s3:ObjectCreated:*\"]\n    filter_prefix       = \"raw/vendas/\"\n    filter_suffix       = \".parquet\"\n  }\n}\n\ndef lambda_handler(event, context):\n    for record in event['Records']:\n        bucket = record['s3']['bucket']['name']\n        key    = record['s3']['object']['key']\n        processar_arquivo(bucket, key)", "python"),
                    Section("S3 + CloudFront: CDN Global",
                        "S3 + CloudFront = CDN global para sites estáticos. Next.js export, SPAs e assets em < 20ms mundialmente.",
                        "resource \"aws_cloudfront_distribution\" \"cdn\" {\n  origin {\n    domain_name = aws_s3_bucket.site.bucket_regional_domain_name\n    origin_id   = \"S3Origin\"\n    s3_origin_config {\n      origin_access_identity = aws_cloudfront_origin_access_identity.oai.cloudfront_access_identity_path\n    }\n  }\n\n  default_cache_behavior {\n    allowed_methods        = [\"GET\", \"HEAD\"]\n    cached_methods         = [\"GET\", \"HEAD\"]\n    target_origin_id       = \"S3Origin\"\n    viewer_protocol_policy = \"redirect-to-https\"\n    compress               = true\n    forwarded_values {\n      query_string = false\n      cookies { forward = \"none\" }\n    }\n  }\n\n  enabled = true\n}", "hcl"),
                ],
                exercise="Configure lifecycle no S3 para mover logs para Glacier após 90 dias. Gere presigned URLs para download de relatórios.",
                takeaway="S3 Lifecycle economiza 80% em storage de dados antigos automaticamente. Presigned URLs são a forma segura de dar acesso temporário."
            ),
            Lesson("aws-m2-l2", "RDS e DynamoDB: Banco de Dados Gerenciado", 18,
                "RDS elimina a operação do banco. DynamoDB resolve escala que SQL não resolve. Aprenda quando usar cada um.",
                [
                    Section("RDS PostgreSQL: Multi-AZ e Read Replicas",
                        "Multi-AZ: failover automático em < 60s. Read Replicas: escalar leitura horizontalmente.",
                        "resource \"aws_db_instance\" \"postgres\" {\n  engine          = \"postgres\"\n  engine_version  = \"16.1\"\n  instance_class  = \"db.t3.medium\"\n  allocated_storage = 100\n  storage_encrypted = true\n\n  multi_az               = true\n  deletion_protection    = true\n  backup_retention_period = 7\n\n  db_subnet_group_name   = aws_db_subnet_group.main.name\n  vpc_security_group_ids = [aws_security_group.db.id]\n\n  performance_insights_enabled = true\n}\n\nresource \"aws_db_instance\" \"replica\" {\n  replicate_source_db = aws_db_instance.postgres.id\n  instance_class      = \"db.t3.large\"\n}", "hcl"),
                    Section("DynamoDB: Quando SQL não Escala",
                        "DynamoDB é serverless, escala para milhões de writes/s. Use para: session store, leaderboards, IoT, carrinhos.",
                        "import boto3\nfrom boto3.dynamodb.conditions import Key\nimport time\n\ndynamodb = boto3.resource('dynamodb')\ntabela = dynamodb.Table('sessoes')\n\ndef salvar_sessao(user_id: str, dados: dict, ttl_s: int = 86400):\n    tabela.put_item(Item={\n        'pk': f'USER#{user_id}',\n        'sk': 'SESSION',\n        'dados': dados,\n        'ttl': int(time.time()) + ttl_s,  # DynamoDB deleta automaticamente\n    })\n\n# Padrão Single-Table Design:\n# pk=USER#123, sk=PROFILE    → perfil\n# pk=USER#123, sk=ORDER#456  → pedido do usuário\n# pk=ORDER#456, sk=ITEM#789  → item do pedido", "python"),
                    Section("ElastiCache Redis: Cache Gerenciado",
                        "ElastiCache Redis elimina operação do Redis. Use para cache de sessão, rate limiting e Pub/Sub.",
                        "import redis, json\n\nr = redis.Redis(\n    host='meu-cluster.abc123.cache.amazonaws.com',\n    port=6379,\n    decode_responses=True,\n)\n\ndef cachear(key: str, valor: dict, ttl: int = 300):\n    r.setex(key, ttl, json.dumps(valor))\n\ndef buscar_cache(key: str) -> dict | None:\n    cached = r.get(key)\n    return json.loads(cached) if cached else None\n\n# Rate limiting\ndef verificar_rate_limit(user_id: str, limite: int = 100) -> bool:\n    key = f'ratelimit:{user_id}'\n    pipe = r.pipeline()\n    pipe.incr(key)\n    pipe.expire(key, 60)\n    return pipe.execute()[0] <= limite", "python"),
                ],
                exercise="Configure RDS PostgreSQL Multi-AZ com Terraform. Implemente cache com ElastiCache Redis para os endpoints mais lentos da API.",
                takeaway="RDS Multi-AZ para HA, Read Replica para escalar leitura. DynamoDB quando precisa de escala serverless. ElastiCache quando o banco virou gargalo."
            ),
            Lesson("aws-m2-l3", "Lambda e API Gateway: Arquitetura Serverless", 20,
                "Serverless elimina gestão de servidores. Lambda escala de zero para milhões sem configuração.",
                [
                    Section("Lambda: Funções como Serviço",
                        "Lambda executa código em resposta a eventos. Pago por 100ms de execução. Escala automática.",
                        "import json, boto3, os\n\ndef lambda_handler(event, context):\n    s3 = boto3.client('s3')\n\n    for record in event['Records']:\n        body = json.loads(record['body'])\n        arquivo = body['arquivo']\n\n        try:\n            obj = s3.get_object(Bucket=os.environ['BUCKET'], Key=arquivo)\n            dados = json.loads(obj['Body'].read())\n            resultado = processar(dados)\n            s3.put_object(\n                Bucket=os.environ['BUCKET'],\n                Key=f'processado/{arquivo}',\n                Body=json.dumps(resultado)\n            )\n        except Exception as e:\n            print(f'Erro em {arquivo}: {e}')\n            raise  # SQS re-entrega a mensagem\n\n    return {'statusCode': 200}", "python"),
                    Section("API Gateway + Lambda: FastAPI Serverless",
                        "API Gateway roteia requests HTTP para Lambda. Pago por request — zero custo quando sem tráfego.",
                        "# serverless.yml\nservice: minha-api\nprovider:\n  name: aws\n  runtime: python3.12\n  region: us-east-1\n\nfunctions:\n  api:\n    handler: app.handler\n    events:\n      - httpApi:\n          path: /{proxy+}\n          method: ANY\n    timeout: 30\n    memorySize: 512\n\n# app.py: FastAPI + Mangum (adapter para Lambda)\nfrom fastapi import FastAPI\nfrom mangum import Mangum\n\napp = FastAPI()\n\n@app.get('/saude')\ndef saude():\n    return {'status': 'ok'}\n\nhandler = Mangum(app)", "yaml"),
                    Section("SQS + Lambda: Processamento Assíncrono com DLQ",
                        "SQS desacopla produtor do consumidor. DLQ captura falhas após N tentativas.",
                        "resource \"aws_sqs_queue\" \"tarefas\" {\n  name                       = \"tarefas-pipeline\"\n  visibility_timeout_seconds = 300\n  redrive_policy = jsonencode({\n    deadLetterTargetArn = aws_sqs_queue.dlq.arn\n    maxReceiveCount     = 3\n  })\n}\n\nresource \"aws_sqs_queue\" \"dlq\" {\n  name                      = \"tarefas-pipeline-dlq\"\n  message_retention_seconds = 1209600  # 14 dias\n}\n\nresource \"aws_lambda_event_source_mapping\" \"sqs\" {\n  event_source_arn               = aws_sqs_queue.tarefas.arn\n  function_name                  = aws_lambda_function.processar.arn\n  batch_size                     = 10\n  bisect_batch_on_function_error = true\n}", "hcl"),
                ],
                exercise="Construa uma API serverless: API Gateway → Lambda (FastAPI + Mangum) → SQS para tarefas assíncronas → DLQ para falhas.",
                takeaway="Lambda + SQS é o padrão mais custo-eficiente para workloads variáveis. DLQ é obrigatória — sem ela mensagens com erro somem silenciosamente."
            ),
        ]),
        Module("aws-m3", "IaC com Terraform e Monitoramento", "Infraestrutura como código e observabilidade na AWS.", [
            Lesson("aws-m3-l1", "Terraform na AWS: Infraestrutura como Código", 22,
                "Terraform é o padrão de fato para IaC na AWS. Toda infraestrutura em código versionado, revisável e repetível.",
                [
                    Section("Estrutura de Projeto Terraform Profissional",
                        "Módulos reutilizáveis, estados remotos no S3 e lock com DynamoDB para trabalho em time.",
                        "# environments/prod/main.tf\nterraform {\n  backend \"s3\" {\n    bucket         = \"meu-terraform-state\"\n    key            = \"prod/terraform.tfstate\"\n    region         = \"us-east-1\"\n    dynamodb_table = \"terraform-locks\"  # evita conflito em time\n    encrypt        = true\n  }\n  required_providers {\n    aws = { source = \"hashicorp/aws\", version = \"~> 5.0\" }\n  }\n}\n\nmodule \"vpc\" {\n  source = \"../../modules/vpc\"\n  cidr   = \"10.0.0.0/16\"\n  name   = \"prod-vpc\"\n}", "hcl"),
                    Section("Secrets: Nunca no tfstate",
                        "tfstate salva o estado dos recursos — incluindo senhas se passadas diretamente. Use Secrets Manager.",
                        "# RUIM: senha salva em texto no tfstate!\nresource \"aws_db_instance\" \"db\" {\n  password = \"minha-senha-123\"\n}\n\n# BOM: gerada pelo Terraform, salva no Secrets Manager\nresource \"random_password\" \"db\" { length = 32 }\n\nresource \"aws_secretsmanager_secret_version\" \"db\" {\n  secret_id     = aws_secretsmanager_secret.db.id\n  secret_string = jsonencode({ password = random_password.db.result })\n}\n\nresource \"aws_db_instance\" \"db\" {\n  password = random_password.db.result\n}\n\n# Na aplicação: buscar dinamicamente\nimport boto3, json\n\ndef get_db_password() -> str:\n    sm = boto3.client('secretsmanager')\n    secret = sm.get_secret_value(SecretId='prod/app/db-password')\n    return json.loads(secret['SecretString'])['password']", "python"),
                    Section("CI/CD para Terraform: GitHub Actions",
                        "Plan no PR para revisão, apply no merge para main. Ninguém faz terraform apply manual em produção.",
                        "# .github/workflows/terraform.yml\non:\n  pull_request:\n    paths: ['infrastructure/**']\n  push:\n    branches: [main]\n\njobs:\n  plan:\n    if: github.event_name == 'pull_request'\n    steps:\n      - uses: aws-actions/configure-aws-credentials@v4\n        with:\n          role-to-assume: arn:aws:iam::123:role/GitHubActionsRole\n          aws-region: us-east-1\n      - run: terraform init && terraform plan -out=tfplan\n\n  apply:\n    if: github.ref == 'refs/heads/main'\n    environment: production  # requer aprovação manual\n    steps:\n      - run: terraform apply -auto-approve", "yaml"),
                ],
                exercise="Crie um módulo Terraform reutilizável para VPC. Use remote state no S3. Configure CI/CD com plan no PR e apply no merge.",
                takeaway="Estado remoto + DynamoDB lock são obrigatórios em time. Apply manual em produção é erro de processo — use CI/CD com aprovação."
            ),
            Lesson("aws-m3-l2", "CloudWatch: Logs, Métricas e Alarmes", 18,
                "CloudWatch é a observabilidade nativa da AWS. Configure antes de ir para produção, não depois do incidente.",
                [
                    Section("Logs Estruturados no CloudWatch",
                        "Aplicações devem logar JSON estruturado. CloudWatch Logs Insights permite queries SQL-like nos logs.",
                        "import json\nfrom datetime import datetime\n\nclass JSONLogger:\n    def __init__(self, service: str):\n        self.service = service\n\n    def log(self, level: str, message: str, **ctx):\n        print(json.dumps({\n            'timestamp': datetime.utcnow().isoformat(),\n            'level': level,\n            'service': self.service,\n            'message': message,\n            **ctx\n        }))\n\n    def info(self, msg, **ctx):  self.log('INFO', msg, **ctx)\n    def error(self, msg, **ctx): self.log('ERROR', msg, **ctx)\n\nlogger = JSONLogger('api-pedidos')\nlogger.info('pedido_processado', pedido_id=123, tempo_ms=150)\n\n# CloudWatch Logs Insights:\n# fields @timestamp, pedido_id, tempo_ms\n# | filter level = 'ERROR'\n# | stats avg(tempo_ms) by bin(5m)", "python"),
                    Section("Métricas Customizadas e Alarmes",
                        "Métricas de negócio (pedidos/min, taxa de conversão) são tão importantes quanto CPU/RAM.",
                        "import boto3\n\ncw = boto3.client('cloudwatch')\n\ndef registrar_metrica(nome: str, valor: float):\n    cw.put_metric_data(\n        Namespace='MeuApp/Negocio',\n        MetricData=[{'MetricName': nome, 'Value': valor, 'Unit': 'Count'}]\n    )\n\n# Alarme: notificar se pedidos caírem abaixo de 10/5min\ncw.put_metric_alarm(\n    AlarmName='PedidosCaindo',\n    MetricName='PedidosCriados',\n    Namespace='MeuApp/Negocio',\n    Statistic='Sum',\n    Period=300,\n    EvaluationPeriods=2,\n    Threshold=10,\n    ComparisonOperator='LessThanThreshold',\n    AlarmActions=['arn:aws:sns:us-east-1:123:alertas-producao'],\n    TreatMissingData='breaching'\n)", "python"),
                    Section("X-Ray: Tracing Distribuído",
                        "X-Ray rastreia requests através de Lambda, API Gateway e RDS automaticamente com zero código.",
                        "from aws_xray_sdk.core import xray_recorder, patch_all\n\npatch_all()  # instrumenta boto3, requests, sqlalchemy automaticamente\n\n@xray_recorder.capture('processar_pedido')\ndef processar_pedido(pedido_id: int):\n    with xray_recorder.in_subsegment('buscar_banco'):\n        pedido = db.get(pedido_id)\n\n    with xray_recorder.in_subsegment('chamar_pagamento'):\n        resultado = requests.post('https://api.pagamento.com/cobrar')\n\n    return resultado\n\n# X-Ray Service Map:\n# Cliente → API Gateway → Lambda → RDS\n# Latência e taxa de erro em cada hop", "python"),
                ],
                exercise="Configure logs JSON, métricas de negócio customizadas e alarme no SNS para quando erros ultrapassarem 1% das requests.",
                takeaway="Logs sem estrutura não são consultáveis. Métricas de negócio revelam o impacto real do problema — CPU alto não significa nada sem contexto."
            ),
            Lesson("aws-m3-l3", "Deploy Containerizado: ECR + ECS Fargate", 22,
                "Pipeline completo: GitHub Actions → ECR → ECS Fargate. Aplicação em produção sem gerenciar servidores.",
                [
                    Section("ECR: Registry Privado de Imagens",
                        "ECR é o Docker Hub privado da AWS. Integra nativamente com ECS e EKS.",
                        "# GitHub Actions: build e push para ECR\n- name: Login no ECR\n  uses: aws-actions/amazon-ecr-login@v2\n\n- name: Build e push\n  env:\n    ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}\n    IMAGE_TAG: ${{ github.sha }}\n  run: |\n    docker build -t $ECR_REGISTRY/minha-api:$IMAGE_TAG .\n    docker push $ECR_REGISTRY/minha-api:$IMAGE_TAG\n\n# Lifecycle: manter apenas 10 imagens mais recentes\nresource \"aws_ecr_lifecycle_policy\" \"api\" {\n  repository = aws_ecr_repository.api.name\n  policy = jsonencode({\n    rules = [{\n      rulePriority = 1\n      action = { type = \"expire\" }\n      selection = { tagStatus = \"any\", countType = \"imageCountMoreThan\", countNumber = 10 }\n    }]\n  })\n}", "yaml"),
                    Section("ECS Fargate: Containers sem EC2",
                        "Fargate executa containers sem você gerenciar instâncias. Pago pelo vCPU/memória usados.",
                        "resource \"aws_ecs_task_definition\" \"api\" {\n  family                   = \"minha-api\"\n  requires_compatibilities = [\"FARGATE\"]\n  network_mode             = \"awsvpc\"\n  cpu                      = 512\n  memory                   = 1024\n\n  container_definitions = jsonencode([{\n    name  = \"api\"\n    image = \"${aws_ecr_repository.api.repository_url}:latest\"\n    portMappings = [{ containerPort = 8000 }]\n    secrets = [{\n      name      = \"DATABASE_URL\"\n      valueFrom = aws_secretsmanager_secret.db.arn\n    }]\n    logConfiguration = {\n      logDriver = \"awslogs\"\n      options = {\n        awslogs-group  = \"/ecs/minha-api\"\n        awslogs-region = \"us-east-1\"\n      }\n    }\n  }])\n}\n\nresource \"aws_ecs_service\" \"api\" {\n  task_definition = aws_ecs_task_definition.api.arn\n  desired_count   = 2\n  launch_type     = \"FARGATE\"\n\n  load_balancer {\n    target_group_arn = aws_lb_target_group.app.arn\n    container_name   = \"api\"\n    container_port   = 8000\n  }\n}", "hcl"),
                    Section("Blue/Green Deploy com CodeDeploy",
                        "Nova versão sobe em paralelo, tráfego migra gradualmente. Rollback automático em segundos se algo falhar.",
                        "resource \"aws_codedeploy_deployment_group\" \"api\" {\n  deployment_config_name = \"CodeDeployDefault.ECSLinear10PercentEvery1Minutes\"\n  # 10% do tráfego por minuto → migração em 10 minutos\n\n  ecs_service {\n    cluster_name = aws_ecs_cluster.main.name\n    service_name = aws_ecs_service.api.name\n  }\n\n  load_balancer_info {\n    target_group_pair_info {\n      prod_traffic_route { listener_arns = [aws_lb_listener.https.arn] }\n      target_group { name = aws_lb_target_group.blue.name }\n      target_group { name = aws_lb_target_group.green.name }\n    }\n  }\n\n  auto_rollback_configuration {\n    enabled = true\n    events  = [\"DEPLOYMENT_FAILURE\"]\n  }\n}", "hcl"),
                ],
                exercise="Configure pipeline completo: GitHub Actions → ECR → ECS Fargate com blue/green deploy e rollback automático em falha.",
                takeaway="ECS Fargate + ALB + Blue/Green = deploy com zero downtime e rollback em segundos. Nunca faça deploy manual em produção."
            ),
        ]),
        Module("aws-m4", "Well-Architected, Segurança e DR", "Checklist profissional antes de ir para produção.", [
            Lesson("aws-m4-l1", "Well-Architected Framework", 15,
                "6 pilares para sistemas de qualidade. Use como checklist antes de lançar em produção.",
                [
                    Section("Os 6 Pilares na Prática",
                        "Operational Excellence, Security, Reliability, Performance, Cost Optimization, Sustainability.",
                        "# SECURITY (mais crítico)\n# - IAM least privilege\n# - Secrets no Secrets Manager\n# - VPC com subnets privadas para banco/app\n# - Encryption at rest e in transit\n# - GuardDuty habilitado\n# - CloudTrail para auditoria\n\n# RELIABILITY\n# - Multi-AZ para RDS e EC2\n# - Auto Scaling Groups\n# - Health checks e circuit breakers\n# - Backup automatizado com testes de restore\n\n# COST OPTIMIZATION\n# - Reserved Instances para cargas previsíveis\n# - Spot para batch jobs (economia de 90%)\n# - S3 Lifecycle para dados antigos\n# - Budget alerts no AWS Budgets", "bash"),
                    Section("AWS Cost Explorer e Budget Alerts",
                        "Surpresa na fatura AWS é evitável. Configure alertas antes de atingir o limite.",
                        "import boto3\n\nbudgets = boto3.client('budgets')\n\n# Alerta quando custo > 80% do limite mensal\nbudgets.create_budget(\n    AccountId='123456789012',\n    Budget={\n        'BudgetName': 'Limite-Mensal-Producao',\n        'BudgetLimit': {'Amount': '500', 'Unit': 'USD'},\n        'BudgetType': 'COST',\n        'TimeUnit': 'MONTHLY',\n    },\n    NotificationsWithSubscribers=[{\n        'Notification': {\n            'NotificationType': 'ACTUAL',\n            'ComparisonOperator': 'GREATER_THAN',\n            'Threshold': 80,\n        },\n        'Subscribers': [{'SubscriptionType': 'EMAIL', 'Address': 'eng@empresa.com'}]\n    }]\n)", "python"),
                    Section("Graviton e Serverless: Sustentabilidade e Custo",
                        "Graviton (ARM) é 40% mais eficiente que x86. Serverless escala a zero. Sustentabilidade e custo andam juntos.",
                        "# Mudar para Graviton: só trocar o instance_type\nresource \"aws_db_instance\" \"postgres\" {\n  instance_class = \"db.t4g.medium\"  # 't4g' = Graviton, 35% mais barato\n}\n\nresource \"aws_ecs_task_definition\" \"api\" {\n  runtime_platform {\n    cpu_architecture        = \"ARM64\"  # Graviton Fargate\n    operating_system_family = \"LINUX\"\n  }\n}\n\n# Right-sizing: identificar instâncias superprovisionadas\naws ce get-rightsizing-recommendation \\\n    --service \"AmazonEC2\" \\\n    --configuration '{ \"RecommendationTarget\": \"SAME_INSTANCE_FAMILY\" }'", "hcl"),
                ],
                exercise="Rode o Well-Architected Tool na conta AWS. Identifique os 3 riscos mais críticos e implemente as correções.",
                takeaway="Well-Architected é um checklist de coisas que vão dar problema em produção. Use antes de lançar, não depois do incidente."
            ),
            Lesson("aws-m4-l2", "Segurança: GuardDuty, WAF e Config", 18,
                "Segurança na AWS é compartilhada. AWS cuida da infraestrutura, você cuida do que coloca nela.",
                [
                    Section("GuardDuty: Detecção de Ameaças com ML",
                        "GuardDuty analisa CloudTrail, VPC Flow Logs e DNS automaticamente. Detecta comportamentos suspeitos.",
                        "resource \"aws_guardduty_detector\" \"main\" {\n  enable = true\n  datasources {\n    s3_logs { enable = true }\n    malware_protection {\n      scan_ec2_instance_with_findings {\n        ebs_volumes { enable = true }\n      }\n    }\n  }\n}\n\n# Reagir automaticamente a achados críticos:\nresource \"aws_cloudwatch_event_rule\" \"guardduty_high\" {\n  event_pattern = jsonencode({\n    source      = [\"aws.guardduty\"]\n    detail-type = [\"GuardDuty Finding\"]\n    detail      = { severity = [{ numeric = [\">=\", 7] }] }\n  })\n}\n# EventBridge → Lambda → bloquear IP no WAF / revogar credenciais", "hcl"),
                    Section("WAF: Proteger APIs de Ataques",
                        "WAF filtra requests maliciosos antes de chegarem na aplicação. SQLi, XSS, bots e rate limit por IP.",
                        "resource \"aws_wafv2_web_acl\" \"api\" {\n  name  = \"api-protecao\"\n  scope = \"REGIONAL\"\n  default_action { allow {} }\n\n  rule {\n    name     = \"AWSManagedRulesCommonRuleSet\"\n    priority = 1\n    override_action { none {} }\n    statement {\n      managed_rule_group_statement {\n        vendor_name = \"AWS\"\n        name        = \"AWSManagedRulesCommonRuleSet\"\n      }\n    }\n    visibility_config {\n      sampled_requests_enabled = true\n      cloudwatch_metrics_enabled = true\n      metric_name = \"CommonRuleSet\"\n    }\n  }\n\n  rule {\n    name     = \"RateLimit\"\n    priority = 10\n    action { block {} }\n    statement {\n      rate_based_statement {\n        limit              = 2000\n        aggregate_key_type = \"IP\"\n      }\n    }\n  }\n}", "hcl"),
                    Section("AWS Config: Conformidade Contínua",
                        "Config monitora mudanças e verifica conformidade. Detecta drift de IaC e recursos fora das regras.",
                        "resource \"aws_config_config_rule\" \"s3_sem_acesso_publico\" {\n  name = \"s3-bucket-public-read-prohibited\"\n  source {\n    owner             = \"AWS\"\n    source_identifier = \"S3_BUCKET_PUBLIC_READ_PROHIBITED\"\n  }\n}\n\nresource \"aws_config_config_rule\" \"rds_encrypted\" {\n  name = \"rds-storage-encrypted\"\n  source {\n    owner             = \"AWS\"\n    source_identifier = \"RDS_STORAGE_ENCRYPTED\"\n  }\n}\n\n# Auto-remediation: bloquear S3 público automaticamente\nresource \"aws_config_remediation_configuration\" \"s3\" {\n  config_rule_name = aws_config_config_rule.s3_sem_acesso_publico.name\n  target_type      = \"SSM_DOCUMENT\"\n  target_id        = \"AWS-DisableS3BucketPublicReadWrite\"\n  automatic        = true\n}", "hcl"),
                ],
                exercise="Habilite GuardDuty e configure resposta automática para achados de alta severidade via EventBridge → Lambda → SNS.",
                takeaway="GuardDuty detecta, WAF bloqueia, Config audita. Os três juntos cobrem detecção, prevenção e conformidade — o mínimo para produção."
            ),
            Lesson("aws-m4-l3", "Disaster Recovery: RTO, RPO e Failover", 18,
                "DR não é opcional — é quanto tempo você aceita ficar fora do ar e quanto dado aceita perder.",
                [
                    Section("Estratégias DR por Custo vs RTO",
                        "Backup & Restore: RTO horas, custo baixo. Pilot Light: RTO 30min. Warm Standby: RTO 5min. Multi-Site: RTO zero.",
                        "# Estratégias por criticidade:\n\n# Backup & Restore (RPO: horas, RTO: 1-8h)\n# - Backups S3, restaurar em nova região\n# - Use para: apps não-críticas\n\n# Pilot Light (RPO: minutos, RTO: 15-60min)\n# - Banco em réplica na região DR\n# - Compute desligado (AMI/Terraform prontos)\n# - Ligar e escalar em desastre\n\n# Warm Standby (RPO: segundos, RTO: 1-15min)\n# - Versão reduzida rodando na DR\n# - Escalar automaticamente se primary cair\n# - Use para: e-commerce, SaaS\n\n# Multi-Site Active/Active (RPO: 0, RTO: 0)\n# - Duas regiões ativas com Route 53 failover\n# - Aurora Global Database (< 1s replication lag)\n# - Use para: fintech, healthcare crítico", "bash"),
                    Section("Route 53 Failover Automático",
                        "Route 53 detecta falhas via health check e redireciona para região DR sem intervenção manual.",
                        "resource \"aws_route53_health_check\" \"primary\" {\n  fqdn              = \"api.meusite.com\"\n  port              = 443\n  type              = \"HTTPS\"\n  resource_path     = \"/saude\"\n  failure_threshold = 3\n  request_interval  = 10\n}\n\nresource \"aws_route53_record\" \"primary\" {\n  name = \"api.meusite.com\"\n  type = \"A\"\n  failover_routing_policy { type = \"PRIMARY\" }\n  health_check_id = aws_route53_health_check.primary.id\n  set_identifier  = \"primary\"\n  alias {\n    name    = aws_lb.primary.dns_name\n    zone_id = aws_lb.primary.zone_id\n    evaluate_target_health = true\n  }\n}\n\nresource \"aws_route53_record\" \"secondary\" {\n  name = \"api.meusite.com\"\n  type = \"A\"\n  failover_routing_policy { type = \"SECONDARY\" }  # ativa quando primary falha\n  set_identifier = \"secondary\"\n  alias {\n    name    = aws_lb.dr_region.dns_name\n    zone_id = aws_lb.dr_region.zone_id\n    evaluate_target_health = true\n  }\n}", "hcl"),
                    Section("Aurora Global Database: Replicação Multi-Região",
                        "Aurora Global Database replica com lag < 1 segundo. Promoção da réplica para primary em < 1 minuto.",
                        "resource \"aws_rds_global_cluster\" \"main\" {\n  global_cluster_identifier = \"minha-app-global\"\n  engine                    = \"aurora-postgresql\"\n  engine_version            = \"16.1\"\n}\n\n# Cluster primário (us-east-1)\nresource \"aws_rds_cluster\" \"primary\" {\n  cluster_identifier        = \"app-primary\"\n  engine                    = \"aurora-postgresql\"\n  global_cluster_identifier = aws_rds_global_cluster.main.id\n}\n\n# Cluster secundário (sa-east-1 — São Paulo)\nresource \"aws_rds_cluster\" \"secondary\" {\n  provider                  = aws.sa_east_1\n  cluster_identifier        = \"app-secondary\"\n  engine                    = \"aurora-postgresql\"\n  global_cluster_identifier = aws_rds_global_cluster.main.id\n}\n\n# Promover secondary em DR:\n# aws rds failover-global-cluster \\\n#   --global-cluster-identifier minha-app-global \\\n#   --target-db-cluster-identifier arn:...:app-secondary", "hcl"),
                ],
                exercise="Defina RTO e RPO para uma aplicação. Implemente Pilot Light com réplica RDS em sa-east-1 e failover Route 53 automático.",
                takeaway="DR sem teste não é DR — é esperança. Faça game day a cada 6 meses: corte a região primária e meça o RTO real."
            ),
        ]),
    ]
)


# ─────────────────────────────────────────────────────────────────────────────
# CURSO 10 — BUSINESS INTELLIGENCE
# ─────────────────────────────────────────────────────────────────────────────
BI_COURSE = Course(
    id="business-intelligence",
    title="Business Intelligence: Dados que Convencem",
    tagline="Transforme números em decisões — dashboards, KPIs e storytelling com dados",
    description="Aprenda BI do zero: modelagem dimensional, SQL analítico, Power BI/Metabase, KPIs de negócio e como apresentar dados para executivos.",
    level="Iniciante → Intermediário",
    category="Analytics",
    duration_hours=18,
    skills=["SQL", "Power BI", "Metabase", "Modelagem Dimensional", "KPIs", "Storytelling com Dados", "dbt"],
    color="#8b5cf6",
    modules=[
        Module("bi-m1", "Fundamentos de BI e Modelagem Dimensional", "O alicerce de qualquer solução de BI profissional.", [
            Lesson("bi-m1-l1", "O que é BI e por que importa", 15,
                "BI não é sobre ferramentas — é sobre responder perguntas de negócio com dados. Entenda o ciclo completo.",
                [
                    Section("O Ciclo de BI: Da Fonte ao Dashboard",
                        "Fonte → ETL → Data Warehouse → BI Tool → Decisão. Cada etapa tem sua responsabilidade. BI sem DW é relatório, não BI.",
                        "# Ciclo completo de BI:\n\n# 1. FONTES DE DADOS\n#    ERP (vendas, estoque, financeiro)\n#    CRM (clientes, oportunidades)\n#    Google Analytics (comportamento digital)\n#    Planilhas (dados manuais — inevitável)\n\n# 2. ETL/ELT (dbt + Airflow)\n#    Extrai → Transforma → Carrega no DW\n\n# 3. DATA WAREHOUSE (BigQuery, Redshift, Snowflake, DuckDB)\n#    Dados históricos, modelagem dimensional\n#    Otimizado para queries analíticas\n\n# 4. FERRAMENTA DE BI (Power BI, Metabase, Looker)\n#    Dashboards, KPIs, relatórios ad-hoc\n\n# 5. DECISÃO\n#    O único objetivo de toda a cadeia\n\n# Pergunta antes de construir qualquer dashboard:\n# 'Que decisão será tomada com base nesse dado?'\n# Se não houver resposta, não construa o dashboard.", "bash"),
                    Section("KPIs vs Métricas vs Indicadores",
                        "KPI (Key Performance Indicator) é uma métrica vinculada a um objetivo estratégico. Nem toda métrica é KPI.",
                        "# Métricas: qualquer número mensurável\n# - Número de usuários cadastrados\n# - Tempo de resposta da API\n# - Linhas de código\n\n# KPI: métrica vinculada a objetivo estratégico\n# - Taxa de conversão de trial para pago (objetivo: crescimento)\n# - NPS (objetivo: retenção)\n# - CAC / LTV ratio (objetivo: unit economics saudável)\n\n# North Star Metric: o único número que captura o valor\n# que o produto entrega ao cliente\n# - Spotify: horas de música ouvidas por usuário\n# - Airbnb: noites reservadas\n# - WhatsApp: mensagens enviadas por dia\n\n# Framework OKR para KPIs:\n# Objective: Aumentar retenção de clientes\n# Key Results:\n#   KR1: Churn mensal < 2% (hoje: 4%)\n#   KR2: NPS > 50 (hoje: 32)\n#   KR3: 70% dos usuários ativos em D30 (hoje: 45%)", "bash"),
                    Section("Tipos de Análise em BI",
                        "Descritiva: o que aconteceu. Diagnóstica: por que aconteceu. Preditiva: o que vai acontecer. Prescritiva: o que fazer.",
                        "# Descritiva: relatórios e dashboards\n-- Faturamento do mês por categoria\nSELECT\n    categoria,\n    SUM(valor)    AS faturamento,\n    COUNT(*)      AS total_pedidos,\n    AVG(valor)    AS ticket_medio\nFROM fato_vendas\nWHERE mes = DATE_TRUNC('month', CURRENT_DATE)\nGROUP BY categoria\nORDER BY faturamento DESC;\n\n-- Diagnóstica: análise de queda no faturamento\n-- Por que o faturamento caiu 20% em março?\nSELECT\n    canal,\n    MES_ANTERIOR.faturamento   AS mes_anterior,\n    MES_ATUAL.faturamento      AS mes_atual,\n    (MES_ATUAL.faturamento - MES_ANTERIOR.faturamento)\n        / MES_ANTERIOR.faturamento * 100 AS variacao_pct\nFROM ...\nWHERE variacao_pct < -10  -- canais que caíram mais de 10%\nORDER BY variacao_pct;", "sql"),
                ],
                exercise="Mapeie as fontes de dados, defina 3 KPIs e 1 North Star Metric para uma empresa de e-commerce fictícia. Justifique cada escolha.",
                takeaway="Dashboard sem KPI claro é decoração. Antes de abrir o Power BI, responda: 'Que decisão esse dado vai apoiar?'"
            ),
            Lesson("bi-m1-l2", "Modelagem Dimensional: Star Schema e Snowflake", 22,
                "Star Schema é a estrutura de dados que torna dashboards rápidos e intuitivos. É o padrão de BI há 30 anos.",
                [
                    Section("Fatos e Dimensões",
                        "Fato: tabela de eventos mensuráveis (vendas, cliques, pageviews). Dimensão: contexto do fato (quem, quando, onde, o quê).",
                        "-- Star Schema para vendas\n-- FATO: evento mensurável com métricas numéricas\nCREATE TABLE fato_vendas (\n    venda_id        BIGINT PRIMARY KEY,\n    data_id         INT REFERENCES dim_data(data_id),\n    cliente_id      INT REFERENCES dim_cliente(cliente_id),\n    produto_id      INT REFERENCES dim_produto(produto_id),\n    loja_id         INT REFERENCES dim_loja(loja_id),\n    -- Métricas (o que queremos somar/agregar)\n    quantidade      INT,\n    valor_unitario  DECIMAL(10,2),\n    desconto        DECIMAL(10,2),\n    valor_total     DECIMAL(10,2)\n);\n\n-- DIMENSÃO: contexto do fato\nCREATE TABLE dim_cliente (\n    cliente_id      INT PRIMARY KEY,\n    nome_cliente    VARCHAR(200),\n    segmento        VARCHAR(50),  -- B2B, B2C, Governo\n    cidade          VARCHAR(100),\n    estado          CHAR(2),\n    data_cadastro   DATE\n);\n\nCREATE TABLE dim_produto (\n    produto_id      INT PRIMARY KEY,\n    nome_produto    VARCHAR(200),\n    categoria       VARCHAR(100),\n    subcategoria    VARCHAR(100),\n    marca           VARCHAR(100),\n    preco_lista     DECIMAL(10,2)\n);", "sql"),
                    Section("Dim Data: A Dimensão Mais Importante",
                        "Dim Data é a dimensão mais usada em qualquer DW. Permite análises por dia, semana, mês, trimestre, ano e sazonalidade.",
                        "-- Gerar dim_data com Python\nimport pandas as pd\nfrom datetime import date\n\ndef gerar_dim_data(inicio: str, fim: str) -> pd.DataFrame:\n    datas = pd.date_range(inicio, fim, freq='D')\n    return pd.DataFrame({\n        'data_id':       datas.strftime('%Y%m%d').astype(int),\n        'data':          datas.date,\n        'ano':           datas.year,\n        'trimestre':     datas.quarter,\n        'mes':           datas.month,\n        'nome_mes':      datas.strftime('%B'),\n        'semana_ano':    datas.isocalendar().week.astype(int),\n        'dia_semana':    datas.dayofweek + 1,\n        'nome_dia':      datas.strftime('%A'),\n        'fim_de_semana': datas.dayofweek >= 5,\n        'dia_util':      ~(datas.dayofweek >= 5),\n        'trimestre_fiscal': ((datas.month - 4) % 12 // 3 + 1),  # fiscal abril\n    })\n\ndf = gerar_dim_data('2020-01-01', '2030-12-31')\ndf.to_sql('dim_data', engine, if_exists='replace', index=False)", "python"),
                    Section("Slowly Changing Dimensions (SCD)",
                        "O que acontece quando o cliente muda de cidade? SCD define como rastrear mudanças históricas nas dimensões.",
                        "-- SCD Tipo 1: sobrescrever (sem histórico)\n-- Use quando histórico não importa\nUPDATE dim_cliente\nSET cidade = 'São Paulo', estado = 'SP'\nWHERE cliente_id = 123;\n\n-- SCD Tipo 2: manter histórico com versões (mais comum)\n-- Cada mudança cria uma nova linha\nCREATE TABLE dim_cliente_scd2 (\n    cliente_sk      BIGINT PRIMARY KEY,  -- surrogate key\n    cliente_id      INT,                  -- natural key\n    nome_cliente    VARCHAR(200),\n    segmento        VARCHAR(50),\n    cidade          VARCHAR(100),\n    vigente_de      DATE,\n    vigente_ate     DATE,        -- NULL = registro atual\n    is_atual        BOOLEAN\n);\n\n-- Query: estado do cliente em uma data específica\nSELECT *\nFROM dim_cliente_scd2\nWHERE cliente_id = 123\n  AND '2023-06-15' BETWEEN vigente_de AND COALESCE(vigente_ate, '9999-12-31');\n\n-- dbt snapshot: implementa SCD2 automaticamente\n{% snapshot snapshot_clientes %}\n{{ config(unique_key='cliente_id', strategy='timestamp', updated_at='updated_at') }}\nSELECT * FROM {{ source('raw', 'clientes') }}\n{% endsnapshot %}", "sql"),
                ],
                exercise="Modele um Star Schema para um e-commerce com fato_pedidos e as dimensões dim_cliente, dim_produto, dim_data e dim_canal.",
                takeaway="Star Schema é intuitivo para o usuário de negócio: 'quero ver vendas [fato] por mês [dim_data] e por categoria [dim_produto]'. Nunca use o schema transacional diretamente no BI."
            ),
            Lesson("bi-m1-l3", "SQL Analítico: Window Functions e CTEs", 22,
                "SQL analítico é a habilidade mais valorizada em BI. Window functions transformam o que você consegue calcular em SQL.",
                [
                    Section("Window Functions: Calcular sem GROUP BY",
                        "Window functions calculam sobre um conjunto de linhas sem colapsar o resultado. Essenciais para rankings, acumulados e YoY.",
                        "-- Ranking de produtos por faturamento por categoria\nSELECT\n    categoria,\n    produto,\n    faturamento,\n    RANK() OVER (PARTITION BY categoria ORDER BY faturamento DESC) AS rank_categoria,\n    ROW_NUMBER() OVER (ORDER BY faturamento DESC)                  AS rank_geral\nFROM fato_vendas_resumo;\n\n-- Crescimento MoM (Month over Month)\nSELECT\n    mes,\n    faturamento,\n    LAG(faturamento, 1) OVER (ORDER BY mes) AS faturamento_mes_anterior,\n    faturamento - LAG(faturamento, 1) OVER (ORDER BY mes) AS variacao,\n    ROUND(\n        (faturamento - LAG(faturamento, 1) OVER (ORDER BY mes))\n        / LAG(faturamento, 1) OVER (ORDER BY mes) * 100, 1\n    ) AS variacao_pct\nFROM (\n    SELECT DATE_TRUNC('month', data_venda) AS mes,\n           SUM(valor_total) AS faturamento\n    FROM fato_vendas\n    GROUP BY 1\n) t\nORDER BY mes;", "sql"),
                    Section("Acumulados e Médias Móveis",
                        "Running total e moving average são os KPIs mais comuns em dashboards executivos.",
                        "-- Faturamento acumulado no ano (YTD)\nSELECT\n    mes,\n    faturamento_mes,\n    SUM(faturamento_mes) OVER (\n        PARTITION BY ano\n        ORDER BY mes\n        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW\n    ) AS faturamento_ytd\nFROM vendas_mensais;\n\n-- Média móvel de 3 meses (suaviza sazonalidade)\nSELECT\n    mes,\n    faturamento,\n    AVG(faturamento) OVER (\n        ORDER BY mes\n        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW\n    ) AS media_3m\nFROM vendas_mensais;\n\n-- Percentual do total por grupo\nSELECT\n    categoria,\n    faturamento,\n    ROUND(\n        faturamento * 100.0 / SUM(faturamento) OVER (),\n        1\n    ) AS pct_total,\n    ROUND(\n        faturamento * 100.0 / SUM(faturamento) OVER (PARTITION BY regiao),\n        1\n    ) AS pct_regiao\nFROM faturamento_categoria;", "sql"),
                    Section("CTEs: Queries Legíveis e Reutilizáveis",
                        "CTEs (WITH) tornam queries complexas legíveis. São a diferença entre SQL que o time entende e SQL que só você entende.",
                        "-- CTE: análise de cohort de retenção\nWITH primeira_compra AS (\n    SELECT\n        cliente_id,\n        MIN(DATE_TRUNC('month', data_venda)) AS mes_aquisicao\n    FROM fato_vendas\n    GROUP BY cliente_id\n),\n\ncompras_por_mes AS (\n    SELECT\n        v.cliente_id,\n        DATE_TRUNC('month', v.data_venda) AS mes_compra,\n        p.mes_aquisicao\n    FROM fato_vendas v\n    JOIN primeira_compra p USING (cliente_id)\n),\n\ncohort AS (\n    SELECT\n        mes_aquisicao,\n        EXTRACT(MONTH FROM AGE(mes_compra, mes_aquisicao)) AS meses_desde_aquisicao,\n        COUNT(DISTINCT cliente_id) AS clientes_retidos\n    FROM compras_por_mes\n    GROUP BY 1, 2\n)\n\nSELECT\n    mes_aquisicao,\n    meses_desde_aquisicao,\n    clientes_retidos,\n    ROUND(\n        clientes_retidos * 100.0\n        / FIRST_VALUE(clientes_retidos) OVER (PARTITION BY mes_aquisicao ORDER BY meses_desde_aquisicao),\n        1\n    ) AS taxa_retencao_pct\nFROM cohort\nORDER BY mes_aquisicao, meses_desde_aquisicao;", "sql"),
                ],
                exercise="Calcule: (1) Top 5 produtos por faturamento em cada categoria usando RANK(). (2) Crescimento YoY por mês. (3) Análise de cohort de retenção.",
                takeaway="Window functions são o superpoder do SQL analítico. LAG/LEAD para variações, SUM OVER para acumulados, RANK para rankings. Domine os 5 principais e resolva 90% dos problemas."
            ),
        ]),
        Module("bi-m2", "Ferramentas de BI: Power BI e Metabase", "Transformar dados em dashboards que pessoas usam.", [
            Lesson("bi-m2-l1", "Power BI: DAX e Modelagem", 22,
                "Power BI é a ferramenta de BI mais usada no mercado. DAX é a linguagem que separa usuários básicos de profissionais.",
                [
                    Section("Modelagem no Power BI: Relacionamentos e Schema",
                        "Power BI implementa Star Schema nativamente. Relacionamentos definem como as tabelas se conectam.",
                        "# Configuração de relacionamentos no Power BI:\n\n# 1. Carregar tabelas no Power Query\n# 2. Ir para a view 'Modelo'\n# 3. Criar relacionamentos arrastando campos\n\n# Regras de relacionamento:\n# - Cardinalidade: Many-to-One (fato → dimensão) é o padrão\n# - Direção do filtro: Single (dimensão filtra fato)\n# - Nunca Many-to-Many sem tabela de bridge\n\n# Boas práticas de modelagem:\n# - Uma tabela de data importada (não coluna calculada)\n# - Marcar dim_data como 'Tabela de datas'\n# - Esconder colunas de chave das dimensões\n# - Nomear medidas descritivamente (ex: 'Faturamento Total')\n# - Organizar medidas em tabela separada (sem dados)\n\n# Hierarquias: facilitar drill-down\n# Ano → Trimestre → Mês → Dia\n# País → Estado → Cidade\n# Categoria → Subcategoria → Produto", "bash"),
                    Section("DAX: Medidas Essenciais",
                        "DAX (Data Analysis Expressions) é a linguagem de fórmulas do Power BI. Medidas calculam em contexto de filtro.",
                        "-- Medidas DAX essenciais:\n\n-- Faturamento Total\nFaturamento Total = SUM(fato_vendas[valor_total])\n\n-- Ticket Médio\nTicket Médio = DIVIDE(\n    SUM(fato_vendas[valor_total]),\n    COUNTROWS(fato_vendas),\n    0  -- retorna 0 se divisão por zero\n)\n\n-- Faturamento mesmo período ano anterior (YoY)\nFaturamento AA =\nCALCULATE(\n    [Faturamento Total],\n    SAMEPERIODLASTYEAR(dim_data[data])\n)\n\n-- Crescimento YoY %\nCrescimento YoY % =\nVAR fat_atual = [Faturamento Total]\nVAR fat_aa    = [Faturamento AA]\nRETURN\n    IF(\n        fat_aa = 0,\n        BLANK(),\n        DIVIDE(fat_atual - fat_aa, fat_aa)\n    )\n\n-- Faturamento acumulado no ano (YTD)\nFaturamento YTD =\nTOTALYTD(\n    [Faturamento Total],\n    dim_data[data]\n)", "dax"),
                    Section("CALCULATE: A Função Mais Importante do DAX",
                        "CALCULATE modifica o contexto de filtro. É o coração de 80% das medidas avançadas em DAX.",
                        "-- CALCULATE: faturamento só de produtos Premium\nFaturamento Premium =\nCALCULATE(\n    [Faturamento Total],\n    dim_produto[segmento] = \"Premium\"\n)\n\n-- % do total ignorando filtro de categoria\nFaturamento % Total =\nDIVIDE(\n    [Faturamento Total],\n    CALCULATE(\n        [Faturamento Total],\n        ALL(dim_produto)  -- remove filtro de produto\n    )\n)\n\n-- Clientes novos (compraram pela 1a vez no período)\nClientes Novos =\nCALCULATE(\n    DISTINCTCOUNT(fato_vendas[cliente_id]),\n    FILTER(\n        fato_vendas,\n        fato_vendas[data_venda]\n            = CALCULATE(\n                MIN(fato_vendas[data_venda]),\n                ALLEXCEPT(fato_vendas, fato_vendas[cliente_id])\n            )\n    )\n)\n\n-- Regra: nunca use CALCULATE dentro de CALCULATE sem necessidade\n-- Cada CALCULATE adiciona uma camada de contexto de filtro", "dax"),
                ],
                exercise="Crie um modelo Star Schema no Power BI e implemente: Faturamento Total, Ticket Médio, Crescimento YoY % e Faturamento YTD.",
                takeaway="CALCULATE é o segredo do DAX. Entenda contexto de filtro e você consegue calcular qualquer métrica. ALL e ALLEXCEPT são os modificadores mais usados."
            ),
            Lesson("bi-m2-l2", "Metabase: BI Self-Service para o Time", 18,
                "Metabase é open-source, fácil de usar e permite que o time de negócio faça suas próprias queries. Ideal para startups e times ágeis.",
                [
                    Section("Metabase: Configuração e Conexão",
                        "Metabase conecta direto ao banco. O time de negócio faz perguntas em linguagem natural, sem SQL.",
                        "# Docker: rodar Metabase localmente\ndocker run -d \\\n  --name metabase \\\n  -p 3000:3000 \\\n  -e MB_DB_TYPE=postgres \\\n  -e MB_DB_HOST=localhost \\\n  -e MB_DB_PORT=5432 \\\n  -e MB_DB_DBNAME=metabase_db \\\n  -e MB_DB_USER=metabase \\\n  -e MB_DB_PASS=senha \\\n  metabase/metabase:latest\n\n# Acessar: http://localhost:3000\n\n# Boas práticas de configuração:\n# 1. Conectar ao DW (ou read replica), nunca ao banco de produção transacional\n# 2. Criar usuário read-only específico para o Metabase\n# 3. Configurar 'hiding' de tabelas técnicas (apenas fato_ e dim_)\n# 4. Renomear colunas para nomes amigáveis ao negócio\n# 5. Configurar permissões por grupo (Executivos, Analistas, Operacional)", "bash"),
                    Section("Perguntas e Dashboards no Metabase",
                        "Metabase tem duas formas de query: interface visual (sem SQL) e SQL editor (para analistas).",
                        "-- Pergunta SQL no Metabase: faturamento por mês\n-- Usar variáveis do Metabase para filtros dinâmicos\nSELECT\n    DATE_TRUNC('month', data_venda)  AS mes,\n    SUM(valor_total)                  AS faturamento,\n    COUNT(DISTINCT cliente_id)        AS clientes_ativos,\n    SUM(valor_total) / COUNT(*)       AS ticket_medio\nFROM fato_vendas\nWHERE 1=1\n  [[AND data_venda >= {{data_inicio}}]]\n  [[AND data_venda <= {{data_fim}}]]\n  [[AND categoria = {{categoria}}]]\nGROUP BY 1\nORDER BY 1\n\n-- [[...]] = filtro opcional (aparece como widget no dashboard)\n-- {{variavel}} = parâmetro do usuário\n\n-- Alertas automáticos:\n-- Metabase envia email quando métrica cruza threshold\n-- Ex: churn > 5% → email para o time de CS", "sql"),
                    Section("Alertas e Assinaturas de Dashboard",
                        "Dashboards que ninguém abre não têm valor. Configure envios automáticos para garantir que os dados cheguem às pessoas.",
                        "# Assinatura de Dashboard no Metabase:\n# Settings > Subscriptions > New Email Subscription\n# - Frequência: Diária, Semanal, Mensal\n# - Destinatários: grupos ou emails individuais\n# - Horário: configurável por timezone\n\n# Alertas por threshold:\n# Questions > Bell icon > Create Alert\n# - Quando: valor muda, cruza threshold, nova linha\n# - Ex: 'Me avise quando Churn Rate > 5%'\n\n# Integração com Slack:\n# Settings > Admin > Integrations > Slack\n# Cada dashboard pode ser enviado para canal específico\n# /metabase no Slack mostra dashboards disponíveis\n\n# API do Metabase: automatizar exports\nimport requests\n\nresp = requests.post('https://metabase.empresa.com/api/session',\n    json={'username': 'admin@empresa.com', 'password': 'senha'})\ntoken = resp.json()['id']\n\n# Exportar dados de uma question em CSV\nresp = requests.get(\n    'https://metabase.empresa.com/api/card/42/query/csv',\n    headers={'X-Metabase-Session': token}\n)\nwith open('relatorio.csv', 'wb') as f:\n    f.write(resp.content)", "python"),
                ],
                exercise="Configure Metabase apontando para um DW PostgreSQL local. Crie 3 perguntas com filtros dinâmicos e monte um dashboard com assinatura diária por email.",
                takeaway="Metabase democratiza o acesso a dados. O sucesso do BI é medido pelo número de decisões baseadas em dados, não pelo número de dashboards criados."
            ),
            Lesson("bi-m2-l3", "Looker Studio e Google Analytics 4", 15,
                "Looker Studio (ex-Data Studio) é gratuito e integra nativamente com todo o ecossistema Google. Ideal para marketing analytics.",
                [
                    Section("Looker Studio: Conectores e Relatórios",
                        "Looker Studio tem 800+ conectores nativos. Google Analytics, Google Ads, BigQuery, YouTube — sem escrever código.",
                        "# Conectores mais usados:\n# - Google Analytics 4 (comportamento de usuário)\n# - Google Ads (performance de campanhas)\n# - Google Search Console (SEO, impressões, cliques)\n# - BigQuery (DW corporativo)\n# - Google Sheets (dados manuais)\n# - PostgreSQL, MySQL (via Community Connectors)\n\n# Boas práticas de design no Looker Studio:\n# 1. Usar uma paleta de cores consistente (máx 5 cores)\n# 2. Gráfico de barras > pizza (comparação é mais fácil)\n# 3. Drill-down: clique em barra → detalha por sub-dimensão\n# 4. Filtros na parte superior (data sempre presente)\n# 5. Scorecard (número grande) para os 3-5 KPIs principais\n# 6. Tabela no rodapé para quem quer detalhe\n# 7. Mobile-friendly: evitar 6+ colunas de tabela", "bash"),
                    Section("Google Analytics 4: Métricas de Produto",
                        "GA4 é event-based — qualquer interação do usuário pode ser um evento. Aprenda as métricas essenciais.",
                        "# Métricas GA4 essenciais para produto:\n\n# Aquisição:\n# - Users (usuários únicos no período)\n# - New Users (primeiro contato com o site)\n# - Sessions (visitas)\n# - Channel Grouping (Organic, Paid, Direct, Email)\n\n# Engajamento:\n# - Engaged Sessions (> 10s ou 2 pageviews)\n# - Engagement Rate = Engaged / Total Sessions\n# - Avg Engagement Time (substitui Bounce Rate no GA4)\n# - Pages per Session\n\n# Conversão:\n# - Conversions (eventos marcados como conversão)\n# - Conversion Rate = Conversions / Sessions\n# - Revenue (para e-commerce)\n\n# Eventos customizados via gtag.js\n# gtag('event', 'purchase', {\n#   transaction_id: 'T_12345',\n#   value: 150.00,\n#   currency: 'BRL',\n#   items: [{item_id: 'SKU_123', item_name: 'Produto X'}]\n# })", "javascript"),
                    Section("BigQuery + Looker Studio: Analytics em Escala",
                        "GA4 exporta para BigQuery automaticamente. Com BigQuery, você faz SQL em cima dos dados brutos do Analytics.",
                        "-- Análise de funil de conversão com dados brutos do GA4 no BigQuery\n-- Tabela: analytics_XXXXXX.events_*\n\nWITH eventos AS (\n    SELECT\n        user_pseudo_id,\n        event_name,\n        event_timestamp,\n        (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS session_id\n    FROM `projeto.analytics_123.events_*`\n    WHERE _TABLE_SUFFIX BETWEEN '20240101' AND '20240131'\n),\n\nfunil AS (\n    SELECT\n        user_pseudo_id,\n        MAX(CASE WHEN event_name = 'page_view' THEN 1 END)         AS viu_pagina,\n        MAX(CASE WHEN event_name = 'add_to_cart' THEN 1 END)       AS adicionou_carrinho,\n        MAX(CASE WHEN event_name = 'begin_checkout' THEN 1 END)    AS iniciou_checkout,\n        MAX(CASE WHEN event_name = 'purchase' THEN 1 END)          AS comprou\n    FROM eventos\n    GROUP BY user_pseudo_id\n)\n\nSELECT\n    SUM(viu_pagina)          AS total_visitantes,\n    SUM(adicionou_carrinho)  AS adicionaram_carrinho,\n    SUM(iniciou_checkout)    AS iniciaram_checkout,\n    SUM(comprou)             AS compraram,\n    ROUND(SUM(comprou) * 100.0 / SUM(viu_pagina), 1) AS taxa_conversao_pct\nFROM funil;", "sql"),
                ],
                exercise="Conecte GA4 ao Looker Studio e crie um dashboard de marketing: aquisição por canal, funil de conversão e receita por semana.",
                takeaway="GA4 + BigQuery + Looker Studio é a stack de marketing analytics gratuita mais poderosa do mercado. O funil de conversão é o relatório mais valioso para qualquer produto digital."
            ),
        ]),
        Module("bi-m3", "KPIs por Área de Negócio", "Os indicadores essenciais de cada área — o que medir e por quê.", [
            Lesson("bi-m3-l1", "KPIs de Vendas e CRM", 18,
                "Vendas é a área mais orientada a dados. Aprenda os KPIs que toda empresa de vendas monitora.",
                [
                    Section("Funil de Vendas: Do Lead ao Cliente",
                        "Funil de vendas mede conversão em cada etapa. Taxa de conversão por etapa revela onde o processo quebra.",
                        "-- Análise de funil de vendas CRM\nWITH funil AS (\n    SELECT\n        DATE_TRUNC('month', data_criacao)  AS mes,\n        COUNT(*) FILTER (WHERE etapa >= 1)  AS leads,\n        COUNT(*) FILTER (WHERE etapa >= 2)  AS qualificados,\n        COUNT(*) FILTER (WHERE etapa >= 3)  AS propostas,\n        COUNT(*) FILTER (WHERE etapa >= 4)  AS negociacoes,\n        COUNT(*) FILTER (WHERE etapa = 5)   AS fechados\n    FROM oportunidades\n    GROUP BY 1\n)\n\nSELECT\n    mes,\n    leads,\n    ROUND(qualificados * 100.0 / leads, 1)       AS pct_qualificacao,\n    ROUND(propostas * 100.0 / qualificados, 1)   AS pct_proposta,\n    ROUND(negociacoes * 100.0 / propostas, 1)    AS pct_negociacao,\n    ROUND(fechados * 100.0 / leads, 1)           AS conversao_total_pct,\n    fechados\nFROM funil\nORDER BY mes;", "sql"),
                    Section("CAC, LTV e LTV/CAC Ratio",
                        "CAC: custo para adquirir um cliente. LTV: receita total gerada pelo cliente. LTV/CAC > 3 é o benchmark saudável.",
                        "-- Cálculo de CAC e LTV\nWITH aquisicao AS (\n    -- CAC = Total investido em marketing e vendas / Clientes adquiridos\n    SELECT\n        mes,\n        SUM(custo_marketing + custo_vendas) AS investimento,\n        COUNT(DISTINCT cliente_id)           AS novos_clientes,\n        SUM(custo_marketing + custo_vendas)\n            / NULLIF(COUNT(DISTINCT cliente_id), 0) AS cac\n    FROM campanhas c\n    JOIN clientes_novos n USING (mes)\n    GROUP BY mes\n),\n\nltv AS (\n    -- LTV = Ticket médio × frequência × tempo de retenção\n    SELECT\n        AVG(valor_total)                     AS ticket_medio,\n        COUNT(*) / COUNT(DISTINCT cliente_id) AS freq_compras_ano,\n        AVG(meses_ativo) / 12.0              AS anos_retencao,\n        AVG(valor_total)\n            * (COUNT(*) / COUNT(DISTINCT cliente_id))\n            * (AVG(meses_ativo) / 12.0)      AS ltv\n    FROM fato_vendas f\n    JOIN dim_cliente_scd2 d USING (cliente_id)\n)\n\nSELECT\n    a.mes, a.cac, l.ltv,\n    ROUND(l.ltv / NULLIF(a.cac, 0), 1) AS ltv_cac_ratio\n    -- > 3: saudável | > 5: excelente | < 1: insustentável\nFROM aquisicao a, ltv l;", "sql"),
                    Section("Churn e Net Revenue Retention",
                        "Churn mede quem saiu. NRR mede se os clientes que ficaram expandiram o gasto. NRR > 100% significa crescimento sem novos clientes.",
                        "-- Churn Rate mensal\nWITH ativos AS (\n    SELECT\n        DATE_TRUNC('month', data)         AS mes,\n        COUNT(DISTINCT cliente_id)         AS clientes_ativos\n    FROM assinaturas\n    WHERE status = 'ativo'\n    GROUP BY 1\n),\n\ncancelamentos AS (\n    SELECT\n        DATE_TRUNC('month', data_cancelamento) AS mes,\n        COUNT(*) AS cancelados\n    FROM assinaturas\n    WHERE status = 'cancelado'\n    GROUP BY 1\n)\n\nSELECT\n    a.mes,\n    a.clientes_ativos,\n    c.cancelados,\n    ROUND(c.cancelados * 100.0 / a.clientes_ativos, 2) AS churn_rate_pct\n    -- Benchmark SaaS saudável: < 2% mensal (< 22% anual)\nFROM ativos a\nJOIN cancelamentos c USING (mes)\nORDER BY mes;\n\n-- Net Revenue Retention (NRR)\n-- NRR = (MRR início + Expansão - Churn - Contração) / MRR início\n-- NRR > 100%: crescimento só com base atual (melhor indicador de saúde SaaS)", "sql"),
                ],
                exercise="Construa um dashboard de vendas com: funil por etapa, CAC/LTV ratio e churn rate mensal dos últimos 12 meses.",
                takeaway="LTV/CAC > 3 e Churn < 2% mensal são os dois números mais importantes de um SaaS. Se LTV/CAC < 1, o negócio perde dinheiro em cada cliente adquirido."
            ),
            Lesson("bi-m3-l2", "KPIs de Produto e Engajamento", 18,
                "Produtos digitais vivem de métricas de engajamento. Aprenda a medir o que importa para retenção e growth.",
                [
                    Section("Retenção: D1, D7, D30",
                        "Retenção mede se os usuários voltam. D1, D7, D30 são os benchmarks universais do mercado.",
                        "-- Retenção D1, D7, D30 por coorte de aquisição\nWITH primeira_sessao AS (\n    SELECT user_id, MIN(DATE(event_time)) AS data_aquisicao\n    FROM eventos\n    WHERE event_name = 'app_open'\n    GROUP BY user_id\n),\n\nretencao AS (\n    SELECT\n        p.user_id,\n        p.data_aquisicao,\n        MAX(CASE WHEN DATE(e.event_time) = p.data_aquisicao + 1  THEN 1 END) AS retido_d1,\n        MAX(CASE WHEN DATE(e.event_time) = p.data_aquisicao + 7  THEN 1 END) AS retido_d7,\n        MAX(CASE WHEN DATE(e.event_time) = p.data_aquisicao + 30 THEN 1 END) AS retido_d30\n    FROM primeira_sessao p\n    LEFT JOIN eventos e USING (user_id)\n    GROUP BY 1, 2\n)\n\nSELECT\n    data_aquisicao,\n    COUNT(*)                                  AS total_usuarios,\n    ROUND(AVG(retido_d1) * 100, 1)            AS retencao_d1_pct,\n    ROUND(AVG(retido_d7) * 100, 1)            AS retencao_d7_pct,\n    ROUND(AVG(retido_d30) * 100, 1)           AS retencao_d30_pct\n    -- Benchmarks mobile: D1>25%, D7>10%, D30>4%\n    -- Benchmarks SaaS: D1>50%, D7>30%, D30>15%\nFROM retencao\nGROUP BY 1\nORDER BY 1;", "sql"),
                    Section("DAU, MAU e Stickiness",
                        "DAU/MAU (Stickiness) mede a frequência de uso. WhatsApp: 85%. Redes sociais medianas: 20%. Apps que abrem só quando precisam: 5%.",
                        "-- DAU e MAU\nWITH dau AS (\n    SELECT\n        DATE(event_time)          AS data,\n        COUNT(DISTINCT user_id)   AS dau\n    FROM eventos\n    WHERE event_name = 'app_open'\n    GROUP BY 1\n),\n\nmau AS (\n    SELECT\n        DATE_TRUNC('month', DATE(event_time)) AS mes,\n        COUNT(DISTINCT user_id)               AS mau\n    FROM eventos\n    WHERE event_name = 'app_open'\n    GROUP BY 1\n)\n\nSELECT\n    d.data,\n    d.dau,\n    m.mau,\n    ROUND(d.dau * 100.0 / m.mau, 1) AS stickiness_pct\n    -- > 20%: bom | > 50%: excelente | WhatsApp: ~85%\nFROM dau d\nJOIN mau m ON DATE_TRUNC('month', d.data) = m.mes\nORDER BY d.data;", "sql"),
                    Section("NPS: Net Promoter Score",
                        "NPS é a métrica de satisfação mais usada no mundo. Pergunta única: 'De 0 a 10, você recomendaria nossa empresa?'",
                        "-- Cálculo de NPS\nWITH classificacao AS (\n    SELECT\n        resposta,\n        CASE\n            WHEN resposta >= 9 THEN 'promotor'\n            WHEN resposta >= 7 THEN 'neutro'\n            ELSE 'detrator'\n        END AS tipo\n    FROM pesquisa_nps\n    WHERE data_resposta >= CURRENT_DATE - 90\n)\n\nSELECT\n    COUNT(*)                                                   AS total_respostas,\n    COUNT(*) FILTER (WHERE tipo = 'promotor')                  AS promotores,\n    COUNT(*) FILTER (WHERE tipo = 'neutro')                    AS neutros,\n    COUNT(*) FILTER (WHERE tipo = 'detrator')                  AS detratores,\n    ROUND(\n        (COUNT(*) FILTER (WHERE tipo = 'promotor')\n         - COUNT(*) FILTER (WHERE tipo = 'detrator'))\n        * 100.0 / COUNT(*), 0\n    ) AS nps\n    -- NPS: > 50 excelente | > 30 bom | > 0 ok | < 0 problema\nFROM classificacao;", "sql"),
                ],
                exercise="Construa um dashboard de produto com: retenção D1/D7/D30 por coorte, DAU/MAU e NPS mensal dos últimos 6 meses.",
                takeaway="Retenção D30 é o preditor mais forte de sucesso de longo prazo. Um produto com D30 de 30% cresce mais fácil que um com D30 de 5% — mesmo com mais usuários novos."
            ),
            Lesson("bi-m3-l3", "Storytelling com Dados", 20,
                "Dados sem narrativa não convencem. Storytelling é a habilidade que transforma análises em decisões.",
                [
                    Section("A Pirâmide de Minto: Conclusão Primeiro",
                        "Executivos não leem relatórios de baixo para cima. Comece com a conclusão, depois suporte com dados.",
                        "# Estrutura ruim (analítico, de baixo para cima):\n# 1. Metodologia\n# 2. Dados coletados\n# 3. Análise realizada\n# 4. Problemas encontrados\n# 5. Conclusão: 'Portanto, o faturamento caiu por X'\n\n# Estrutura boa (Pirâmide de Minto, de cima para baixo):\n# SITUAÇÃO: 'Faturamento caiu 23% em março'\n# COMPLICAÇÃO: 'A queda concentrou-se no canal digital'\n# SOLUÇÃO: 'Recomendamos renegociar contratos de frete'\n# SUPORTE: dados que comprovam cada ponto\n\n# Template de apresentação executiva:\n# Slide 1: 1 número grande + 1 frase de insight\n#   'Faturamento março: R$ 1,2M (-23% vs fev)'\n# Slide 2: O que causou\n# Slide 3: Impacto se não agir\n# Slide 4: Recomendação e próximos passos\n# Slide 5: Backup de dados para quem quiser detalhe", "bash"),
                    Section("Design de Dashboard: O Que Funciona",
                        "Um dashboard eficaz tem no máximo 5-7 métricas, hierarquia visual clara e contexto (comparativo).",
                        "# Princípios de design de dashboard:\n\n# 1. HIERARQUIA VISUAL\n# Número grande (scorecard) no topo: KPI principal\n# Gráfico de tendência abaixo: contexto histórico\n# Tabela de detalhe embaixo: para quem quer mais\n\n# 2. SEMPRE MOSTRAR COMPARATIVO\n# Ruim: 'Faturamento: R$ 1,2M'\n# Bom:  'R$ 1,2M (-23% vs mês anterior | -5% vs meta)'\n# O número sozinho não tem significado\n\n# 3. ESCOLHA O GRÁFICO CERTO\n# Comparação no tempo → Linha\n# Comparação entre categorias → Barra horizontal\n# Parte do todo → Barra 100% empilhada (NÃO pizza)\n# Correlação → Scatter plot\n# Distribuição → Histograma ou boxplot\n# Mapa → quando geografia importa\n\n# 4. UMA COR = UMA COISA\n# Não colorir por beleza, colorir por significado\n# Verde = bom, Vermelho = ruim, Cinza = contexto\n\n# 5. REMOVER RUÍDO\n# Grid lines leves ou sem grid\n# Sem 3D\n# Rótulos só onde necessário", "bash"),
                    Section("De Análise para Recomendação",
                        "Analistas júniors descrevem dados. Analistas sêniors transformam dados em recomendações com impacto estimado.",
                        "# Análise júnior:\n# 'O faturamento do canal digital caiu 40% em março\n#  comparado a fevereiro. O ticket médio também caiu,\n#  passando de R$ 250 para R$ 180.'\n\n# Análise sênior:\n# PROBLEMA: Canal digital caiu 40% em março\n# CAUSA RAIZ: Ticket médio caiu 28% (R$250→R$180)\n#   → Clientes migrando para produtos mais baratos\n#   → Abandono de carrinho aumentou 15% em itens > R$200\n# HIPÓTESE: Custo de frete para pedidos abaixo de R$200\n#   subiu de R$15 para R$30 em fev (mudança de contrato)\n# IMPACTO ESTIMADO: Recuperação de R$280k/mês se frete\n#   gratuito acima de R$150\n# RECOMENDAÇÃO: Oferecer frete grátis > R$150 por 60 dias\n#   Custo estimado: R$45k (vs R$280k de receita recuperada)\n# PRÓXIMO PASSO: Aprovação do budget de R$45k até sexta\n\n# Regra: toda análise deve terminar com\n# 'Portanto, recomendo [ação] porque [dado].\n#  O impacto esperado é [resultado] em [prazo].'", "bash"),
                ],
                exercise="Escreva uma análise de queda de faturamento usando a Pirâmide de Minto. Inclua causa, impacto estimado e recomendação com ROI.",
                takeaway="Dados sem narrativa ficam no relatório. Narrativa sem dados é achismo. A combinação das duas é o que move organizações a agir."
            ),
        ]),
        Module("bi-m4", "Projeto Final: BI End-to-End", "Pipeline completo do dado bruto ao dashboard executivo.", [
            Lesson("bi-m4-l1", "dbt + BI: Transformações Testadas", 18,
                "dbt é o elo entre o DW e a ferramenta de BI. Modelos dbt alimentam dashboards com dados sempre frescos e testados.",
                [
                    Section("Camada Marts: Modelos Prontos para BI",
                        "A camada mart do dbt gera as tabelas que a ferramenta de BI consome. Otimizadas para consulta, sem joins complexos.",
                        "-- models/marts/fct_vendas_bi.sql\n-- Modelo desnormalizado para BI: sem joins no dashboard\n{{ config(materialized='table', sort='data_venda', dist='cliente_id') }}\n\nSELECT\n    -- Chaves\n    v.venda_id,\n    v.data_venda,\n\n    -- Dimensão tempo (já expandida — sem join no BI)\n    d.ano,\n    d.trimestre,\n    d.mes,\n    d.nome_mes,\n    d.semana_ano,\n    d.dia_util,\n\n    -- Dimensão cliente\n    c.nome_cliente,\n    c.segmento,\n    c.cidade,\n    c.estado,\n\n    -- Dimensão produto\n    p.nome_produto,\n    p.categoria,\n    p.subcategoria,\n    p.marca,\n\n    -- Dimensão canal\n    v.canal,\n\n    -- Métricas\n    v.quantidade,\n    v.valor_unitario,\n    v.desconto,\n    v.valor_total,\n    v.margem_bruta\n\nFROM {{ ref('stg_vendas') }} v\nLEFT JOIN {{ ref('dim_data') }}    d ON v.data_venda = d.data\nLEFT JOIN {{ ref('dim_clientes') }} c ON v.cliente_id = c.cliente_id\nLEFT JOIN {{ ref('dim_produtos') }} p ON v.produto_id = p.produto_id", "sql"),
                    Section("Testes dbt para Garantir Qualidade dos Dados",
                        "Nenhum dashboard deve ser publicado sem testes nos dados que o alimenta.",
                        "# models/marts/schema.yml\nversion: 2\n\nmodels:\n  - name: fct_vendas_bi\n    description: 'Fato de vendas desnormalizada para BI'\n    columns:\n      - name: venda_id\n        tests: [not_null, unique]\n      - name: data_venda\n        tests: [not_null]\n      - name: valor_total\n        tests:\n          - not_null\n          - dbt_utils.accepted_range:\n              min_value: 0.01\n              max_value: 1000000\n      - name: segmento\n        tests:\n          - accepted_values:\n              values: ['B2B', 'B2C', 'Governo']\n      - name: canal\n        tests:\n          - not_null\n          - accepted_values:\n              values: ['Digital', 'Loja Física', 'Televendas', 'Marketplace']\n\n    # Teste customizado: faturamento diário deve ser > 0\n    tests:\n      - dbt_utils.expression_is_true:\n          expression: \"valor_total > 0\"", "yaml"),
                    Section("Orquestrar dbt com Airflow para Atualização Automática",
                        "Dados frescos automaticamente: Airflow roda dbt todo dia às 6h, alimentando os dashboards antes do expediente.",
                        "from airflow.decorators import dag, task\nfrom airflow.operators.bash import BashOperator\nfrom datetime import datetime\n\n@dag(\n    schedule='0 5 * * 1-5',  # Segunda a sexta às 5h\n    start_date=datetime(2024, 1, 1),\n    tags=['bi', 'producao']\n)\ndef pipeline_bi_diario():\n\n    extrair = BashOperator(\n        task_id='extrair_fontes',\n        bash_command='python /opt/pipeline/extrair.py --data {{ ds }}'\n    )\n\n    dbt_run = BashOperator(\n        task_id='dbt_run',\n        bash_command='dbt run --profiles-dir /opt/dbt --target prod --select marts.*'\n    )\n\n    dbt_test = BashOperator(\n        task_id='dbt_test',\n        bash_command='dbt test --profiles-dir /opt/dbt --target prod --select marts.*'\n    )\n\n    notificar = BashOperator(\n        task_id='notificar_slack',\n        bash_command='python /opt/notify.py --message \"BI atualizado às {{ ts }}\"'\n    )\n\n    extrair >> dbt_run >> dbt_test >> notificar\n\npipeline_bi_diario()", "python"),
                ],
                exercise="Crie modelos dbt para a camada mart de vendas. Adicione testes de qualidade. Configure Airflow para rodar todo dia às 5h e notificar no Slack.",
                takeaway="dbt garante que os dados do dashboard são testados. Sem testes, você descobre o erro quando o CEO pergunta por que o número está errado em uma reunião."
            ),
            Lesson("bi-m4-l2", "Dashboard Executivo: Design e Entrega", 18,
                "O dashboard executivo é o produto final do BI. Aprenda a estruturar, apresentar e manter.",
                [
                    Section("Estrutura de um Dashboard Executivo",
                        "Executives querem 3 coisas: onde estamos, como chegamos aqui, e o que fazer a seguir.",
                        "# Estrutura recomendada para dashboard C-Level:\n\n# SEÇÃO 1: SAÚDE DO NEGÓCIO (acima do fold)\n# 3-5 scorecards com KPIs principais + variação\n# Faturamento | Clientes Ativos | Churn | NPS | CAC\n\n# SEÇÃO 2: TENDÊNCIA (linha do tempo)\n# Gráfico de linha: últimos 12 meses\n# Benchmarks e metas como linhas de referência\n# Anotações em eventos importantes (campanhas, mudanças)\n\n# SEÇÃO 3: DECOMPOSIÇÃO (o que contribuiu)\n# Faturamento por canal / produto / região\n# Comparativo vs período anterior\n# Top N (produtos, clientes, campanhas)\n\n# SEÇÃO 4: ALERTAS (o que precisa de ação)\n# Lista dos 5 maiores desvios vs meta\n# Clientes em risco de churn (score de risco)\n\n# REGRA: Um dashboard deve responder\n# 'Como estamos indo?' sem precisar de explicação.\n# Se precisar de legenda ou manual, redesenhe.", "bash"),
                    Section("Review Cadence: BI que Vira Rotina",
                        "BI que não é revisado regularmente não muda decisões. Construa ritmo de revisão junto com o dashboard.",
                        "# Cadência de revisão por nível:\n\n# DIÁRIO (equipe operacional)\n# - Dashboard: ops em tempo real\n# - Responsável: gerente de operações\n# - Foco: anomalias do dia, SLAs\n# - Formato: Slack digest automático às 8h\n\n# SEMANAL (gestão)\n# - Dashboard: performance da semana\n# - Responsável: heads de área\n# - Foco: progresso vs metas semanais\n# - Formato: reunião 30min toda segunda + report por email\n\n# MENSAL (diretoria)\n# - Dashboard: KPIs estratégicos\n# - Responsável: C-level\n# - Foco: tendências, OKRs, decisões de recursos\n# - Formato: deck de 5 slides + Q&A 30min\n\n# TRIMESTRAL (board/investidores)\n# - Dashboard: unit economics, crescimento, projeções\n# - Responsável: CEO + CFO\n# - Foco: saúde do negócio, guidance\n# - Formato: board deck completo", "bash"),
                    Section("Governança de Dados: Uma Fonte de Verdade",
                        "O problema mais comum em BI: cada área tem um número diferente para a mesma métrica. Governança resolve isso.",
                        "# Problemas de governança mais comuns:\n# - Vendas reporta receita bruta, Financeiro reporta líquida\n# - Marketing conta leads qualificados, Vendas conta prospects\n# - TI usa UTC, Negócio usa horário de Brasília\n\n# Solução: Data Dictionary + Metric Catalog\n\n# data_dictionary.yml — definição autoritativa\nmetricas:\n  faturamento_liquido:\n    descricao: 'Receita após descontos, impostos e devoluções'\n    formula: 'SUM(valor_total) - SUM(devolucoes) - SUM(impostos)'\n    fonte: 'fato_vendas'\n    dono: 'Financeiro'\n    atualizado_em: 'Diário às 6h'\n\n  clientes_ativos:\n    descricao: 'Clientes com ao menos 1 compra nos últimos 90 dias'\n    formula: 'COUNT(DISTINCT cliente_id WHERE dias_desde_ultima_compra <= 90)'\n    fonte: 'dim_clientes'\n    dono: 'CRM'\n    cuidado: 'Não confundir com clientes cadastrados'", "yaml"),
                ],
                exercise="Construa o dashboard executivo final com as 5 seções. Documente 3 métricas no data dictionary. Apresente para um 'executivo' (colega ou mentor).",
                takeaway="Um dashboard que o CEO usa toda semana vale mais que 100 dashboards que ninguém abre. Foque em adoção, não em quantidade."
            ),
            Lesson("bi-m4-l3", "BI Moderno: Semantic Layer e Headless BI", 15,
                "A nova fronteira do BI: semantic layer desacopla métricas de ferramentas. Uma definição, em qualquer ferramenta.",
                [
                    Section("Semantic Layer: Definir Métricas Uma Vez",
                        "Semantic layer é uma camada entre o DW e as ferramentas de BI onde você define métricas — sem repetir em cada ferramenta.",
                        "# Problema sem semantic layer:\n# Power BI: Faturamento = SUM(valor_total) WHERE status = 'aprovado'\n# Metabase: SELECT SUM(valor) FROM vendas WHERE status = 'aprovado'\n# Python: df[df.status == 'aprovado']['valor'].sum()\n# Cada ferramenta tem sua versão da mesma métrica\n# Quando a regra muda, atualizar em 5 lugares\n\n# Com semantic layer (ex: dbt Semantic Layer, Cube.dev):\n# Definir uma vez:\n# metrics:\n#   - name: faturamento\n#     type: sum\n#     sql: valor_total\n#     filter: status = 'aprovado'\n\n# Power BI, Metabase, Python consomem a mesma definição\n# Quando a regra muda: mudar em 1 lugar\n\n# Ferramentas de semantic layer:\n# dbt Semantic Layer (MetricFlow) — open source, integra com dbt\n# Cube.dev — mais features, headless BI\n# Looker (LookML) — proprietário, maduro\n# AtScale — enterprise", "bash"),
                    Section("dbt MetricFlow: Métricas como Código",
                        "MetricFlow é o semantic layer nativo do dbt. Define métricas em YAML, consulta com SQL semântico.",
                        "# models/metrics/metrics.yml\n\nsemantic_models:\n  - name: vendas\n    model: ref('fct_vendas_bi')\n    entities:\n      - name: venda\n        type: primary\n        expr: venda_id\n      - name: cliente\n        type: foreign\n        expr: cliente_id\n    dimensions:\n      - name: data_venda\n        type: time\n        type_params: { time_granularity: day }\n      - name: categoria\n        type: categorical\n    measures:\n      - name: valor_total\n        agg: sum\n        expr: valor_total\n\nmetrics:\n  - name: faturamento\n    type: simple\n    label: 'Faturamento'\n    type_params:\n      measure: valor_total\n\n  - name: crescimento_mom\n    type: derived\n    label: 'Crescimento MoM'\n    type_params:\n      expr: (faturamento - faturamento_lag(1)) / faturamento_lag(1)\n      metrics:\n        - name: faturamento\n          offset_window: 1 month", "yaml"),
                    Section("O Futuro do BI: AI-Assisted Analytics",
                        "LLMs estão mudando como pessoas interagem com dados. Natural Language → SQL → visualização automaticamente.",
                        "# Evolução do BI:\n# 2000s: Relatórios estáticos agendados\n# 2010s: Dashboards interativos self-service\n# 2020s: Análise conversacional com LLMs\n\n# Exemplo: Metabase AI (integração com LLM)\n# Usuário: 'Qual foi o produto mais vendido em março no Sul?'\n# Metabase: gera SQL → executa → mostra resultado\n\n# Exemplo com API OpenAI/Anthropic:\nfrom anthropic import Anthropic\nimport duckdb\n\nclient = Anthropic()\ncon = duckdb.connect('warehouse.duckdb')\n\ndef perguntar_dados(pergunta: str) -> str:\n    schema = con.execute(\"DESCRIBE fct_vendas_bi\").fetchdf().to_string()\n\n    resposta = client.messages.create(\n        model='claude-sonnet-4-6',\n        max_tokens=1024,\n        messages=[{\n            'role': 'user',\n            'content': f'Schema: {schema}\\n\\nPergunta: {pergunta}\\n\\nResponda com SQL válido apenas.'\n        }]\n    )\n    sql = resposta.content[0].text\n    return con.execute(sql).fetchdf()\n\nresultado = perguntar_dados('Quais os 5 clientes com maior faturamento em 2024?')", "python"),
                ],
                exercise="Implemente um bot simples de perguntas sobre dados usando a API do Claude: o usuário digita uma pergunta, o bot gera SQL, executa e retorna o resultado.",
                takeaway="Semantic layer é a evolução natural do BI — define métricas uma vez, usa em qualquer ferramenta. AI analytics vai democratizar ainda mais o acesso a dados nos próximos anos."
            ),
        ]),
    ]
)


# ─────────────────────────────────────────────────────────────────────────────
# CATALOG — adicionar todos os cursos aqui
# ─────────────────────────────────────────────────────────────────────────────
COURSES: list[Course] = [
    SQL_COURSE, PYTHON_DATA_COURSE, ML_COURSE, GIT_COURSE,
    DOCKER_COURSE, FASTAPI_COURSE, DATA_ENG_COURSE, ARCH_COURSE,
    AWS_COURSE, BI_COURSE,
]
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
