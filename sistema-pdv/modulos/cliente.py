"""
Módulo de modelo de Cliente para o sistema PDV.
"""
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional, Dict, List, Any

# Importa funções auxiliares
from utils.helpers import format_currency, format_date, validate_cpf, validate_email, format_phone
from utils.database import execute_query
from utils.logger import logger

@dataclass
class Cliente:
    """
    Classe que representa um cliente no sistema PDV.
    """
    id: Optional[int] = None
    nome: str = ''
    email: Optional[str] = None
    telefone: Optional[str] = None
    cpf: Optional[str] = None
    endereco: Optional[str] = None
    data_nascimento: Optional[datetime] = None
    data_cadastro: Optional[datetime] = None
    ativo: bool = True
    
    # Campos calculados
    total_compras: float = field(init=False, default=0.0)
    total_vendas: int = field(init=False, default=0)
    
    def __post_init__(self):
        """Inicializa campos calculados após a criação do objeto."""
        if self.id is not None:
            self._carregar_estatisticas()
    
    def _carregar_estatisticas(self):
        """Carrega estatísticas do cliente (total de compras, etc.)."""
        try:
            # Total gasto em compras
            result = execute_query(
                """
                SELECT COALESCE(SUM(total), 0) as total
                FROM vendas
                WHERE cliente_id = ? AND status = 'finalizada'
                """,
                (self.id,),
                fetch="value"
            )
            self.total_compras = float(result) if result else 0.0
            
            # Total de compras
            result = execute_query(
                """
                SELECT COUNT(*) as total
                FROM vendas
                WHERE cliente_id = ? AND status = 'finalizada'
                """,
                (self.id,),
                fetch="value"
            )
            self.total_vendas = int(result) if result else 0
            
        except Exception as e:
            logger.error(f"Erro ao carregar estatísticas do cliente ID {self.id}: {e}")
            self.total_compras = 0.0
            self.total_vendas = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte o objeto para dicionário.
        
        Returns:
            Dicionário com os dados do cliente
        """
        data = asdict(self)
        
        # Converte datetime para string
        date_fields = ['data_nascimento', 'data_cadastro']
        for field in date_fields:
            if field in data and data[field] and isinstance(data[field], datetime):
                data[f"{field}_formatado"] = format_date(data[field])
                data[field] = data[field].isoformat()
        
        # Formata valores monetários
        data['total_compras_formatado'] = format_currency(self.total_compras)
        
        # Formata CPF e telefone
        if 'cpf' in data and data['cpf']:
            data['cpf_formatado'] = format_cpf(data['cpf'])
            
        if 'telefone' in data and data['telefone']:
            data['telefone_formatado'] = format_phone(data['telefone'])
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Cliente':
        """
        Cria uma instância de Cliente a partir de um dicionário.
        
        Args:
            data: Dicionário com os dados do cliente
            
        Returns:
            Instância de Cliente
        """
        # Converte strings de data para datetime
        date_fields = ['data_nascimento', 'data_cadastro']
        for field in date_fields:
            if field in data and data[field] and isinstance(data[field], str):
                try:
                    data[field] = datetime.fromisoformat(data[field])
                except (ValueError, TypeError):
                    data[field] = None
        
        # Remove campos calculados que não devem ser definidos diretamente
        data.pop('total_compras', None)
        data.pop('total_vendas', None)
        
        # Cria a instância do cliente
        return cls(**data)
    
    def validar(self) -> List[str]:
        """
        Valida os dados do cliente.
        
        Returns:
            Lista de mensagens de erro (vazia se válido)
        """
        erros = []
        
        if not self.nome or len(self.nome.strip()) < 3:
            erros.append("O nome deve ter pelo menos 3 caracteres.")
        
        if self.email and not validate_email(self.email):
            erros.append("O e-mail informado não é válido.")
        
        if self.cpf and not validate_cpf(self.cpf):
            erros.append("O CPF informado não é válido.")
        
        if self.telefone and len(self.telefone) < 10:
            erros.append("O telefone deve ter pelo menos 10 dígitos.")
        
        return erros
    
    # Métodos de persistência
    
    @classmethod
    def buscar_por_filtros(
            cls,
            nome: Optional[str] = None,
            cpf: Optional[str] = None,
            email: Optional[str] = None,
            telefone: Optional[str] = None,
            ativo: Optional[bool] = None,
            data_cadastro_inicio: Optional[datetime] = None,
            data_cadastro_fim: Optional[datetime] = None,
            ordenar_por: str = 'nome',
            ordem: str = 'ASC',
            limite: int = 100,
            offset: int = 0
        ) -> List['Cliente']:
        """
        Busca clientes com base nos filtros fornecidos.
        
        Args:
            nome: Nome ou parte do nome do cliente
            cpf: CPF do cliente (com ou sem formatação)
            email: E-mail do cliente
            telefone: Telefone do cliente (com ou sem formatação)
            ativo: Status de ativação do cliente
            data_cadastro_inicio: Data de cadastro inicial para filtro
            data_cadastro_fim: Data de cadastro final para filtro
            ordenar_por: Campo para ordenação (nome, data_cadastro, total_compras)
            ordem: 'ASC' para ascendente, 'DESC' para descendente
            limite: Número máximo de registros por página
            offset: Número de registros a pular
            
        Returns:
            Lista de Clientes que correspondem aos filtros
        """
        try:
            query = """
                SELECT c.*, 
                       COALESCE(SUM(CASE WHEN v.status = 'finalizada' THEN v.total ELSE 0 END), 0) as total_compras,
                       COUNT(DISTINCT v.id) as total_vendas
                FROM clientes c
                LEFT JOIN vendas v ON c.id = v.cliente_id
                WHERE 1=1
            """
            
            params = []
            
            # Aplica filtros
            if nome:
                query += " AND c.nome LIKE ?"
                params.append(f"%{nome}%")
                
            if cpf:
                # Remove formatação do CPF para busca
                cpf_limpo = ''.join(filter(str.isdigit, cpf))
                query += " AND REPLACE(REPLACE(REPLACE(c.cpf, '.', ''), '-', ''), ' ', '') = ?"
                params.append(cpf_limpo)
                
            if email:
                query += " AND c.email LIKE ?"
                params.append(f"%{email}%")
                
            if telefone:
                # Remove formatação do telefone para busca
                telefone_limpo = ''.join(filter(str.isdigit, telefone))
                query += " AND REPLACE(REPLACE(REPLACE(REPLACE(c.telefone, '(', ''), ')', ''), '-', ''), ' ', '') LIKE ?"
                params.append(f"%{telefone_limpo}%")
                
            if ativo is not None:
                query += " AND c.ativo = ?"
                params.append(1 if ativo else 0)
                
            if data_cadastro_inicio:
                query += " AND DATE(c.data_cadastro) >= ?"
                params.append(data_cadastro_inicio.strftime('%Y-%m-%d'))
                
            if data_cadastro_fim:
                query += " AND DATE(c.data_cadastro) <= ?"
                params.append(data_cadastro_fim.strftime('%Y-%m-%d'))
                
            # Agrupa por cliente para o cálculo das estatísticas
            query += " GROUP BY c.id"
            
            # Ordenação
            if ordenar_por in ['nome', 'email', 'data_cadastro']:
                query += f" ORDER BY c.{ordenar_por} {ordem.upper()}"
            elif ordenar_por in ['total_compras', 'total_vendas']:
                query += f" ORDER BY {ordenar_por} {ordem.upper()}"
            else:
                query += " ORDER BY c.nome ASC"
                
            # Paginação
            if limite > 0:
                query += " LIMIT ? OFFSET ?"
                params.extend([limite, offset])
            
            # Executa a consulta
            resultados = execute_query(query, tuple(params), fetch="all")
            
            # Converte os resultados em objetos Cliente
            clientes = []
            for cliente_dict in resultados:
                cliente = cls(**cliente_dict)
                cliente.total_compras = float(cliente_dict.get('total_compras', 0))
                cliente.total_vendas = int(cliente_dict.get('total_vendas', 0))
                clientes.append(cliente)
                
            return clientes
            
        except Exception as e:
            logger.error(f"Erro ao buscar clientes: {e}")
            return []
    
    @classmethod
    def buscar_por_id(cls, cliente_id: int) -> Optional['Cliente']:
        """
        Busca um cliente pelo ID.
        
        Args:
            cliente_id: ID do cliente
            
        Returns:
            Instância de Cliente ou None se não encontrado
        """
        try:
            result = execute_query(
                """
                SELECT * FROM clientes WHERE id = ?
                """,
                (cliente_id,),
                fetch="one"
            )
            
            if not result:
                return None
                
            return cls(**result)
            
        except Exception as e:
            logger.error(f"Erro ao buscar cliente por ID {cliente_id}: {e}")
            return None
    
    @classmethod
    def buscar_por_cpf(cls, cpf: str) -> Optional['Cliente']:
        """
        Busca um cliente pelo CPF.
        
        Args:
            cpf: CPF do cliente (com ou sem formatação)
            
        Returns:
            Instância de Cliente ou None se não encontrado
        """
        try:
            # Remove caracteres não numéricos do CPF
            cpf_limpo = ''.join(filter(str.isdigit, str(cpf)))
            
            result = execute_query(
                "SELECT * FROM clientes WHERE cpf = ?",
                (cpf_limpo,),
                fetch="one"
            )
            
            if result:
                return cls.from_dict(dict(result))
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar cliente por CPF {cpf}: {e}")
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
    ) -> List['Cliente']:
        """
        Busca clientes com opções de filtro e paginação.
        
        Args:
            filtro: Texto para busca no nome, email ou CPF
            apenas_ativos: Se True, retorna apenas clientes ativos
            ordenar_por: Campo para ordenação (nome, data_cadastro, total_compras)
            ordem: 'ASC' para ascendente, 'DESC' para descendente
            limite: Número máximo de registros por página
            offset: Número de registros a pular
            
        Returns:
            Lista de Clientes
        """
        try:
            # Mapeia campos de ordenação para evitar SQL injection
            campos_ordenacao = {
                'nome': 'nome',
                'data_cadastro': 'data_cadastro',
                'total_compras': 'total_compras'
            }
            
            campo_ordenacao = campos_ordenacao.get(ordenar_.lower(), 'nome')
            ordem = 'ASC' if ordem.upper() == 'ASC' else 'DESC'
            
            query = """
                SELECT c.*,
                       COALESCE(SUM(CASE WHEN v.status = 'finalizada' THEN v.total ELSE 0 END), 0) as total_compras,
                       COUNT(CASE WHEN v.status = 'finalizada' THEN 1 END) as total_vendas
                FROM clientes c
                LEFT JOIN vendas v ON c.id = v.cliente_id
                WHERE 1=1
            """
            params = []
            
            if apenas_ativos:
                query += " AND c.ativo = 1"
                
            if filtro:
                query += """
                    AND (
                        c.nome LIKE ? 
                        OR c.email LIKE ? 
                        OR c.cpf LIKE ?
                        OR c.telefone LIKE ?
                    )
                """
                termo = f'%{filtro}%'
                params.extend([termo, termo, termo, termo])
            
            # Agrupa por cliente para evitar duplicatas
            query += f" GROUP BY c.id ORDER BY {campo_ordenacao} {ordem}"
            
            # Adiciona paginação
            query += " LIMIT ? OFFSET ?"
            params.extend([limite, offset])
            
            results = execute_query(query, tuple(params), fetch="all")
            return [cls.from_dict(dict(row)) for row in results]
            
        except Exception as e:
            logger.error(f"Erro ao buscar clientes: {e}")
            return []
    
    def salvar(self) -> bool:
        """
        Salva o cliente no banco de dados.
        
        Returns:
            True se o cliente foi salvo com sucesso, False caso contrário
        """
        # Valida os dados antes de salvar
        erros = self.validar()
        if erros:
            logger.warning(f"Erros de validação ao salvar cliente: {', '.join(erros)}")
            return False
            
        try:
            # Remove caracteres não numéricos do CPF e telefone
            cpf_limpo = ''.join(filter(str.isdigit, str(self.cpf))) if self.cpf else None
            telefone_limpo = ''.join(filter(str.isdigit, str(self.telefone))) if self.telefone else None
            
            if self.id is None:
                # Inserir novo cliente
                query = """
                    INSERT INTO clientes (
                        nome, email, telefone, cpf, endereco, data_nascimento
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                params = (
                    self.nome.strip(),
                    self.email.lower().strip() if self.email else None,
                    telefone_limpo,
                    cpf_limpo,
                    self.endereco.strip() if self.endereco else None,
                    self.data_nascimento
                )
                
                self.id = execute_query(query, params, fetch="lastrowid")
                logger.info(f"Cliente criado com sucesso: {self.nome} (ID: {self.id})")
                
            else:
                # Atualizar cliente existente
                query = """
                    UPDATE clientes SET
                        nome = ?,
                        email = ?,
                        telefone = ?,
                        cpf = ?,
                        endereco = ?,
                        data_nascimento = ?,
                        ativo = ?
                    WHERE id = ?
                """
                params = (
                    self.nome.strip(),
                    self.email.lower().strip() if self.email else None,
                    telefone_limpo,
                    cpf_limpo,
                    self.endereco.strip() if self.endereco else None,
                    self.data_nascimento,
                    1 if self.ativo else 0,
                    self.id
                )
                
                execute_query(query, params, fetch="none")
                logger.info(f"Cliente atualizado: {self.nome} (ID: {self.id})")
            
            # Atualiza as estatísticas
            self._carregar_estatisticas()
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar cliente {self.nome}: {e}")
            return False
    
    def excluir(self) -> bool:
        """
        Marca o cliente como inativo no banco de dados.
        
        Returns:
            True se o cliente foi marcado como inativo, False caso contrário
        """
        if self.id is None:
            return False
            
        try:
            # Verifica se o cliente tem vendas associadas
            result = execute_query(
                "SELECT COUNT(*) as total FROM vendas WHERE cliente_id = ?",
                (self.id,),
                fetch="value"
            )
            
            if result and result > 0:
                # Se o cliente tiver vendas, apenas marca como inativo
                execute_query(
                    "UPDATE clientes SET ativo = 0 WHERE id = ?",
                    (self.id,),
                    fetch="none"
                )
                logger.info(f"Cliente marcado como inativo: {self.nome} (ID: {self.id})")
            else:
                # Se não tiver vendas, remove do banco
                execute_query(
                    "DELETE FROM clientes WHERE id = ?",
                    (self.id,),
                    fetch="none"
                )
                logger.info(f"Cliente removido: {self.nome} (ID: {self.id})")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao excluir cliente ID {self.id}: {e}")
            return False
    
    def obter_historico_compras(self, limite: int = 10) -> List[Dict]:
        """
        Obtém o histórico de compras do cliente.
        
        Args:
            limite: Número máximo de compras a retornar
            
        Returns:
            Lista de dicionários com os dados das compras
        """
        if self.id is None:
            return []
            
        try:
            query = """
                SELECT 
                    v.id,
                    v.codigo,
                    v.data_venda,
                    v.total,
                    v.forma_pagamento,
                    v.status,
                    GROUP_CONCAT(p.nome, ' (', iv.quantidade, 'x ', iv.preco_unitario, ')') as itens
                FROM vendas v
                JOIN itens_venda iv ON v.id = iv.venda_id
                JOIN produtos p ON iv.produto_id = p.id
                WHERE v.cliente_id = ?
                GROUP BY v.id
                ORDER BY v.data_venda DESC
                LIMIT ?
            """
            
            results = execute_query(
                query,
                (self.id, limite),
                fetch="all"
            )
            
            # Converte os resultados para dicionário e formata os dados
            historico = []
            for row in results:
                venda = dict(row)
                venda['data_venda_formatada'] = format_date(venda['data_venda'])
                venda['total_formatado'] = format_currency(venda['total'])
                historico.append(venda)
                
            return historico
            
        except Exception as e:
            logger.error(f"Erro ao obter histórico de compras do cliente ID {self.id}: {e}")
            return []

# Testes unitários
if __name__ == "__main__":
    # Teste de criação de cliente
    cliente = Cliente(
        nome="João da Silva",
        email="joao@exemplo.com",
        telefone="11999998888",
        cpf="12345678909",
        endereco="Rua das Flores, 123 - Centro"
    )
    
    print(f"Cliente criado: {cliente.nome}")
    
    # Teste de validação
    erros = cliente.validar()
    if erros:
        print(f"Erros de validação: {erros}")
    else:
        print("Cliente válido!")
    
    # Teste de conversão para dicionário
    cliente_dict = cliente.to_dict()
    print(f"Cliente como dicionário: {cliente_dict}")
    
    # Teste de criação a partir de dicionário
    novo_cliente = Cliente.from_dict(cliente_dict)
    print(f"Novo cliente a partir de dicionário: {novo_cliente.nome}")
    
    # Teste de busca
    clientes = Cliente.buscar_todos(filtro="João")
    print(f"Clientes encontrados: {len(clientes)}")
