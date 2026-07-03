from django.core.management.base import BaseCommand
from pedidos.models import Categoria, Pedido


NOVAS_CATEGORIAS = [
    "DISTRIBUIDOR",
    "OUTROS",
    "MARCA PRÓPRIA",
    "GRANEL",
    "OPERACIONAL",
    "SEM CLASSIFICAÇÃO",
]


class Command(BaseCommand):
    help = "Substitui todas as categorias pelas categorias padrão Bio Mundo"

    def handle(self, *args, **kwargs):
        # Desvincula pedidos das categorias antigas para evitar PROTECT
        atualizados = Pedido.objects.filter(categoria__isnull=False).update(categoria=None)
        if atualizados:
            self.stdout.write(f"  {atualizados} pedido(s) desvinculados das categorias antigas")

        # Remove categorias antigas
        removidas = Categoria.objects.all().delete()
        self.stdout.write(f"  Categorias removidas: {removidas[0]}")

        # Cria novas categorias
        for i, nome in enumerate(NOVAS_CATEGORIAS, start=1):
            Categoria.objects.create(nome=nome, ordem=i)
            self.stdout.write(f"  [OK] {nome}")

        self.stdout.write(self.style.SUCCESS("\nCategorias atualizadas com sucesso!"))
