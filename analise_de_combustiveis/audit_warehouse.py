import duckdb

db_path = r"d:\GithubGit\MeuPortfolio\analise_de_combustiveis\data-lake\warehouse\fuel_analytics.duckdb"

conn = duckdb.connect(db_path)
tables = ["curated_weekly_prices", "latest_overview"]
for table in tables:
    print(f"\n--- {table} ---")
    res = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
    cols = [r[1] for r in res]
    print(f"Columns: {', '.join(cols)}")
    count = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    print(f"Row count: {count}")

conn.close()
