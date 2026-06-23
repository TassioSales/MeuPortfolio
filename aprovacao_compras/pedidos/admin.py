from django.contrib import admin
from .models import Pedido, Anexo, Historico


class AnexoInline(admin.TabularInline):
    model = Anexo
    extra = 0
    readonly_fields = ("nome_arquivo", "arquivo", "data_upload", "uploader")


class HistoricoInline(admin.TabularInline):
    model = Historico
    extra = 0
    readonly_fields = ("usuario", "acao", "observacao", "data_evento")
    can_delete = False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("numero_pedido", "titulo", "solicitante", "status", "data_criacao", "aprovador")
    list_filter = ("status",)
    search_fields = ("titulo", "solicitante__username", "numero_pedido")
    readonly_fields = ("numero_pedido", "data_criacao", "data_envio", "data_aprovacao")
    inlines = [AnexoInline, HistoricoInline]
    ordering = ("-data_criacao",)


@admin.register(Anexo)
class AnexoAdmin(admin.ModelAdmin):
    list_display = ("nome_arquivo", "pedido", "uploader", "data_upload")
    readonly_fields = ("data_upload",)


@admin.register(Historico)
class HistoricoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "acao", "usuario", "data_evento")
    readonly_fields = ("data_evento",)
