# Gerenciador de Ativos

Aplicação para gerenciamento de carteira de investimentos com integração ao Yahoo Finance.

## Funcionalidades

- Acompanhamento de ativos (ações, FIIs, ETFs, etc.)
- Cálculo automático de resultados (lucro/prejuízo)
- Análise de desempenho da carteira
- Relatórios detalhados
- Exportação para Excel
- Interface web amigável

## Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/gerenciador-ativos.git
   cd gerenciador-ativos
   ```

2. Crie um ambiente virtual e ative-o:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   
   # Linux/MacOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

## Configuração

1. Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:
   ```
   FLASK_ENV=development
   SECRET_KEY=sua_chave_secreta_aqui
   ```

## Uso

1. Inicie o servidor de desenvolvimento:
   ```bash
   # No Windows
   set FLASK_APP=src.main:app
   flask run
   
   # No Linux/MacOS
   export FLASK_APP=src.main:app
   flask run
   ```

2. Acesse a aplicação em [http://localhost:5000](http://localhost:5000)

## Estrutura do Projeto

```
gereciador_ativos/
├── data/                   # Dados da aplicação
│   ├── database/           # Arquivos de banco de dados
│   └── exports/            # Arquivos exportados
├── src/                    # Código-fonte
│   ├── config/             # Configurações
│   ├── models/             # Modelos de dados
│   ├── services/           # Lógica de negócios
│   ├── static/             # Arquivos estáticos (CSS, JS, imagens)
│   ├── templates/          # Templates HTML
│   └── utils/              # Utilitários
├── tests/                  # Testes automatizados
├── .env.example            # Exemplo de arquivo de configuração
├── .gitignore
├── README.md
└── requirements.txt        # Dependências do projeto
```

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues e enviar pull requests.

## Autor

Seu Nome - [@seu_usuario](https://github.com/seu-usuario)
