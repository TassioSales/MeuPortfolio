"""
Script para popular a tabela 'ativos' com dados de exemplo.
Execute este script após criar as migrações necessárias.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# Adiciona o diretório raiz ao path para permitir importações absolutas
sys.path.append(str(Path(__file__).parent.parent))

from src import create_app
from src.models import db
from src.models.ativo import Ativo, HistoricoPreco

def generate_sample_data():
    """Gera dados de exemplo para popular a tabela de ativos."""
    # Dados de exemplo para diferentes tipos de ativos
    sample_assets = [
        # Ações
        {
            'symbol': 'PETR4.SA',
            'name': 'Petróleo Brasileiro S.A. - Petrobras',
            'price': 32.15,
            'preco_abertura': 31.50,
            'preco_max': 32.45,
            'preco_min': 31.20,
            'preco_fechamento_anterior': 31.80,
            'variacao_24h': 0.35,
            'variacao_percentual_24h': 1.10,
            'volume_24h': 45218765,
            'valor_mercado': 412500000000,
            'max_52s': 35.20,
            'min_52s': 25.10,
            'pe_ratio': 5.2,
            'pb_ratio': 1.8,
            'dividend_yield': 12.5,
            'roe': 28.7,
            'setor': 'Energia',
            'subsetor': 'Petróleo e Gás',
            'segmento': 'Exploração, Refino e Distribuição',
            'bolsa': 'B3',
            'tipo': 'stocks',
            'source': 'brapi'
        },
        {
            'symbol': 'VALE3.SA',
            'name': 'Vale S.A.',
            'price': 72.45,
            'preco_abertura': 73.20,
            'preco_max': 73.80,
            'preco_min': 71.90,
            'preco_fechamento_anterior': 73.10,
            'variacao_24h': -0.65,
            'variacao_percentual_24h': -0.89,
            'volume_24h': 32154876,
            'valor_mercado': 385200000000,
            'max_52s': 85.30,
            'min_52s': 65.40,
            'pe_ratio': 4.8,
            'pb_ratio': 2.1,
            'dividend_yield': 15.2,
            'roe': 32.5,
            'setor': 'Materiais Básicos',
            'subsetor': 'Mineração',
            'segmento': 'Minério de Ferro',
            'bolsa': 'B3',
            'tipo': 'stocks',
            'source': 'brapi'
        },
        # Criptomoedas
        {
            'symbol': 'BTCUSDT',
            'name': 'Bitcoin',
            'price': 145000.00,
            'preco_abertura': 143500.00,
            'preco_max': 146500.00,
            'preco_min': 142000.00,
            'preco_fechamento_anterior': 142500.00,
            'variacao_24h': 2500.00,
            'variacao_percentual_24h': 1.75,
            'volume_24h': 2500000000,
            'valor_mercado': 2800000000000,
            'max_52s': 180000.00,
            'min_52s': 98000.00,
            'setor': 'Criptomoedas',
            'bolsa': 'Binance',
            'tipo': 'crypto',
            'source': 'binance'
        },
        # Fundos Imobiliários
        {
            'symbol': 'HGLG11.SA',
            'name': 'CSHG Logística FII',
            'price': 145.90,
            'preco_abertura': 145.50,
            'preco_max': 146.30,
            'preco_min': 145.20,
            'preco_fechamento_anterior': 145.00,
            'variacao_24h': 0.90,
            'variacao_percentual_24h': 0.62,
            'volume_24h': 2548765,
            'valor_mercado': 12500000000,
            'max_52s': 152.30,
            'min_52s': 125.40,
            'dividend_yield': 8.7,
            'setor': 'Fundos Imobiliários',
            'subsetor': 'Logística',
            'segmento': 'Galpões Logísticos',
            'bolsa': 'B3',
            'tipo': 'fii',
            'source': 'brapi'
        },
        # ETFs
        {
            'symbol': 'BOVA11.SA',
            'name': 'iShares Ibovespa Fundo de Índice',
            'price': 112.45,
            'preco_abertura': 112.00,
            'preco_max': 113.20,
            'preco_min': 111.80,
            'preco_fechamento_anterior': 111.70,
            'variacao_24h': 0.75,
            'variacao_percentual_24h': 0.67,
            'volume_24h': 3542187,
            'valor_mercado': 12500000000,
            'max_52s': 118.90,
            'min_52s': 95.30,
            'setor': 'ETFs',
            'subsetor': 'Índice Bovespa',
            'bolsa': 'B3',
            'tipo': 'etf',
            'source': 'brapi'
        }
    ]
    
    # Gera dados históricos para cada ativo (últimos 30 dias)
    for asset in sample_assets:
        chart_data = []
        base_price = asset['price']
        
        for i in range(30, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            # Variação de preço aleatória entre -2% e +2%
            price_change = base_price * (1 + (0.02 - 0.04 * (i % 3) / 30))
            chart_data.append({
                'date': date,
                'price': round(price_change, 2)
            })
            
        asset['historico_precos'] = json.dumps(chart_data)
    
    return sample_assets

def seed_database():
    """Popula o banco de dados com dados de exemplo."""
    # Cria a aplicação e o contexto
    app = create_app()
    app.app_context().push()
    
    try:
        # Limpa a tabela de ativos (opcional, descomente se necessário)
        # Ativo.query.delete()
        # db.session.commit()
        
        # Gera dados de exemplo
        sample_assets = generate_sample_data()
        
        # Adiciona os ativos ao banco de dados
        for asset_data in sample_assets:
            # Verifica se o ativo já existe
            existing_asset = Ativo.query.filter_by(symbol=asset_data['symbol']).first()
            
            if existing_asset:
                # Atualiza o ativo existente
                for key, value in asset_data.items():
                    if hasattr(existing_asset, key):
                        setattr(existing_asset, key, value)
                print(f"Atualizado: {asset_data['symbol']} - {asset_data['name']}")
            else:
                # Cria um novo ativo
                new_asset = Ativo(**asset_data)
                db.session.add(new_asset)
                print(f"Adicionado: {asset_data['symbol']} - {asset_data['name']}")
        
        # Salva as alterações
        db.session.commit()
        print("Banco de dados populado com sucesso!")
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao popular o banco de dados: {str(e)}")
        raise
    finally:
        db.session.close()

if __name__ == "__main__":
    seed_database()
