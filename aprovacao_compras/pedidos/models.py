from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


def gerar_numero_pedido():
    from django.db.models import Max
    ultimo = Pedido.objects.aggregate(Max("numero_pedido"))["numero_pedido__max"] or 0
    return ultimo + 1


class Pedido(models.Model):
    STATUS_CHOICES = [
        ("rascunho", "Rascunho"),
        ("aberto", "Em Aberto"),
        ("correcao", "Aguardando Correção"),
        ("aprovado", "Aprovado"),
        ("reprovado", "Reprovado"),
    ]

    numero_pedido = models.PositiveIntegerField(unique=True, editable=False)
    data_criacao = models.DateTimeField(default=timezone.now)
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pedidos_solicitados",
    )
    titulo = models.CharField(max_length=200)
    descricao = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="rascunho")
    data_envio = models.DateTimeField(null=True, blank=True)
    data_aprovacao = models.DateTimeField(null=True, blank=True)
    aprovador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos_aprovados",
    )
    motivo_reprovacao = models.TextField(blank=True)

    class Meta:
        ordering = ["-data_criacao"]
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"

    def save(self, *args, **kwargs):
        if not self.pk:
            self.numero_pedido = gerar_numero_pedido()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"#{self.numero_pedido:04d} — {self.titulo}"

    @property
    def status_badge(self):
        return {
            "rascunho": ("secondary", "Rascunho"),
            "aberto": ("warning", "Em Aberto"),
            "correcao": ("correcao", "Aguardando Correção"),
            "aprovado": ("success", "Aprovado"),
            "reprovado": ("danger", "Reprovado"),
        }.get(self.status, ("secondary", self.status))


class Anexo(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="anexos")
    nome_arquivo = models.CharField(max_length=255)
    arquivo = models.FileField(upload_to="anexos/%Y/%m/")
    data_upload = models.DateTimeField(default=timezone.now)
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )

    class Meta:
        verbose_name = "Anexo"
        verbose_name_plural = "Anexos"

    def __str__(self):
        return self.nome_arquivo


class Historico(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="historico")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    acao = models.CharField(max_length=100)
    observacao = models.TextField(blank=True)
    data_evento = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-data_evento"]
        verbose_name = "Histórico"
        verbose_name_plural = "Históricos"

    def __str__(self):
        return f"{self.pedido} — {self.acao} em {self.data_evento:%d/%m/%Y %H:%M}"
