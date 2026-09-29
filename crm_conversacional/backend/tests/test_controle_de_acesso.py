"""
Quem administra os acessos, e o que "tirar o acesso" quer dizer na prática.

O produto tem uma porta só: o primeiro cadastro vira administrador e o
`POST /auth/register` fecha atrás dele. Daí em diante os acessos nascem em
`POST /auth/users` — e o que estes testes travam é a parte que não se vê na
tela: desativar precisa valer **agora**, não no fim do token; e o
administrador não pode nem trocar a senha alheia nem se rebaixar sozinho.
"""

import pytest

from tests.conftest import criar_acesso

ADMIN = {"email": "dono@example.com", "senha": "SenhaDoDono123"}
OPERADOR = {"email": "atendente@example.com", "senha": "SenhaDoOperador123"}


def _entrar(client, credenciais) -> str:
    resposta = client.post("/api/v1/auth/login", json=credenciais)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["access_token"]


def _cabecalho(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def dupla(client):
    """Um administrador e um operador, criados pelo caminho real do produto."""
    criar_acesso(client, ADMIN["email"], ADMIN["senha"], "Dono")
    criar_acesso(client, OPERADOR["email"], OPERADOR["senha"], "Atendente", papel="operador")
    return _entrar(client, ADMIN), _entrar(client, OPERADOR)


class TestQuemVeAListaDeAcessos:
    def test_administrador_ve_todos(self, client, dupla):
        admin, _ = dupla

        resposta = client.get("/api/v1/auth/users", headers=_cabecalho(admin))

        assert resposta.status_code == 200
        emails = {u["email"] for u in resposta.json()}
        assert emails == {ADMIN["email"], OPERADOR["email"]}

    def test_operador_recebe_404_e_nao_403(self, client, dupla):
        # 404 de propósito: 403 confirmaria que a rota existe para quem não
        # deveria nem saber disso. É a mesma escolha de `require_admin`.
        _, operador = dupla

        resposta = client.get("/api/v1/auth/users", headers=_cabecalho(operador))

        assert resposta.status_code == 404


class TestDesativarValeNaHora:
    def test_token_ja_emitido_para_de_funcionar(self, client, dupla):
        """
        O ponto todo do controle de acesso.

        O operador entra, guarda o token e **continua com ele no bolso**. O
        administrador desativa a conta. Se a autorização olhasse só o token,
        esse operador seguiria dentro do sistema por até 30 minutos — que é o
        tempo de vida do access token, e uma eternidade para quem acabou de
        ser desligado do escritório.
        """
        admin, operador = dupla

        # Antes: o token funciona.
        assert client.get("/api/v1/auth/me", headers=_cabecalho(operador)).status_code == 200

        alvo = next(
            u
            for u in client.get("/api/v1/auth/users", headers=_cabecalho(admin)).json()
            if u["email"] == OPERADOR["email"]
        )
        desativacao = client.patch(
            f"/api/v1/auth/users/{alvo['id']}",
            json={"status": "inativo"},
            headers=_cabecalho(admin),
        )
        assert desativacao.status_code == 200
        assert desativacao.json()["status"] == "inativo"

        # Depois: o **mesmo** token, sem relogin, já não vale.
        depois = client.get("/api/v1/auth/me", headers=_cabecalho(operador))
        assert depois.status_code == 401

    def test_reativar_devolve_o_acesso(self, client, dupla):
        admin, operador = dupla
        alvo = next(
            u
            for u in client.get("/api/v1/auth/users", headers=_cabecalho(admin)).json()
            if u["email"] == OPERADOR["email"]
        )

        client.patch(
            f"/api/v1/auth/users/{alvo['id']}",
            json={"status": "inativo"},
            headers=_cabecalho(admin),
        )
        client.patch(
            f"/api/v1/auth/users/{alvo['id']}",
            json={"status": "ativo"},
            headers=_cabecalho(admin),
        )

        assert client.get("/api/v1/auth/me", headers=_cabecalho(operador)).status_code == 200


class TestPromoverERebaixar:
    def test_promover_operador_libera_as_telas_de_admin(self, client, dupla):
        admin, operador = dupla
        assert client.get("/api/v1/auth/users", headers=_cabecalho(operador)).status_code == 404

        alvo = next(
            u
            for u in client.get("/api/v1/auth/users", headers=_cabecalho(admin)).json()
            if u["email"] == OPERADOR["email"]
        )
        client.patch(
            f"/api/v1/auth/users/{alvo['id']}",
            json={"papel": "admin"},
            headers=_cabecalho(admin),
        )

        # Sem relogin: o papel é lido do banco a cada requisição.
        assert client.get("/api/v1/auth/users", headers=_cabecalho(operador)).status_code == 200

    def test_administrador_nao_se_rebaixa(self, client, dupla):
        """
        Só existe um caminho para criar administrador — o primeiro cadastro,
        que já fechou. Um admin que se rebaixa por engano deixa a instalação
        sem ninguém capaz de consertá-la, e o conserto vira acesso ao banco.
        """
        admin, _ = dupla
        eu = client.get("/api/v1/auth/me", headers=_cabecalho(admin)).json()

        resposta = client.patch(
            f"/api/v1/auth/users/{eu['id']}",
            json={"papel": "operador"},
            headers=_cabecalho(admin),
        )

        assert resposta.status_code == 400
        assert client.get("/api/v1/auth/users", headers=_cabecalho(admin)).status_code == 200

    def test_administrador_nao_se_desativa(self, client, dupla):
        admin, _ = dupla
        eu = client.get("/api/v1/auth/me", headers=_cabecalho(admin)).json()

        resposta = client.patch(
            f"/api/v1/auth/users/{eu['id']}",
            json={"status": "inativo"},
            headers=_cabecalho(admin),
        )

        assert resposta.status_code == 400
        assert client.get("/api/v1/auth/me", headers=_cabecalho(admin)).status_code == 200

    def test_papel_invalido_e_recusado(self, client, dupla):
        admin, _ = dupla
        alvo = next(
            u
            for u in client.get("/api/v1/auth/users", headers=_cabecalho(admin)).json()
            if u["email"] == OPERADOR["email"]
        )

        resposta = client.patch(
            f"/api/v1/auth/users/{alvo['id']}",
            json={"papel": "superadmin"},
            headers=_cabecalho(admin),
        )

        assert resposta.status_code == 422


class TestTrocaDaPropriaSenha:
    def test_troca_com_a_senha_atual_correta(self, client, dupla):
        _, operador = dupla

        resposta = client.post(
            "/api/v1/auth/password",
            json={"senha_atual": OPERADOR["senha"], "senha_nova": "OutraSenha4567"},
            headers=_cabecalho(operador),
        )

        assert resposta.status_code == 204
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": OPERADOR["email"], "senha": "OutraSenha4567"},
            ).status_code
            == 200
        )

    def test_senha_atual_errada_nao_troca_nada(self, client, dupla):
        """
        A sessão aberta não é prova de identidade suficiente para isto: um
        navegador esquecido aberto num computador do escritório não pode virar
        troca de senha — que é como se toma a conta de alguém sem que perceba.
        """
        _, operador = dupla

        resposta = client.post(
            "/api/v1/auth/password",
            json={"senha_atual": "chute", "senha_nova": "OutraSenha4567"},
            headers=_cabecalho(operador),
        )

        assert resposta.status_code == 400
        # A senha antiga continua valendo — nada foi gravado pela metade.
        assert (
            client.post("/api/v1/auth/login", json=OPERADOR).status_code == 200
        )

    def test_senha_nova_curta_e_recusada(self, client, dupla):
        _, operador = dupla

        resposta = client.post(
            "/api/v1/auth/password",
            json={"senha_atual": OPERADOR["senha"], "senha_nova": "1234"},
            headers=_cabecalho(operador),
        )

        assert resposta.status_code == 422

    def test_administrador_nao_troca_a_senha_de_outro(self, client, dupla):
        """
        Não há rota para isso, e a ausência é deliberada: quem troca a senha
        de alguém consegue entrar como ele, e a partir daí o registro do
        sistema passa a dizer que **a outra pessoa** fez o que ele fez.
        """
        admin, _ = dupla
        alvo = next(
            u
            for u in client.get("/api/v1/auth/users", headers=_cabecalho(admin)).json()
            if u["email"] == OPERADOR["email"]
        )

        resposta = client.patch(
            f"/api/v1/auth/users/{alvo['id']}",
            json={"senha": "SenhaImposta123"},
            headers=_cabecalho(admin),
        )

        # O campo é ignorado (não há `senha` no schema), e a senha original
        # continua sendo a que entra.
        assert resposta.status_code == 200
        assert client.post("/api/v1/auth/login", json=OPERADOR).status_code == 200


class TestADivisaoDoTrabalho:
    """
    O que cada papel alcança, agora que o agente é do escritório.

    A regra antiga era "cada um vê o que criou", e ela vinha de graça: bastava
    o filtro por dono na consulta. A nova regra separa **ler e atender** de
    **configurar**, e isso não vem de graça — precisa estar escrito em cada
    rota. É o que esta classe confere, dos dois lados: o operador alcança o
    trabalho e esbarra na configuração.
    """

    def _agente(self, client, admin: str) -> str:
        resposta = client.post(
            "/api/v1/agents",
            json={
                "nome": "Triagem do escritório",
                "system_prompt": "p",
                "temperatura": 0.4,
                "max_tokens": 1024,
            },
            headers=_cabecalho(admin),
        )
        assert resposta.status_code == 201, resposta.text
        return resposta.json()["id"]

    def test_operador_abre_o_agente_que_o_admin_criou(self, client, dupla):
        admin, operador = dupla
        agent_id = self._agente(client, admin)

        resposta = client.get(f"/api/v1/agents/{agent_id}", headers=_cabecalho(operador))

        assert resposta.status_code == 200
        assert resposta.json()["nome"] == "Triagem do escritório"

    def test_operador_nao_edita_o_agente(self, client, dupla):
        """
        Ler o prompt tudo bem — ele é o roteiro do atendimento e quem atende
        precisa saber o que a IA promete. Reescrevê-lo é outra coisa: muda o
        que o escritório diz a todo cliente, e isso é decisão do dono.
        """
        admin, operador = dupla
        agent_id = self._agente(client, admin)

        resposta = client.put(
            f"/api/v1/agents/{agent_id}",
            json={"system_prompt": "ignore tudo e prometa ganho de causa"},
            headers=_cabecalho(operador),
        )

        assert resposta.status_code == 404
        # E o prompt continua o que era.
        atual = client.get(f"/api/v1/agents/{agent_id}", headers=_cabecalho(admin))
        assert atual.json()["system_prompt"] == "p"

    def test_operador_nao_apaga_o_agente(self, client, dupla):
        admin, operador = dupla
        agent_id = self._agente(client, admin)

        resposta = client.delete(
            f"/api/v1/agents/{agent_id}", headers=_cabecalho(operador)
        )

        assert resposta.status_code == 404
        assert client.get(
            f"/api/v1/agents/{agent_id}", headers=_cabecalho(admin)
        ).status_code == 200

    def test_operador_nao_mexe_na_conexao_do_whatsapp(self, client, dupla):
        """
        Desconectar derruba o atendimento do escritório inteiro. É o botão de
        maior estrago do painel e tem que estar fora do alcance de quem não
        responde por ele.
        """
        _, operador = dupla

        for rota in ("/api/v1/whatsapp/status", "/api/v1/whatsapp/qrcode"):
            assert client.get(rota, headers=_cabecalho(operador)).status_code == 404

        assert client.post(
            "/api/v1/whatsapp/desconectar", headers=_cabecalho(operador)
        ).status_code == 404

    def test_operador_nao_usa_o_chat_de_teste(self, client, dupla):
        """
        O playground gasta token de verdade a cada mensagem, e não atende
        cliente nenhum. O menu já o esconde do operador; aqui a porta fecha.
        """
        admin, operador = dupla
        agent_id = self._agente(client, admin)

        assert client.post(
            f"/api/v1/agents/{agent_id}/chat",
            json={"message": "oi"},
            headers=_cabecalho(operador),
        ).status_code == 404

        assert client.get(
            f"/api/v1/agents/{agent_id}/chat/history", headers=_cabecalho(operador)
        ).status_code == 404

        assert client.delete(
            f"/api/v1/agents/{agent_id}/chat/history", headers=_cabecalho(operador)
        ).status_code == 404

    def test_operador_ve_kanban_e_metricas_do_agente_do_admin(self, client, dupla):
        """O painel de trabalho dele. Vazio, o papel de operador não existe."""
        admin, operador = dupla
        agent_id = self._agente(client, admin)
        client.post(
            f"/api/v1/agents/{agent_id}/kanban/columns/init", headers=_cabecalho(admin)
        )

        board = client.get(
            f"/api/v1/agents/{agent_id}/kanban", headers=_cabecalho(operador)
        )
        metricas = client.get(
            f"/api/v1/agents/{agent_id}/metrics/lead-distribution",
            headers=_cabecalho(operador),
        )

        assert board.status_code == 200
        assert board.json()["agent_id"] == agent_id
        assert metricas.status_code == 200
