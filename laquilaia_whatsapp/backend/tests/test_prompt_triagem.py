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

    def test_proibe_prometer_e_cravar_valor(self):
        assert "prometer resultado, ganho ou prazo de processo" in PROMPT_TRIAGEM_JURIDICA
        assert "cravar valor de indenização" in PROMPT_TRIAGEM_JURIDICA
        assert "vai ganhar" in PROMPT_TRIAGEM_JURIDICA

    def test_proibe_falar_de_honorarios(self):
        """
        Quanto o escritório cobra é decisão comercial dele, não do prompt.
        Um número inventado aqui vira compromisso assumido com o cliente.
        """
        assert "falar de honorários" in PROMPT_TRIAGEM_JURIDICA

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


class TestInformarComAtribuicao:
    """
    O ponto que mudou o atendimento inteiro.

    Antes o prompt proibia dizer à pessoa o que estava em jogo, e o resultado
    era um atendimento que só perguntava: ela contava dois anos sem carteira e
    recebia outra pergunta. Agora informa — sempre atribuindo ao advogado.
    """

    def test_manda_informar_em_vez_de_se_esconder(self):
        assert "Não se esconda atrás do advogado" in PROMPT_TRIAGEM_JURIDICA
        assert "não está atendendo, está empurrando" in PROMPT_TRIAGEM_JURIDICA

    def test_exige_a_atribuicao_na_mesma_mensagem(self):
        """
        Informar sem atribuir compromete quem assina. É a diferença entre
        "você tem direito a R$ 30 mil" e "em casos assim entram X e Y; quem
        confirma o seu é o advogado".
        """
        assert "a atribuição, na mesma mensagem" in PROMPT_TRIAGEM_JURIDICA
        assert "Quem confirma" in PROMPT_TRIAGEM_JURIDICA

    def test_o_espelho_existe_e_tem_os_quatro_passos(self):
        """
        A mensagem que devolve o que foi entendido e explica o que está em
        jogo. Sem ela, a parte consultiva vira intenção sem lugar no roteiro.
        """
        assert "**4. O espelho.**" in PROMPT_TRIAGEM_JURIDICA
        assert "atribua ao advogado, na mesma mensagem" in PROMPT_TRIAGEM_JURIDICA

    def test_manda_citar_so_o_que_os_fatos_sustentam(self):
        """Listar todas as verbas em todo caso vira folheto."""
        assert "só o que os fatos sustentam" in PROMPT_TRIAGEM_JURIDICA

    def test_tem_vocabulario_para_informar(self):
        """
        Sem a lista, o modelo inventa nome de verba ou fica no genérico. Ela é
        o repertório, não um roteiro para recitar inteiro.
        """
        for verba in (
            "reconhecimento de vínculo",
            "multa de 40%",
            "horas extras",
            "adicional noturno",
            "insalubridade",
            "dano moral",
        ):
            assert verba in PROMPT_TRIAGEM_JURIDICA


class TestApenasTrabalhista:
    def test_o_escritorio_e_de_trabalhista(self):
        assert "exclusivamente causas trabalhistas" in PROMPT_TRIAGEM_JURIDICA

    def test_nao_oferece_menu_de_areas(self):
        """
        Perguntar "seu caso é sobre o quê?" a quem escreveu por causa de uma
        demissão é burocracia. O menu servia a um escritório generalista.
        """
        assert "Não ofereça menu de áreas" in PROMPT_TRIAGEM_JURIDICA
        assert "Previdenciário (INSS" not in PROMPT_TRIAGEM_JURIDICA

    def test_outro_assunto_nao_e_dispensado_na_porta(self):
        """
        Quem chega com divórcio não pode levar um "não é aqui" e ficar sem
        resposta: registra-se o contato e um humano indica o caminho.
        """
        assert "não a dispense" in PROMPT_TRIAGEM_JURIDICA
        assert "alguém retorna para" in PROMPT_TRIAGEM_JURIDICA
        assert "nao_qualificado" in PROMPT_TRIAGEM_JURIDICA


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

    def test_pede_o_que_dimensiona_um_caso_trabalhista(self):
        um_paragrafo = PROMPT_TRIAGEM_JURIDICA.replace("\n", " ")
        for dado in (
            "último salário",
            "tempo de casa",
            "quantas por semana",       # horas extras
            "carteira assinada",
            "salário por fora",
            "o que já foi pago",
        ):
            assert dado in um_paragrafo

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
