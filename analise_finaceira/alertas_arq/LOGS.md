# Sistema de Logs do Módulo de Alertas

Este documento descreve o sistema de logs implementado no módulo de alertas, incluindo configuração, níveis de log e melhores práticas.

## Visão Geral

O sistema de logs foi implementado para fornecer rastreabilidade e facilitar a depuração das operações relacionadas aos alertas. Ele registra informações importantes sobre as operações realizadas, erros e eventos significativos.

## Configuração

O sistema de logs está configurado no arquivo `routes.py` e `models.py` com as seguintes características:

- **Nível de log**: INFO (padrão)
- **Saídas**:
  - Arquivo: `alertas.log` (na raiz do projeto)
  - Console (saída padrão)
- **Formato**:
  ```
  %(asctime)s - %(name)s - %(levelname)s - %(message)s
  ```

## Níveis de Log

O sistema utiliza os seguintes níveis de log, em ordem crescente de gravidade:

1. **DEBUG**: Informações detalhadas, úteis apenas para depuração
2. **INFO**: Confirmação de que as coisas estão funcionando conforme o esperado
3. **WARNING**: Indica que algo inesperado aconteceu, mas o software ainda funciona normalmente
4. **ERROR**: Problemas mais sérios que impediram o software de executar alguma função
5. **CRITICAL**: Erros graves que podem fazer o programa parar de funcionar

## O Que é Registrado

### Rotas da API

- Acesso a cada rota
- Parâmetros de entrada (com ofuscação de dados sensíveis)
- Resultados das operações
- Erros e exceções

### Operações no Modelo Alerta

- Criação de novos alertas
- Atualização de alertas existentes
- Exclusão de alertas
- Busca de alertas
- Operações no histórico de alertas

### Dados Sensíveis

Os seguintes dados são ofuscados nos logs:

- `valor_referencia`: Substituído por `***`

## Melhores Práticas

1. **Use o nível de log apropriado**:
   - DEBUG: Para informações detalhadas de depuração
   - INFO: Para acompanhar o fluxo normal do aplicativo
   - WARNING: Para situações inesperadas que não são erros
   - ERROR: Para erros que afetam uma única operação
   - CRITICAL: Para erros que afetam todo o aplicativo

2. **Registre mensagens úteis**:
   - Inclua informações relevantes no log (IDs, contagens, etc.)
   - Use formatação de string (f-strings) para incluir variáveis
   - Adicione `exc_info=True` ao registrar exceções

3. **Evite dados sensíveis**:
   - Nunca registre senhas ou tokens
   - Ofusque dados sensíveis conforme necessário

## Exemplos de Uso

```python
# Log de informação simples
logger.info("Operação concluída com sucesso")

# Log com variáveis
logger.info(f"Usuário {user_id} acessou o sistema")

# Log de aviso
logger.warning(f"Tentativa de acesso não autorizado para o usuário {user_id}")

# Log de erro com exceção
try:
    # Código que pode falhar
    pass
except Exception as e:
    logger.error(f"Erro ao processar a requisição: {str(e)}", exc_info=True)
```

## Monitoramento

Os logs são armazenados no arquivo `alertas.log` e também são exibidos no console. Para monitoramento em produção, considere:

1. Implementar rotação de logs
2. Enviar logs para um sistema centralizado (ELK, Graylog, etc.)
3. Configurar alertas para erros críticos

## Solução de Problemas

Se os logs não estiverem aparecendo, verifique:

1. Se o diretório de logs tem permissão de escrita
2. Se o nível de log está configurado corretamente
3. Se os handlers estão configurados corretamente

## Manutenção

- Revise periodicamente os níveis de log
- Limpe ou rotacione os arquivos de log regularmente
- Atualize as mensagens de log conforme o sistema evolui
