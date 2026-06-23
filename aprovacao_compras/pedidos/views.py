import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, FileResponse
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Pedido, Anexo, Historico
from core.notifications import (
    notificar_novo_pedido,
    notificar_pedido_aprovado,
    notificar_correcao_solicitada,
    notificar_pedido_reprovado,
    notificar_pedido_reenviado,
)


ALLOWED_EXTENSIONS = {".xlsx", ".xls"}
EDITAVEIS = ("rascunho", "correcao")


def _registrar_historico(pedido, usuario, acao, obs=""):
    Historico.objects.create(pedido=pedido, usuario=usuario, acao=acao, observacao=obs)


def _salvar_anexos(request, pedido):
    for arq in request.FILES.getlist("anexos"):
        ext = os.path.splitext(arq.name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            messages.warning(request, f"Arquivo '{arq.name}' ignorado — somente .xlsx e .xls.")
            continue
        Anexo.objects.create(pedido=pedido, nome_arquivo=arq.name, arquivo=arq, uploader=request.user)


def _enviar_para_aprovacao(pedido, usuario, acao_hist="Enviado para aprovação"):
    pedido.status = "aberto"
    pedido.data_envio = timezone.now()
    pedido.save()
    _registrar_historico(pedido, usuario, acao_hist)


# ─── COMPRADOR ────────────────────────────────────────────────────────────────

@login_required
def criar_pedido(request):
    if not (request.user.is_comprador or request.user.is_admin_perfil or request.user.is_superuser):
        messages.error(request, "Apenas compradores podem criar pedidos.")
        return redirect("dashboard")

    if request.method == "POST":
        titulo = request.POST.get("titulo", "").strip()
        descricao = request.POST.get("descricao", "").strip()
        acao = request.POST.get("acao", "rascunho")

        if not titulo or not descricao:
            messages.error(request, "Título e descrição são obrigatórios.")
            return render(request, "pedidos/criar.html", {"form_data": request.POST})

        pedido = Pedido.objects.create(
            solicitante=request.user, titulo=titulo,
            descricao=descricao, status="rascunho",
        )
        _registrar_historico(pedido, request.user, "Pedido criado")
        _salvar_anexos(request, pedido)

        if acao == "enviar":
            _enviar_para_aprovacao(pedido, request.user)
            notificar_novo_pedido(pedido)
            messages.success(request, f"Pedido #{pedido.numero_pedido:04d} enviado para aprovação.")
        else:
            messages.success(request, f"Rascunho #{pedido.numero_pedido:04d} salvo.")

        return redirect("detalhe_pedido", pk=pedido.pk)

    return render(request, "pedidos/criar.html", {})


@login_required
def editar_pedido(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk, solicitante=request.user)

    if pedido.status not in EDITAVEIS:
        messages.error(request, "Este pedido não pode ser editado no status atual.")
        return redirect("detalhe_pedido", pk=pedido.pk)

    if request.method == "POST":
        titulo = request.POST.get("titulo", "").strip()
        descricao = request.POST.get("descricao", "").strip()
        acao = request.POST.get("acao", "rascunho")
        remover_ids = request.POST.getlist("remover_anexo")

        if not titulo or not descricao:
            messages.error(request, "Título e descrição são obrigatórios.")
            return render(request, "pedidos/editar.html", {"pedido": pedido})

        era_correcao = pedido.status == "correcao"
        pedido.titulo = titulo
        pedido.descricao = descricao

        # Remove anexos marcados pelo usuário
        if remover_ids:
            Anexo.objects.filter(pk__in=remover_ids, pedido=pedido).delete()

        # Adiciona novos anexos
        _salvar_anexos(request, pedido)

        if acao == "enviar":
            motivo_anterior = pedido.motivo_reprovacao
            pedido.status = "aberto"
            pedido.data_envio = timezone.now()
            pedido.data_aprovacao = None
            pedido.aprovador = None
            pedido.motivo_reprovacao = ""
            pedido.save()
            if era_correcao:
                _registrar_historico(
                    pedido, request.user,
                    "Correção realizada e reenviado",
                    f"Solicitação anterior: {motivo_anterior}" if motivo_anterior else "",
                )
                notificar_pedido_reenviado(pedido)
            else:
                _registrar_historico(pedido, request.user, "Enviado para aprovação")
                notificar_novo_pedido(pedido)
            messages.success(request, f"Pedido #{pedido.numero_pedido:04d} reenviado para aprovação.")
        else:
            novo_status = "correcao" if era_correcao else "rascunho"
            pedido.status = novo_status
            pedido.save()
            _registrar_historico(pedido, request.user, "Pedido editado")
            messages.success(request, "Alterações salvas.")

        return redirect("detalhe_pedido", pk=pedido.pk)

    return render(request, "pedidos/editar.html", {"pedido": pedido})


@login_required
def enviar_pedido(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk, solicitante=request.user, status="rascunho")
    _enviar_para_aprovacao(pedido, request.user)
    messages.success(request, f"Pedido #{pedido.numero_pedido:04d} enviado para aprovação.")
    return redirect("detalhe_pedido", pk=pedido.pk)


@login_required
def remover_anexo(request, pk, anexo_id):
    pedido = get_object_or_404(Pedido, pk=pk, solicitante=request.user)
    if pedido.status not in EDITAVEIS:
        messages.error(request, "Não é possível remover anexos neste status.")
        return redirect("detalhe_pedido", pk=pedido.pk)
    anexo = get_object_or_404(Anexo, pk=anexo_id, pedido=pedido)
    anexo.delete()
    messages.success(request, f"Anexo '{anexo.nome_arquivo}' removido.")
    return redirect("editar_pedido", pk=pedido.pk)


# ─── COMPARTILHADO ────────────────────────────────────────────────────────────

@login_required
def detalhe_pedido(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    pode_ver = (
        request.user.is_aprovador
        or request.user.is_admin_perfil
        or request.user.is_superuser
        or pedido.solicitante == request.user
    )
    if not pode_ver:
        messages.error(request, "Acesso negado.")
        return redirect("dashboard")
    return render(request, "pedidos/detalhe.html", {"pedido": pedido})


@login_required
def download_anexo(request, pk, anexo_id):
    pedido = get_object_or_404(Pedido, pk=pk)
    anexo = get_object_or_404(Anexo, pk=anexo_id, pedido=pedido)
    return FileResponse(anexo.arquivo.open("rb"), as_attachment=True, filename=anexo.nome_arquivo)


# ─── APROVADOR ────────────────────────────────────────────────────────────────

@login_required
def aprovar_pedido(request, pk):
    if not (request.user.is_aprovador or request.user.is_admin_perfil or request.user.is_superuser):
        messages.error(request, "Você não tem permissão para aprovar pedidos.")
        return redirect("dashboard")

    pedido = get_object_or_404(Pedido, pk=pk, status="aberto")

    if request.method == "POST":
        decisao = request.POST.get("decisao")
        motivo_correcao = request.POST.get("motivo_correcao", "").strip()
        motivo_reprovacao = request.POST.get("motivo_reprovacao", "").strip()
        comentario = request.POST.get("comentario", "").strip()

        if decisao == "aprovar":
            pedido.status = "aprovado"
            pedido.data_aprovacao = timezone.now()
            pedido.aprovador = request.user
            pedido.motivo_reprovacao = ""
            pedido.save()
            _registrar_historico(pedido, request.user, "Aprovado", comentario)
            notificar_pedido_aprovado(pedido, comentario)
            messages.success(request, f"Pedido #{pedido.numero_pedido:04d} aprovado.")
            return redirect("controle_processos")

        elif decisao == "correcao":
            if not motivo_correcao:
                messages.error(request, "Informe o que deve ser corrigido.")
                return render(request, "pedidos/aprovar.html", {"pedido": pedido})
            pedido.status = "correcao"
            pedido.aprovador = request.user
            pedido.motivo_reprovacao = motivo_correcao
            pedido.data_aprovacao = None
            pedido.save()
            _registrar_historico(pedido, request.user, "Correção solicitada", motivo_correcao)
            notificar_correcao_solicitada(pedido, motivo_correcao)
            messages.info(request, f"Pedido #{pedido.numero_pedido:04d} devolvido para correção.")
            return redirect("controle_processos")

        elif decisao == "reprovar":
            if not motivo_reprovacao:
                messages.error(request, "Informe o motivo da reprovação.")
                return render(request, "pedidos/aprovar.html", {"pedido": pedido})
            pedido.status = "reprovado"
            pedido.data_aprovacao = timezone.now()
            pedido.aprovador = request.user
            pedido.motivo_reprovacao = motivo_reprovacao
            pedido.save()
            _registrar_historico(pedido, request.user, "Reprovado definitivamente", motivo_reprovacao)
            notificar_pedido_reprovado(pedido, motivo_reprovacao)
            messages.warning(request, f"Pedido #{pedido.numero_pedido:04d} reprovado.")
            return redirect("controle_processos")

        else:
            messages.error(request, "Selecione uma decisão.")

    return render(request, "pedidos/aprovar.html", {"pedido": pedido})


# ─── CONTROLE / EXPORTAÇÃO ───────────────────────────────────────────────────

@login_required
def controle_processos(request):
    qs = Pedido.objects.exclude(status="rascunho").select_related("solicitante", "aprovador")
    if request.user.is_comprador:
        qs = qs.filter(solicitante=request.user)

    data_ini = request.GET.get("data_ini", "")
    data_fim = request.GET.get("data_fim", "")
    status_f = request.GET.get("status", "")
    solicitante_q = request.GET.get("solicitante", "")
    numero_q = request.GET.get("numero", "")
    busca = request.GET.get("busca", "")

    if data_ini:
        qs = qs.filter(data_criacao__date__gte=data_ini)
    if data_fim:
        qs = qs.filter(data_criacao__date__lte=data_fim)
    if status_f:
        qs = qs.filter(status=status_f)
    if solicitante_q:
        qs = qs.filter(solicitante__username__icontains=solicitante_q)
    if numero_q:
        try:
            qs = qs.filter(numero_pedido=int(numero_q))
        except ValueError:
            pass
    if busca:
        qs = qs.filter(Q(titulo__icontains=busca) | Q(descricao__icontains=busca))

    paginator = Paginator(qs.order_by("-data_criacao"), 20)
    page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "pedidos/controle.html", {
        "page": page,
        "data_ini": data_ini,
        "data_fim": data_fim,
        "status_f": status_f,
        "solicitante_q": solicitante_q,
        "numero_q": numero_q,
        "busca": busca,
        "status_choices": Pedido.STATUS_CHOICES,
    })


@login_required
def exportar_pdf(request, pk):
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from io import BytesIO

    pedido = get_object_or_404(Pedido, pk=pk)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    elements = []
    elements.append(Paragraph(f"CompraBio — Pedido #{pedido.numero_pedido:04d}", styles["Title"]))
    elements.append(Spacer(1, 12))
    data = [
        ["Campo", "Valor"],
        ["Título", pedido.titulo],
        ["Solicitante", str(pedido.solicitante)],
        ["Status", pedido.get_status_display()],
        ["Data Criação", pedido.data_criacao.strftime("%d/%m/%Y %H:%M")],
        ["Data Envio", pedido.data_envio.strftime("%d/%m/%Y %H:%M") if pedido.data_envio else "—"],
        ["Data Decisão", pedido.data_aprovacao.strftime("%d/%m/%Y %H:%M") if pedido.data_aprovacao else "—"],
        ["Aprovador", str(pedido.aprovador) if pedido.aprovador else "—"],
        ["Motivo Reprovação", pedido.motivo_reprovacao or "—"],
    ]
    t = Table(data, colWidths=[150, 350])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#00502A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F6F6")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d8e0df")),
        ("PADDING", (0, 0), (-1, -1), 7),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 16))
    elements.append(Paragraph("Descrição", styles["Heading2"]))
    elements.append(Paragraph(pedido.descricao, styles["Normal"]))
    doc.build(elements)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"pedido_{pedido.numero_pedido:04d}.pdf")


@login_required
def exportar_excel(request):
    import openpyxl
    from io import BytesIO

    qs = Pedido.objects.exclude(status="rascunho").select_related("solicitante", "aprovador")
    if request.user.is_comprador:
        qs = qs.filter(solicitante=request.user)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Pedidos"
    ws.append(["Nr Pedido", "Data", "Solicitante", "Titulo", "Status",
                "Data Envio", "Data Decisao", "Aprovador", "Motivo Reprovacao"])
    for p in qs.order_by("-data_criacao"):
        ws.append([
            p.numero_pedido,
            p.data_criacao.strftime("%d/%m/%Y %H:%M"),
            str(p.solicitante),
            p.titulo,
            p.get_status_display(),
            p.data_envio.strftime("%d/%m/%Y %H:%M") if p.data_envio else "",
            p.data_aprovacao.strftime("%d/%m/%Y %H:%M") if p.data_aprovacao else "",
            str(p.aprovador) if p.aprovador else "",
            p.motivo_reprovacao or "",
        ])
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return HttpResponse(
        buffer.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="pedidos.xlsx"'},
    )
