import requests
from datetime import datetime, timedelta

API_URL = "http://localhost:8000"

def populate():
    # 1. Create Assets
    assets = [
        {"ticker": "PETR4.SA", "name": "Petrobras PN", "asset_type": "STOCK"},
        {"ticker": "VALE3.SA", "name": "Vale ON", "asset_type": "STOCK"},
        {"ticker": "HGLG11.SA", "name": "CSHG Logistica", "asset_type": "FII"},
        {"ticker": "IVVB11.SA", "name": "iShares S&P 500", "asset_type": "ETF"},
        {"ticker": "BTC", "name": "Bitcoin", "asset_type": "CRYPTO"},
        {"ticker": "ETH", "name": "Ethereum", "asset_type": "CRYPTO"},
    ]
    
    asset_ids = {}
    for asset in assets:
        resp = requests.post(f"{API_URL}/assets/", json=asset)
        if resp.status_code == 200:
            data = resp.json()
            asset_ids[asset["ticker"]] = data["id"]
            print(f"Created asset {asset['ticker']} with ID {data['id']}")
        else:
            print(f"Error creating {asset['ticker']}: {resp.text}")

    # 2. Create Transactions
    # To have a realistic scenario, we'll set some older dates and average prices
    # Note: the API currently uses default datetime.utcnow for date if not provided,
    # but the schema accepts date. We will provide it.
    
    transactions = []
    
    if "PETR4.SA" in asset_ids:
        transactions.append({
            "asset_id": asset_ids["PETR4.SA"],
            "transaction_type": "BUY",
            "quantity": 100,
            "price_per_unit": 22.50, # Bought cheap
            "fees": 2.50,
            "date": (datetime.utcnow() - timedelta(days=300)).isoformat()
        })
        
    if "VALE3.SA" in asset_ids:
        transactions.append({
            "asset_id": asset_ids["VALE3.SA"],
            "transaction_type": "BUY",
            "quantity": 50,
            "price_per_unit": 85.00,
            "fees": 5.00,
            "date": (datetime.utcnow() - timedelta(days=150)).isoformat()
        })

    if "HGLG11.SA" in asset_ids:
        transactions.append({
            "asset_id": asset_ids["HGLG11.SA"],
            "transaction_type": "BUY",
            "quantity": 20,
            "price_per_unit": 160.00,
            "fees": 0.00, # FIIs often have 0 fee
            "date": (datetime.utcnow() - timedelta(days=60)).isoformat()
        })
        
    if "BTC" in asset_ids:
        transactions.append({
            "asset_id": asset_ids["BTC"],
            "transaction_type": "BUY",
            "quantity": 0.05,
            "price_per_unit": 150000.00, # BRL
            "fees": 50.00,
            "date": (datetime.utcnow() - timedelta(days=400)).isoformat()
        })
        
    if "ETH" in asset_ids:
        transactions.append({
            "asset_id": asset_ids["ETH"],
            "transaction_type": "BUY",
            "quantity": 1.5,
            "price_per_unit": 10000.00, # BRL
            "fees": 15.00,
            "date": (datetime.utcnow() - timedelta(days=200)).isoformat()
        })

    for tx in transactions:
        resp = requests.post(f"{API_URL}/transactions/", json=tx)
        if resp.status_code == 200:
            print(f"Created transaction for Asset ID {tx['asset_id']}")
        else:
            print(f"Error creating transaction: {resp.text}")

if __name__ == "__main__":
    populate()
