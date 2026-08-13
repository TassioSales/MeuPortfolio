"""
Testes do prompt de triagem.

O prompt é o produto: é o texto que o cliente encontra no WhatsApp. Estas
travas descrevem o que ele promete — cada uma existe porque a promessa importa
para alguém do outro lado, ou porque o sistema depende dela para funcionar.

Elas não medem qualidade de conversa; isso só se vê conversando. Medem que as
regras que não podem sumir numa edição continuam lá.
"""

import json

from app.prompts import PROMPT_TRIAGEM_JURIDICA
from app.services.lead_processor import lead_processor


class TestLimitesDoAtendimento:
    """O que a triagem não pode fazer, porque quem responde por isso é o advogado."""

    def test_proibe_dar_parecer_e_estimar_valor(self):
        assert 'dizer se a pessoa "tem direito"' in PROMPT_TRIAGEM_JURIDICA
        assert "estimar valores de indenização" in PROMPT_TRIAGEM_JURIDICA
        assert "prometer resultado" in PROMPT_TRIAGEM_JURIDICA

    def test_proibe_dizer_ao_cliente_que_o_caso_e_pequeno(self):
        """
        A triagem coleta os números que dimensionam o caso — e é justamente por
        isso que ela precisa da proibição explícita. Quem decide se compensa é
        o advogado, com o parecer na mão; a pessoa do outro lado não pode ouvir
        de um robô que o problema dela é pequeno demais.
        """
        assert "não compensa" in PROMPT_TRIAGEM_JURIDICA
        assert "O tamanho do caso não entra no score" in PROMPT_TRIAGEM_JURIDICA

    def test_deixa_claro_que_nao_e_o_advogado(self):
        assert "Você NÃO é o advogado" in PROMPT_TRIAGEM_JURIDICA


class TestFormatoDaConversa:
    def test_uma_pergunta_por_vez(self):
        """
        É WhatsApp. Uma lista de perguntas de uma vez faz a pessoa responder
        uma e esquecer as outras — ou sumir.
        """
        assert "**Uma pergunta por vez.**" in PROMPT_TRIAGEM_JURIDICA

    def test_insiste_no_concreto_quando_a_resposta_vem_vaga(self):
        """
        O que separava a triagem rasa da funda: aceitar "fui demitido e acho
        que foi errado" como se fosse um caso. É o assunto, não o caso.
        """
        assert "não é um caso — é o assunto" in PROMPT_TRIAGEM_JURIDICA
        for vago in ('"quando?"', '"faz tempo"', '"não pagaram"'):
            assert vago in PROMPT_TRIAGEM_JURIDICA

    def test_desiste_em_vez_de_insistir(self):
        """Interrogatório não traz o dado — espanta a pessoa."""
        assert "insistir irrita e não traz o dado" in PROMPT_TRIAGEM_JURIDICA


class TestColetaDosNumeros:
    """
    Sem estes dados o parecer não consegue dizer se o caso comporta o trabalho
    do escritório — e o advogado descobre na primeira consulta.
    """

    def test_pede_o_que_dimensiona_cada_area(self):
        for dado in (
            "último salário",          # trabalhista
            "tempo de casa",
            "quantas \\\npor semana",  # horas extras
            "quanto custou",           # consumidor
            "tempo de contribuição",   # previdenciário
            "bens em comum",           # família
            "valor envolvido",         # cível
        ):
            assert dado.replace("\\\n", "") in PROMPT_TRIAGEM_JURIDICA.replace("\n", " ")

    def test_nao_pergunta_dinheiro_em_caso_criminal(self):
        """Perguntar valores a quem está respondendo processo criminal é surdez."""
        assert "**não pergunte valores**" in PROMPT_TRIAGEM_JURIDICA

    def test_manda_registrar_o_numero_como_veio(self):
        """
        Estimar aqui contamina o parecer: o modelo seguinte lê o número como se
        a pessoa tivesse dito. Recusa é dado; invenção é problema.
        """
        assert "nunca estime, nunca converta" in PROMPT_TRIAGEM_JURIDICA
        assert "Número recusado é dado" in PROMPT_TRIAGEM_JURIDICA


class TestBlocoDeRegistro:
    """O JSON é contrato com o `lead_processor` — se ele mudar de forma, quebra."""

    def _bloco_do_prompt(self) -> dict:
        return lead_processor._extract_json(PROMPT_TRIAGEM_JURIDICA)

    def test_o_exemplo_do_prompt_e_json_valido(self):
        """
        O modelo copia o formato do exemplo. Exemplo que não parseia vira lead
        perdido em silêncio: o `_extract_json` devolve `None` e a qualificação
        simplesmente não acontece.
        """
        assert isinstance(self._bloco_do_prompt(), dict)

    def test_traz_os_campos_que_o_processador_le(self):
        bloco = self._bloco_do_prompt()

        for campo in (
            "nome_cliente",
            "email",
            "score_qualificacao",
            "status_proposto",
            "inconsistencias",
            "problemas_detectados",
        ):
            assert campo in bloco

    def test_traz_os_campos_novos_de_dimensionamento(self):
        bloco = self._bloco_do_prompt()

        assert "dados_economicos" in bloco
        assert "documentos_em_maos" in bloco
        # O exemplo precisa mostrar número com unidade: é o que o parecer lê
        # depois para dimensionar. "2.100" sozinho não diz se é salário ou dívida.
        assert "R$" in bloco["dados_economicos"]

    def test_o_bloco_nunca_deve_aparecer_para_o_cliente(self):
        assert "não aparece para o cliente" in PROMPT_TRIAGEM_JURIDICA
