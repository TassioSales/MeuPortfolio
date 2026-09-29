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
Se você utiliza a versão compilada, basta executar o arquivo `dist/finance_project.exe`. 

#### 📱 Acesso pelo Celular/Tablet
O sistema agora é responsivo e acessível em rede:
1. Inicie o sistema no seu computador.
2. Observe a mensagem no terminal: **"Acesso na Rede (Celular/Tablet): http://192.168.x.x:8080"**.
3. No seu celular, conectado à mesma rede Wi-Fi, abra o navegador e digite esse endereço.
4. O design se ajustará automaticamente para a tela do seu aparelho.

---

## 2. Arquivo de Configuração (.env)

O sistema utiliza um arquivo `.env` para gerenciar variáveis sensíveis e comportamentos globais. Seção por seção:

- **`django_debug`**: `True` para desenvolvimento (mostra erros detalhados), `False` para uso real.
- **`SECRET_KEY`**: Chave de segurança única do seu sistema.
- **Banco de Dados**: Por padrão, o sistema usa SQLite (`db.sqlite3`). Para usar PostgreSQL, descomente as linhas `DB_NAME`, `DB_USER`, etc. no seu `.env`.

---

## 3. Passo a Passo de Uso

### A. Dashboard Principal
- **Filtros:** no topo, escolha o período (Mês, 3/6/12 meses, Ano, Tudo ou Personalizado), o tipo e uma ou mais categorias. Em **Mais filtros** ficam forma de pagamento, conta, faixa de valor e as chaves "Parcelas de empréstimo" e "Aportes em investimento como despesa". O dashboard lembra o último filtro, mas sempre abre no mês atual. **Limpar tudo** volta ao padrão.
- **Linha 1 — período filtrado:** Receitas, Despesas (com quanto é empréstimo e cartão), Resultado (com taxa de poupança) e Saldo projetado para o fim do período. O selo colorido compara com o período anterior: verde quando a mudança é boa, vermelho quando é ruim.
- **Linha 2 — posição patrimonial:** Caixa hoje, Investido, Dívida de empréstimos e **Patrimônio líquido** (caixa + investido − dívida). Essa linha não muda com os filtros.
- **Categoria selecionada:** ao filtrar uma única categoria aparece o painel dela: total, % das despesas, orçamento, 12 meses e quebra por subcategoria.
- **Atividades:** a aba **Recentes** mostra o que você lançou por último, de qualquer mês. Parcelas de uma mesma compra aparecem juntas ("5x de R$ 244,13"). **A vencer** lista os próximos 15 dias; **Maiores** lista as maiores despesas do período.
- **Gráficos:** receitas × despesas por mês (os meses futuros aparecem mais claros), despesas por categoria (clique numa fatia para filtrar), gasto acumulado comparado com o período anterior, o que já está comprometido nos próximos 12 meses, evolução do caixa e da dívida, formas de pagamento e orçamentos.

### B. Gestão de Transações
1. Vá em **Transações** no menu lateral.
2. Clique em **Adicionar** para registrar um novo gasto ou ganho. No **Crédito**, o valor é dividido em parcelas que somam exatamente o total.
3. Use os **filtros** (os mesmos do dashboard, mais busca, origem e "só previstos/realizados"). Os **KPIs** do topo valem para o filtro inteiro, não só para a página: receitas, despesas, saldo, nº de lançamentos, ticket médio, média diária, maior despesa e a variação em relação ao período anterior.
4. **Uma categoria selecionada** mostra o total só dela, incluindo as subcategorias.
5. Clique no cabeçalho **Data, Descrição, Valor ou Lançado** para ordenar. Escolha 25, 50 ou 100 itens por página.
6. **Em massa:** marque as linhas para excluir ou trocar a categoria, a forma de pagamento ou a conta.
7. **Parcelas e recorrências:** ao editar ou excluir, escolha "só este", "este e os próximos" ou "todas as parcelas".
8. **Exportar** baixa em CSV ou Excel exatamente o filtro atual. **Duplicar** abre um lançamento novo já preenchido.
9. **Previsto** = data futura; **realizado** = data até hoje.

### B2. Empréstimos
- As parcelas previstas entram automaticamente nas **despesas** de cada mês, na categoria "Empréstimos": dashboard, transações, relatórios e fluxo de caixa.
- **Empréstimo informal:** deixe **Nº de Parcelas = 0**. Para definir à mão quanto vai pagar por mês, preencha **Parcela combinada**. Esse valor substitui o cálculo automático em qualquer modalidade. Com juros 0 e sem parcela combinada, nada é previsto e você registra cada pagamento no valor que quiser.
- **Registrar pagamento** converte a parcela prevista do mês em realizada, sem duplicar, e recalcula as próximas. O último pagamento pode ser **desfeito** na tela do empréstimo.
- **Registrar o valor recebido como receita:** lança o principal − IOF como entrada na data do empréstimo, para que o saldo não fique artificialmente negativo.

### B3. Fluxo de Caixa
- **Saldo hoje** considera só o que já aconteceu. O **Menor saldo previsto** mostra o dia em que o dinheiro fica mais apertado.
- Cada mês soma o que é **certo** (parcelas do cartão, contas fixas, empréstimos e outros lançamentos futuros) e o que é **estimado** (o gasto do dia a dia, pela mediana dos últimos meses completos). A seção **Como calculamos** mostra os números usados.
- **Cenários:** o pessimista usa a faixa alta do gasto variável; o otimista, a faixa baixa. O que é certo não muda entre eles.
- Clique num mês do **Extrato do futuro** para ver os lançamentos daquele mês. O **Histórico realizado** mostra os últimos meses nas mesmas colunas.

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
