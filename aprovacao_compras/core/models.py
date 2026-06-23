from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    PERFIL_CHOICES = [
        ("comprador", "Comprador"),
        ("aprovador", "Aprovador"),
        ("admin", "Administrador"),
    ]
    perfil = models.CharField(max_length=20, choices=PERFIL_CHOICES, default="comprador")

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_perfil_display()})"

    @property
    def is_comprador(self):
        return self.perfil == "comprador"

    @property
    def is_aprovador(self):
        return self.perfil == "aprovador"

    @property
    def is_admin_perfil(self):
        return self.perfil == "admin"
