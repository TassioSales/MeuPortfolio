"""
O caso como as telas o veem.

Estava dentro de `routers/chat.py`, onde nasceu — a tela de atendimentos foi a
primeira a mostrar caso. Quando o card do Kanban passou a abrir o mesmo
conteúdo, importar um schema de dentro de outro router deixou de ser aceitável:
router importa router é como duas telas viram uma só sem ninguém decidir isso.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class CasoDoContato(BaseModel):
    """Um assunto trazido por este contato."""

    id: str
    area: Optional[str] = None
    resumo: Optional[str] = None
    # Preenchido só quando a parte não é quem manda a mensagem.
    titular: Optional[str] = None
    score_qualificacao: int = 0
    # Faixa em reais e o veredito do parecer contra o piso do escritório. A
    # faixa vai junto do veredito de propósito: "abaixo do piso" sem número é
    # uma etiqueta que ninguém consegue contestar, e contestar é o trabalho de
    # quem lê.
    valor_estimado_min: Optional[int] = None
    valor_estimado_max: Optional[int] = None
    viabilidade: str = "indeterminado"
    data_abertura: Optional[datetime] = None
    analise_preliminar: Optional[str] = None


class LeadDossie(BaseModel):
    """
    Tudo o que o escritório sabe sobre um contato, numa resposta só.

    Existe porque o card do Kanban mostrava nome, telefone e um número de 0 a
    100 — e o número sozinho não diz nada. Quem abre um card quer saber do que
    se trata, quanto vale e o que fazer primeiro; isso estava tudo gravado e
    não tinha por onde sair.
    """

    lead_id: str
    nome: Optional[str] = None
    email: Optional[str] = None
    phone_number: str
    status_funil: Optional[str] = None
    score_qualificacao: int = 0
    data_criacao: Optional[datetime] = None
    # Para o botão que leva à conversa. Nulo quando o lead veio de um
    # atendimento que não existe mais.
    conversation_id: Optional[str] = None

    # O que a triagem coletou, como a pessoa falou.
    dados_economicos: Optional[str] = None
    documentos_em_maos: Optional[str] = None
    inconsistencias: Optional[str] = None
    problemas_detectados: Optional[str] = None
    recomendacoes: Optional[str] = None

    # Parecer de quando o contato ainda era o caso. Contatos qualificados antes
    # da separação não têm caso arquivado, e o parecer deles não pode sumir da
    # tela por causa disso.
    analise_preliminar: Optional[str] = None
    casos: List[CasoDoContato] = []
