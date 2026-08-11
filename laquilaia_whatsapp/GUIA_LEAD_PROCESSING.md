# Guia de Lead Processing com Function Calling - L'Aquila AI

## 🎯 Lead Processing com Claude - Fase 7

Sistema automático para qualificação de leads através de análise de resposta do Claude com extração de dados estruturados em JSON.

---

## 📋 Fluxo Completo

```
WhatsApp User
    │ (mensagem)
    ▼
Backend recebe via Webhook
    │
    ├─→ Message Orchestrator
    │   ├─→ LLM Service (Claude)
    │   └─→ Response com JSON embutido
    │
    ├─→ Lead Processor
    │   ├─→ Extrai JSON da resposta
    │   ├─→ Valida schema
    │   ├─→ Cria/atualiza Lead
    │   ├─→ Atualiza LeadDetails
    │   ├─→ Adiciona LeadTimeline
    │   └─→ Move Kanban Card
    │
    ├─→ Envia resposta WhatsApp
    │
    └─→ Cliente recebe e lead está qualificado no Kanban
```

---

## ⚠️ O bloco JSON não chega ao cliente

O `message_orchestrator` remove o bloco ```json antes de gravar a mensagem e
de enviá-la pelo WhatsApp — só o texto conversacional segue. Antes ia tudo, e
o cliente recebia o próprio dossiê: o score que a empresa deu a ele, as
inconsistências e as objeções detectadas.

Quem faz a limpeza é `lead_processor.texto_para_o_cliente()`. Só o bloco
cercado por ```` ```json ```` sai; JSON solto no meio de uma frase fica, porque
pode ser conteúdo legítimo da conversa.

O **chat de teste** (`/dashboard/chat-test`) continua mostrando a resposta
inteira, com o bloco: é a ferramenta de validar o prompt, e esconder o JSON ali
tiraria justamente o que se quer conferir.

---

## 🤖 System Prompt com Instrução de JSON

Para que o Claude retorne dados estruturados de qualificação, o system_prompt do agente deve incluir uma instrução especial:

### Exemplo 1: Agente de Vendas

```
Você é um agente de vendas para uma plataforma SaaS de inteligência artificial.

Sua responsabilidade é:
1. Cumprimentar o visitante com educação
2. Entender as necessidades do cliente
3. Qualificar o lead baseado em critérios

IMPORTANTE: Após qualificar o cliente, SEMPRE retorne os dados estruturados em um bloco JSON como mostrado abaixo:

```json
{
  "nome_cliente": "Nome Completo",
  "email": "email@example.com",
  "score_qualificacao": 85,
  "status_proposto": "qualificado",
  "inconsistencias": "Descrição de informações faltantes ou contraditórias",
  "problemas_detectados": "Possíveis objeções ou problemas",
  "recomendacoes": "Próximos passos recomendados"
}
```

Explicação dos campos:
- nome_cliente: Nome da pessoa de contato (obrigatório)
- email: E-mail para contato (opcional, mas recomendado)
- score_qualificacao: Pontuação 0-100 indicando qualidade do lead
- status_proposto: Um de [qualificado, nao_qualificado, com_duvidas]
- inconsistencias: Detalhes de informações incompletas
- problemas_detectados: Objeções ou desafios
- recomendacoes: Ação sugerida

Mantenha o restante da conversa normal, apenas adicione o JSON após análise.
```

### Exemplo 2: Agente de Suporte

```
Você é um agente de suporte ao cliente para nossa plataforma.

Responsabilidades:
1. Atender educadamente
2. Resolver dúvidas técnicas
3. Qualificar urgência de ticket

Se o cliente relatar um problema crítico, retorne análise estruturada:

```json
{
  "nome_cliente": "Nome extraído da conversa",
  "email": "email@example.com",
  "score_qualificacao": 95,
  "status_proposto": "qualificado",
  "inconsistencias": "",
  "problemas_detectados": "Sistema indisponível há 2 horas, impacta 50 usuários",
  "recomendacoes": "Escalação imediata para equipe técnica"
}
```

Mantenha uma conversa amigável e sempre tente ajudar antes de finalizar.
```

---

## 💻 Lead Processor API

### Classe: LeadProcessor

```python
from app.services.lead_processor import lead_processor

# Processar resposta de Claude
result = await lead_processor.process_response(
    response_text="Texto completo da resposta do Claude",
    phone_number="5561999887234",
    conversation_id="conv-123",
    agent_id="agent-456",
    db=db_session
)

# Resultado
{
    "success": True,
    "lead_id": "lead-789",
    "qualification_data": {
        "nome_cliente": "João Silva",
        "score_qualificacao": 85,
        ...
    },
    "message": "Lead qualificado com sucesso"
}
```

### Métodos Principais

#### 1. process_response()
Processa resposta Claude e extrai qualificação.

```python
result = await lead_processor.process_response(
    response_text: str,      # Resposta de Claude
    phone_number: str,       # Telefone do cliente
    conversation_id: str,    # ID da conversa
    agent_id: str,          # ID do agente
    db: AsyncSession        # Sessão do DB
) -> Dict[str, Any]
```

**Retorno:**
```python
{
    "success": bool,
    "lead_id": str,                    # Se qualificado
    "qualification_data": dict,        # Dados extraídos
    "message": str,
    # ou
    "reason": str,                     # Se erro
}
```

#### 2. _extract_json()
Extrai JSON da resposta.

```python
data = lead_processor._extract_json(
    "Texto com ```json {...}``` ou JSON puro"
)
# Retorna: parsed JSON dict ou None
```

**Formatos Suportados:**
```
Markdown code block:
```json
{...}
```

Bare JSON object:
{...}

Mixed text (ignora texto, pega apenas JSON):
"Cliente qual qualificado e aqui estão os dados: {...}"
```

#### 3. _validate_schema()
Valida dados contra schema esperado.

```python
is_valid = lead_processor._validate_schema({
    "nome_cliente": "João",
    "score_qualificacao": 85,
    "status_proposto": "qualificado"
})
# Retorna: True ou False
```

---

## 📊 Estrutura de Dados de Qualificação

### JSON Schema Esperado

```json
{
  "nome_cliente": "string",           // OBRIGATÓRIO
  "email": "string",                  // Opcional
  "score_qualificacao": 0-100,        // OBRIGATÓRIO (int)
  "status_proposto": "string",        // OBRIGATÓRIO (qualificado|nao_qualificado|com_duvidas)
  "inconsistencias": "string",        // Opcional
  "problemas_detectados": "string",   // Opcional
  "recomendacoes": "string"           // Opcional
}
```

### Status Propostos

| Status | Significado | Ação |
|--------|------------|------|
| `qualificado` | Lead pronto para vendas/ação | Mover para coluna "Lead Qualificado" |
| `nao_qualificado` | Não atende critérios | Mover para "Arquivado" |
| `com_duvidas` | Precisa mais informações | Manter em "Em Qualificação" |

### Score de Qualificação (0-100)

- **0-30:** Muito fraco, provavelmente spam
- **30-60:** Interesse moderado, precisa de qualificação adicional
- **60-80:** Bom lead, pronto para seguimento
- **80-100:** Excelente lead, contato imediato recomendado

---

## 🗄️ Banco de Dados

### Modelo: Lead

```python
class Lead(Base):
    __tablename__ = "leads"
    
    id: str                 # UUID
    phone_number: str       # Único, indexado
    conversation_id: str    # FK para Conversation
    nome: str              # Nome do cliente
    email: str             # Email (opcional)
    status_funil: str      # novo, em_qualificacao, qualificado, agendado, arquivado
    data_criacao: datetime
    data_atualizacao: datetime
```

### Modelo: LeadDetails

```python
class LeadDetails(Base):
    __tablename__ = "lead_details"
    
    id: str                 # UUID
    lead_id: str           # FK para Lead (1:1)
    score_qualificacao: int # 0-100
    inconsistencias: str   # Dados faltantes
    problemas_detectados: str
    dados_json: str        # JSON completo armazenado
    data_atualizacao: datetime
```

### Modelo: LeadTimeline

```python
class LeadTimeline(Base):
    __tablename__ = "lead_timeline"
    
    id: str                 # UUID
    lead_id: str           # FK para Lead
    status_anterior: str   # Status antes da mudança
    status_novo: str       # Status novo
    motivo: str            # Descrição da mudança
    timestamp: datetime
```

### Modelo: KanbanCard

```python
class KanbanCard(Base):
    __tablename__ = "kanban_cards"
    
    id: str                 # UUID
    column_id: str         # FK para KanbanColumn
    lead_id: str           # FK para Lead (1:1)
    ordem: int             # Posição na coluna
    data_movimentacao: datetime
```

---

## 🧪 Testes

### Executar Testes

```bash
# Todos os testes de lead processor
docker-compose exec backend pytest tests/test_lead_processor.py -v

# Teste específico
docker-compose exec backend pytest tests/test_lead_processor.py::TestLeadProcessorJSONExtraction::test_extract_json_from_markdown_code_block -v

# Com cobertura
docker-compose exec backend pytest tests/test_lead_processor.py --cov=app.services.lead_processor
```

### Cobertura de Testes (20+ testes)

**JSON Extraction (4 testes)**
- ✅ Extração de markdown code block
- ✅ Extração de bare JSON object
- ✅ Sem JSON na resposta
- ✅ JSON inválido

**Schema Validation (6 testes)**
- ✅ Schema válido
- ✅ Nome cliente faltando
- ✅ Score faltando
- ✅ Score fora do range (>100)
- ✅ Status inválido
- ✅ Com defaults

**Lead Management (4 testes)**
- ✅ Criar novo lead
- ✅ Recuperar lead existente
- ✅ Atualizar lead com qualificação
- ✅ Criar/atualizar LeadDetails

**Timeline & Kanban (3 testes)**
- ✅ Adicionar entrada de timeline
- ✅ Mover em Kanban
- ✅ Remover card antigo

**Full Flow (3 testes)**
- ✅ Processar resposta com qualificação
- ✅ Processar sem dados de qualificação
- ✅ Schema inválido

---

## 📈 Fluxo de Criação de Agente com Qualificação

### 1. Criar Agente via API

```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Agente Vendas com Qualificação",
    "system_prompt": "Você é um agente de vendas... [com instrução JSON acima]",
    "temperatura": 0.7,
    "max_tokens": 1024
  }'
```

### 2. Configurar Kanban (Fase 8)

Criar colunas padrão para o agente:
- Novo Lead
- Em Qualificação
- Lead Qualificado
- Agendado
- Arquivado

### 3. Webhook envia mensagem

Cliente envia: "Olá, preciso de solução para gerenciar 500 clientes"

### 4. Claude analisa e retorna

```
Ótimo! Vejo que você busca solução para CRM...

```json
{
  "nome_cliente": "João Silva",
  "email": "joao@empresa.com",
  "score_qualificacao": 88,
  "status_proposto": "qualificado",
  "inconsistencias": "Nenhuma",
  "problemas_detectados": "Orçamento ainda não aprovado",
  "recomendacoes": "Contatar segunda-feira para discutir implementação"
}
```

Posso te passar um orçamento customizado...
```

### 5. Backend processa

1. Extrai JSON da resposta
2. Cria Lead em DB
3. Armazena score e detalhes
4. Move card automaticamente para "Lead Qualificado"
5. Adiciona timeline com motivo
6. Envia resposta por WhatsApp

### 6. Kanban atualiza em tempo real (Fase 15)

Admin vê novo card em "Lead Qualificado" com score 88

---

## 🔍 Exemplos de Qualificação

### Exemplo 1: Lead Qualificado

**Cliente:** "Olá, somos uma startup de 20 pessoas, queremos melhorar nosso atendimento"

**Claude responde:**
```
Que legal! Startup em crescimento é nosso foco. Vou qualificar você.

```json
{
  "nome_cliente": "Maria Santos",
  "email": "maria@startup.io",
  "score_qualificacao": 82,
  "status_proposto": "qualificado",
  "inconsistencias": "Ainda não confirmou o setor",
  "problemas_detectados": "Orçamento limitado para MVP",
  "recomendacoes": "Apresentar plano especial startup"
}
```

Podemos arranjar algo legal para vocês!
```

### Exemplo 2: Lead com Dúvidas

**Cliente:** "Não sei se preciso realmente disso"

**Claude responde:**
```
Vou anotar como lead em análise, precisamos entender melhor suas necessidades.

```json
{
  "nome_cliente": "Pedro Costa",
  "email": "pedro@empresa.com",
  "score_qualificacao": 45,
  "status_proposto": "com_duvidas",
  "inconsistencias": "Tamanho da equipe não definido",
  "problemas_detectados": "Falta de clareza sobre ROI",
  "recomendacoes": "Agendar reunião com decision maker"
}
```

Sem problema, vamos explorar juntos!
```

### Exemplo 3: Não Qualificado

**Cliente:** "Sou apenas curiosidade, preciso focar em outras prioridades"

**Claude responde:**
```
Entendi, agradeço o interesse e fico disponível quando precisar.

```json
{
  "nome_cliente": "Lucas Ferreira",
  "email": "lucas@empresa.com",
  "score_qualificacao": 15,
  "status_proposto": "nao_qualificado",
  "inconsistencias": "Cliente não é decision maker",
  "problemas_detectados": "Sem budget aprovado, está em research",
  "recomendacoes": "Agendar follow-up em 6 meses"
}
```

Sucesso com seus projetos!
```

---

## 🐛 Troubleshooting

### "JSON não é extraído da resposta"

**Problema:** Lead Processor retorna `no_qualification_data`

**Solução:**
1. Verificar que system_prompt contém instrução de JSON
2. Claude deve estar formatando o JSON corretamente
3. Verificar se está em ```json{}``` ou bare JSON
4. Aumentar `max_tokens` se JSON for muito grande

### "Schema inválido"

**Problema:** Lead Processor retorna `invalid_schema`

**Solução:**
1. Validar campos obrigatórios presentes: `nome_cliente`, `score_qualificacao`
2. Score deve estar entre 0-100
3. `status_proposto` deve ser um de: qualificado, nao_qualificado, com_duvidas
4. Ver logs: `docker-compose logs backend | grep "invalid schema"`

### "Lead não é criado"

**Problema:** Sem novo lead em banco de dados

**Solução:**
1. Verificar se qualificação foi processada: `"success": True`
2. Validar permission: agente deve estar ativo
3. Verificar integridade do banco: `docker-compose logs postgres`
4. Se erro de FK: Conversation pode não existir

### "Kanban não atualiza"

**Problema:** Lead criado mas card não aparece em Kanban

**Solução:**
1. Verificar se colunas foram criadas: `GET /api/v1/agents/{id}/kanban/columns`
2. Status proposto deve mapear para coluna existente
3. Verificar logs: `docker-compose logs backend | grep "Kanban"`

---

## 📊 Monitoramento

### Verificar Leads Qualificados

```sql
SELECT l.id, l.nome, l.phone_number, ld.score_qualificacao, l.status_funil
FROM leads l
LEFT JOIN lead_details ld ON l.id = ld.lead_id
ORDER BY ld.score_qualificacao DESC
LIMIT 10;
```

### Ver Timeline de Lead

```sql
SELECT * FROM lead_timeline
WHERE lead_id = 'lead-123'
ORDER BY timestamp DESC;
```

### Contar Leads por Status

```sql
SELECT status_funil, COUNT(*) as total
FROM leads
GROUP BY status_funil;
```

---

## 🚀 Próximas Fases

- **Fase 8:** Kanban Backend (CRUD completo de cards)
- **Fase 9:** Dashboard de Métricas (taxa de qualificação)
- **Fase 10-14:** Frontend (visualização Kanban)
- **Fase 15:** WebSocket (atualização em tempo real)

---

**Última Atualização:** 2026-08-11  
**Status:** Fase 7 - Lead Processing Completo ✅

