"""
De que estado vem o telefone.

Não há campo de endereço no cadastro — ninguém pergunta o estado a quem
escreve no WhatsApp, e perguntar seria mais uma pergunta antes de ouvir o
caso. Mas o DDD já está ali, dentro de um número que o sistema guarda desde o
primeiro contato.

Serve para uma decisão concreta: onde o anúncio está funcionando. Um
escritório que atende o Brasil inteiro precisa saber se o dinheiro do Meta Ads
está trazendo gente de São Paulo ou de Roraima.

**O DDD diz a origem da linha, não onde a pessoa mora.** Quem se mudou levou o
número; a portabilidade é entre operadoras, mas o código de área acompanha o
chip. Para decidir campanha isso é bom o bastante; para endereço processual,
não é, e não deve ser usado assim.
"""

from typing import Optional

# Os 67 DDDs em uso no Brasil, por unidade federativa.
DDD_POR_UF = {
    "AC": ("68",),
    "AL": ("82",),
    "AM": ("92", "97"),
    "AP": ("96",),
    "BA": ("71", "73", "74", "75", "77"),
    "CE": ("85", "88"),
    "DF": ("61",),
    "ES": ("27", "28"),
    "GO": ("62", "64"),
    "MA": ("98", "99"),
    "MG": ("31", "32", "33", "34", "35", "37", "38"),
    "MS": ("67",),
    "MT": ("65", "66"),
    "PA": ("91", "93", "94"),
    "PB": ("83",),
    "PE": ("81", "87"),
    "PI": ("86", "89"),
    "PR": ("41", "42", "43", "44", "45", "46"),
    "RJ": ("21", "22", "24"),
    "RN": ("84",),
    "RO": ("69",),
    "RR": ("95",),
    "RS": ("51", "53", "54", "55"),
    "SC": ("47", "48", "49"),
    "SE": ("79",),
    "SP": ("11", "12", "13", "14", "15", "16", "17", "18", "19"),
    "TO": ("63",),
}

UF_POR_DDD = {ddd: uf for uf, ddds in DDD_POR_UF.items() for ddd in ddds}


def uf_do_telefone(numero: Optional[str]) -> Optional[str]:
    """
    A UF de um telefone brasileiro, ou `None`.

    Aceita o que o WhatsApp entrega: `5561999887766`, `+55 (61) 99988-7766`,
    `61999887766`. Tudo que não for dígito é descartado antes.

    Devolve `None` — e não um estado chutado — para número internacional,
    número curto demais e DDD que não existe. Numa tela de "de onde vêm os
    leads", um estado errado é pior que um "não sei": o escritório move
    orçamento de campanha com base nisso.
    """
    if not numero:
        return None

    digitos = "".join(c for c in str(numero) if c.isdigit())

    # O 55 do Brasil, quando presente. Sem ele o número tem 10 ou 11 dígitos
    # (DDD + linha); com ele, 12 ou 13.
    if digitos.startswith("55") and len(digitos) in (12, 13):
        digitos = digitos[2:]

    if len(digitos) not in (10, 11):
        return None

    return UF_POR_DDD.get(digitos[:2])
