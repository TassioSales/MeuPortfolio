from django.db import migrations, models
import django.db.models.deletion


CATEGORIAS_PADRAO = [
    (0, "TI / Tecnologia"),
    (1, "Recursos Humanos"),
    (2, "Marketing"),
    (3, "Operacional"),
    (4, "Infraestrutura / Facilities"),
    (5, "Financeiro"),
    (6, "Limpeza / Higiene"),
    (7, "Outros"),
]


def seed_categorias(apps, schema_editor):
    Categoria = apps.get_model("pedidos", "Categoria")
    for ordem, nome in CATEGORIAS_PADRAO:
        Categoria.objects.get_or_create(nome=nome, defaults={"ordem": ordem, "ativa": True})


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("pedidos", "0003_add_categoria_valor_prazo"),
    ]

    operations = [
        # 1. Cria tabela Categoria
        migrations.CreateModel(
            name="Categoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=100, unique=True)),
                ("ativa", models.BooleanField(default=True)),
                ("ordem", models.PositiveSmallIntegerField(default=0)),
            ],
            options={
                "verbose_name": "Categoria",
                "verbose_name_plural": "Categorias",
                "ordering": ["ordem", "nome"],
            },
        ),
        # 2. Popula com as 8 categorias padrão
        migrations.RunPython(seed_categorias, noop),
        # 3. Remove o CharField antigo
        migrations.RemoveField(model_name="pedido", name="categoria"),
        # 4. Adiciona FK
        migrations.AddField(
            model_name="pedido",
            name="categoria",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="pedidos",
                to="pedidos.categoria",
            ),
        ),
    ]
