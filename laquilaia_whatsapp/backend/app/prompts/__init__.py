"""
Prompts do produto, versionados junto com o código.

O prompt de um agente vive na coluna `system_prompt` do banco, escrita pelo
painel — e era o único lugar onde ele existia. O texto que define como o
escritório atende, que é o produto, não estava no git: perder o banco era
perder o produto, e não havia como revisar mudança nele nem voltar atrás.

Daqui sai a versão canônica. O painel continua mandando: quem edita pelo painel
está experimentando, e é para experimentar mesmo. O que este módulo garante é
que existe um texto de referência para onde voltar.
"""

from app.prompts.coleta_contrato import BLOCO_DE_COLETA
from app.prompts.triagem_juridica import PROMPT_TRIAGEM_JURIDICA

__all__ = ["BLOCO_DE_COLETA", "PROMPT_TRIAGEM_JURIDICA"]
