import duckdb
import os

db_path = r"d:\GithubGit\MeuPortfolio\analise_de_combustiveis\data-lake\warehouse\fuel_analytics.duckdb"

try:
    conn = duckdb.connect(db_path)
    for table in ["curated_weekly_prices", "latest_overview"]:
        print(f"\nSchema for {table}:")
        info = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
        for col in info:
            print(f" - {col[1]} ({col[2]})")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
