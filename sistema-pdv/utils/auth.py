"""
Módulo de autenticação e autorização para o sistema PDV.
"""
import bcrypt
import os
import time
from typing import Dict, Optional, Union

# Importa o logger e o banco de dados
from .logger import logger
from .database import execute_query

def hash_password(password: str) -> str:
    """
    Gera um hash seguro para a senha usando bcrypt.
    
    Args:
        password: Senha em texto puro
        
    Returns:
        Hash da senha
    """
    try:
        # Gera um salt e faz o hash da senha
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except Exception as e:
        logger.error(f"Erro ao gerar hash da senha: {e}")
        raise ValueError("Erro ao processar a senha")

def check_password(password: str, hashed_password: str) -> bool:
    """
    Verifica se a senha corresponde ao hash armazenado.
    
    Args:
        password: Senha em texto puro para verificar
        hashed_password: Hash da senha armazenado
        
    Returns:
        True se a senha estiver correta, False caso contrário
    """
    try:
        if not password or not hashed_password:
            return False
        return bcrypt.checkpw(
            password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Erro ao verificar senha: {e}")
        return False

def authenticate(email: str, password: str) -> Optional[Dict[str, Union[int, str]]]:
    """
    Autentica um usuário com base no email e senha.
    
    Args:
        email: Email do usuário
        password: Senha em texto puro
        
    Returns:
        Dicionário com os dados do usuário autenticado ou None se falhar
    """
    if not email or not password:
        return None
    
    try:
        # Busca o usuário pelo email
        user = execute_query(
            "SELECT id, nome, email, senha_hash, role FROM usuarios WHERE email = ? AND ativo = 1",
            (email.lower().strip(),),
            fetch="one"
        )
        
        if not user:
            logger.warning(f"Tentativa de login com email não cadastrado: {email}")
            return None
        
        # Verifica a senha
        if check_password(password, user['senha_hash']):
            logger.info(f"Login bem-sucedido para o usuário: {user['email']} (ID: {user['id']})")
            return {
                'id': user['id'],
                'nome': user['nome'],
                'email': user['email'],
                'role': user['role']
            }
        else:
            logger.warning(f"Senha incorreta para o usuário: {email}")
            return None
            
    except Exception as e:
        logger.error(f"Erro ao autenticar usuário {email}: {e}")
        return None

def check_role(required_role: str, user_role: str) -> bool:
    """
    Verifica se o papel do usuário tem permissão para acessar um recurso.
    
    Args:
        required_role: Papel mínimo necessário ('admin' ou 'vendedor')
        user_role: Papel do usuário atual
        
    Returns:
        True se o usuário tiver permissão, False caso contrário
    """
    if not required_role or not user_role:
        return False
    
    # Define a hierarquia de papéis
    roles = {
        'admin': 2,
        'vendedor': 1
    }
    
    # Verifica se os papéis são válidos
    if required_role.lower() not in roles or user_role.lower() not in roles:
        return False
    
    # Verifica se o papel do usuário atende ao requisito mínimo
    return roles[user_role.lower()] >= roles[required_role.lower()]

def get_user(user_id: int) -> Optional[Dict]:
    """
    Obtém os dados de um usuário pelo ID.
    
    Args:
        user_id: ID do usuário
        
    Returns:
        Dicionário com os dados do usuário ou None se não encontrado
    """
    try:
        user = execute_query(
            "SELECT id, nome, email, role FROM usuarios WHERE id = ? AND ativo = 1",
            (user_id,),
            fetch="one"
        )
        return dict(user) if user else None
    except Exception as e:
        logger.error(f"Erro ao buscar usuário ID {user_id}: {e}")
        return None

def create_user(nome: str, email: str, password: str, role: str = 'vendedor') -> Optional[int]:
    """
    Cria um novo usuário no sistema.
    
    Args:
        nome: Nome completo do usuário
        email: Email do usuário (deve ser único)
        password: Senha em texto puro
        role: Papel do usuário ('admin' ou 'vendedor')
        
    Returns:
        ID do usuário criado ou None em caso de erro
    """
    try:
        # Verifica se o email já está em uso
        existing = execute_query(
            "SELECT id FROM usuarios WHERE email = ?",
            (email.lower().strip(),),
            fetch="one"
        )
        
        if existing:
            logger.warning(f"Tentativa de cadastrar email já existente: {email}")
            return None
        
        # Gera o hash da senha
        hashed_password = hash_password(password)
        
        # Insere o novo usuário
        user_id = execute_query(
            """
            INSERT INTO usuarios (nome, email, senha_hash, role)
            VALUES (?, ?, ?, ?)
            """,
            (nome.strip(), email.lower().strip(), hashed_password, role.lower()),
            fetch="lastrowid"
        )
        
        if user_id:
            logger.info(f"Novo usuário criado: {email} (ID: {user_id}, Role: {role})")
            return user_id
        
        return None
        
    except Exception as e:
        logger.error(f"Erro ao criar usuário {email}: {e}")
        return None

# Testes unitários
if __name__ == "__main__":
    # Teste de hash e verificação de senha
    password = "senha123"
    hashed = hash_password(password)
    print(f"Hash da senha: {hashed}")
    print(f"Senha válida? {check_password(password, hashed)}")
    print(f"Senha inválida? {not check_password('senha_errada', hashed)}")
    
    # Teste de autenticação
    user = authenticate("admin@loja.com", "admin123")
    print(f"Usuário autenticado: {user}")
    
    # Teste de verificação de papel
    print(f"Admin pode acessar recurso de admin? {check_role('admin', 'admin')}")
    print(f"Vendedor pode acessar recurso de admin? {check_role('admin', 'vendedor')}")
    print(f"Admin pode acessar recurso de vendedor? {check_role('vendedor', 'admin')}")
