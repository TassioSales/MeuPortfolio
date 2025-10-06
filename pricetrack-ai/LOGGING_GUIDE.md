# 📝 Sistema de Logging Loguru - PriceTrack AI

## 🚀 Visão Geral

O PriceTrack AI utiliza o **Loguru**, uma biblioteca de logging moderna e poderosa para Python, que oferece recursos avançados como:

- ✅ **Logging colorido** no console
- ✅ **Rotação automática** de arquivos
- ✅ **Compressão** de logs antigos
- ✅ **Thread-safe** por padrão
- ✅ **Backtrace** e diagnóstico automático
- ✅ **Filtros** personalizados
- ✅ **Formatação** estruturada
- ✅ **Múltiplos handlers** simultâneos

## 📁 Estrutura de Logs

```
logs/
├── app.log              # Logs gerais da aplicação
├── errors.log            # Apenas erros (ERROR e acima)
├── audit.log             # Ações do usuário e auditoria
├── performance.log       # Métricas de performance
├── app.log.1             # Logs rotacionados (zipados)
├── errors.log.1          # Erros rotacionados (zipados)
└── ...
```

## 🔧 Configuração

### Configuração Básica

```python
from core.logger import setup_logging, get_logger

# Configurar logging
setup_logging()

# Obter logger para módulo
logger = get_logger(__name__)

# Usar logger
logger.info("Mensagem de informação")
logger.warning("Aviso importante")
logger.error("Erro crítico")
```

### Configuração Avançada

```python
from core.logger import setup_logging

# Configuração personalizada
setup_logging(
    level="DEBUG",           # Nível de logging
    log_dir="logs",          # Diretório dos logs
    max_size="10 MB",        # Tamanho máximo antes da rotação
    rotation="1 day",         # Frequência de rotação
    retention="30 days",      # Tempo de retenção
    enable_console=True,      # Habilitar console
    enable_file=True         # Habilitar arquivo
)
```

### Configuração por Ambiente

```python
from core.logger import configure_logging_for_environment

# Desenvolvimento
configure_logging_for_environment("development")

# Produção
configure_logging_for_environment("production")

# Testes
configure_logging_for_environment("testing")
```

## 🎯 Funcionalidades Específicas

### 1. Logging de Ações do Usuário

```python
from core.logger import log_user_action

log_user_action(logger, "login", "Usuário fez login", user_id="user_123")
log_user_action(logger, "product_search", "Pesquisou por iPhone 15")
log_user_action(logger, "alert_config", "Configurou alerta de preço")
```

### 2. Logging de Chamadas de API

```python
from core.logger import log_api_call

# Sucesso
log_api_call(logger, "search_products", 150, True)

# Falha
log_api_call(logger, "generate_tags", 0, False)
```

### 3. Logging de Operações de Banco

```python
from core.logger import log_database_operation

# Sucesso
log_database_operation(logger, "INSERT", "products", True, 123)

# Falha
log_database_operation(logger, "UPDATE", "products", False)
```

### 4. Logging de Performance

```python
from core.logger import log_performance

log_performance(
    logger, 
    "search_products", 
    0.5,  # duração em segundos
    products_found=5,
    cache_hit=True,
    tokens_used=150
)
```

### 5. Logging de Segurança

```python
from core.logger import log_security_event

log_security_event(
    logger, 
    "login_attempt", 
    "MEDIUM", 
    "Tentativa de login suspeita"
)
```

### 6. Logging de Métricas de Negócio

```python
from core.logger import log_business_metric

log_business_metric(logger, "total_users", 150, "users")
log_business_metric(logger, "success_rate", 98.5, "percent")
```

### 7. Logging Contextual

```python
from core.logger import log_with_context

log_with_context(
    logger, 
    "INFO", 
    "Produto processado",
    product_id=123,
    price=2999.90,
    user_id="user_456"
)
```

## 📊 Formato dos Logs

### Console (Desenvolvimento)
```
2024-01-15 14:30:25 | INFO     | core.ai_services:search_products:45 | Busca por 'iPhone 15' retornou 5 produtos
```

### Arquivo
```
2024-01-15 14:30:25 | INFO     | core.ai_services:search_products:45 | Busca por 'iPhone 15' retornou 5 produtos
```

### Logs Específicos

**audit.log** (apenas ações do usuário):
```
2024-01-15 14:30:25 | INFO     | core.ai_services:search_products:45 | Ação do usuário: product_search - Pesquisou por iPhone 15
```

**performance.log** (apenas métricas de performance):
```
2024-01-15 14:30:25 | INFO     | core.ai_services:search_products:45 | Performance - search_products | Duration: 0.500s | products_found=5
```

## 🔍 Filtros e Handlers

### Filtros Personalizados

```python
# Handler apenas para erros
logger.add(
    "logs/errors.log",
    level="ERROR",
    filter=lambda record: record["level"].name == "ERROR"
)

# Handler para auditoria
logger.add(
    "logs/audit.log",
    filter=lambda record: "audit" in record["extra"]
)

# Handler para performance
logger.add(
    "logs/performance.log",
    filter=lambda record: "performance" in record["extra"]
)
```

## 🎨 Cores e Formatação

### Cores no Console
- 🟢 **Verde**: Timestamp
- 🔵 **Azul**: Nome da função/linha
- 🟡 **Amarelo**: Warnings
- 🔴 **Vermelho**: Errors
- ⚪ **Branco**: Mensagens

### Formatação Personalizada

```python
log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)
```

## 📈 Monitoramento e Análise

### Análise de Logs

```bash
# Logs em tempo real
tail -f logs/app.log

# Apenas erros
tail -f logs/errors.log

# Ações do usuário
tail -f logs/audit.log

# Performance
tail -f logs/performance.log
```

### Busca em Logs

```bash
# Buscar por usuário específico
grep "user_123" logs/audit.log

# Buscar por produto específico
grep "iPhone 15" logs/app.log

# Buscar por performance lenta
grep "Duration: [1-9]\." logs/performance.log
```

### Estatísticas

```bash
# Contar logs por nível
grep -c "INFO" logs/app.log
grep -c "ERROR" logs/errors.log
grep -c "WARNING" logs/app.log

# Top 10 produtos mais pesquisados
grep "product_search" logs/audit.log | cut -d'"' -f4 | sort | uniq -c | sort -nr | head -10
```

## 🚀 Exemplos Práticos

### Exemplo 1: Serviço de IA

```python
from core.logger import get_logger, log_api_call, log_performance
import time

logger = get_logger(__name__)

def search_products(product_name: str):
    start_time = time.time()
    
    try:
        # Simular chamada de API
        response = api_call(product_name)
        
        # Log de sucesso
        log_api_call(logger, "search_products", response.tokens, True)
        
        # Log de performance
        duration = time.time() - start_time
        log_performance(logger, "search_products", duration, products_found=len(response.products))
        
        return response.products
        
    except Exception as e:
        # Log de erro
        log_api_call(logger, "search_products", 0, False)
        logger.error(f"Erro na busca: {str(e)}", exc_info=True)
        raise
```

### Exemplo 2: Operações de Banco

```python
from core.logger import get_logger, log_database_operation

logger = get_logger(__name__)

def create_product(product_data):
    try:
        # Criar produto
        product = Product(**product_data)
        db.add(product)
        db.commit()
        
        # Log de sucesso
        log_database_operation(logger, "INSERT", "products", True, product.id)
        logger.info(f"Produto criado: {product.name}")
        
        return product
        
    except Exception as e:
        # Log de erro
        log_database_operation(logger, "INSERT", "products", False)
        logger.error(f"Erro ao criar produto: {str(e)}")
        raise
```

### Exemplo 3: Ações do Usuário

```python
from core.logger import get_logger, log_user_action

logger = get_logger(__name__)

def handle_user_action(action, details, user_id):
    # Log da ação
    log_user_action(logger, action, details, user_id)
    
    # Processar ação
    result = process_action(action, details)
    
    logger.info(f"Ação '{action}' processada com sucesso")
    return result
```

## 🔧 Troubleshooting

### Problema: Logs não aparecem no console

**Solução**: Verificar se `enable_console=True` na configuração

### Problema: Arquivos de log não são criados

**Solução**: Verificar permissões de escrita no diretório `logs/`

### Problema: Logs muito verbosos

**Solução**: Ajustar o nível para `INFO` ou `WARNING`

### Problema: Arquivos de log muito grandes

**Solução**: Ajustar `max_size` e `rotation` na configuração

## 📚 Recursos Adicionais

- [Documentação Loguru](https://loguru.readthedocs.io/)
- [Exemplos de Uso](exemplo_loguru.py)
- [Configurações Avançadas](logging_config.py)

## 🎯 Boas Práticas

1. **Use níveis apropriados**: DEBUG para desenvolvimento, INFO para produção
2. **Inclua contexto**: Sempre inclua informações relevantes nos logs
3. **Use funções específicas**: `log_user_action`, `log_api_call`, etc.
4. **Monitore performance**: Use `log_performance` para operações críticas
5. **Separe logs por tipo**: Use filtros para logs específicos
6. **Configure retenção**: Ajuste `retention` baseado no espaço disponível
7. **Teste configurações**: Sempre teste em ambiente de desenvolvimento primeiro

---

**🎉 O sistema de logging Loguru está pronto para uso!**
