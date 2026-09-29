"""Telefone brasileiro em forma legível."""

from typing import Optional


def formatar_telefone_br(numero: Optional[str]) -> Optional[str]:
    """
    `5561999887766` vira `(61) 99988-7766`.

    Número que não couber no formato brasileiro sai como veio: inventar
    parênteses num número internacional só torna o erro mais difícil de ver.
    """
    if not numero:
        return None

    digitos = "".join(c for c in str(numero) if c.isdigit())
    if digitos.startswith("55") and len(digitos) in (12, 13):
        digitos = digitos[2:]

    if len(digitos) == 11:
        return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
    if len(digitos) == 10:
        return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"
    return numero
