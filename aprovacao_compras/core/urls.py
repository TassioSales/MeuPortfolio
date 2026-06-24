from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("cadastro/", views.registro_view, name="registro"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("usuarios/", views.gerenciar_usuarios, name="gerenciar_usuarios"),
    path("configuracoes/categorias/", views.gerenciar_categorias, name="gerenciar_categorias"),
]
