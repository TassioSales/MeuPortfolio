"""
Módulo contendo exceções personalizadas para a aplicação.
"""

class InsufficientFundsError(Exception):
    """Exceção lançada quando não há fundos suficientes para uma operação."""
    pass


class InvalidOperationError(Exception):
    """Exceção lançada quando uma operação inválida é tentada."""
    pass


class AssetNotFoundError(Exception):
    """Exceção lançada quando um ativo não é encontrado."""
    pass


class DuplicateAssetError(Exception):
    """Exceção lançada quando se tenta adicionar um ativo que já existe."""
    pass


class ValidationError(Exception):
    """Exceção lançada quando ocorre um erro de validação."""
    pass


class APIError(Exception):
    """Exceção base para erros de API."""
    def __init__(self, message: str, status_code: int = 500, payload: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}
    
    def to_dict(self) -> dict:
        """Converte a exceção para um dicionário."""
        rv = dict(self.payload or {})
        rv['message'] = self.message
        rv['status_code'] = self.status_code
        return rv


class APINotFoundError(APIError):
    """Exceção lançada quando um recurso não é encontrado na API."""
    def __init__(self, message: str = "Recurso não encontrado", payload: dict = None):
        super().__init__(message, 404, payload)


class APIBadRequestError(APIError):
    """Exceção lançada quando uma requisição inválida é feita à API."""
    def __init__(self, message: str = "Requisição inválida", payload: dict = None):
        super().__init__(message, 400, payload)


class APIUnauthorizedError(APIError):
    """Exceção lançada quando a autenticação falha ou não é fornecida."""
    def __init__(self, message: str = "Não autorizado", payload: dict = None):
        super().__init__(message, 401, payload)


class APIForbiddenError(APIError):
    """Exceção lançada quando o acesso ao recurso é negado."""
    def __init__(self, message: str = "Acesso negado", payload: dict = None):
        super().__init__(message, 403, payload)


class APIRateLimitError(APIError):
    """Exceção lançada quando o limite de requisições é excedido."""
    def __init__(self, message: str = "Limite de requisições excedido", payload: dict = None):
        super().__init__(message, 429, payload)


class APIServiceUnavailableError(APIError):
    """Exceção lançada quando o serviço da API está indisponível."""
    def __init__(self, message: str = "Serviço indisponível", payload: dict = None):
        super().__init__(message, 503, payload)
