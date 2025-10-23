"""
Módulo de modelo de Usuário para o sistema PDV.
"""
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional, Dict, List, Any

# Importa funções auxiliares
from utils.helpers import validate_email
from utils.auth import hash_password, check_password
from utils.database import execute_query
from utils.logger import logger

@dataclass
class Usuario:
    """
    Classe que representa um usuário no sistema PDV.
    """
    id: Optional[int] = None
    nome: str = ''
    email: str = ''
    senha_hash: str = ''
    role: str = 'vendedor'  # 'admin' ou 'vendedor'
    data_cadastro: Optional[datetime] = None
    ultimo_acesso: Optional[datetime] = None
    ativo: bool = True
    
    # Campos não persistidos
    senha: str = field(init=False, default='', repr=False)
    confirmar_senha: str = field(init=False, default='', repr=False)
    
    def __post_init__(self):
        """Inicializa campos após a criação do objeto."""
        # Se senha foi fornecida diretamente, gera o hash
        if self.senha and not self.senha_hash:
            self.senha_hash = hash_password(self.senha)
    
    def to_dict(self, incluir_senha: bool = False) -> Dict[str, Any]:
        """
        Converte o objeto para dicionário.
        
        Args:
            incluir_senha: Se True, inclui a senha em texto puro (não recomendado)
            
        Returns:
            Dicionário com os dados do usuário
        """
        data = asdict(self)
        
        # Remove campos não persistentes
        data.pop('senha', None)
        data.pop('confirmar_senha', None)
        
        # Remove o hash da senha a menos que seja explicitamente solicitado
        if not incluir_senha:
            data.pop('senha_hash', None)
        
        # Converte datetime para string
        date_fields = ['data_cadastro', 'ultimo_acesso']
        for field in date_fields:
            if field in data and data[field] and isinstance(data[field], datetime):
                data[f"{field}_formatado"] = data[field].strftime('%d/%m/%Y %H:%M:%S')
                data[field] = data[field].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Usuario':
        """
        Cria uma instância de Usuario a partir de um dicionário.
        
        Args:
            data: Dicionário com os dados do usuário
            
        Returns:
            Instância de Usuario
        """
        # Remove campos não persistentes
        data.pop('senha', None)
        data.pop('confirmar_senha', None)
        
        # Converte strings de data para datetime
        date_fields = ['data_cadastro', 'ultimo_acesso']
        for field in date_fields:
            if field in data and data[field] and isinstance(data[field], str):
                try:
                    data[field] = datetime.fromisoformat(data[field])
                except (ValueError, TypeError):
                    data[field] = None
        
        # Cria a instância do usuário
        return cls(**data)
    
    def validar(self, validar_senha: bool = True) -> List[str]:
        """
        Valida os dados do usuário.
        
        Args:
            validar_senha: Se True, valida também a senha
            
        Returns:
            Lista de mensagens de erro (vazia se válido)
        """
        erros = []
        
        if not self.nome or len(self.nome.strip()) < 3:
            erros.append("O nome deve ter pelo menos 3 caracteres.")
        
        if not validate_email(self.email):
            erros.append("O e-mail informado não é válido.")
        
        if validar_senha:
            if not self.senha and not self.senha_hash:
                erros.append("A senha é obrigatória.")
            elif self.senha and len(self.senha) < 6:
                erros.append("A senha deve ter pelo menos 6 caracteres.")
            elif self.senha != self.confirmar_senha:
                erros.append("As senhas não conferem.")
        
        if self.role not in ['admin', 'vendedor']:
            erros.append("O perfil do usuário é inválido.")
        
        return erros
    
    def verificar_senha(self, senha: str) -> bool:
        """
        Verifica se a senha fornecida está correta.
        
        Args:
            senha: Senha em texto puro para verificar
            
        Returns:
            True se a senha estiver correta, False caso contrário
        """
        if not self.senha_hash:
            return False
        return check_password(senha, self.senha_hash)
    
    def atualizar_ultimo_acesso(self) -> bool:
        """
        Atualiza a data do último acesso do usuário.
        
        Returns:
            True se a atualização foi bem-sucedida, False caso contrário
        """
        if not self.id:
            return False
            
        try:
            self.ultimo_acesso = datetime.now()
            execute_query(
                "UPDATE usuarios SET ultimo_acesso = ? WHERE id = ?",
                (self.ultimo_acesso, self.id),
                fetch="none"
            )
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar último acesso do usuário ID {self.id}: {e}")
            return False
    
    # Métodos de persistência
    
    @classmethod
    def buscar_por_filtros(
            cls,
            nome: Optional[str] = None,
            email: Optional[str] = None,
            role: Optional[str] = None,
            ativo: Optional[bool] = None,
            data_cadastro_inicio: Optional[datetime] = None,
            data_cadastro_fim: Optional[datetime] = None,
            ordenar_por: str = 'nome',
            ordem: str = 'ASC',
            limite: int = 100,
            offset: int = 0
        ) -> List['Usuario']:
        """
        Busca usuários com base nos filtros fornecidos.
        
        Args:
            nome: Nome ou parte do nome do usuário
            email: E-mail do usuário ou parte do e-mail
            role: Papel do usuário (admin, vendedor)
            ativo: Status de ativação do usuário
            data_cadastro_inicio: Data de cadastro inicial para filtro
            data_cadastro_fim: Data de cadastro final para filtro
            ordenar_por: Campo para ordenação (nome, email, data_cadastro, ultimo_acesso)
            ordem: 'ASC' para ascendente, 'DESC' para descendente
            limite: Número máximo de registros por página
            offset: Número de registros a pular
            
        Returns:
            Lista de Usuários que correspondem aos filtros
        """
        try:
            query = """
                SELECT *
                FROM usuarios
                WHERE 1=1
            """
            
            params = []
            
            # Aplica filtros
            if nome:
                query += " AND nome LIKE ?"
                params.append(f"%{nome}%")
                
            if email:
                query += " AND email LIKE ?"
                params.append(f"%{email}%")
                
            if role:
                query += " AND role = ?"
                params.append(role)
                
            if ativo is not None:
                query += " AND ativo = ?"
                params.append(1 if ativo else 0)
                
            if data_cadastro_inicio:
                query += " AND DATE(data_cadastro) >= ?"
                params.append(data_cadastro_inicio.strftime('%Y-%m-%d'))
                
            if data_cadastro_fim:
                query += " AND DATE(data_cadastro) <= ?"
                params.append(data_cadastro_fim.strftime('%Y-%m-%d'))
            
            # Ordenação
            if ordenar_por in ['nome', 'email', 'data_cadastro', 'ultimo_acesso']:
                query += f" ORDER BY {ordenar_por} {ordem.upper()}"
            else:
                query += " ORDER BY nome ASC"
                
            # Paginação
            if limite > 0:
                query += " LIMIT ? OFFSET ?"
                params.extend([limite, offset])
            
            # Executa a consulta
            resultados = execute_query(query, tuple(params), fetch="all")
            
            # Converte os resultados em objetos Usuario
            usuarios = [cls(**usuario_dict) for usuario_dict in resultados]
            
            return usuarios
            
        except Exception as e:
            logger.error(f"Erro ao buscar usuários: {e}")
            return []
    
    @classmethod
    def buscar_por_id(cls, usuario_id: int) -> Optional['Usuario']:
        """
        Busca um usuário pelo ID.
        
        Args:
            usuario_id: ID do usuário
            
        Returns:
            Instância de Usuario ou None se não encontrado
        """
        try:
            result = execute_query(
                """
                SELECT * FROM usuarios WHERE id = ?
                """,
                (usuario_id,),
                fetch="one"
            )
            
            if not result:
                return None
                
            return cls(**result)
            
        except Exception as e:
            logger.error(f"Erro ao buscar usuário por ID {usuario_id}: {e}")
            return None
    
    @classmethod
    def buscar_por_email(cls, email: str) -> Optional['Usuario']:
        """
        Busca um usuário pelo email.
        
        Args:
            email: Email do usuário
            
        Returns:
            Instância de Usuario ou None se não encontrado
        """
        try:
            result = execute_query(
                "SELECT * FROM usuarios WHERE email = ?",
                (email.lower().strip(),),
                fetch="one"
            )
            
            if result:
                return cls.from_dict(dict(result))
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar usuário por email {email}: {e}")
            return None
    
    @classmethod
    def autenticar(cls, email: str, senha: str) -> Optional['Usuario']:
        """
        Autentica um usuário pelo email e senha.
        
        Args:
            email: Email do usuário
            senha: Senha em texto puro
            
        Returns:
            Instância de Usuario se autenticado com sucesso, None caso contrário
        """
        try:
            usuario = cls.buscar_por_email(email)
            if not usuario or not usuario.ativo:
                return None
                
            if usuario.verificar_senha(senha):
                # Atualiza o último acesso
                usuario.atualizar_ultimo_acesso()
                return usuario
                
            return None
            
        except Exception as e:
            logger.error(f"Erro ao autenticar usuário {email}: {e}")
            return None
    
    @classmethod
    def buscar_todos(
        cls, 
        filtro: str = '', 
        apenas_ativos: bool = True,
        ordenar_por: str = 'nome',
        ordem: str = 'ASC',
        limite: int = 100,
        offset: int = 0
    ) -> List['Usuario']:
        """
        Busca usuários com opções de filtro e paginação.
        
        Args:
            filtro: Texto para busca no nome ou email
            apenas_ativos: Se True, retorna apenas usuários ativos
            ordenar_por: Campo para ordenação (nome, email, data_cadastro, ultimo_acesso)
            ordem: 'ASC' para ascendente, 'DESC' para descendente
            limite: Número máximo de registros por página
            offset: Número de registros a pular
            
        Returns:
            Lista de Usuários
        """
        try:
            # Mapeia campos de ordenação para evitar SQL injection
            campos_ordenacao = {
                'nome': 'nome',
                'email': 'email',
                'data_cadastro': 'data_cadastro',
                'ultimo_acesso': 'ultimo_acesso',
                'role': 'role'
            }
            
            campo_ordenacao = campos_ordenacao.get(ordenar_por.lower(), 'nome')
            ordem = 'ASC' if ordem.upper() == 'ASC' else 'DESC'
            
            query = "SELECT * FROM usuarios WHERE 1=1"
            params = []
            
            if apenas_ativos:
                query += " AND ativo = 1"
                
            if filtro:
                query += " AND (nome LIKE ? OR email LIKE ?)"
                termo = f'%{filtro}%'
                params.extend([termo, termo])
            
            # Ordenação
            query += f" ORDER BY {campo_ordenacao} {ordem}"
            
            # Paginação
            query += " LIMIT ? OFFSET ?"
            params.extend([limite, offset])
            
            results = execute_query(query, tuple(params), fetch="all")
            return [cls.from_dict(dict(row)) for row in results]
            
        except Exception as e:
            logger.error(f"Erro ao buscar usuários: {e}")
            return []
    
    def salvar(self) -> bool:
        """
        Salva o usuário no banco de dados.
        
        Returns:
            True se o usuário foi salvo com sucesso, False caso contrário
        """
        # Valida os dados antes de salvar
        erros = self.validar(validar_senha=not bool(self.id) or bool(self.senha))
        if erros:
            logger.warning(f"Erros de validação ao salvar usuário: {', '.join(erros)}")
            return False
            
        try:
            # Se for uma nova senha, gera o hash
            if self.senha:
                self.senha_hash = hash_password(self.senha)
            
            if self.id is None:
                # Inserir novo usuário
                query = """
                    INSERT INTO usuarios (
                        nome, email, senha_hash, role, data_cadastro, ativo
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                params = (
                    self.nome.strip(),
                    self.email.lower().strip(),
                    self.senha_hash,
                    self.role.lower(),
                    datetime.now(),
                    1 if self.ativo else 0
                )
                
                self.id = execute_query(query, params, fetch="lastrowid")
                logger.info(f"Usuário criado com sucesso: {self.email} (ID: {self.id})")
                
            else:
                # Atualizar usuário existente
                query = """
                    UPDATE usuarios SET
                        nome = ?,
                        email = ?,
                        role = ?,
                        ativo = ?
                """
                params = [
                    self.nome.strip(),
                    self.email.lower().strip(),
                    self.role.lower(),
                    1 if self.ativo else 0
                ]
                
                # Se a senha foi alterada
                if self.senha:
                    query += ", senha_hash = ?"
                    params.append(self.senha_hash)
                
                query += " WHERE id = ?"
                params.append(self.id)
                
                execute_query(query, tuple(params), fetch="none")
                logger.info(f"Usuário atualizado: {self.email} (ID: {self.id})")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar usuário {self.email}: {e}")
            return False
    
    def excluir(self) -> bool:
        """
        Marca o usuário como inativo no banco de dados.
        
        Returns:
            True se o usuário foi marcado como inativo, False caso contrário
        """
        if self.id is None:
            return False
            
        try:
            # Não permite excluir o próprio usuário
            if self.id == 1:  # ID 1 é geralmente o usuário admin principal
                logger.warning("Não é possível excluir o usuário administrador principal")
                return False
            
            # Marca como inativo em vez de excluir
            execute_query(
                "UPDATE usuarios SET ativo = 0 WHERE id = ?",
                (self.id,),
                fetch="none"
            )
            
            logger.info(f"Usuário marcado como inativo: {self.email} (ID: {self.id})")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao excluir usuário ID {self.id}: {e}")
            return False

# Testes unitários
if __name__ == "__main__":
    # Teste de criação de usuário
    usuario = Usuario(
        nome="Administrador",
        email="admin@loja.com",
        senha="admin123",
        role="admin"
    )
    
    print(f"Usuário criado: {usuario.nome}")
    
    # Teste de validação
    erros = usuario.validar()
    if erros:
        print(f"Erros de validação: {erros}")
    else:
        print("Usuário válido!")
    
    # Teste de verificação de senha
    senha_correta = usuario.verificar_senha("admin123")
    print(f"Senha correta? {senha_correta}")
    
    # Teste de conversão para dicionário
    usuario_dict = usuario.to_dict()
    print(f"Usuário como dicionário: {usuario_dict}")
    
    # Teste de criação a partir de dicionário
    novo_usuario = Usuario.from_dict(usuario_dict)
    print(f"Novo usuário a partir de dicionário: {novo_usuario.nome}")
    
    # Teste de autenticação
    usuario_autenticado = Usuario.autenticar("admin@loja.com", "admin123")
    print(f"Usuário autenticado: {usuario_autenticado.nome if usuario_autenticado else 'Falha na autenticação'}")
