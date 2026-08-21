"""
Um rascunho de contrato para o advogado editar — não um contrato pronto.

A diferença importa. As cláusulas abaixo são a estrutura usual de um contrato
de honorários trabalhista; o **percentual** está deliberadamente como lacuna
(`____`), porque é decisão comercial do escritório. Um número escrito aqui
viraria obrigação assumida com o cliente por conta de um default de software.

Pela mesma razão o rascunho nasce **inativo**: enquanto alguém não o ler,
editar e ativar, nenhum contrato sai dele.
"""

MODELO_BASE = """# CONTRATO DE PRESTAÇÃO DE SERVIÇOS ADVOCATÍCIOS

**CONTRATANTE:** {{cliente.nome}}, {{cliente.nacionalidade}}, {{cliente.estado_civil}}, {{cliente.profissao}}, portador(a) do RG nº {{cliente.rg}} e inscrito(a) no CPF sob o nº {{cliente.cpf}}, residente e domiciliado(a) em {{cliente.endereco}}, {{cliente.cidade}}/{{cliente.uf}}, CEP {{cliente.cep}}, telefone {{cliente.telefone}}.

**CONTRATADO:** {{escritorio.nome}}, inscrito no CNPJ sob o nº {{escritorio.cnpj}}, com endereço em {{escritorio.endereco}}, neste ato representado por {{escritorio.fundador}}, advogado(a) inscrito(a) na OAB sob o nº {{escritorio.oab}}.

As partes acima identificadas têm entre si justo e contratado o presente instrumento, que se regerá pelas cláusulas seguintes.

**CLÁUSULA 1ª — DO OBJETO**

O CONTRATADO prestará ao CONTRATANTE serviços de advocacia na área de {{caso.area}}, referentes a: {{caso.resumo}}

**CLÁUSULA 2ª — DAS OBRIGAÇÕES DO CONTRATADO**

O CONTRATADO obriga-se a conduzir a causa com zelo e diligência, mantendo o CONTRATANTE informado sobre o andamento do processo, observados os deveres do Estatuto da Advocacia e o Código de Ética e Disciplina da OAB.

**CLÁUSULA 3ª — DAS OBRIGAÇÕES DO CONTRATANTE**

O CONTRATANTE obriga-se a fornecer ao CONTRATADO todos os documentos e informações necessários à defesa de seus interesses, respondendo pela veracidade do que declarar, e a comparecer aos atos processuais para os quais for intimado.

**CLÁUSULA 4ª — DOS HONORÁRIOS**

A título de honorários advocatícios contratuais, o CONTRATANTE pagará ao CONTRATADO o percentual de ____ (____________ por cento) sobre o proveito econômico efetivamente obtido, a ser descontado quando do recebimento.

Os honorários de sucumbência, quando fixados judicialmente, pertencem ao CONTRATADO, nos termos do art. 23 da Lei nº 8.906/94.

**CLÁUSULA 5ª — DAS DESPESAS**

As custas processuais, taxas, emolumentos e despesas com diligências correm por conta do CONTRATANTE, ressalvada a concessão de gratuidade da justiça.

**CLÁUSULA 6ª — DA RESCISÃO**

O presente contrato poderá ser rescindido por qualquer das partes, mediante comunicação escrita, sem prejuízo dos honorários proporcionais aos serviços já prestados.

**CLÁUSULA 7ª — DO FORO**

Fica eleito o foro da comarca de {{escritorio.cidade}} para dirimir eventuais controvérsias oriundas deste contrato.

E por estarem assim justos e contratados, assinam o presente instrumento.

{{data.cidade_e_data}}


____________________________________________
{{cliente.nome}}
CONTRATANTE


____________________________________________
{{escritorio.fundador}} — OAB {{escritorio.oab}}
CONTRATADO
"""

NOME_BASE = "Honorários advocatícios (rascunho)"
