import duckdb
import os

db_path = r"d:\GithubGit\MeuPortfolio\analise_de_combustiveis\data-lake\warehouse\fuel_analytics.duckdb"

if not os.path.exists(db_path):
    print(f"Error: {db_path} does not exist")
    exit(1)

try:
    conn = duckdb.connect(db_path)
    print("Tables:")
    print(conn.execute("SHOW TABLES").fetchall())
    
    # Check if curated_weekly_prices exists
    tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
    if "curated_weekly_prices" in tables:
        print("\ncurated_weekly_prices sample:")
        print(conn.execute("SELECT * FROM curated_weekly_prices LIMIT 5").fetchall())
        print("\nCount:")
        print(conn.execute("SELECT count(*) FROM curated_weekly_prices").fetchall())
    else:
        print("\ncurated_weekly_prices TABLE MISSING")
        
    if "latest_overview" in tables:
        print("\nlatest_overview sample:")
        print(conn.execute("SELECT * FROM latest_overview LIMIT 5").fetchall())
    else:
        print("\nlatest_overview TABLE MISSING")
    
    conn.close()
except Exception as e:
    print(f"DuckDB Error: {e}")
