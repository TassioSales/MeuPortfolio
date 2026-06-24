from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from pedidos.models import Pedido
from core.notifications import _emails_aprovadores, _enviar, _wrap, _tabela_pedido, _botao, _url_pedido


class Command(BaseCommand):
    help = "Envia lembrete por email para pedidos em aberto há mais de X dias sem decisão."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dias",
            type=int,
            default=2,
            help="Número de dias sem decisão para disparar o lembrete (padrão: 2).",
        )

    def handle(self, *args, **options):
        dias = options["dias"]
        limite = timezone.now() - timedelta(days=dias)

        pedidos_parados = Pedido.objects.filter(
            status="aberto",
            data_envio__lte=limite,
        ).select_related("solicitante")

        if not pedidos_parados.exists():
            self.stdout.write(self.style.SUCCESS(f"Nenhum pedido parado há mais de {dias} dias."))
            return

        destinatarios = _emails_aprovadores()
        if not destinatarios:
            self.stdout.write(self.style.WARNING("Nenhum aprovador com email cadastrado."))
            return

        for pedido in pedidos_parados:
            dias_aberto = (timezone.now() - pedido.data_envio).days
            data_envio  = pedido.data_envio.strftime("%d/%m/%Y às %H:%M")

            conteudo = f"""
<h2 style="margin:0 0 6px;font-size:19px;color:#0d2e1a;">
  Pedido aguardando decisão há <span style="color:#ee8f2f;">{dias_aberto} dia{"s" if dias_aberto != 1 else ""}</span>
</h2>
<p style="margin:0 0 20px;font-size:14px;color:#5a7a6e;">
  O pedido abaixo ainda não recebeu aprovação, reprovação ou solicitação de correção.
</p>

{_tabela_pedido(pedido, [
    _botao_info("Enviado em", data_envio),
    _botao_info("Dias aguardando", str(dias_aberto)),
])}

<div style="background:#fff8ec;border-left:4px solid #ee8f2f;border-radius:0 8px 8px 0;
  padding:12px 16px;margin:16px 0;font-size:13px;color:#7a4a00;">
  <strong>Ação necessária:</strong> acesse o sistema e analise este pedido o quanto antes.
</div>

{_botao("→ Analisar Pedido", _url_pedido(pedido), "#ee8f2f")}
"""
            html  = _wrap(conteudo, cor_header="#015350")
            texto = (
                f"Lembrete: pedido #{pedido.numero_pedido:04d} aguarda decisão há {dias_aberto} dias.\n"
                f"Título: {pedido.titulo}\n"
                f"Solicitante: {pedido.solicitante.get_full_name() or pedido.solicitante.username}\n"
                f"Enviado em: {data_envio}\n\n"
                f"Acesse o CompraBio para analisar."
            )
            _enviar(
                destinatarios,
                f"[Lembrete] Pedido #{pedido.numero_pedido:04d} aguarda decisão há {dias_aberto} dia(s)",
                html, texto,
            )
            self.stdout.write(f"  Lembrete enviado: #{pedido.numero_pedido:04d} — {pedido.titulo[:50]}")

        self.stdout.write(self.style.SUCCESS(
            f"\n{pedidos_parados.count()} lembrete(s) enviado(s) para {destinatarios}."
        ))


def _botao_info(label, valor):
    from core.notifications import _linha_info
    return _linha_info(label, valor)
