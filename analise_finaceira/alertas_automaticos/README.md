# Módulo de Alertas Automáticos

Este módulo é responsável por analisar transações financeiras e gerar alertas automáticos com base em regras pré-definidas, como detecção de valores atípicos usando Z-Score.

## Estrutura do Projeto

```
alertas_automaticos/
├── src/
│   ├── __init__.py         # Inicialização do pacote
│   ├── config.py           # Configurações do módulo
│   ├── analyse.py          # Lógica de análise de dados
│   ├── alert_service.py    # Gerenciamento de alertas no banco de dados
│   └── alertasAutomaticos.py # Ponto de entrada para execução das análises
└── README.md               # Documentação
```

## Funcionalidades

- **Análise de Z-Score por categoria**: Detecta valores atípicos nas transações financeiras agrupadas por categoria e tipo.
- **Gerenciamento de Alertas**: Salva, atualiza e consulta alertas no banco de dados.
- **Tratamento de Erros**: Tratamento robusto de erros e logging detalhado.
- **Configuração Flexível**: Parâmetros ajustáveis para personalizar o comportamento das análises.

## Requisitos

- Python 3.8+
- Bibliotecas Python:
  - pandas
  - numpy
  - scipy
  - sqlite3 (incluído na biblioteca padrão do Python)

## Instalação

1. Clone o repositório:
   ```bash
   git clone <url-do-repositório>
   cd analise_finaceira
   ```

2. Instale as dependências:
   ```bash
   pip install pandas numpy scipy
   ```

## Como Usar

### Executando Análises

Para executar as análises e gerar alertas, utilize o script `alertasAutomaticos.py`:

```python
from alertas_automaticos.src.alertasAutomaticos import GerenciadorAlertas

# Inicializa o gerenciador
gerenciador = GerenciadorAlertas()

# Executa as análises e salva os alertas
total_alertas = gerenciador.executar_analise()
print(f"Foram gerados {total_alertas} alertas.")
```

### Consultando Alertas

Para consultar os alertas gerados:

```python
from alertas_automaticos.src.alert_service import alert_service

# Obtém a primeira página de alertas (20 itens por página)
resultado = alert_service.obter_alertas(pagina=1, itens_por_pagina=20)

# Exibe os alertas
for alerta in resultado['alertas']:
    print(f"{alerta['titulo']} - {alerta['descricao']}")
```

### Testando o Módulo

Um script de teste está disponível na raiz do projeto:

```bash
python testar_alertas_automaticos.py
```

## Configuração

As configurações do módulo podem ser ajustadas no arquivo `alertas_automaticos/src/config.py`:

```python
# Configurações gerais
CONFIG = {
    'zscore_limite': 3.0,  # Limite para considerar um valor como outlier
    'min_transacoes_grupo': 3,  # Número mínimo de transações por grupo para análise
    'db_path': 'caminho/para/seu/banco.db'  # Caminho para o banco de dados
}
```

## Logs

Os logs são gerados usando o módulo `logger.py` localizado em `D:/Github/MeuPortfolio/analise_finaceira/logger.py`. Certifique-se de que este arquivo esteja acessível.

## Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Commit suas alterações (`git commit -am 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para mais detalhes.
