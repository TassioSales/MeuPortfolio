# Conciliação Bancária

Cruza o extrato do banco com o contas a receber, casa o que dá para casar com evidência, e deixa o
resto para revisão — com sugestão de por onde começar.

O fechamento do mês em empresa pequena é feito na mão, no Excel, linha por linha. A parte chata não
é o pagamento exato: é a tarifa que o banco descontou, o depósito único que quitou três boletos, o
pagamento dividido em duas parcelas e o histórico em que o banco escreve `CRED TEF 0002 CONTA 44` e
espera que você adivinhe de quem é o dinheiro.

```
ARQUIVO                situacao      estrategia         conf.   diferenca  motivo
---------------------------------------------------------------------------------------------
L00042 → T00107        divergente    dentro_tolerancia  0.60    -3.50      diferença cabe na tolerância; confira tarifa
L00088 → T00012        conciliado    documento          0.99     0.00      documento 447291 aparece no histórico
L00103 → T15,T16,T17   conciliado    um_para_muitos     0.80     0.00      crédito igual à soma de 3 títulos de MERCADO CENTRAL
L00007 → T00233        conciliado    valor_e_nome       0.85     0.00      valor idêntico e 100% do nome de Padaria do João
```

## Resultado medido

Contra um cenário sintético com gabarito, três sementes diferentes:

| Semente | Pagamentos | Precisão | Cobertura | Casamentos errados | Para revisão |
|---|---|---|---|---|---|
| 42 | 153 | 99,2% | 86,3% | 1 | 31 |
| 7 | 155 | 98,5% | 85,8% | 2 | 31 |
| 2026 | 150 | 98,5% | 88,7% | 2 | 25 |

Os cinco erros das três execuções são **do mesmo cliente com título de valor idêntico**: o cliente
devia dois boletos de R$ 250,00 e o pagamento foi atribuído ao outro. O saldo dele fica correto, só
o número do título troca.

**Zero casamentos atribuindo dinheiro ao cliente errado.** Essa é a métrica que decide se a
ferramenta pode ser usada: uma linha deixada para revisão custa minutos de uma pessoa, um pagamento
lançado no cliente errado entra na contabilidade e aparece meses depois.

Reproduza com `python avaliar.py`.

## Como funciona

Sete estratégias em cascata, da evidência mais forte para a mais fraca. Cada lançamento e cada
título é consumido no máximo uma vez, e cada estratégia só enxerga o que as anteriores deixaram.

| # | Estratégia | Evidência |
|---|---|---|
| 1 | `documento` | O número do boleto aparece no histórico e identifica um título |
| 2 | `apelido` | Um humano já corrigiu esse histórico antes e a ferramenta guardou |
| 3 | `valor_e_data` | Valor idêntico, dentro da janela, e candidato único |
| 4 | `valor_e_nome` | Valor idêntico e o nome do sacado aparece no histórico |
| 5 | `um_para_muitos` | O crédito é a soma exata de até 4 títulos do mesmo cliente |
| 6 | `muitos_para_um` | Vários créditos somam um título — entrada mais parcela |
| 7 | `tolerancia` | Diferença cabe em tarifa ou desconto; entra como **divergente**, nunca conciliado |

A ordem não é arbitrária. Rodar a estratégia fraca antes faria ela consumir um título que a forte
casaria melhor.

### Três decisões que definem a ferramenta

**Ambiguidade não é resolvida no chute.** Dois títulos do mesmo valor na janela e sem nome no
histórico: a ferramenta não casa nenhum. Dois subconjuntos de títulos que somam o mesmo valor: não
casa nenhum. Escolher um deles acertaria metade das vezes, e a metade errada é a que custa caro.

**O extrato tem voz.** Se o histórico diz `PIX RECEBIDO FLORICULTURA JARDIM` e o único título
daquele valor na janela é de outra empresa, a ferramenta recusa. Essa checagem nasceu de erro real:
sem ela, a medição acusava casamento de cliente trocado.

**Todo casamento carrega o motivo.** Quem confere o fechamento precisa saber por que o sistema
juntou aquelas linhas. Conciliação que ninguém consegue auditar não é usada duas vezes.

### O que ele aprende

Quando alguém diz de quem é um histórico opaco, o par fica gravado em SQLite e vale para as próximas
execuções. Não há modelo nem treino: é uma tabela de associação, e o apelido só é gravado quando o
nome do cliente **não** aparecia no histórico — se aparecia, a similaridade já resolveria e a regra
seria peso morto. Apelido gravado errado se remove pela interface.

## Como rodar

No Windows, clique duas vezes em `run.bat`. Ele cria o ambiente virtual, instala as dependências e
abre a interface na porta 8504.

| Comando | O que faz |
|---|---|
| `run.bat` | abre a interface |
| `run.bat testes` | roda os 80 testes |
| `run.bat avaliar` | mede precisão e cobertura contra o gabarito |

No Linux e no macOS é o mesmo, com `./run.sh`.

À mão:

```bash
pip install -r requirements.txt
streamlit run app.py
python -m pytest tests -q
python avaliar.py
```

Não tem os seus arquivos? A aba **Dados de exemplo** gera um extrato OFX e um contas a receber CSV
com os casos difíceis nas proporções em que eles aparecem num mês real.

## Formatos aceitos

**Extrato: OFX**, que todo banco brasileiro exporta. O leitor cobre OFX 1.x, que é SGML e faz
parser XML recusar o arquivo, e OFX 2.x, que é XML de verdade. Aceita ponto e vírgula como separador
decimal, porque os exportadores divergem. Débito é descartado: tarifa e transferência enviada não
quitam título a receber.

**Contas a receber: CSV**, com os nomes de coluna que os ERPs usam — `cliente`, `sacado`,
`razao_social`, `pagador` e `devedor` são a mesma coisa, assim como `vencimento`, `dt_vencimento` e
`vcto`. Obrigar o usuário a renomear coluna antes de usar a ferramenta é onde a maioria desiste.

## Limites

**Só crédito.** Conciliação de pagamentos a fornecedor é outro problema e não está aqui.

**Sem rateio parcial.** Um pagamento a menos que não cabe na tolerância fica para revisão em vez de
ser lançado como quitação parcial. Fazer isso direito exige saber a política de juros e desconto da
empresa, que não está no extrato nem no CSV.

**A combinação de títulos é limitada a 4 por depósito e 12 títulos por cliente na busca.** Acima
disso a busca por soma de subconjuntos cresce rápido demais sem encontrar caso real.

**O gabarito é sintético.** Os números acima medem o motor contra dados gerados com ruído realista,
não contra o extrato de uma empresa de verdade. É honesto tratá-los como limite superior.

## Estrutura

```
core/
  modelos.py        tipos imutáveis do domínio
  normalizacao.py   limpeza do histórico bancário e similaridade de nome
  ofx.py            leitor de OFX 1.x e 2.x
  importacao.py     leitor de CSV com sinônimos de coluna
  regras.py         janela, tolerâncias e limites, com o porquê de cada padrão
  matching.py       o motor: as sete estratégias
  persistencia.py   SQLite com decisões e apelidos aprendidos
  relatorio.py      resumo, tabela de casamentos e pendências
dados_exemplo/
  gerar.py          cenário sintético com gabarito
tests/              80 testes
avaliar.py          mede precisão e cobertura contra o gabarito
app.py              interface Streamlit
```

Python 3.11+. Três dependências: Polars, Streamlit e pytest.
