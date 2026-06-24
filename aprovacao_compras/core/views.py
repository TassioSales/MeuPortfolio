from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from pedidos.models import Pedido, Categoria


def registro_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    errors = {}
    form = {}

    if request.method == "POST":
        User = get_user_model()
        form = {
            "first_name": request.POST.get("first_name", "").strip(),
            "last_name":  request.POST.get("last_name", "").strip(),
            "username":   request.POST.get("username", "").strip().lower(),
            "email":      request.POST.get("email", "").strip().lower(),
            "password1":  request.POST.get("password1", ""),
            "password2":  request.POST.get("password2", ""),
        }

        if not form["first_name"]:
            errors["first_name"] = "Informe o nome."
        if not form["username"]:
            errors["username"] = "Informe um nome de usuário."
        elif User.objects.filter(username=form["username"]).exists():
            errors["username"] = "Nome de usuário já está em uso."
        if not form["email"]:
            errors["email"] = "Informe o e-mail."
        elif User.objects.filter(email=form["email"]).exists():
            errors["email"] = "Este e-mail já está cadastrado."
        if len(form["password1"]) < 6:
            errors["password1"] = "A senha deve ter pelo menos 6 caracteres."
        elif form["password1"] != form["password2"]:
            errors["password2"] = "As senhas não coincidem."

        if not errors:
            user = User.objects.create_user(
                username=form["username"],
                email=form["email"],
                password=form["password1"],
                first_name=form["first_name"],
                last_name=form["last_name"],
                perfil="comprador",
            )
            login(request, user)
            messages.success(
                request,
                f"Bem-vindo(a), {user.first_name}! Seu cadastro foi criado. "
                "O administrador definirá seu perfil de acesso em breve."
            )
            return redirect("dashboard")

    return render(request, "auth/registro.html", {"errors": errors, "form": form})


@login_required
def gerenciar_usuarios(request):
    if not (request.user.is_admin_perfil or request.user.is_superuser):
        messages.error(request, "Acesso restrito ao administrador.")
        return redirect("dashboard")

    User = get_user_model()

    if request.method == "POST":
        action = request.POST.get("action", "salvar")
        user_id = request.POST.get("user_id")
        alvo = get_object_or_404(User, pk=user_id) if user_id else None

        if alvo and alvo == request.user and action in ("deletar",):
            messages.error(request, "Você não pode excluir sua própria conta.")
            return redirect("gerenciar_usuarios")

        if action == "deletar" and alvo:
            nome = alvo.get_full_name() or alvo.username
            alvo.delete()
            messages.success(request, f"Usuário '{nome}' excluído.")

        elif action == "resetar_senha" and alvo:
            nova_senha = request.POST.get("nova_senha", "").strip()
            if len(nova_senha) < 6:
                messages.error(request, "A senha deve ter pelo menos 6 caracteres.")
            else:
                alvo.set_password(nova_senha)
                alvo.save()
                messages.success(
                    request,
                    f"Senha de '{alvo.get_full_name() or alvo.username}' redefinida com sucesso."
                )

        elif action == "salvar" and alvo:
            novo_perfil = request.POST.get("perfil")
            ativo = request.POST.get("ativo") == "1"
            novo_email = request.POST.get("email", "").strip().lower()
            perfis_validos = [c[0] for c in User.PERFIL_CHOICES]
            if alvo == request.user:
                messages.warning(request, "Você não pode alterar seu próprio perfil.")
            elif novo_perfil in perfis_validos:
                alvo.perfil = novo_perfil
                alvo.is_active = ativo
                if novo_email:
                    alvo.email = novo_email
                alvo.save()
                messages.success(
                    request,
                    f"Usuário {alvo.get_full_name() or alvo.username} atualizado."
                )

        return redirect("gerenciar_usuarios")

    usuarios = User.objects.all().order_by("perfil", "first_name", "username")
    return render(request, "core/usuarios.html", {"usuarios": usuarios})


def logout_view(request):
    logout(request)
    return redirect("login")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(request.GET.get("next", "dashboard"))
        error = "Usuário ou senha inválidos."
    return render(request, "auth/login.html", {"error": error})


@login_required
def dashboard(request):
    data_ini  = request.GET.get("data_ini", "")
    data_fim  = request.GET.get("data_fim", "")
    filtro_status    = request.GET.get("status", "")
    filtro_categoria = request.GET.get("categoria", "")
    busca            = request.GET.get("q", "").strip()

    qs = Pedido.objects.exclude(status="rascunho")
    if request.user.is_comprador:
        qs = qs.filter(solicitante=request.user)

    if data_ini:
        qs = qs.filter(data_criacao__date__gte=data_ini)
    if data_fim:
        qs = qs.filter(data_criacao__date__lte=data_fim)
    if filtro_status:
        qs = qs.filter(status=filtro_status)
    if filtro_categoria:
        qs = qs.filter(categoria_id=filtro_categoria)
    if busca:
        qs = qs.filter(Q(titulo__icontains=busca) | Q(descricao__icontains=busca))

    totais = qs.aggregate(
        total=Count("id"),
        aprovados=Count("id", filter=Q(status="aprovado")),
        reprovados=Count("id", filter=Q(status="reprovado")),
        abertos=Count("id", filter=Q(status="aberto")),
    )

    hoje = timezone.now()
    meses = []
    for i in range(5, -1, -1):
        d = hoje - timedelta(days=30 * i)
        label = d.strftime("%b/%y")
        count = qs.filter(data_criacao__month=d.month, data_criacao__year=d.year).count()
        meses.append({"label": label, "count": count})

    pedidos = qs.select_related("solicitante", "aprovador").order_by("-data_criacao")[:50]

    return render(request, "dashboard.html", {
        "totais": totais,
        "pedidos": pedidos,
        "meses": meses,
        "data_ini": data_ini,
        "data_fim": data_fim,
        "filtro_status": filtro_status,
        "filtro_categoria": filtro_categoria,
        "busca": busca,
        "status_choices": Pedido.STATUS_CHOICES,
        "categorias": Categoria.objects.filter(ativa=True),
    })


@login_required
def admin_dashboard(request):
    if not (request.user.is_admin_perfil or request.user.is_superuser):
        return redirect("dashboard")

    qs = Pedido.objects.exclude(status="rascunho")
    totais = qs.aggregate(
        total=Count("id"),
        aprovados=Count("id", filter=Q(status="aprovado")),
        reprovados=Count("id", filter=Q(status="reprovado")),
        pendentes=Count("id", filter=Q(status="aberto")),
    )
    total = totais["total"] or 1
    totais["taxa_aprovacao"] = round(totais["aprovados"] / total * 100, 1)
    totais["taxa_reprovacao"] = round(totais["reprovados"] / total * 100, 1)

    hoje = timezone.now()
    meses = []
    for i in range(5, -1, -1):
        d = hoje - timedelta(days=30 * i)
        label = d.strftime("%b/%y")
        base = qs.filter(data_criacao__month=d.month, data_criacao__year=d.year)
        meses.append({
            "label": label,
            "total": base.count(),
            "aprovados": base.filter(status="aprovado").count(),
            "reprovados": base.filter(status="reprovado").count(),
        })

    return render(request, "admin_dashboard.html", {
        "totais": totais,
        "totais_agg": totais,
        "meses": meses,
    })


@login_required
def gerenciar_categorias(request):
    if not (request.user.is_admin_perfil or request.user.is_superuser):
        messages.error(request, "Acesso restrito ao administrador.")
        return redirect("dashboard")

    if request.method == "POST":
        action = request.POST.get("action")
        cat_id = request.POST.get("cat_id")

        if action == "criar":
            nome = request.POST.get("nome", "").strip()
            if not nome:
                messages.error(request, "Informe o nome da categoria.")
            elif Categoria.objects.filter(nome__iexact=nome).exists():
                messages.error(request, f"Já existe uma categoria com o nome '{nome}'.")
            else:
                ordem = Categoria.objects.count()
                Categoria.objects.create(nome=nome, ordem=ordem)
                messages.success(request, f"Categoria '{nome}' criada.")

        elif action == "salvar" and cat_id:
            cat = get_object_or_404(Categoria, pk=cat_id)
            nome = request.POST.get("nome", "").strip()
            ativa = request.POST.get("ativa") == "1"
            if not nome:
                messages.error(request, "O nome não pode ser vazio.")
            elif Categoria.objects.filter(nome__iexact=nome).exclude(pk=cat_id).exists():
                messages.error(request, f"Já existe outra categoria com o nome '{nome}'.")
            else:
                cat.nome = nome
                cat.ativa = ativa
                cat.save()
                messages.success(request, f"Categoria '{cat.nome}' atualizada.")

        elif action == "deletar" and cat_id:
            cat = get_object_or_404(Categoria, pk=cat_id)
            if cat.pedidos.exists():
                messages.error(request, f"'{cat.nome}' possui pedidos vinculados e não pode ser excluída.")
            else:
                cat.delete()
                messages.success(request, "Categoria excluída.")

        return redirect("gerenciar_categorias")

    categorias = Categoria.objects.annotate(total_pedidos=Count("pedidos")).order_by("ordem", "nome")
    return render(request, "core/categorias.html", {"categorias": categorias})
