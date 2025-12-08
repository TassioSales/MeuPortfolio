import os
import django
import random
from datetime import datetime, timedelta

# Configurar o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_project.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Category, Transaction, Account

def create_sample_data():
    print("🚀 Iniciando criação de dados de exemplo...")

    # 1. Criar Usuário de Teste (se não existir)
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
        {'name': 'Investimentos', 'type': 'investment', 'balance': 10000.00},
    ]
    
    accounts = []
    for acc in accounts_data:
        account, created = Account.objects.get_or_create(user=user, name=acc['name'], defaults={'type': acc['type'], 'balance': acc['balance']})
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
    ]

    categories = {}
    for cat in categories_data:
        category, created = Category.objects.get_or_create(user=user, name=cat['name'], defaults={'type': cat['type'], 'color': cat['color']})
        categories[cat['name']] = category
        if created:
            print(f"✅ Categoria '{cat['name']}' criada")

    # 4. Criar Transações (Últimos 30 dias)
    print("⏳ Gerando transações...")
    today = datetime.now().date()
    
    # Receitas
    Transaction.objects.create(user=user, account=accounts[1], category=categories['Salário'], amount=5000.00, date=today.replace(day=5), description="Salário Mensal", type='income')
    Transaction.objects.create(user=user, account=accounts[1], category=categories['Freelance'], amount=800.00, date=today.replace(day=15), description="Projeto Extra", type='income')

    # Despesas Aleatórias
    descriptions = ['Almoço', 'Uber', 'Cinema', 'Supermercado', 'Aluguel', 'Gasolina', 'Jantar', 'Netflix']
    
    for _ in range(15):
        days_ago = random.randint(0, 30)
        date = today - timedelta(days=days_ago)
        cat_name = random.choice(['Alimentação', 'Transporte', 'Lazer', 'Moradia'])
        category = categories[cat_name]
        account = random.choice(accounts[:2]) # Usar apenas Carteira ou Nubank
        amount = round(random.uniform(20.0, 300.0), 2)
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
