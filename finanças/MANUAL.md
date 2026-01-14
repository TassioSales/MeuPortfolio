# Manual do Sistema - MeuPortfolio

Bem-vindo ao **MeuPortfolio**, seu sistema premium de gestão financeira e investimentos. Este documento fornece um guia passo a passo para configuração e uso da plataforma.

---

## 1. Configuração Inicial

### Pré-requisitos
- **Python 3.10+** instalado.
- **Ambiente Virtual (Venv)** recomendado.

### Passo a Passo de Instalação (Desenvolvedor)
1. **Instalar Dependências:** Execute o arquivo `install.bat`. Ele criará o ambiente virtual e instalará todos os pacotes necessários.
2. **Configurações:** Renomeie o arquivo `.env.example` para `.env` e ajuste as chaves se necessário (veja a seção de configuração abaixo).
3. **Popular Dados (Opcional):** Execute `populate_data.bat` para carregar categorias e transações de exemplo.
4. **Executar:** Use o arquivo `run.bat` para iniciar o servidor local.

### Uso do Executável (Usuário Final)
Se você utiliza a versão compilada, basta executar o arquivo `dist/finance_project.exe`. Nenhuma instalação de Python é necessária.

---

## 2. Arquivo de Configuração (.env)

O sistema utiliza um arquivo `.env` para gerenciar variáveis sensíveis e comportamentos globais. Seção por seção:

- **`django_debug`**: `True` para desenvolvimento (mostra erros detalhados), `False` para uso real.
- **`SECRET_KEY`**: Chave de segurança única do seu sistema.
- **Banco de Dados**: Por padrão, o sistema usa SQLite (`db.sqlite3`). Para usar PostgreSQL, descomente as linhas `DB_NAME`, `DB_USER`, etc. no seu `.env`.

---

## 3. Passo a Passo de Uso

### A. Dashboard Principal
Ao logar, você verá o resumo do mês atual:
- **KPIs:** Receitas, Despesas e Saldo Total.
- **Atividades:** Lista rápida das últimas 5 transações.
- **Gráfico de Fluxo:** Comparação visual entre o que entrou e o que saiu nos últimos 6 meses.

### B. Gestão de Transações
1. Vá em **Transações** no menu lateral.
2. Clique em **Adicionar** para registrar um novo gasto ou ganho.
3. Utilize os **Filtros** para buscar por descrição, data ou categoria.
4. **Importação:** Você pode importar transações em massa clicando no botão **Importar**.

### C. Sistema de Investimentos (Patrimônio)
O módulo de investimentos é adaptativo:
1. **Renda Fixa (CDI/SELIC):** Informe a taxa (% do CDI ou Pré-fixada) e o sistema calculará o rendimento projetado e o valor atualizado no Porto Seguro.
2. **Renda Variável (Ações/FIIs):** Digite o ticker (ex: PETR4) e use o botão **Buscar** para obter a cotação em tempo real.
3. **Moedas (Dólar/Euro/BTC):** Selecione a moeda ou digite a sigla para ver o valor convertido e a cotação atual.

### D. Porto Seguro
Este dashboard consolidado mostra seu patrimônio real, somando saldo em conta, valor atualizado de investimentos em renda fixa e total de moedas estrangeiras.

---

## 4. Dicas de Produtividade
- **Teclas de Atalho:** O sistema é responsivo. No mobile, use o ícone de menu no topo.
- **Temas:** Alterne entre os temas **Claro** e **Escuro** clicando no botão "Appearance" na parte inferior da sidebar.
- **Animações:** Todas as telas possuem transições suaves para uma experiência premium.

---

## 5. Suporte e Manutenção
- **Logs:** Problemas podem ser verificados na pasta `logs/`.
- **Backup:** O projeto inclui um script `backup.bat` para salvar seu banco de dados e arquivos importantes.
