"""
Script de seed: cria usuários e pedidos de exemplo.
Uso: python seed.py
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.utils import timezone
from core.models import Usuario
from pedidos.models import Pedido, Historico


def criar_usuario(username, first_name, last_name, password, perfil, email=""):
    if Usuario.objects.filter(username=username).exists():
        print(f"  [skip] {username} já existe")
        return Usuario.objects.get(username=username)
    u = Usuario.objects.create_user(
        username=username, password=password,
        first_name=first_name, last_name=last_name,
        email=email, perfil=perfil,
    )
    print(f"  [OK] Usuário criado: {username} ({perfil})")
    return u


def criar_pedido(solicitante, titulo, descricao, status, aprovador=None, motivo=""):
    p = Pedido.objects.create(
        solicitante=solicitante, titulo=titulo, descricao=descricao,
        status=status,
        data_envio=timezone.now() if status != "rascunho" else None,
        data_aprovacao=timezone.now() if status in ("aprovado", "reprovado") else None,
        aprovador=aprovador if status in ("aprovado", "reprovado") else None,
        motivo_reprovacao=motivo,
    )
    Historico.objects.create(pedido=p, usuario=solicitante, acao="Pedido criado")
    if status != "rascunho":
        Historico.objects.create(pedido=p, usuario=solicitante, acao="Enviado para aprovação")
    if status == "aprovado" and aprovador:
        Historico.objects.create(pedido=p, usuario=aprovador, acao="Aprovado")
    if status == "reprovado" and aprovador:
        Historico.objects.create(pedido=p, usuario=aprovador, acao="Reprovado", observacao=motivo)
    print(f"  [OK] Pedido #{p.numero_pedido:04d}: {titulo[:40]} ({status})")
    return p


print("\n=== Criando usuários ===")
admin = criar_usuario("admin", "Admin", "Sistema", "admin123", "admin", "admin@compraflow.local")
lucas = criar_usuario("lucas", "Lucas", "Aprovador", "lucas123", "aprovador")
ana = criar_usuario("ana", "Ana", "Compradora", "ana123", "comprador")
joao = criar_usuario("joao", "João", "Comprador", "joao123", "comprador")

# Superuser
if not Usuario.objects.filter(username="admin").first().is_staff:
    u = Usuario.objects.get(username="admin")
    u.is_staff = True
    u.is_superuser = True
    u.save()
    print("  [OK] admin promovido a superuser")

print("\n=== Criando pedidos ===")
criar_pedido(ana, "Compra de Notebooks para Equipe de TI", "Necessidade de substituir os notebooks antigos da equipe de TI. 5 unidades modelo Dell Latitude 5540.", "aprovado", lucas)
criar_pedido(ana, "Aquisição de Software de Gestão de Projetos", "Licença anual do Jira para 20 usuários. Necessário para controle de tarefas.", "aprovado", lucas)
criar_pedido(joao, "Cadeiras Ergonômicas — Sede", "12 cadeiras ergonômicas para o escritório sede. Orçamentos em anexo.", "reprovado", lucas, "Orçamento excede o limite trimestral. Revisar quantidade.")
criar_pedido(ana, "Impressora Multifuncional — Filial SP", "Impressora HP LaserJet Pro para a filial de São Paulo.", "aberto")
criar_pedido(joao, "Contratação de Serviço de Limpeza", "Renovação do contrato de limpeza por mais 12 meses.", "aberto")
criar_pedido(ana, "Headsets para Atendimento ao Cliente", "20 headsets Jabra para a equipe de SAC.", "rascunho")
criar_pedido(joao, "Mesa de Reunião — Sala Principal", "Mesa de reunião para 12 pessoas. Material madeira + vidro.", "aprovado", lucas)

print("\n=== Seed concluído ===")
print("\nCredenciais:")
print("  admin     / admin123  (Administrador + superuser -> /admin/)")
print("  lucas     / lucas123  (Aprovador)")
print("  ana       / ana123    (Compradora)")
print("  joao      / joao123   (Comprador)")
print()
