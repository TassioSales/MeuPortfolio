"""
A agente recolhendo CPF, RG e endereço na conversa.

**A regra que manda em tudo aqui: nada confia no modelo para completar.** O
bloco JSON traz só o que a pessoa disse, e este módulo grava só o que veio. Um
CPF inventado num contrato é um contrato nulo, e o modelo que inventa não avisa
que inventou.

**E a gravação é acumulativa, nunca destrutiva.** O agente manda o bloco a cada
mensagem com dado novo; um bloco posterior com menos campos não pode apagar o
que um anterior trouxe — senão a última mensagem da conversa zeraria a coleta
inteira.
"""

import pytest
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import Agent, Conversation, DadosDoContrato, Lead
from app.services import coleta_service
from app.services.llm_service import sistema_do_agente


def _bloco(**campos) -> str:
    import json

    corpo = json.dumps({"dados_contrato": campos}, ensure_ascii=False)
    return f"Claro! Já anotei.\n\n```json\n{corpo}\n```"


async def _lead(sufixo: str) -> str:
    async with AsyncSessionLocal() as db:
        db.add(Agent(id=f"ag-{sufixo}", nome="Ag", system_prompt="p",
                     temperatura=0.4, max_tokens=1024, status="ativo"))
        await db.flush()
        db.add(Conversation(id=f"cv-{sufixo}", agent_id=f"ag-{sufixo}",
                            phone_number=f"5561{sufixo}", status="ativa"))
        await db.flush()
        db.add(Lead(id=f"lead-{sufixo}", conversation_id=f"cv-{sufixo}",
                    nome="Maria", phone_number=f"5561{sufixo}"))
        await db.commit()
    return f"lead-{sufixo}"


# ----------------------------------------------------------- o prompt

class TestOBlocoNoPrompt:
    def test_a_coleta_nao_existe_na_triagem(self):
        """
        Instrução que não deve valer agora é instrução que não deve estar lá.
        Deixá-la no prompt base com um "faça só quando..." põe o modelo a um
        mal-entendido de distância de pedir CPF a quem acabou de dizer "oi" —
        que é onde a conversa morre.
        """
        class A:
            system_prompt = "PROMPT"
            nome_atendente = ""

        na_triagem = sistema_do_agente(A(), None, "triagem")
        na_coleta = sistema_do_agente(A(), None, "coleta")

        assert "CPF" not in na_triagem
        assert "CPF" in na_coleta
        assert len(na_coleta) > len(na_triagem)

    def test_o_bloco_proibe_falar_de_honorarios(self):
        """
        Continua sendo decisão comercial do escritório. O percentual está no
        contrato; quem explica condição comercial é o advogado.
        """
        from app.prompts import BLOCO_DE_COLETA

        assert "honorários" in BLOCO_DE_COLETA
        assert "não fale de honorários" in BLOCO_DE_COLETA.lower()


# ---------------------------------------------------------- extração

class TestExtracao:
    def test_le_o_bloco_e_normaliza(self):
        dados = coleta_service.extrair(
            _bloco(cpf="123.456.789-01", uf="df", cep="70000000", cidade="Gama")
        )
        # CPF só com dígitos: assim "123.456.789-01" e "12345678901" são o
        # mesmo CPF no banco.
        assert dados == {
            "cpf": "12345678901", "uf": "DF", "cep": "70000-000", "cidade": "Gama",
        }

    def test_cpf_de_tamanho_errado_e_descartado(self):
        """
        Erro de digitação ou alucinação. Descartar e continuar perguntando é
        melhor que gravar um número que ninguém vai conferir.
        """
        assert coleta_service.extrair(_bloco(cpf="123", cidade="Gama")) == {
            "cidade": "Gama"
        }

    def test_campo_vazio_nao_conta_como_dado(self):
        """
        `""` do modelo quer dizer "não tenho". Deixá-lo passar apagaria o valor
        que uma mensagem anterior trouxe.
        """
        assert coleta_service.extrair(_bloco(rg="", cpf="12345678901")) == {
            "cpf": "12345678901"
        }

    def test_campo_desconhecido_e_ignorado(self):
        assert coleta_service.extrair(_bloco(inventado="x", cidade="Gama")) == {
            "cidade": "Gama"
        }

    def test_sem_bloco_devolve_nada(self):
        assert coleta_service.extrair("Oi, tudo bem?") is None

    def test_bloco_de_qualificacao_nao_e_confundido(self):
        """O bloco da triagem tem outra forma e não pode virar dado civil."""
        texto = '```json\n{"nome_cliente": "Maria", "score_qualificacao": 80}\n```'
        assert coleta_service.extrair(texto) is None

    def test_json_quebrado_num_bloco_nao_esconde_o_outro(self):
        texto = '```json\n{quebrado\n```\n```json\n{"dados_contrato": {"cidade": "Gama"}}\n```'
        assert coleta_service.extrair(texto) == {"cidade": "Gama"}

    def test_uf_invalida_e_descartada(self):
        assert coleta_service.extrair(_bloco(uf="Distrito Federal")) == {}


# ---------------------------------------------------------- gravação

class TestGravacao:
    @pytest.mark.asyncio
    async def test_grava_e_acumula_entre_mensagens(self):
        """
        O agente manda o bloco a cada dado novo. Um bloco posterior com menos
        campos não pode zerar a coleta inteira.
        """
        lead_id = await _lead("g1")

        async with AsyncSessionLocal() as db:
            await coleta_service.gravar(db, lead_id, {"cpf": "12345678901"})
            await db.commit()
        async with AsyncSessionLocal() as db:
            await coleta_service.gravar(db, lead_id, {"cidade": "Gama", "uf": "DF"})
            await db.commit()

        async with AsyncSessionLocal() as db:
            d = (
                await db.execute(
                    select(DadosDoContrato).where(DadosDoContrato.lead_id == lead_id)
                )
            ).scalars().first()

        assert d.cpf == "12345678901"
        assert d.cidade == "Gama" and d.uf == "DF"

    @pytest.mark.asyncio
    async def test_nome_nao_vai_para_a_tabela_de_dados(self):
        """
        O nome mora no lead — é o mesmo que aparece no card e na lista de
        clientes. Duplicá-lo aqui criaria dois nomes que podem divergir.
        """
        lead_id = await _lead("g2")

        async with AsyncSessionLocal() as db:
            registro = await coleta_service.gravar(
                db, lead_id, {"nome": "Maria Aparecida", "cpf": "12345678901"}
            )
            await db.commit()

        assert not hasattr(registro, "nome") or getattr(registro, "nome", None) is None


class TestCompletude:
    def test_falta_o_que_o_contrato_nao_pode_dispensar(self):
        assert set(coleta_service.o_que_falta(None)) == {
            "cpf", "endereco", "cidade", "uf"
        }

    @pytest.mark.asyncio
    async def test_rg_ausente_nao_trava_o_contrato(self):
        """
        Muita gente não sabe o RG de cabeça. Travar por causa dele é perder o
        cliente por um campo que o advogado completa em trinta segundos — ele
        sai como lacuna visível no PDF.
        """
        lead_id = await _lead("c1")

        async with AsyncSessionLocal() as db:
            await coleta_service.gravar(db, lead_id, {
                "cpf": "12345678901", "endereco": "Q 312", "cidade": "Gama", "uf": "DF",
            })
            await db.commit()
            dados = await coleta_service.dados_do_lead(db, lead_id)

        assert dados.rg is None
        assert coleta_service.esta_completo(dados) is True
