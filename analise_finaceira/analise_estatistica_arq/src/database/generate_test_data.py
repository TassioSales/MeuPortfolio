# generate_test_data.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

def generate_test_data():
    """Gera dados de teste para análise estatística compatíveis com processamento.py."""
    tipos_operacao = {
        'receita': ['Depósito', 'Transferência', 'Pix', 'Transferência PIX', 'Crédito'],
        'despesa': ['Pagamento', 'Lançamento', 'Compra', 'Pagamento PIX', 'Débito'],
        'investimento': {
            'Ações': ['Compra', 'Venda', 'Dividendos'],
            'ETFs': ['Compra', 'Venda'],
            'Renda Fixa': ['Aplicação', 'Resgate'],
            'Criptomoedas': ['Compra', 'Venda']
        }
    }
    
    categorias = {
        'Trabalho': ['Salário', 'Bônus', '13º', 'Freelance', 'Trabalho extra'],
        'Moradia': ['Aluguel', 'Condomínio', 'IPTU', 'Internet', 'Água', 'Luz'],
        'Alimentação': ['Supermercado', 'Restaurante', 'Delivery', 'Merenda'],
        'Saúde': ['Plano de Saúde', 'Consulta', 'Medicamento', 'Exame'],
        'Transporte': ['Gasolina', 'Estacionamento', 'Taxi', 'Ônibus', 'Metrô'],
        'Educação': ['Faculdade', 'Cursos', 'Livros', 'Material Escolar'],
        'Lazer': ['Cinema', 'Viagem', 'Hobby', 'Show', 'Esporte'],
        'Investimentos': ['Ações', 'ETFs', 'Renda Fixa', 'Criptomoedas']
    }
    
    tipos = ['receita', 'despesa', 'investimento']
    
    formas_pagamento = {
        'Débito': ['Débito', 'Débito Online'],
        'Crédito': ['Crédito', 'Crédito Parcelado'],
        'Transferência': ['Transferência', 'PIX'],
        'Dinheiro': ['Dinheiro', 'Pix'],
        'Boleto': ['Boleto']
    }
    
    ativos = {
        'Ações': ['PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'B3SA3', 'ABEV3', 'ITSA4', 'PETR3', 'BBAS3'],
        'ETFs': ['BOVA11', 'IVVB11', 'SMAL11', 'IMAB11', 'SPXI11', 'KMAX11', 'KIND11'],
        'Renda Fixa': ['Tesouro Selic', 'CDB', 'LCI', 'LCA', 'CDB 100% CDI', 'CDB 110% CDI'],
        'Criptomoedas': ['BTC', 'ETH', 'BNB', 'ADA', 'DOT', 'SOL', 'XRP', 'DOGE', 'AVAX']
    }
    
    data = []
    
    current_date = datetime(2023, 1, 1)
    end_date = datetime.now()
    
    salarios = []
    for year in range(2023, end_date.year + 1):
        for month in range(1, 13):
            try:
                d = datetime(year, month, 15)
                if d <= end_date:
                    salarios.append(d)
            except ValueError:
                pass
            try:
                d = datetime(year, month, 30 if month != 2 else 28)
                if d <= end_date:
                    salarios.append(d)
            except ValueError:
                pass
    
    while current_date <= end_date:
        if current_date in salarios:
            valor = round(random.uniform(5000, 15000), 2)
            data.append({
                'data': current_date.strftime('%d/%m/%Y'),
                'valor': valor,
                'preco': valor,
                'quantidade': 1,
                'tipo_operacao': random.choice(tipos_operacao['receita']),
                'taxa': 0.0,
                'ativo': '',
                'tipo': 'receita',
                'categoria': 'Trabalho',
                'descricao': random.choice(['Salário', 'Bônus', '13º']),
                'forma_pagamento': random.choice(formas_pagamento['Transferência']),
                'indicador1': 0.0,
                'indicador2': 0.0
            })
            
            if random.random() < 0.1:
                valor = round(random.uniform(1000, 5000), 2)
                data.append({
                    'data': current_date.strftime('%d/%m/%Y'),
                    'valor': valor,
                    'preco': valor,
                    'quantidade': 1,
                    'tipo_operacao': random.choice(tipos_operacao['receita']),
                    'taxa': 0.0,
                    'ativo': '',
                    'tipo': 'receita',
                    'categoria': 'Trabalho',
                    'descricao': random.choice(['Bônus', '13º']),
                    'forma_pagamento': random.choice(formas_pagamento['Transferência']),
                    'indicador1': 0.0,
                    'indicador2': 0.0
                })
        
        for _ in range(random.randint(1, 5)):
            categoria = random.choice(list(categorias.keys()))
            tipo = 'receita' if categoria == 'Trabalho' else 'investimento' if categoria == 'Investimentos' else 'despesa'
            
            descricao = random.choice(categorias[categoria])
            
            if categoria == 'Trabalho':
                forma_pagamento = random.choice(formas_pagamento['Transferência'])
            elif categoria == 'Investimentos':
                forma_pagamento = random.choice(formas_pagamento['Transferência'] + formas_pagamento['Débito'])
            elif categoria == 'Moradia':
                forma_pagamento = random.choice(formas_pagamento['Boleto'] + formas_pagamento['Transferência'])
            else:
                forma_pagamento = random.choice([item for sublist in formas_pagamento.values() for item in sublist])
            
            if tipo == 'receita':
                tipo_operacao = random.choice(tipos_operacao['receita'])
            elif tipo == 'investimento':
                tipo_investimento = random.choice(['Ações', 'ETFs', 'Renda Fixa', 'Criptomoedas'])
                tipo_operacao = random.choice(tipos_operacao['investimento'][tipo_investimento])
            else:
                tipo_operacao = random.choice(tipos_operacao['despesa'])
            
            quantidade = 1
            taxa = 0.0
            preco = 0.0
            ativo = ''
            indicador1 = 0.0
            indicador2 = 0.0
            
            if tipo == 'receita':
                valor = round(random.uniform(1000, 15000), 2)
                if descricao in ['Salário', 'Bônus', '13º']:
                    valor = round(random.uniform(5000, 15000), 2)
                elif descricao == 'Freelance':
                    valor = round(random.uniform(1000, 5000), 2)
                preco = valor
            elif tipo == 'investimento':
                tipo_investimento = random.choice(['Ações', 'ETFs', 'Renda Fixa', 'Criptomoedas'])
                ativo = random.choice(ativos[tipo_investimento])
                
                if tipo_investimento == 'Ações':
                    preco = round(random.uniform(10, 200), 2)
                    quantidade = random.randint(1, 100)
                    taxa = round(random.uniform(0, 20), 2)
                    indicador1 = round(random.uniform(0, 10), 4)
                    indicador2 = round(random.uniform(0, 5), 4)
                elif tipo_investimento == 'ETFs':
                    preco = round(random.uniform(20, 150), 2)
                    quantidade = random.randint(1, 50)
                    taxa = round(random.uniform(0, 15), 2)
                    indicador1 = round(random.uniform(0, 8), 4)
                    indicador2 = round(random.uniform(0, 3), 4)
                elif tipo_investimento == 'Renda Fixa':
                    preco = round(random.uniform(1000, 5000), 2)
                    quantidade = 1
                    taxa = round(random.uniform(0, 10), 2)
                    indicador1 = round(random.uniform(0, 5), 4)
                    indicador2 = round(random.uniform(0, 2), 4)
                else:  # Criptomoedas
                    preco = round(random.uniform(10000, 100000), 2)
                    quantidade = round(random.uniform(0.001, 1), 6)
                    taxa = round(random.uniform(0, 30), 2)
                    indicador1 = round(random.uniform(0, 20), 4)
                    indicador2 = round(random.uniform(0, 10), 4)
                
                valor = round(preco * quantidade, 2)
            else:  # despesa
                if categoria == 'Moradia':
                    preco = round(random.uniform(1000, 3000), 2)
                elif categoria == 'Alimentação':
                    preco = round(random.uniform(100, 1000), 2)
                elif categoria == 'Saúde':
                    preco = round(random.uniform(100, 2000), 2)
                elif categoria == 'Transporte':
                    preco = round(random.uniform(50, 500), 2)
                else:
                    preco = round(random.uniform(50, 1000), 2)
                valor = preco
            
            data.append({
                'data': current_date.strftime('%d/%m/%Y'),
                'valor': valor,
                'preco': preco,
                'quantidade': quantidade,
                'tipo_operacao': tipo_operacao,
                'taxa': taxa,
                'ativo': ativo,
                'tipo': tipo,
                'categoria': categoria,
                'descricao': descricao,
                'forma_pagamento': forma_pagamento,
                'indicador1': indicador1,
                'indicador2': indicador2
            })
        
        current_date += timedelta(days=1)
    
    df = pd.DataFrame(data)
    
    df = df.drop_duplicates(subset=['data', 'descricao', 'valor', 'tipo'])
    
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database')
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, 'transacoes_teste.csv')
    df.to_csv(output_path, index=False, sep=';', encoding='utf-8-sig')
    print(f'Arquivo completo gerado em: {output_path}')
    
    sample_df = df.sample(n=10, random_state=42) if len(df) >= 10 else df
    sample_path = os.path.join(output_dir, 'transacoes_teste_10.csv')
    sample_df.to_csv(sample_path, index=False, sep=';', encoding='utf-8-sig')
    print(f'Arquivo com 10 linhas gerado em: {sample_path}')
    print(f"Dados gerados e salvos em '{output_path}'")
    print(f"Total de registros gerados: {len(df)}")

if __name__ == '__main__':
    generate_test_data()