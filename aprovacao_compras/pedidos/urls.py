from django.urls import path
from . import views

urlpatterns = [
    path("novo/", views.criar_pedido, name="criar_pedido"),
    path("<int:pk>/", views.detalhe_pedido, name="detalhe_pedido"),
    path("<int:pk>/editar/", views.editar_pedido, name="editar_pedido"),
    path("<int:pk>/aprovar/", views.aprovar_pedido, name="aprovar_pedido"),
    path("<int:pk>/enviar/", views.enviar_pedido, name="enviar_pedido"),
    path("<int:pk>/anexo/<int:anexo_id>/download/", views.download_anexo, name="download_anexo"),
    path("<int:pk>/anexo/<int:anexo_id>/remover/", views.remover_anexo, name="remover_anexo"),
    path("controle/", views.controle_processos, name="controle_processos"),
    path("<int:pk>/exportar-pdf/", views.exportar_pdf, name="exportar_pdf"),
    path("exportar-excel/", views.exportar_excel, name="exportar_excel"),
]
