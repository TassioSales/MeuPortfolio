# Email — CompraBio

**Para:** lucas.castilho@biomundo.com.br  
**Assunto:** Sistema de Aprovação de Compras — versão local para validação

---

Olá, Lucas!

Desenvolvemos o **CompraBio**, um sistema web para controle e aprovação de pedidos de compra da Bio Mundo. Está funcionando localmente aqui e quero te passar um overview antes de qualquer próximo passo.

---

## O que foi construído

O sistema tem três perfis de acesso distintos:

- **Comprador** — abre pedidos, preenche detalhes (título, descrição, categoria, valor estimado, prazo), anexa arquivos e envia para aprovação
- **Aprovador** — recebe os pedidos em aberto, aprova, reprova ou devolve com pedido de correção
- **Administrador** — gerencia usuários, categorias e tem visão completa de tudo

O fluxo de um pedido passa pelos seguintes estados:

**Rascunho → Em Aberto → Aprovado / Reprovado / Aguardando Correção**

Cada mudança de status fica registrada no histórico do pedido — dá pra ver quem fez o quê e quando.

Tem também exportação de pedidos em Excel e PDF, e um painel de controle de processos que mostra os pedidos em andamento agrupados por status.

---

## Telas desenvolvidas

Em anexo estão 4 prints do sistema rodando:

- `01_login.png` — tela de login com a logo da Bio Mundo
- `02_dashboard.png` — painel principal com resumo dos pedidos por status
- `03_controle.png` — controle de processos (visão do aprovador)
- `04_novo_pedido.png` — formulário de criação de pedido (visão do comprador)

---

## Como acessar localmente

O sistema roda com um script `.bat` que faz tudo sozinho: cria o ambiente virtual, instala as dependências e sobe o servidor.

Antes de abrir o navegador, é preciso fazer uma configuração de uma linha no arquivo `hosts` do Windows. Isso mapeia o domínio local `comprabio.local` para a máquina:

**Arquivo:** `C:\Windows\System32\drivers\etc\hosts`  
**Linha a adicionar:**
```
127.0.0.1   comprabio.local
```

Depois é só rodar o `run.bat` na pasta do projeto e acessar:

**http://comprabio.local:8000**

Usuários de teste já criados:

| Usuário | Senha | Perfil |
|---|---|---|
| admin | admin123 | Administrador |
| lucas.castilho | lucas123 | Aprovador |
| junior.lima | junior123 | Comprador |

---

## O que gostaria de saber

Antes de avançar para qualquer implantação ou ajuste maior, quero entender o que faz sentido do ponto de vista do processo de compras da rede:

1. O fluxo de status (rascunho → aberto → aprovado/reprovado/correção) reflete como vocês trabalham hoje, ou tem alguma etapa faltando?
2. Quais campos do pedido são realmente necessários no dia a dia? Tem algum que falta ou que não faz sentido?
3. O sistema precisa notificar alguém por email quando um pedido muda de status?
4. Vai existir mais de um aprovador? Se sim, todos aprovam qualquer categoria ou tem alguma separação?
5. Tem alguma integração que faria diferença — ERP, planilha existente, sistema de notas fiscais?

Qualquer feedback é bem-vindo, desde ajuste de interface até mudança de fluxo. O objetivo agora é validar antes de qualquer coisa ir para um servidor.

Abraço,  
Tássio

---

*Prints anexados: 01_login.png, 02_dashboard.png, 03_controle.png, 04_novo_pedido.png*
