# Guia de Autenticação - L'Aquila AI

## 🔐 Sistema de Autenticação JWT

Este projeto usa **JWT (JSON Web Tokens)** para autenticação stateless com **bcrypt** para hash de senhas.

## 📋 Endpoints de Autenticação

Todos os endpoints estão sob `/api/v1/auth`

### 1. Registro de Usuário
**POST** `/api/v1/auth/register`

#### Request
```json
{
  "email": "usuario@example.com",
  "nome": "João Silva",
  "senha": "SenhaForte123!"
}
```

#### Response (201 Created)
```json
{
  "id": "user-uuid-123",
  "email": "usuario@example.com",
  "nome": "João Silva",
  "status": "ativo",
  "data_criacao": "2026-08-10T20:45:00Z"
}
```

#### Erros
- `400`: Email já registrado
- `422`: Validação falhou (email inválido, senha fraca, etc)

---

### 2. Login
**POST** `/api/v1/auth/login`

#### Request
```json
{
  "email": "usuario@example.com",
  "senha": "SenhaForte123!"
}
```

#### Response (200 OK)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### Erros
- `401`: Email ou senha inválidos
- `403`: Conta do usuário não está ativa

---

### 3. Refresh Token
**POST** `/api/v1/auth/refresh`

Gera um novo access token usando o refresh token.

#### Request
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Response (200 OK)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### Erros
- `400`: Refresh token não fornecido
- `401`: Refresh token inválido ou expirado

---

### 4. Verificar Token
**POST** `/api/v1/auth/verify-token`

Verifica se um token é válido.

#### Request
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Response (200 OK) - Token Válido
```json
{
  "valid": true,
  "user_id": "user-uuid-123",
  "message": "Token is valid"
}
```

#### Response (200 OK) - Token Inválido
```json
{
  "valid": false,
  "user_id": null,
  "message": "Token is invalid or expired"
}
```

---

## 🛡️ Usando Autenticação em Requisições

### Com cURL
```bash
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8000/api/v1/agents
```

### Com Postman
1. Vá para a aba "Authorization"
2. Selecione "Bearer Token"
3. Cole o `access_token` no campo

### Com JavaScript/Fetch
```javascript
const token = localStorage.getItem('access_token');

fetch('http://localhost:8000/api/v1/agents', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
.then(res => res.json())
.then(data => console.log(data));
```

### Com Python/Requests
```python
import requests

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
headers = {"Authorization": f"Bearer {token}"}

response = requests.get(
  'http://localhost:8000/api/v1/agents',
  headers=headers
)
print(response.json())
```

---

## 🔑 Estrutura dos Tokens JWT

### Access Token
- **Tipo**: JWT
- **Expiração**: 30 minutos (configurável em `ACCESS_TOKEN_EXPIRE_MINUTES`)
- **Payload**:
  ```json
  {
    "sub": "user-id",
    "exp": 1691701200,
    "iat": 1691699400,
    "type": "access"
  }
  ```

### Refresh Token
- **Tipo**: JWT
- **Expiração**: 7 dias
- **Payload**:
  ```json
  {
    "sub": "user-id",
    "exp": 1692304200,
    "iat": 1691699400,
    "type": "refresh"
  }
  ```

---

## 🔄 Fluxo de Autenticação Típico

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Usuário clica "Login"                                    │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. POST /auth/login                                         │
│    {email, senha}                                           │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Backend valida credenciais e retorna tokens             │
│    {access_token, refresh_token}                           │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Frontend armazena tokens (localStorage/sessionStorage)  │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Requisições subsequentes usam Authorization header      │
│    Authorization: Bearer <access_token>                     │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Quando access_token expira:                             │
│    POST /auth/refresh                                      │
│    {refresh_token}                                         │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Backend valida refresh_token e retorna novo access_token│
│    {access_token}                                          │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. Frontend atualiza token e continua requisições         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧪 Testando Autenticação

### Usando Swagger UI (Recomendado)
1. Acesse http://localhost:8000/docs
2. Clique em qualquer endpoint que necessite autenticação
3. Clique no botão "Authorize" (cadeado)
4. Selecione "Bearer Token"
5. Cole seu `access_token`
6. Clique "Authorize" e depois "Close"
7. Agora todos os endpoints estarão autenticados

### Rodar Testes
```bash
# Todos os testes de autenticação
docker-compose exec backend pytest tests/test_auth.py -v

# Um teste específico
docker-compose exec backend pytest tests/test_auth.py::TestUserLogin::test_login_success -v

# Com cobertura
docker-compose exec backend pytest tests/test_auth.py --cov=app.services.auth_service
```

---

## 🔒 Boas Práticas de Segurança

### ✅ Faça
- ✅ Armazene tokens em localStorage (com segurança adequada)
- ✅ Use HTTPS em produção (nunca HTTP)
- ✅ Implemente logout limpando tokens
- ✅ Use senhas fortes (mín. 8 caracteres)
- ✅ Implemente rate limiting em endpoints de login
- ✅ Rotacione refresh tokens periodicamente

### ❌ NÃO Faça
- ❌ Não guarde tokens em cookies sem HttpOnly flag
- ❌ Não exponha tokens em URLs
- ❌ Não use senhas fracas padrão
- ❌ Não envie credenciais em logs
- ❌ Não reutilize tokens entre usuários

---

## 🛠️ Configuração (vars de Ambiente)

```env
# Tempo de expiração do access token (em minutos)
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Chave secreta para assinar tokens
SECRET_KEY=your-super-secret-key-change-in-production

# Algoritmo de assinatura (HS256 recomendado)
ALGORITHM=HS256
```

---

## 🐛 Troubleshooting

### "Invalid or expired token"
**Causa**: Token expirou ou está malformado
**Solução**: Faça login novamente ou use o refresh token

### "Missing authorization token"
**Causa**: Requisição sem header `Authorization`
**Solução**: Adicione `Authorization: Bearer <token>`

### "User account is not active"
**Causa**: Usuário foi desativado
**Solução**: Ative o usuário no banco de dados

### "Invalid email or password"
**Causa**: Email ou senha incorretos
**Solução**: Verifique credenciais ou registre uma nova conta

---

## 📚 Referências

- [JWT.io - Debugar e entender JWTs](https://jwt.io)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

---

**Última Atualização:** 2026-08-10  
**Status:** Fase 2 - Autenticação Implementada ✅
