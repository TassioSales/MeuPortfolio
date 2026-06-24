import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, FileResponse
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Pedido, Anexo, Historico, Categoria
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

        categoria_id    = request.POST.get("categoria", "")
        valor_str       = request.POST.get("valor_estimado", "").strip().replace(",", ".")
        prazo_str       = request.POST.get("prazo_necessario", "").strip()

        if not titulo or not descricao:
            messages.error(request, "Título e descrição são obrigatórios.")
            return render(request, "pedidos/criar.html", {"form_data": request.POST,
                                                          "categorias": Categoria.objects.filter(ativa=True)})

        categoria_obj    = Categoria.objects.filter(pk=categoria_id).first()
        valor_estimado   = None
        prazo_necessario = None
        try:
            if valor_str:
                valor_estimado = float(valor_str)
        except ValueError:
            messages.warning(request, "Valor estimado inválido — campo ignorado.")
        try:
            if prazo_str:
                from datetime import date
                prazo_necessario = date.fromisoformat(prazo_str)
        except ValueError:
            messages.warning(request, "Data de prazo inválida — campo ignorado.")

        pedido = Pedido.objects.create(
            solicitante=request.user, titulo=titulo,
            descricao=descricao, status="rascunho",
            categoria=categoria_obj, valor_estimado=valor_estimado,
            prazo_necessario=prazo_necessario,
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

    return render(request, "pedidos/criar.html", {"categorias": Categoria.objects.filter(ativa=True)})


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
            return render(request, "pedidos/editar.html", {"pedido": pedido, "categorias": Categoria.objects.filter(ativa=True)})

        categoria_id    = request.POST.get("categoria", "")
        valor_str       = request.POST.get("valor_estimado", "").strip().replace(",", ".")
        prazo_str       = request.POST.get("prazo_necessario", "").strip()

        era_correcao = pedido.status == "correcao"
        pedido.titulo    = titulo
        pedido.descricao = descricao
        pedido.categoria = Categoria.objects.filter(pk=categoria_id).first()
        try:
            pedido.valor_estimado = float(valor_str) if valor_str else None
        except ValueError:
            pass
        try:
            from datetime import date
            pedido.prazo_necessario = date.fromisoformat(prazo_str) if prazo_str else None
        except ValueError:
            pass

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

    return render(request, "pedidos/editar.html", {"pedido": pedido, "categorias": Categoria.objects.filter(ativa=True)})


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
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from io import BytesIO
    import datetime

    pedido = get_object_or_404(Pedido, pk=pk)
    historico = list(pedido.historico.select_related("usuario").order_by("data_evento"))

    C_TEAL   = colors.HexColor("#015350")
    C_ORANGE = colors.HexColor("#ee8f2f")
    C_GREEN  = colors.HexColor("#00502A")
    C_BG     = colors.HexColor("#F6F6F6")
    C_BORDER = colors.HexColor("#d8e0df")
    C_TEXT   = colors.HexColor("#0d2e1a")
    C_MUTED  = colors.HexColor("#5a7a6e")
    C_PURPLE = colors.HexColor("#893d74")
    C_RED    = colors.HexColor("#8c2000")

    STATUS_MAP = {
        "rascunho": (C_BG,                       C_MUTED,                      "Rascunho"),
        "aberto":   (colors.HexColor("#fff7eb"),  colors.HexColor("#7a4a00"),   "Em Aberto"),
        "correcao": (colors.HexColor("#f5eaf2"),  C_PURPLE,                     "Aguardando Correção"),
        "aprovado": (colors.HexColor("#eefbd2"),  colors.HexColor("#2d5a00"),   "Aprovado"),
        "reprovado":(colors.HexColor("#fff0eb"),  C_RED,                        "Reprovado"),
    }

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=15*mm, bottomMargin=20*mm,
    )
    W = doc.width

    def P(text, **kw):
        return Paragraph(str(text), ParagraphStyle("_", **kw))

    elements = []

    # ── Cabeçalho ─────────────────────────────────────────────────────────
    hdr = Table([
        [
            P("CompraBio", fontName="Helvetica-Bold", fontSize=20, textColor=colors.white, leading=24),
            P(f"#{pedido.numero_pedido:04d}", fontName="Helvetica-Bold", fontSize=26,
              textColor=colors.white, leading=30, alignment=TA_RIGHT),
        ],
        [
            P("Bio Mundo · Aprovação de Pedidos de Compra",
              fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#91bab5"), leading=12),
            P("PEDIDO DE COMPRA", fontName="Helvetica", fontSize=8,
              textColor=colors.HexColor("#91bab5"), leading=10, alignment=TA_RIGHT),
        ],
    ], colWidths=[W * 0.6, W * 0.4])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), C_TEAL),
        ("LEFTPADDING",  (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING",   (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 14),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW",    (0, -1), (-1, -1), 3, C_ORANGE),
    ]))
    elements.append(hdr)
    elements.append(Spacer(1, 8))

    # ── Título + badge de status ───────────────────────────────────────────
    sbg, sfg, slabel = STATUS_MAP.get(pedido.status, (C_BG, C_MUTED, pedido.status))
    ts = Table([[
        P(pedido.titulo, fontName="Helvetica-Bold", fontSize=13, textColor=C_TEXT, leading=17),
        P(slabel, fontName="Helvetica-Bold", fontSize=10, textColor=sfg, leading=13, alignment=TA_CENTER),
    ]], colWidths=[W * 0.72, W * 0.28])
    ts.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.white),
        ("BACKGROUND", (1, 0), (1, 0), sbg),
        ("BOX",        (0, 0), (0, 0), 1,   C_BORDER),
        ("BOX",        (1, 0), (1, 0), 1.5, sfg),
        ("PADDING",    (0, 0), (-1, -1), 12),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(ts)
    elements.append(Spacer(1, 8))

    # ── Grid de informações ────────────────────────────────────────────────
    solicitante  = pedido.solicitante.get_full_name() or pedido.solicitante.username
    aprovador    = (pedido.aprovador.get_full_name() or pedido.aprovador.username) if pedido.aprovador else "—"
    d_criacao    = pedido.data_criacao.strftime("%d/%m/%Y  %H:%M")
    d_envio      = pedido.data_envio.strftime("%d/%m/%Y  %H:%M") if pedido.data_envio else "—"
    d_decisao    = pedido.data_aprovacao.strftime("%d/%m/%Y  %H:%M") if pedido.data_aprovacao else "—"
    categoria    = pedido.categoria.nome if pedido.categoria else "—"
    valor        = f"R$ {pedido.valor_estimado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pedido.valor_estimado else "—"
    prazo        = pedido.prazo_necessario.strftime("%d/%m/%Y") if pedido.prazo_necessario else "—"

    def lbl(t): return P(t, fontName="Helvetica-Bold", fontSize=7, textColor=C_MUTED, leading=9)
    def val(t): return P(t, fontName="Helvetica",      fontSize=10, textColor=C_TEXT,  leading=14)

    h = W / 2 - 2
    info = Table([
        [lbl("SOLICITANTE"),       lbl("APROVADOR / ANALISADOR")],
        [val(solicitante),         val(aprovador)],
        [Spacer(1, 6),             Spacer(1, 6)],
        [lbl("CATEGORIA"),         lbl("VALOR ESTIMADO")],
        [val(categoria),           val(valor)],
        [Spacer(1, 6),             Spacer(1, 6)],
        [lbl("PRAZO NECESSÁRIO"),  lbl("Nº DO PEDIDO")],
        [val(prazo),               val(f"#{pedido.numero_pedido:04d}")],
        [Spacer(1, 6),             Spacer(1, 6)],
        [lbl("DATA DE CRIAÇÃO"),   lbl("DATA DE ENVIO")],
        [val(d_criacao),           val(d_envio)],
        [Spacer(1, 6),             Spacer(1, 6)],
        [lbl("DECISÃO"),           P("", fontName="Helvetica", fontSize=10, textColor=C_TEXT, leading=14)],
        [val(d_decisao),           P("", fontName="Helvetica", fontSize=10, textColor=C_TEXT, leading=14)],
    ], colWidths=[h, h])
    info.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), C_BG),
        ("BOX",         (0, 0), (-1, -1), 1,   C_BORDER),
        ("LINEAFTER",   (0, 0), (0, -1),  0.5, C_BORDER),
        ("PADDING",     (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
    ]))
    elements.append(info)
    elements.append(Spacer(1, 10))

    # ── Bloco de motivo (reprovação ou correção) ───────────────────────────
    if pedido.motivo_reprovacao:
        m_bg = colors.HexColor("#fff0eb") if pedido.status == "reprovado" else colors.HexColor("#f5eaf2")
        m_fg = C_RED if pedido.status == "reprovado" else C_PURPLE
        m_lbl = "MOTIVO DA REPROVAÇÃO" if pedido.status == "reprovado" else "CORREÇÃO SOLICITADA"
        mot = Table([
            [P(m_lbl, fontName="Helvetica-Bold", fontSize=7, textColor=m_fg, leading=9)],
            [P(pedido.motivo_reprovacao, fontName="Helvetica", fontSize=10, textColor=m_fg, leading=14)],
        ], colWidths=[W])
        mot.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, -1), m_bg),
            ("BOX",         (0, 0), (-1, -1), 2, m_fg),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("PADDING",     (0, 0), (-1, -1), 11),
        ]))
        elements.append(mot)
        elements.append(Spacer(1, 10))

    # ── Descrição ──────────────────────────────────────────────────────────
    elements.append(HRFlowable(width=W, thickness=1, color=C_BORDER, spaceAfter=6))
    elements.append(P("DESCRIÇÃO", fontName="Helvetica-Bold", fontSize=8, textColor=C_MUTED, leading=10))
    elements.append(Spacer(1, 5))
    desc = Table([
        [P(pedido.descricao, fontName="Helvetica", fontSize=11, textColor=C_TEXT, leading=16)]
    ], colWidths=[W])
    desc.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX",        (0, 0), (-1, -1), 1, C_BORDER),
        ("PADDING",    (0, 0), (-1, -1), 14),
    ]))
    elements.append(desc)

    # ── Histórico ──────────────────────────────────────────────────────────
    if historico:
        elements.append(Spacer(1, 12))
        elements.append(HRFlowable(width=W, thickness=1, color=C_BORDER, spaceAfter=6))
        elements.append(P("HISTÓRICO DO PEDIDO", fontName="Helvetica-Bold", fontSize=8, textColor=C_MUTED, leading=10))
        elements.append(Spacer(1, 5))

        hist_rows = []
        row_bgs = []
        for i, ev in enumerate(historico):
            bg = colors.white if i % 2 == 0 else C_BG
            nome = (ev.usuario.get_full_name() or ev.usuario.username) if ev.usuario else "Sistema"
            data_ev = ev.data_evento.strftime("%d/%m/%Y  %H:%M")
            hist_rows.append([
                P(f"<b>{ev.acao}</b>", fontName="Helvetica-Bold", fontSize=10, textColor=C_TEXT, leading=13),
                P(f"{nome}  ·  {data_ev}", fontName="Helvetica", fontSize=8,
                  textColor=C_MUTED, leading=10, alignment=TA_RIGHT),
            ])
            row_bgs.append(bg)
            if ev.observacao:
                hist_rows.append([
                    P(ev.observacao, fontName="Helvetica", fontSize=9, textColor=C_MUTED, leading=12),
                    P("", fontName="Helvetica", fontSize=9, leading=12),
                ])
                row_bgs.append(bg)

        ts_hist = [
            ("BOX",     (0, 0), (-1, -1), 1, C_BORDER),
            ("PADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("VALIGN",  (0, 0), (-1, -1), "TOP"),
        ]
        for i, bg in enumerate(row_bgs):
            ts_hist.append(("BACKGROUND", (0, i), (-1, i), bg))
            ts_hist.append(("LINEBELOW",  (0, i), (-1, i), 0.5, C_BORDER))

        hist_t = Table(hist_rows, colWidths=[W * 0.65, W * 0.35])
        hist_t.setStyle(TableStyle(ts_hist))
        elements.append(hist_t)

    # ── Rodapé ─────────────────────────────────────────────────────────────
    elements.append(Spacer(1, 14))
    now_str = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")
    footer = Table([[
        P(f"Gerado em {now_str}", fontName="Helvetica", fontSize=8, textColor=C_MUTED, leading=10),
        P("CompraBio · Bio Mundo", fontName="Helvetica-Bold", fontSize=8,
          textColor=C_MUTED, leading=10, alignment=TA_CENTER),
        P("Documento sem validade jurídica", fontName="Helvetica", fontSize=8,
          textColor=C_MUTED, leading=10, alignment=TA_RIGHT),
    ]], colWidths=[W / 3, W / 3, W / 3])
    footer.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, -1), 1, C_BORDER),
        ("PADDING",   (0, 0), (-1, -1), 8),
    ]))
    elements.append(footer)

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
