# WA Evolution no Windows

Como colocar a Evolution API para rodar **na mesma máquina do bot, sem Docker** —
o arranjo para Windows Server 2016.

O `GOLIVE.md` trata a Evolution como serviço externo, que já existe em algum
lugar e você aponta pelo `EVOLUTION_URL`. Este arquivo cobre o caso em que ela
não existe em lugar nenhum e o servidor disponível é um Windows.

## Por que não Docker

A Evolution é distribuída como imagem Docker, e essa é a forma que o projeto
dela testa e suporta. Só que a imagem é **Linux**, e o Windows Server 2016 não
executa contêiner Linux:

| caminho | por que não serve aqui |
| --- | --- |
| Docker EE no Server 2016 | roda contêiner **Windows**; a imagem da Evolution é Linux |
| LCOW (Linux Containers on Windows) | descontinuado, nunca saiu de experimental |
| WSL2 | só a partir do Windows Server 2019 |

Sobra o caminho de código-fonte: Node instalado na máquina, `npm ci`, build, e o
processo vigiado pelo Windows como serviço. É o que o
`servicos/instalar-evolution.ps1` automatiza.

> [!important] Isto é um desvio do caminho suportado
> A Evolution não testa Windows. O que está aqui funciona por ela ser uma
> aplicação Node comum, não porque alguém garanta que vai continuar assim. Duas
> consequências práticas: **fixe a versão** (o script usa uma tag, nunca
> `latest`) e **teste a atualização fora do horário de atendimento**, porque uma
> dependência nova com binário só para Linux quebra o `npm ci` — e aí a
> Evolution que estava rodando continua rodando, mas a nova não sobe.

## O desenho

Três serviços do Windows na mesma máquina, mais o Postgres:

```
WhatsApp
   │
   ▼
painel-evolution   :8080   sessão do Baileys, fala com o WhatsApp
   │  POST /webhook/<segredo>
   ▼
painel-bot         :9511   conversa, chamados, banco (SQLite)
   ▲
   │  /internal/*
painel-web         :8511   painel de chamados — a única porta pública
```

Duas escolhas que valem explicação:

**A Evolution chama o bot direto, não o painel.** O desvio pelo painel que o
`GOLIVE.md` descreve existe porque lá fora uma porta pública tem de atender os
dois. Aqui os três processos estão na mesma máquina e a Evolution alcança o bot
em `127.0.0.1` — um salto a menos é um ponto de falha a menos.

**Sem Redis.** Ele não tem build oficial para Windows. A Evolution funciona com
o cache em memória do próprio processo (`CACHE_LOCAL_ENABLED=true`); o que se
perde é compartilhar cache entre várias instâncias dela, e aqui só existe uma.
O bot também trata o Redis como opcional — sem ele o limite de taxa volta a
valer por instância, que é o que já acontece hoje.

**Com Postgres, sem escolha.** A Evolution v2 exige um servidor de banco; ela
não usa SQLite. Este Postgres é **dela**, não do projeto: o bot continua com o
arquivo SQLite e nunca fala com ele.

## Antes de começar

Confira estes três — o script falha cedo se faltar algum, mas é melhor saber
antes:

**1. Node no PATH do sistema.** O serviço roda fora da sua sessão; `node` no
PATH do *usuário* não basta.

```powershell
node -v          # precisa ser >= 20 para a Evolution
```

> [!warning] O piso do projeto é mais alto que o da Evolution
> O `package.json` do bot exige Node >= 24. Versões recentes do Node vêm
> subindo o piso de Windows suportado, e **é preciso confirmar que a série 24
> instala no Server 2016** — se não instalar, o problema é anterior à Evolution:
> é o bot que não roda nessa máquina. Verifique isso primeiro, antes de qualquer
> outra coisa deste documento.

**2. Git for Windows.** É como a Evolution é baixada na versão exata.

**3. Postgres.** Instalador nativo em postgresql.org/download/windows. Anote a
senha do usuário `postgres`; o script pede.

## Instalação

```powershell
cd C:\caminho\do\whatsapp-suporte\servicos
.\instalar-evolution.ps1
```

Como Administrador. É idempotente: rodar de novo atualiza o que mudou.

O script lê o `.env` **do projeto** para pegar `EVOLUTION_API_KEY`,
`WEBHOOK_SEGREDO`, `PORT` e `EVOLUTION_INSTANCIA`, e escreve o `.env` da
Evolution a partir deles. Isso não é conveniência: é o que garante que o segredo
do webhook seja o mesmo dos dois lados **por construção**.

> [!important] O erro que isso evita
> Com segredos diferentes, a Evolution entrega tudo certinho e o bot recusa com
> 401. Nenhum log de nenhum dos dois diz "o segredo não bate" — você vê
> mensagens chegando no WhatsApp e nada acontecendo, e passa o dia procurando no
> lugar errado.

Opções que existem:

```powershell
.\instalar-evolution.ps1 -Versao v2.2.3      # outra tag
.\instalar-evolution.ps1 -Raiz D:\evolution  # outro disco
.\instalar-evolution.ps1 -Desinstalar        # tira o serviço, preserva a sessão
```

## Primeira subida

Dois passos que nenhum script faz por você.

### 1. Apontar o bot para a Evolution

No `.env` **do projeto**:

```dotenv
EVOLUTION_URL=http://127.0.0.1:8080
EVOLUTION_INSTANCIA=suporte
```

```powershell
Restart-Service painel-bot
```

Se o `.env` ficar com a Evolution de mentira (`127.0.0.1:4000`), o conjunto sobe
inteiro, sem erro nenhum, e não entrega uma única mensagem. O script avisa
quando detecta isso.

### 2. Parear o número

Uma vez só. Crie a instância e leia o QR Code:

```powershell
$h = @{ apikey = '<EVOLUTION_API_KEY do .env>' }

Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8080/instance/create `
  -Headers $h -ContentType application/json `
  -Body '{"instanceName":"suporte","integration":"WHATSAPP-BAILEYS","qrcode":true}'
```

A resposta traz o QR Code. Leia com o celular em **Aparelhos conectados**.
Confirme:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8080/instance/connectionState/suporte -Headers $h
```

`open` = conectado.

A sessão fica em `C:\evolution\instances\`. É **o** arquivo que não pode ser
perdido: apagar significa parear tudo de novo.

## Verificar que funciona

```powershell
Get-Service painel-evolution, painel-bot, painel-web
```

Os três em `Running`. Depois mande uma mensagem de WhatsApp para o número
pareado e acompanhe:

```powershell
Get-Content C:\caminho\do\projeto\dados\logs\bot.out.log -Wait -Tail 20
```

A mensagem tem de aparecer. Se a Evolution recebe mas o bot não registra nada, o
problema é entre os dois — quase sempre o `WEBHOOK_SEGREDO` ou a porta.

## Operação

| o que | comando |
| --- | --- |
| estado | `Get-Service painel-evolution, painel-bot, painel-web` |
| log da Evolution | `C:\evolution\logs\` |
| log do bot | `dados\logs\` |
| reiniciar | `Restart-Service painel-evolution` |
| parar tudo | `Stop-Service painel-web, painel-bot, painel-evolution` |

**Ordem importa ao parar:** painel, bot, Evolution. O bot fecha o SQLite no
SIGTERM e é aí que o WAL é incorporado ao arquivo.

### Atualizar a Evolution

```powershell
.\instalar-evolution.ps1 -Versao v2.3.0
```

O serviço é parado, o código atualizado, recompilado e o serviço volta. A sessão
pareada em `instances\` e o banco não são tocados.

Faça fora do horário de atendimento. Se o `npm ci` falhar numa dependência sem
build para Windows, o serviço fica parado até você voltar à tag anterior:

```powershell
.\instalar-evolution.ps1 -Versao v2.2.3
```

## Quando não sobe

| sintoma | causa provável |
| --- | --- |
| serviço em ciclo de restart no boot | Postgres ainda subindo. O `<depend>` cobre isso; se não foi detectado, o script avisou |
| `cannot find module` depois de atualizar | o arquivo de entrada mudou de lugar. Ajuste `<arguments>` no `C:\evolution\evolution.xml` |
| mensagens chegam, bot não reage | `WEBHOOK_SEGREDO` diferente dos dois lados, ou `PORT` do bot mudou depois da instalação |
| QR Code some e volta | relógio da máquina fora de hora, ou `instances\` sem permissão de escrita |
| tudo de pé, nada é entregue | `EVOLUTION_URL` no `.env` do projeto ainda apontando para a Evolution de mentira |

O log da Evolution (`C:\evolution\logs\`) registra o motivo real. O
`Get-Service` só diz se o processo está vivo — e ela sobe mesmo sem conseguir
falar com o WhatsApp.

## O `docker-compose.yml` que existe na raiz

Serve para desenvolver e testar numa máquina **com** Docker, e para o dia em que
o servidor for para Server 2019 ou Linux. Não tem uso no Server 2016. O caminho
de produção nesta máquina é este documento.
