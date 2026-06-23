from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger("comprabio.email")


# ── Utilitários ───────────────────────────────────────────────────────────────

def _emails_aprovadores() -> list:
    User = get_user_model()
    return list(
        User.objects.filter(perfil__in=["aprovador", "admin"], is_active=True)
        .exclude(email="")
        .values_list("email", flat=True)
    )


def _enviar(destinatarios: list, assunto: str, html: str, texto: str) -> None:
    destinatarios = [e for e in destinatarios if e and "@" in e]
    if not destinatarios:
        return
    msg = EmailMultiAlternatives(
        subject=f"[CompraBio] {assunto}",
        body=texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=destinatarios,
    )
    msg.attach_alternative(html, "text/html")
    try:
        msg.send(fail_silently=False)
    except Exception as exc:
        logger.warning("Falha ao enviar email para %s: %s", destinatarios, exc)


def _wrap(conteudo: str, cor_header: str = "#00502A") -> str:
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#F0F4F2;font-family:system-ui,-apple-system,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td align="center" style="padding:32px 16px;">
<table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:14px;
  overflow:hidden;border:1px solid #dde5e3;box-shadow:0 2px 16px rgba(0,80,42,.08);">
  <tr>
    <td style="background:{cor_header};padding:20px 28px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td>
            <span style="color:#fff;font-size:17px;font-weight:800;letter-spacing:-.3px;">🛒 CompraBio</span>
            <span style="color:rgba(255,255,255,.6);font-size:12px;margin-left:10px;">Bio Mundo · Aprovação de Pedidos</span>
          </td>
        </tr>
      </table>
    </td>
  </tr>
  <tr><td style="padding:28px 28px 20px;">{conteudo}</td></tr>
  <tr>
    <td style="background:#F6F6F6;padding:14px 28px;border-top:1px solid #E9EEEE;">
      <span style="font-size:11px;color:#8aada5;">
        Esta é uma mensagem automática do CompraBio · Bio Mundo. Não responda este e-mail.
      </span>
    </td>
  </tr>
</table>
</td></tr>
</table>
</body></html>"""


def _botao(texto: str, cor: str = "#00502A") -> str:
    return f"""<div style="margin:24px 0 4px;">
  <span style="background:{cor};color:#fff;padding:12px 28px;border-radius:8px;
    font-weight:700;font-size:14px;display:inline-block;">{texto}</span>
</div>"""


def _linha_info(label: str, valor: str) -> str:
    return f"""<tr>
  <td style="padding:6px 0;font-size:12px;color:#8aada5;font-weight:700;
    text-transform:uppercase;letter-spacing:.05em;width:130px;vertical-align:top;">{label}</td>
  <td style="padding:6px 0;font-size:14px;color:#2d4a38;">{valor}</td>
</tr>"""


def _tabela_pedido(pedido, linhas_extras: list = None) -> str:
    rows = [
        _linha_info("Nº Pedido", f"#{pedido.numero_pedido:04d}"),
        _linha_info("Título", f"<strong>{pedido.titulo}</strong>"),
        _linha_info("Solicitante", pedido.solicitante.get_full_name() or pedido.solicitante.username),
    ]
    if linhas_extras:
        rows.extend(linhas_extras)
    return f"""<table cellpadding="0" cellspacing="0" width="100%"
  style="background:#F6F6F6;border-radius:10px;padding:14px 16px;margin:16px 0;">
  {"".join(rows)}
</table>"""


# ── 1. Novo pedido → Aprovadores ──────────────────────────────────────────────

def notificar_novo_pedido(pedido) -> None:
    solicitante = pedido.solicitante.get_full_name() or pedido.solicitante.username
    data_envio = pedido.data_envio.strftime("%d/%m/%Y às %H:%M") if pedido.data_envio else "—"

    conteudo = f"""
<h2 style="margin:0 0 6px;font-size:19px;color:#0d2e1a;">
  Novo pedido aguarda sua análise
</h2>
<p style="margin:0 0 20px;font-size:14px;color:#5a7a6e;">
  Um pedido de compra foi enviado e está aguardando aprovação.
</p>

{_tabela_pedido(pedido, [
    _linha_info("Enviado em", data_envio),
])}

<div style="background:#fff8ec;border-left:4px solid #ee8f2f;border-radius:0 8px 8px 0;
  padding:12px 16px;margin:16px 0;font-size:13px;color:#7a4a00;">
  <strong>Descrição:</strong><br>
  <span style="line-height:1.6;">{pedido.descricao[:300]}{"..." if len(pedido.descricao) > 300 else ""}</span>
</div>

{_botao("→ Acessar o Sistema para Analisar", "#00502A")}
"""
    html = _wrap(conteudo, cor_header="#015350")
    texto = (
        f"Novo pedido #{pedido.numero_pedido:04d} aguarda análise.\n"
        f"Solicitante: {solicitante}\n"
        f"Título: {pedido.titulo}\n"
        f"Enviado em: {data_envio}\n\n"
        f"Acesse o CompraBio para analisar."
    )
    _enviar(
        _emails_aprovadores(),
        f"Novo pedido #{pedido.numero_pedido:04d} — {pedido.titulo[:50]}",
        html, texto,
    )


# ── 2. Aprovado → Comprador ───────────────────────────────────────────────────

def notificar_pedido_aprovado(pedido, comentario: str = "") -> None:
    aprovador = pedido.aprovador.get_full_name() if pedido.aprovador else "Aprovador"
    data = pedido.data_aprovacao.strftime("%d/%m/%Y às %H:%M") if pedido.data_aprovacao else "—"

    bloco_comentario = ""
    if comentario:
        bloco_comentario = f"""
<div style="background:#eefbd2;border-left:4px solid #B5D840;border-radius:0 8px 8px 0;
  padding:12px 16px;margin:16px 0;font-size:13px;color:#2d5a00;">
  <strong>Comentário do aprovador:</strong><br>
  <span style="line-height:1.6;">{comentario}</span>
</div>"""

    conteudo = f"""
<div style="text-align:center;padding:8px 0 20px;">
  <div style="font-size:48px;line-height:1;">✅</div>
  <h2 style="margin:12px 0 6px;font-size:22px;color:#00502A;">Pedido Aprovado!</h2>
  <p style="margin:0;font-size:14px;color:#5a7a6e;">Sua solicitação de compra foi autorizada.</p>
</div>

{_tabela_pedido(pedido, [
    _linha_info("Aprovado por", aprovador),
    _linha_info("Data", data),
])}

{bloco_comentario}

<p style="font-size:13px;color:#5a7a6e;margin-top:16px;">
  O processo está concluído. Em caso de dúvidas, entre em contato com o aprovador.
</p>
"""
    html = _wrap(conteudo, cor_header="#00502A")
    texto = (
        f"Seu pedido #{pedido.numero_pedido:04d} foi APROVADO!\n"
        f"Título: {pedido.titulo}\n"
        f"Aprovado por: {aprovador} em {data}\n"
        + (f"\nComentário: {comentario}" if comentario else "")
    )
    _enviar(
        [pedido.solicitante.email],
        f"Pedido #{pedido.numero_pedido:04d} APROVADO — {pedido.titulo[:40]}",
        html, texto,
    )


# ── 3. Correção solicitada → Comprador ───────────────────────────────────────

def notificar_correcao_solicitada(pedido, motivo: str) -> None:
    aprovador = pedido.aprovador.get_full_name() if pedido.aprovador else "Aprovador"

    conteudo = f"""
<div style="text-align:center;padding:8px 0 20px;">
  <div style="font-size:48px;line-height:1;">🔧</div>
  <h2 style="margin:12px 0 6px;font-size:22px;color:#5d1a4a;">Correção Solicitada</h2>
  <p style="margin:0;font-size:14px;color:#5a7a6e;">
    Seu pedido foi devolvido para revisão antes de ser aprovado.
  </p>
</div>

{_tabela_pedido(pedido, [
    _linha_info("Solicitado por", aprovador),
])}

<div style="background:#fdf5fb;border:1.5px solid #d9a8cb;border-radius:10px;
  padding:16px;margin:16px 0;">
  <div style="font-size:12px;font-weight:700;color:#5d1a4a;text-transform:uppercase;
    letter-spacing:.05em;margin-bottom:8px;">O que deve ser corrigido</div>
  <div style="font-size:14px;color:#3d1a33;line-height:1.7;">{motivo}</div>
</div>

<div style="background:#fff8ec;border-radius:8px;padding:14px;margin-top:4px;
  font-size:13px;color:#7a4a00;">
  <strong>Próximo passo:</strong> acesse o sistema, edite o pedido conforme solicitado
  e reenvie para aprovação.
</div>

{_botao("→ Corrigir Pedido no Sistema", "#893d74")}
"""
    html = _wrap(conteudo, cor_header="#893d74")
    texto = (
        f"Seu pedido #{pedido.numero_pedido:04d} precisa de correções.\n"
        f"Título: {pedido.titulo}\n"
        f"Solicitado por: {aprovador}\n\n"
        f"O que corrigir:\n{motivo}\n\n"
        f"Acesse o CompraBio, edite o pedido e reenvie."
    )
    _enviar(
        [pedido.solicitante.email],
        f"Pedido #{pedido.numero_pedido:04d} — correcao solicitada, aguarda revisao",
        html, texto,
    )


# ── 4. Reprovado definitivo → Comprador ──────────────────────────────────────

def notificar_pedido_reprovado(pedido, motivo: str) -> None:
    aprovador = pedido.aprovador.get_full_name() if pedido.aprovador else "Aprovador"
    data = pedido.data_aprovacao.strftime("%d/%m/%Y às %H:%M") if pedido.data_aprovacao else "—"

    conteudo = f"""
<div style="text-align:center;padding:8px 0 20px;">
  <div style="font-size:48px;line-height:1;">❌</div>
  <h2 style="margin:12px 0 6px;font-size:22px;color:#8c2000;">Pedido Reprovado</h2>
  <p style="margin:0;font-size:14px;color:#5a7a6e;">
    Sua solicitação de compra foi recusada definitivamente.
  </p>
</div>

{_tabela_pedido(pedido, [
    _linha_info("Reprovado por", aprovador),
    _linha_info("Data", data),
])}

<div style="background:#fff5f0;border:1.5px solid #fcb49a;border-radius:10px;
  padding:16px;margin:16px 0;">
  <div style="font-size:12px;font-weight:700;color:#8c2000;text-transform:uppercase;
    letter-spacing:.05em;margin-bottom:8px;">Motivo da Reprovação</div>
  <div style="font-size:14px;color:#8c2000;line-height:1.7;">{motivo}</div>
</div>

<p style="font-size:13px;color:#5a7a6e;margin-top:8px;">
  Este pedido não pode ser editado. Se necessário, você pode abrir uma nova solicitação
  considerando o motivo informado acima.
</p>
"""
    html = _wrap(conteudo, cor_header="#8c2000")
    texto = (
        f"Seu pedido #{pedido.numero_pedido:04d} foi REPROVADO definitivamente.\n"
        f"Título: {pedido.titulo}\n"
        f"Reprovado por: {aprovador} em {data}\n\n"
        f"Motivo:\n{motivo}\n\n"
        f"Se necessário, abra um novo pedido no CompraBio."
    )
    _enviar(
        [pedido.solicitante.email],
        f"Pedido #{pedido.numero_pedido:04d} REPROVADO — {pedido.titulo[:40]}",
        html, texto,
    )


# ── 5. Corrigido e reenviado → Aprovadores ───────────────────────────────────

def notificar_pedido_reenviado(pedido) -> None:
    solicitante = pedido.solicitante.get_full_name() or pedido.solicitante.username
    data = pedido.data_envio.strftime("%d/%m/%Y às %H:%M") if pedido.data_envio else "—"

    conteudo = f"""
<h2 style="margin:0 0 6px;font-size:19px;color:#0d2e1a;">
  Pedido corrigido — nova análise necessária
</h2>
<p style="margin:0 0 20px;font-size:14px;color:#5a7a6e;">
  O comprador realizou as correções solicitadas e reenviou o pedido para aprovação.
</p>

{_tabela_pedido(pedido, [
    _linha_info("Reenviado em", data),
])}

<div style="background:#eefbd2;border-left:4px solid #B5D840;border-radius:0 8px 8px 0;
  padding:12px 16px;margin:16px 0;font-size:13px;color:#2d5a00;">
  <strong>{solicitante}</strong> revisou o pedido conforme as correções solicitadas
  e aguarda sua nova análise.
</div>

{_botao("→ Analisar Pedido Corrigido", "#015350")}
"""
    html = _wrap(conteudo, cor_header="#015350")
    texto = (
        f"Pedido #{pedido.numero_pedido:04d} foi corrigido e aguarda nova análise.\n"
        f"Título: {pedido.titulo}\n"
        f"Comprador: {solicitante}\n"
        f"Reenviado em: {data}\n\n"
        f"Acesse o CompraBio para analisar."
    )
    _enviar(
        _emails_aprovadores(),
        f"Pedido #{pedido.numero_pedido:04d} corrigido — aguarda nova análise",
        html, texto,
    )
