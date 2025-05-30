"""
Módulo para gerenciamento de autenticação e autorização de usuários.
"""
import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from functools import wraps
from flask import request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import pyotp
import qrcode
import io
import base64
from ..models.usuario import Usuario, TokenBloqueado
from .. import db
from ..utils.logger import logger
from ..exceptions import (
    AuthenticationError,
    UserNotFoundError,
    InvalidTokenError,
    TokenExpiredError,
    InvalidCredentialsError,
    UserAlreadyExistsError
)

class AuthService:
    """Classe para gerenciar autenticação e autorização de usuários."""
    
    def __init__(self, app=None):
        """Inicializa o serviço de autenticação."""
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicializa a extensão com a aplicação Flask."""
        self.app = app
        self.secret_key = app.config.get('SECRET_KEY', 'chave_secreta_padrao_mude_isso')
        self.token_expiration = app.config.get('TOKEN_EXPIRATION', 3600)  # 1 hora
        self.refresh_token_expiration = app.config.get('REFRESH_TOKEN_EXPIRATION', 2592000)  # 30 dias
        self.algorithm = app.config.get('JWT_ALGORITHM', 'HS256')
    
    def register_user(self, email: str, senha: str, nome: str, **kwargs) -> Usuario:
        """
        Registra um novo usuário no sistema.
        
        Args:
            email (str): E-mail do usuário (deve ser único).
            senha (str): Senha do usuário (será hasheada).
            nome (str): Nome completo do usuário.
            **kwargs: Outros campos opcionais do usuário.
            
        Returns:
            Usuario: O objeto do usuário criado.
            
        Raises:
            UserAlreadyExistsError: Se já existir um usuário com o e-mail fornecido.
            ValueError: Se os dados fornecidos forem inválidos.
        """
        try:
            # Verifica se o usuário já existe
            if Usuario.query.filter_by(email=email).first():
                raise UserAlreadyExistsError(f"Já existe um usuário com o e-mail {email}.")
            
            # Cria um novo usuário
            novo_usuario = Usuario(
                email=email,
                senha=generate_password_hash(senha),
                nome=nome,
                data_cadastro=datetime.utcnow(),
                ativo=True,
                **kwargs
            )
            
            # Gera um segredo para 2FA (será ativado posteriormente)
            novo_usuario.two_factor_secret = pyotp.random_base32()
            
            # Salva no banco de dados
            db.session.add(novo_usuario)
            db.session.commit()
            
            logger.info(f"Novo usuário registrado: {email}")
            return novo_usuario
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao registrar usuário {email}: {str(e)}")
            raise
    
    def authenticate_user(self, email: str, senha: str) -> Tuple[Usuario, bool]:
        """
        Autentica um usuário com e-mail e senha.
        
        Args:
            email (str): E-mail do usuário.
            senha (str): Senha do usuário.
            
        Returns:
            Tuple[Usuario, bool]: Uma tupla contendo o usuário autenticado e um booleano
                                indicando se a verificação em duas etapas é necessária.
                                
        Raises:
            InvalidCredentialsError: Se as credenciais forem inválidas.
            UserNotFoundError: Se o usuário não for encontrado.
        """
        try:
            # Busca o usuário pelo e-mail
            usuario = Usuario.query.filter_by(email=email).first()
            
            # Verifica se o usuário existe e a senha está correta
            if not usuario or not check_password_hash(usuario.senha, senha):
                raise InvalidCredentialsError("E-mail ou senha incorretos.")
            
            # Verifica se o usuário está ativo
            if not usuario.ativo:
                raise AuthenticationError("Esta conta está desativada. Entre em contato com o suporte.")
            
            # Verifica se o 2FA está habilitado para este usuário
            dois_fatores_necessario = usuario.two_factor_enabled
            
            # Atualiza o último login
            usuario.ultimo_login = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"Usuário autenticado com sucesso: {email}")
            return usuario, dois_fatores_necessario
            
        except Exception as e:
            logger.error(f"Falha na autenticação para o usuário {email}: {str(e)}")
            raise
    
    def generate_token(self, usuario: Usuario, token_type: str = 'access') -> str:
        """
        Gera um token JWT para o usuário.
        
        Args:
            usuario (Usuario): O objeto do usuário.
            token_type (str): Tipo de token ('access' ou 'refresh').
            
        Returns:
            str: O token JWT gerado.
        """
        try:
            # Define o tempo de expiração com base no tipo de token
            if token_type == 'refresh':
                expires_in = self.refresh_token_expiration
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                token_id = f"refresh_{usuario.id}_{datetime.utcnow().timestamp()}"
            else:
                expires_in = self.token_expiration
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                token_id = f"access_{usuario.id}_{datetime.utcnow().timestamp()}"
            
            # Cria o payload do token
            payload = {
                'user_id': usuario.id,
                'email': usuario.email,
                'type': token_type,
                'exp': expires_at,
                'iat': datetime.utcnow(),
                'jti': token_id,
                'role': usuario.role or 'user'
            }
            
            # Gera o token
            token = jwt.encode(
                payload,
                self.secret_key,
                algorithm=self.algorithm
            )
            
            return token
            
        except Exception as e:
            logger.error(f"Erro ao gerar token para o usuário {usuario.email}: {str(e)}")
            raise
    
    def verify_token(self, token: str, token_type: str = 'access') -> Dict[str, Any]:
        """
        Verifica se um token JWT é válido.
        
        Args:
            token (str): O token JWT a ser verificado.
            token_type (str): O tipo esperado do token ('access' ou 'refresh').
            
        Returns:
            Dict[str, Any]: O payload do token se for válido.
            
        Raises:
            InvalidTokenError: Se o token for inválido.
            TokenExpiredError: Se o token estiver expirado.
            AuthenticationError: Se o token estiver na lista negra.
        """
        try:
            # Verifica se o token está na lista negra
            if TokenBloqueado.esta_na_lista_negra(token):
                raise AuthenticationError("Token revogado. Faça login novamente.")
            
            # Decodifica o token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Verifica o tipo do token
            if payload.get('type') != token_type:
                raise InvalidTokenError(f"Tipo de token inválido. Esperado: {token_type}")
            
            # Verifica se o token expirou
            if datetime.utcnow() > datetime.fromtimestamp(payload['exp']):
                raise TokenExpiredError("Token expirado.")
            
            # Verifica se o usuário existe e está ativo
            usuario = Usuario.query.get(payload['user_id'])
            if not usuario or not usuario.ativo:
                raise AuthenticationError("Usuário não encontrado ou inativo.")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Token expirado.")
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Token inválido: {str(e)}")
        except Exception as e:
            logger.error(f"Erro ao verificar token: {str(e)}")
            raise
    
    def refresh_token(self, refresh_token: str) -> Dict[str, str]:
        """
        Gera um novo token de acesso a partir de um refresh token.
        
        Args:
            refresh_token (str): O refresh token.
            
        Returns:
            Dict[str, str]: Um dicionário contendo o novo token de acesso e o refresh token.
        """
        try:
            # Verifica o refresh token
            payload = self.verify_token(refresh_token, 'refresh')
            
            # Busca o usuário
            usuario = Usuario.query.get(payload['user_id'])
            if not usuario or not usuario.ativo:
                raise AuthenticationError("Usuário não encontrado ou inativo.")
            
            # Gera novos tokens
            new_access_token = self.generate_token(usuario, 'access')
            
            # Retorna os novos tokens
            return {
                'access_token': new_access_token,
                'refresh_token': refresh_token,
                'token_type': 'bearer',
                'expires_in': self.token_expiration
            }
            
        except Exception as e:
            logger.error(f"Erro ao renovar token: {str(e)}")
            raise
    
    def revoke_token(self, token: str) -> None:
        """
        Revoga um token adicionando-o à lista negra.
        
        Args:
            token (str): O token a ser revogado.
        """
        try:
            # Verifica se o token já está na lista negra
            if TokenBloqueado.esta_na_lista_negra(token):
                return
            
            # Adiciona o token à lista negra
            token_bloqueado = TokenBloqueado(
                token=token,
                data_revogacao=datetime.utcnow()
            )
            
            db.session.add(token_bloqueado)
            db.session.commit()
            
            logger.info("Token revogado com sucesso.")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao revogar token: {str(e)}")
            raise
    
    def generate_2fa_secret(self, usuario: Usuario) -> str:
        """
        Gera um novo segredo para autenticação em duas etapas.
        
        Args:
            usuario (Usuario): O usuário para o qual gerar o segredo.
            
        Returns:
            str: O segredo gerado.
        """
        try:
            # Gera um novo segredo
            secret = pyotp.random_base32()
            
            # Atualiza o usuário
            usuario.two_factor_secret = secret
            usuario.two_factor_enabled = False
            
            db.session.commit()
            
            logger.info(f"Novo segredo 2FA gerado para o usuário {usuario.email}")
            return secret
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao gerar segredo 2FA: {str(e)}")
            raise
    
    def get_2fa_uri(self, usuario: Usuario, app_name: str = None) -> str:
        """
        Gera o URI para configuração do aplicativo de autenticação.
        
        Args:
            usuario (Usuario): O usuário.
            app_name (str, optional): Nome do aplicativo. Defaults to None.
            
        Returns:
            str: O URI para configuração do aplicativo de autenticação.
        """
        try:
            if not usuario.two_factor_secret:
                self.generate_2fa_secret(usuario)
            
            # Gera o URI para o aplicativo de autenticação
            app_name = app_name or "Análise de Ações"
            uri = pyotp.totp.TOTP(usuario.two_factor_secret).provisioning_uri(
                name=usuario.email,
                issuer_name=app_name
            )
            
            return uri
            
        except Exception as e:
            logger.error(f"Erro ao gerar URI 2FA: {str(e)}")
            raise
    
    def get_2fa_qr_code(self, usuario: Usuario, app_name: str = None) -> str:
        """
        Gera um QR Code para configuração do aplicativo de autenticação.
        
        Args:
            usuario (Usuario): O usuário.
            app_name (str, optional): Nome do aplicativo. Defaults to None.
            
        Returns:
            str: O QR Code em formato base64.
        """
        try:
            # Obtém o URI para o aplicativo de autenticação
            uri = self.get_2fa_uri(usuario, app_name)
            
            # Gera o QR Code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(uri)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Converte a imagem para base64
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            logger.error(f"Erro ao gerar QR Code 2FA: {str(e)}")
            raise
    
    def verify_2fa_code(self, usuario: Usuario, code: str) -> bool:
        """
        Verifica um código de autenticação em duas etapas.
        
        Args:
            usuario (Usuario): O usuário.
            code (str): O código a ser verificado.
            
        Returns:
            bool: True se o código for válido, False caso contrário.
        """
        try:
            if not usuario.two_factor_secret:
                return False
            
            # Verifica o código
            totp = pyotp.TOTP(usuario.two_factor_secret)
            is_valid = totp.verify(code)
            
            # Se for válido e o 2FA ainda não estiver ativado, ativa
            if is_valid and not usuario.two_factor_enabled:
                usuario.two_factor_enabled = True
                usuario.two_factor_setup_complete = True
                db.session.commit()
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Erro ao verificar código 2FA: {str(e)}")
            return False
    
    def disable_2fa(self, usuario: Usuario) -> bool:
        """
        Desativa a autenticação em duas etapas para um usuário.
        
        Args:
            usuario (Usuario): O usuário.
            
        Returns:
            bool: True se a operação for bem-sucedida, False caso contrário.
        """
        try:
            usuario.two_factor_enabled = False
            usuario.two_factor_secret = None
            usuario.two_factor_setup_complete = False
            
            db.session.commit()
            logger.info(f"2FA desativado para o usuário {usuario.email}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao desativar 2FA: {str(e)}")
            return False


def token_required(f):
    """
    Decorador para proteger rotas que requerem autenticação.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Obtém o token do cabeçalho Authorization
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Token de autenticação não fornecido.'}), 401
        
        try:
            # Verifica o token
            auth_service = current_app.extensions.get('auth_service')
            if not auth_service:
                auth_service = AuthService(current_app)
                current_app.extensions['auth_service'] = auth_service
            
            payload = auth_service.verify_token(token)
            
            # Adiciona o usuário ao contexto da requisição
            from flask import g
            g.current_user = Usuario.query.get(payload['user_id'])
            
            return f(*args, **kwargs)
            
        except TokenExpiredError:
            return jsonify({'message': 'Token expirado. Faça login novamente.'}), 401
        except (InvalidTokenError, AuthenticationError) as e:
            return jsonify({'message': str(e)}), 401
        except Exception as e:
            logger.error(f"Erro na autenticação: {str(e)}")
            return jsonify({'message': 'Falha na autenticação.'}), 401
    
    return decorated


def admin_required(f):
    """
    Decorador para proteger rotas que requerem privilégios de administrador.
    """
    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        from flask import g
        
        if not hasattr(g, 'current_user') or not g.current_user:
            return jsonify({'message': 'Acesso não autorizado.'}), 403
        
        if g.current_user.role != 'admin':
            return jsonify({'message': 'Acesso negado. Privilégios de administrador necessários.'}), 403
        
        return f(*args, **kwargs)
    
    return decorated


# Exemplo de uso:
if __name__ == "__main__":
    from flask import Flask
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'chave_secreta_para_teste'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Inicializa o banco de dados
    from .. import db
    db.init_app(app)
    
    with app.app_context():
        # Cria as tabelas
        db.create_all()
        
        # Cria uma instância do serviço de autenticação
        auth_service = AuthService(app)
        
        # Exemplo de registro de usuário
        try:
            usuario = auth_service.register_user(
                email="teste@example.com",
                senha="senha123",
                nome="Usuário de Teste"
            )
            print(f"Usuário registrado: {usuario.email}")
            
            # Exemplo de autenticação
            usuario_autenticado, _ = auth_service.authenticate_user(
                email="teste@example.com",
                senha="senha123"
            )
            print(f"Usuário autenticado: {usuario_autenticado.nome}")
            
            # Gera um token de acesso
            token = auth_service.generate_token(usuario_autenticado)
            print(f"Token de acesso gerado: {token}")
            
            # Verifica o token
            payload = auth_service.verify_token(token)
            print(f"Token verificado. Usuário ID: {payload['user_id']}")
            
            # Gera URI para 2FA
            uri = auth_service.get_2fa_uri(usuario_autenticado)
            print(f"URI para 2FA: {uri}")
            
            # Gera QR Code para 2FA
            qr_code = auth_service.get_2fa_qr_code(usuario_autenticado)
            print("QR Code gerado com sucesso.")
            
            # Simula a verificação de um código 2FA (em um caso real, o usuário forneceria o código do app autenticador)
            codigo_simulado = pyotp.TOTP(usuario_autenticado.two_factor_secret).now()
            if auth_service.verify_2fa_code(usuario_autenticado, codigo_simulado):
                print("Código 2FA verificado com sucesso!")
                print(f"2FA ativado: {usuario_autenticado.two_factor_enabled}")
            
            # Revoga o token
            auth_service.revoke_token(token)
            print("Token revogado com sucesso.")
            
        except Exception as e:
            print(f"Erro: {str(e)}")
