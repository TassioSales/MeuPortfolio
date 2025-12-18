import os
import django
import random
from datetime import datetime, timedelta
from decimal import Decimal

# Configurar o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_project.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Category, Transaction, Account, Goal, Investment
from app_estoque.models import Produto, Fornecedor

def create_sample_data():
    print("🚀 Iniciando criação de dados de exemplo...")

    # 1. Criar Usuário de Teste
    user, created = User.objects.get_or_create(username='usuario_teste')
    if created:
        user.set_password('senha123')
        user.save()
        print("✅ Usuário 'usuario_teste' criado (senha: senha123)")
    else:
        print("ℹ️ Usuário 'usuario_teste' já existe")

    # 2. Criar Contas
    accounts_data = [
        {'name': 'Carteira', 'type': 'cash', 'balance': 150.00},
        {'name': 'Nubank', 'type': 'bank', 'balance': 2500.00},
        {'name': 'Investimentos', 'type': 'investment', 'balance': 15000.00},
    ]
    
    accounts = []
    for acc in accounts_data:
        account, created = Account.objects.get_or_create(
            user=user, 
            name=acc['name'], 
            defaults={'type': acc['type'], 'balance': acc['balance']}
        )
        accounts.append(account)
        if created:
            print(f"✅ Conta '{acc['name']}' criada")

    # 3. Criar Categorias
    categories_data = [
        {'name': 'Salário', 'type': 'income', 'color': '#28a745'},
        {'name': 'Freelance', 'type': 'income', 'color': '#17a2b8'},
        {'name': 'Alimentação', 'type': 'expense', 'color': '#dc3545'},
        {'name': 'Transporte', 'type': 'expense', 'color': '#ffc107'},
        {'name': 'Lazer', 'type': 'expense', 'color': '#6f42c1'},
        {'name': 'Moradia', 'type': 'expense', 'color': '#fd7e14'},
        {'name': 'Saúde', 'type': 'expense', 'color': '#20c997'},
    ]

    categories = {}
    for cat in categories_data:
        category, created = Category.objects.get_or_create(
            user=user, 
            name=cat['name'], 
            defaults={'type': cat['type'], 'color': cat['color']}
        )
        categories[cat['name']] = category

    # 4. Criar Metas
    goals_data = [
        {'name': 'Viagem Fim de Ano', 'target': 5000.00, 'current': 1500.00, 'deadline': '2025-12-31', 'color': '#0d6efd'},
        {'name': 'Reserva de Emergência', 'target': 10000.00, 'current': 3000.00, 'deadline': '2026-06-30', 'color': '#198754'},
    ]
    
    for goal in goals_data:
        Goal.objects.get_or_create(
            user=user,
            name=goal['name'],
            defaults={
                'target_amount': goal['target'],
                'current_amount': goal['current'],
                'deadline': goal['deadline'],
                'color': goal['color']
            }
        )
        print(f"✅ Meta '{goal['name']}' criada")

    # 5. Criar Investimentos
    investments_data = [
        {'symbol': 'PETR4.SA', 'name': 'Petrobras PN', 'qty': 100, 'price': 35.50, 'date': '2024-01-15'},
        {'symbol': 'VALE3.SA', 'name': 'Vale ON', 'qty': 50, 'price': 68.20, 'date': '2024-02-10'},
        {'symbol': 'HGLG11.SA', 'name': 'CSHG Logística', 'qty': 10, 'price': 160.00, 'date': '2024-03-05'},
        {'symbol': 'MXRF11.SA', 'name': 'Maxi Renda', 'qty': 200, 'price': 10.50, 'date': '2024-04-20'},
    ]

    for inv in investments_data:
        Investment.objects.get_or_create(
            user=user,
            symbol=inv['symbol'],
            defaults={
                'name': inv['name'],
                'quantity': inv['qty'],
                'purchase_price': inv['price'],
                'date': inv['date']
            }
        )
        print(f"✅ Investimento '{inv['symbol']}' criado")

    # 6. Criar Dados de Estoque (Fornecedores e Produtos)
    supplier, _ = Fornecedor.objects.get_or_create(
        nome="Distribuidora Geral",
        defaults={'email': 'contato@distribuidora.com', 'telefone': '11999999999'}
    )

    products_data = [
        {'name': 'Coca-Cola 350ml', 'price': 5.00, 'cost': 2.50, 'stock': 100, 'barcode': '7894900011517'},
        {'name': 'Água Mineral 500ml', 'price': 3.00, 'cost': 1.00, 'stock': 200, 'barcode': '7891234567890'},
        {'name': 'Chocolate Barra', 'price': 8.50, 'cost': 4.50, 'stock': 50, 'barcode': '7891011121314'},
        {'name': 'Salgadinho Batata', 'price': 12.00, 'cost': 7.00, 'stock': 30, 'barcode': '7891516171819'},
    ]

    for prod in products_data:
        Produto.objects.get_or_create(
            nome=prod['name'],
            defaults={
                'preco_venda': prod['price'],
                'preco_custo': prod['cost'],
                'estoque_atual': prod['stock'],
                'estoque_minimo': 10,
                'codigo_barras': prod['barcode'],
                'fornecedor': supplier
            }
        )
        print(f"✅ Produto '{prod['name']}' criado")

    # 7. Criar Transações (Últimos 30 dias)
    print("⏳ Gerando transações...")
    today = datetime.now().date()
    
    # Receitas Fixas
    Transaction.objects.create(user=user, account=accounts[1], category=categories['Salário'], amount=5000.00, date=today.replace(day=5), description="Salário Mensal", type='income')
    
    # Despesas Aleatórias
    descriptions = ['Almoço', 'Uber', 'Cinema', 'Supermercado', 'Aluguel', 'Gasolina', 'Jantar', 'Netflix', 'Farmácia', 'Padaria']
    
    for _ in range(20):
        days_ago = random.randint(0, 30)
        date = today - timedelta(days=days_ago)
        cat_name = random.choice(['Alimentação', 'Transporte', 'Lazer', 'Moradia', 'Saúde'])
        category = categories[cat_name]
        account = random.choice(accounts[:2])
        amount = round(random.uniform(15.0, 400.0), 2)
        desc = random.choice(descriptions)
        
        Transaction.objects.create(
            user=user,
            account=account,
            category=category,
            amount=amount,
            date=date,
            description=desc,
            type='expense'
        )
    
    print("✅ Transações de exemplo criadas com sucesso!")
    print("\n🎉 Tudo pronto! Você pode logar com:")
    print("   Usuário: usuario_teste")
    print("   Senha:   senha123")

if __name__ == '__main__':
    create_sample_data()
