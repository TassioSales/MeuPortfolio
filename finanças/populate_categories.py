import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_project.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Category

username = 'tassiosales'
try:
    user = User.objects.get(username=username)
except User.DoesNotExist:
    # Fallback to the first user if specific user not found
    user = User.objects.first()
    if not user:
        print("Nenhum usuário encontrado. Crie um usuário primeiro.")
        exit(1)
    print(f"Usuário {username} não encontrado. Usando {user.username}.")

categories = [
    ('Salário', 'RECEITA'),
    ('Freelance', 'RECEITA'),
    ('Investimentos', 'RECEITA'),
    ('Alimentação', 'DESPESA'),
    ('Moradia', 'DESPESA'),
    ('Transporte', 'DESPESA'),
    ('Lazer', 'DESPESA'),
    ('Saúde', 'DESPESA'),
    ('Educação', 'DESPESA'),
    ('Outros', 'DESPESA'),
]

print(f"Criando categorias para o usuário: {user.username}")

for name, type_cat in categories:
    cat, created = Category.objects.get_or_create(user=user, name=name, type=type_cat)
    if created:
        print(f"Criada: {name} ({type_cat})")
    else:
        print(f"Já existe: {name} ({type_cat})")

print("Concluído!")
