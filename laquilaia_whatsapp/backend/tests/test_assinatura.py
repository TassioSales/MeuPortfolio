"""
A assinatura eletrônica, e a rota pública que a recebe.

Este é **o único roteador sem autenticação do sistema**, e por isso os testes
aqui pesam mais que os outros. O que eles travam, em ordem:

1. **O token é a única credencial.** Token errado, vazio ou nulo não chega a
   contrato nenhum — e a resposta é sempre 404, nunca "existe mas venceu",
   que confirmaria a existência para quem adivinhou.
2. **A rota pública não vaza o dossiê.** Quem tem o link tem o contrato, não o
   parecer, não o caso, não o telefone.
3. **O contrato é absorvido na assinatura.** Depois dela o documento existe
   dentro do banco e não depende de mais nada — a pessoa pode sumir.
4. **Assinar duas vezes não é erro.** É o segundo toque no botão.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import (
    Agent,
    ConfiguracaoEscritorio,
    Contrato,
    Conversation,
    Lead,
    Message,
)
from app.main import app
from app.services import assinatura_service
from tests.conftest import criar_acesso

client = TestClient(app)

CORPO = "# CONTRATO\nMaria assina isto. Empresa **Silva & Filhos**."


def _login(sufixo: str, papel: str = "admin") -> tuple[dict, str]:
    email = f"asn-{sufixo}@example.com"
    criar_acesso(client, email, "SenhaSegura123!", f"Pessoa {sufixo}", papel=papel)
    r = client.post(
        "/api/v1/auth/login", json={"email": email, "senha": "SenhaSegura123!"}
    )
    cabecalho = {"Authorization": f"Bearer {r.json()['access_token']}"}
    eu = client.get("/api/v1/auth/me", headers=cabecalho).json()
    return cabecalho, eu["id"]


async def _cenario(sufixo: str, dono: str, com_token: bool = True) -> tuple[str, str]:
    """Um contrato pronto para assinar. Devolve (contrato_id, token)."""
    token = assinatura_service.novo_token() if com_token else None
    async with AsyncSessionLocal() as db:
        db.add(ConfiguracaoEscritorio(id="unica", nome="Sales Advocacia"))
        db.add(Agent(id=f"ag-{sufixo}", user_id=dono, nome="Ag", system_prompt="p",
                     temperatura=0.4, max_tokens=1024, status="ativo"))
        await db.flush()
        db.add(Conversation(id=f"cv-{sufixo}", agent_id=f"ag-{sufixo}",
                            phone_number=f"5561{sufixo}", status="ativa"))
        await db.flush()
        db.add(Lead(id=f"lead-{sufixo}", conversation_id=f"cv-{sufixo}",
                    nome="Maria Aparecida da Silva", phone_number=f"5561{sufixo}"))
        await db.flush()
        db.add(
            Contrato(
                id=f"k-{sufixo}", lead_id=f"lead-{sufixo}", corpo=CORPO,
                status="enviado" if com_token else "gerado",
                token_assinatura=token,
                token_expira_em=(
                    datetime.utcnow() + timedelta(days=7) if com_token else None
                ),
                data_envio=datetime.utcnow() if com_token else None,
            )
        )
        await db.commit()
    return f"k-{sufixo}", token


def _assinar(token: str, nome="Maria Aparecida da Silva", aceite=True, png=None, **kwargs):
    return client.post(
        f"/api/v1/assinatura/{token}",
        json={"nome": nome, "aceite": aceite, "assinatura_png": png},
        **kwargs,
    )


# ------------------------------------------------------------------ o token

class TestOToken:
    def test_tem_entropia_de_credencial(self):
        # 32 bytes em base64url. Não é decoração: este valor é a única coisa
        # entre um estranho e o contrato de alguém.
        tokens = {assinatura_service.novo_token() for _ in range(200)}
        assert len(tokens) == 200
        assert all(len(t) >= 40 for t in tokens)

    def test_token_inexistente_da_404(self):
        assert client.get("/api/v1/assinatura/nao-existe").status_code == 404

    @pytest.mark.asyncio
    async def test_contrato_sem_token_nao_e_alcancavel(self):
        """
        A coluna aceita nulo — contrato gerado e não enviado. Um `WHERE token
        IS NULL` devolveria justamente os que ninguém deveria alcançar.
        """
        _, dono = _login("t1")
        await _cenario("t1", dono, com_token=False)

        assert client.get("/api/v1/assinatura/").status_code in (404, 405)
        assert client.get("/api/v1/assinatura/None").status_code == 404
        assert client.get("/api/v1/assinatura/null").status_code == 404

    @pytest.mark.asyncio
    async def test_link_vencido_responde_404_e_nao_410(self):
        """
        Para quem adivinhou o token, "venceu" é confirmação de que existe.
        """
        _, dono = _login("t2")
        contrato_id, token = await _cenario("t2", dono)
        async with AsyncSessionLocal() as db:
            c = (await db.execute(select(Contrato))).scalars().first()
            c.token_expira_em = datetime.utcnow() - timedelta(minutes=1)
            await db.commit()

        assert client.get(f"/api/v1/assinatura/{token}").status_code == 404
        assert _assinar(token).status_code == 404


# ------------------------------------------------------------- o que vaza

class TestOQueAPaginaEntrega:
    @pytest.mark.asyncio
    async def test_entrega_o_contrato_e_nada_do_dossie(self):
        _, dono = _login("v1")
        _, token = await _cenario("v1", dono)

        corpo = client.get(f"/api/v1/assinatura/{token}").json()

        assert corpo["corpo"] == CORPO
        assert corpo["nome_do_cliente"] == "Maria Aparecida da Silva"
        assert corpo["nome_do_escritorio"] == "Sales Advocacia"
        # O que **não** pode estar aí: telefone, id do lead, parecer, caso.
        texto = str(corpo)
        assert "5561" not in texto
        assert "lead" not in corpo


# ------------------------------------------------------------- assinar

class TestAssinar:
    @pytest.mark.asyncio
    async def test_assina_e_registra_a_trilha_de_prova(self):
        _, dono = _login("a1")
        contrato_id, token = await _cenario("a1", dono)

        with patch("app.routers.assinatura._agendar_confirmacao"):
            r = _assinar(token, headers={"User-Agent": "Mozilla/5.0 (Android 14)"})

        assert r.status_code == 200
        assert r.json()["ja_assinado"] is True

        async with AsyncSessionLocal() as db:
            c = (await db.execute(select(Contrato))).scalars().first()

        assert c.status == "assinado"
        assert c.assinado_nome == "Maria Aparecida da Silva"
        assert c.data_assinatura is not None
        assert c.assinado_user_agent and "Android" in c.assinado_user_agent
        assert c.assinado_ip
        # O hash amarra a assinatura a **este** texto.
        assert c.hash_documento == assinatura_service.hash_do_documento(CORPO)

    @pytest.mark.asyncio
    async def test_absorve_o_pdf_no_mesmo_momento(self):
        """
        O ponto do recurso inteiro: depois disto o documento não depende de
        link, de nuvem nem de a pessoa continuar por perto.
        """
        _, dono = _login("a2")
        contrato_id, token = await _cenario("a2", dono)

        with patch("app.routers.assinatura._agendar_confirmacao"):
            _assinar(token)

        async with AsyncSessionLocal() as db:
            c = (await db.execute(select(Contrato))).scalars().first()

        assert c.pdf_assinado and c.pdf_assinado.startswith(b"%PDF-")

    @pytest.mark.asyncio
    async def test_sem_aceite_nao_assina(self):
        """Aceite é ato, não default."""
        _, dono = _login("a3")
        _, token = await _cenario("a3", dono)

        assert _assinar(token, aceite=False).status_code == 422

        async with AsyncSessionLocal() as db:
            c = (await db.execute(select(Contrato))).scalars().first()
        assert c.data_assinatura is None

    @pytest.mark.asyncio
    async def test_nome_curto_e_recusado(self):
        _, dono = _login("a4")
        _, token = await _cenario("a4", dono)
        assert _assinar(token, nome="Jo").status_code == 422

    @pytest.mark.asyncio
    async def test_assinar_duas_vezes_nao_e_erro(self):
        """
        É o segundo toque no botão, ou o link aberto de novo. Recusar
        assustaria quem já assinou — e a primeira assinatura tem de prevalecer.
        """
        _, dono = _login("a5")
        _, token = await _cenario("a5", dono)

        with patch("app.routers.assinatura._agendar_confirmacao"):
            primeira = _assinar(token)
            async with AsyncSessionLocal() as db:
                c = (await db.execute(select(Contrato))).scalars().first()
                quando = c.data_assinatura
            segunda = _assinar(token, nome="Outra Pessoa Qualquer")

        assert primeira.status_code == 200 and segunda.status_code == 200

        async with AsyncSessionLocal() as db:
            c = (await db.execute(select(Contrato))).scalars().first()
        assert c.assinado_nome == "Maria Aparecida da Silva"
        assert c.data_assinatura == quando

    @pytest.mark.asyncio
    async def test_o_link_morre_com_a_assinatura(self):
        """O endereço não pode continuar abrindo um formulário do que já foi."""
        _, dono = _login("a6")
        _, token = await _cenario("a6", dono)

        with patch("app.routers.assinatura._agendar_confirmacao"):
            _assinar(token)

        # Continua abrindo para **ler**, porque quem assinou volta ao link.
        r = client.get(f"/api/v1/assinatura/{token}")
        assert r.status_code == 200 and r.json()["ja_assinado"] is True

        async with AsyncSessionLocal() as db:
            c = (await db.execute(select(Contrato))).scalars().first()
        assert assinatura_service.expirado(c) is True

    @pytest.mark.asyncio
    async def test_ip_vem_do_cabecalho_do_tunel(self):
        """
        Atrás do Cloudflare o IP do socket é o do túnel, igual para todo mundo.
        Sem ler `CF-Connecting-IP`, a trilha de prova registraria sempre o
        mesmo endereço.
        """
        _, dono = _login("a7")
        _, token = await _cenario("a7", dono)

        with patch("app.routers.assinatura._agendar_confirmacao"):
            _assinar(token, headers={"CF-Connecting-IP": "189.45.12.7"})

        async with AsyncSessionLocal() as db:
            c = (await db.execute(select(Contrato))).scalars().first()
        assert c.assinado_ip == "189.45.12.7"


class TestOrabisco:
    """
    A assinatura desenhada com o dedo.

    Juridicamente ela não acrescenta nada — o que prova a assinatura é a
    trilha. Mas o dono abriu o primeiro contrato assinado de verdade e disse
    "não assinou nada ali": um contrato sem nada escrito na linha **não parece
    assinado**, e quem recebe fica sem saber se valeu.

    Como é entrada pública, nada aqui confia no que chega.
    """

    def _png(self, extra: bytes = b"x" * 100) -> str:
        import base64

        bruto = b"\x89PNG\r\n\x1a\n" + extra
        return "data:image/png;base64," + base64.b64encode(bruto).decode()

    def test_png_valido_e_aceito(self):
        assert assinatura_service.png_da_assinatura(self._png()) is not None

    def test_o_que_nao_e_png_e_recusado(self):
        """Guardar o que o cliente disse ser imagem é como se serve upload malicioso."""
        import base64

        gif = "data:image/png;base64," + base64.b64encode(b"GIF89a...").decode()
        assert assinatura_service.png_da_assinatura(gif) is None
        assert assinatura_service.png_da_assinatura("data:image/jpeg;base64,abc") is None
        assert assinatura_service.png_da_assinatura("<script>") is None
        assert assinatura_service.png_da_assinatura(None) is None

    def test_grande_demais_e_recusado_antes_de_decodificar(self):
        """Sem teto, um POST de 30 KB alocaria dezenas de MB ao decodificar."""
        enorme = "data:image/png;base64," + "A" * (
            assinatura_service.LIMITE_DA_ASSINATURA * 4
        )
        assert assinatura_service.png_da_assinatura(enorme) is None

    @pytest.mark.asyncio
    async def test_assina_com_desenho_e_ele_entra_no_pdf(self):
        _, dono = _login("r1")
        _, token = await _cenario("r1", dono)

        with patch("app.routers.assinatura._agendar_confirmacao"):
            r = _assinar(token, png=self._png())
        assert r.status_code == 200

        async with AsyncSessionLocal() as db:
            c = (await db.execute(select(Contrato))).scalars().first()

        assert c.assinatura_imagem is not None
        assert c.assinatura_imagem.startswith(b"\x89PNG")
        assert c.pdf_assinado.startswith(b"%PDF-")

    @pytest.mark.asyncio
    async def test_assina_sem_desenho_continua_valendo(self):
        """
        Navegador sem canvas, mouse ruim, mão trêmula. O que prova a
        assinatura é a trilha — travar nela trocaria o essencial pelo enfeite.
        """
        _, dono = _login("r2")
        _, token = await _cenario("r2", dono)

        with patch("app.routers.assinatura._agendar_confirmacao"):
            r = _assinar(token)
        assert r.status_code == 200

        async with AsyncSessionLocal() as db:
            c = (await db.execute(select(Contrato))).scalars().first()

        assert c.assinatura_imagem is None
        assert c.status == "assinado" and c.pdf_assinado

    @pytest.mark.asyncio
    async def test_desenho_invalido_nao_derruba_a_assinatura(self):
        """
        Recusa silenciosa: o contrato vale sem o desenho, e derrubar uma
        assinatura legítima porque o canvas de um navegador exótico produziu
        algo diferente seria o pior desfecho.
        """
        _, dono = _login("r3")
        _, token = await _cenario("r3", dono)

        with patch("app.routers.assinatura._agendar_confirmacao"):
            r = _assinar(token, png="data:image/png;base64,!!!nao-e-base64!!!")

        assert r.status_code == 200
        async with AsyncSessionLocal() as db:
            c = (await db.execute(select(Contrato))).scalars().first()
        assert c.status == "assinado" and c.assinatura_imagem is None

    def test_pdf_com_desenho_ilegivel_ainda_sai(self):
        """Um contrato não pode deixar de existir por causa de uma figura."""
        from app.services import contrato_service

        pdf = contrato_service.em_pdf(
            "# CONTRATO\nTexto.\n\n____________________\nFulano",
            rabisco=b"\x89PNG\r\n\x1a\nnao-e-uma-imagem-de-verdade",
        )
        assert pdf.startswith(b"%PDF-")


# ----------------------------------------------------- confirmação no chat

class TestConfirmacaoNoChat:
    @pytest.mark.asyncio
    async def test_avisa_no_whatsapp_e_grava_na_conversa(self):
        """
        Sem isto o cliente clica num botão e nada acontece no lugar onde ele
        conversa com o escritório — e a conversa não registra que houve
        assinatura.
        """
        _, dono = _login("c1")
        _, token = await _cenario("c1", dono)

        with patch(
            "app.routers.assinatura.whatsapp_service.send_message",
            new=AsyncMock(return_value={"success": True}),
        ) as enviar:
            with patch("app.routers.assinatura._agendar_confirmacao"):
                _assinar(token)

            # A confirmação roda em tarefa própria, largada depois do commit.
            # Aqui ela é chamada direto: esperar uma tarefa que ninguém
            # aguarda é o caminho para a suíte travar no TRUNCATE do teardown.
            from app.routers.assinatura import _confirmar_no_whatsapp

            await _confirmar_no_whatsapp("lead-c1", "Maria Aparecida da Silva")

        assert enviar.await_count == 1
        assert "Maria" in enviar.await_args.kwargs["message_text"]

        async with AsyncSessionLocal() as db:
            msgs = (await db.execute(select(Message))).scalars().all()

        assert len(msgs) == 1
        # Nem cliente nem IA: o histórico do modelo trata tudo que não é
        # "user" como o escritório falando.
        assert msgs[0].remetente == "sistema"

    @pytest.mark.asyncio
    async def test_evolution_fora_do_ar_nao_desfaz_a_assinatura(self):
        """
        O contrato já está assinado e guardado. O que se perde é o aviso.
        """
        _, dono = _login("c2")
        _, token = await _cenario("c2", dono)

        with patch("app.routers.assinatura._agendar_confirmacao"):
            r = _assinar(token)

        with patch(
            "app.routers.assinatura.whatsapp_service.send_message",
            new=AsyncMock(side_effect=Exception("Evolution fora do ar")),
        ):
            from app.routers.assinatura import _confirmar_no_whatsapp

            await _confirmar_no_whatsapp("lead-c2", "Maria")

        assert r.status_code == 200
        async with AsyncSessionLocal() as db:
            c = (await db.execute(select(Contrato))).scalars().first()
        assert c.status == "assinado" and c.pdf_assinado


# --------------------------------------------------- gerar link e enviar

class TestEnvio:
    @pytest.mark.asyncio
    async def test_gerar_link_renova_e_invalida_o_anterior(self):
        """Dois endereços vivos para o mesmo contrato é um a mais para vazar."""
        cabecalho, dono = _login("e1")
        contrato_id, antigo = await _cenario("e1", dono)

        r = client.post(f"/api/v1/contratos/{contrato_id}/link", headers=cabecalho)
        assert r.status_code == 200
        novo = r.json()["link"].rsplit("/", 1)[-1]

        assert novo != antigo
        assert client.get(f"/api/v1/assinatura/{antigo}").status_code == 404
        assert client.get(f"/api/v1/assinatura/{novo}").status_code == 200

    @pytest.mark.asyncio
    async def test_envia_pelo_whatsapp_e_grava_a_mensagem(self):
        cabecalho, dono = _login("e2")
        contrato_id, _ = await _cenario("e2", dono)

        with patch(
            "app.routers.contratos.whatsapp_service.send_message",
            new=AsyncMock(return_value={"success": True}),
        ) as enviar:
            r = client.post(f"/api/v1/contratos/{contrato_id}/enviar", headers=cabecalho)

        assert r.status_code == 200 and r.json()["enviado"] is True
        texto = enviar.await_args.kwargs["message_text"]
        assert r.json()["link"] in texto
        assert "Maria" in texto

        async with AsyncSessionLocal() as db:
            msgs = (await db.execute(select(Message))).scalars().all()
        assert len(msgs) == 1 and msgs[0].remetente == "sistema"

    @pytest.mark.asyncio
    async def test_evolution_recusando_nao_deixa_link_orfao(self):
        """
        Link gerado e não entregue é link que vence sem ninguém ter recebido —
        e uma mensagem gravada que nunca chegou faria a transcrição mentir.
        """
        cabecalho, dono = _login("e3")
        contrato_id, antigo = await _cenario("e3", dono)

        with patch(
            "app.routers.contratos.whatsapp_service.send_message",
            new=AsyncMock(return_value={"success": False}),
        ):
            r = client.post(f"/api/v1/contratos/{contrato_id}/enviar", headers=cabecalho)

        assert r.status_code == 422

        async with AsyncSessionLocal() as db:
            msgs = (await db.execute(select(Message))).scalars().all()
            c = (await db.execute(select(Contrato))).scalars().first()

        assert msgs == []
        # O token anterior continua valendo: o rollback desfez a troca.
        assert c.token_assinatura == antigo

    @pytest.mark.asyncio
    async def test_contrato_assinado_nao_e_reenviado(self):
        cabecalho, dono = _login("e4")
        contrato_id, token = await _cenario("e4", dono)

        with patch("app.routers.assinatura._agendar_confirmacao"):
            _assinar(token)

        assert client.post(
            f"/api/v1/contratos/{contrato_id}/link", headers=cabecalho
        ).status_code == 422

    def test_anonimo_nao_gera_link(self):
        assert client.post("/api/v1/contratos/x/link").status_code == 401
        assert client.post("/api/v1/contratos/x/enviar").status_code == 401


class TestPdfDoAssinado:
    @pytest.mark.asyncio
    async def test_devolve_o_arquivo_guardado_e_nao_um_redesenho(self):
        """
        O que a pessoa viu e aceitou foi *aquele* arquivo. Documento que se
        regenera não é documento.
        """
        cabecalho, dono = _login("p1")
        contrato_id, token = await _cenario("p1", dono)

        with patch("app.routers.assinatura._agendar_confirmacao"):
            _assinar(token)

        async with AsyncSessionLocal() as db:
            c = (await db.execute(select(Contrato))).scalars().first()
            guardado = c.pdf_assinado

        r = client.get(f"/api/v1/contratos/{contrato_id}/pdf", headers=cabecalho)
        assert r.status_code == 200
        assert r.content == guardado
