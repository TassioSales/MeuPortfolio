"""
Módulo de modelo de Produto para o sistema PDV.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any, List

# Importa funções auxiliares
from utils.helpers import format_currency, parse_currency
from utils.database import execute_query
from utils.logger import logger

@dataclass
class Produto:
    """
    Classe que representa um produto no sistema PDV.
    """
    id: Optional[int] = None
    codigo_barras: Optional[str] = None
    nome: str = ''
    descricao: str = ''
    preco_compra: float = 0.0
    preco_venda: float = 0.0
    estoque: int = 0
    estoque_minimo: int = 5
    categoria_id: Optional[int] = None
    categoria_nome: Optional[str] = None
    data_cadastro: Optional[datetime] = None
    ativo: bool = True
    
    # Campos calculados
    valor_total_estoque: float = field(init=False)
    
    def __post_init__(self):
        """Inicializa campos calculados após a criação do objeto."""
        self.valor_total_estoque = self.estoque * self.preco_venda
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte o objeto para dicionário.
        
        Returns:
            Dicionário com os dados do produto
        """
        data = asdict(self)
        
        # Converte datetime para string
        if data.get('data_cadastro') and isinstance(data['data_cadastro'], datetime):
            data['data_cadastro'] = data['data_cadastro'].isoformat()
        
        # Formata valores monetários
        data['preco_compra_formatado'] = format_currency(self.preco_compra)
        data['preco_venda_formatado'] = format_currency(self.preco_venda)
        data['valor_total_estoque_formatado'] = format_currency(self.valor_total_estoque)
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Produto':
        """
        Cria uma instância de Produto a partir de um dicionário.
        
        Args:
            data: Dicionário com os dados do produto
            
        Returns:
            Instância de Produto
        """
        # Converte strings de data para datetime
        if 'data_cadastro' in data and isinstance(data['data_cadastro'], str):
            from datetime import datetime
            try:
                data['data_cadastro'] = datetime.fromisoformat(data['data_cadastro'])
            except (ValueError, TypeError):
                data['data_cadastro'] = None
        
        # Converte strings de preço para float
        if 'preco_compra' in data and isinstance(data['preco_compra'], str):
            data['preco_compra'] = parse_currency(data['preco_compra'])
            
        if 'preco_venda' in data and isinstance(data['preco_venda'], str):
            data['preco_venda'] = parse_currency(data['preco_venda'])
        
        # Cria a instância do produto
        return cls(**data)
    
    # Métodos de persistência
    
    @classmethod
    def buscar_por_id(cls, produto_id: int) -> Optional['Produto']:
        """
        Busca um produto pelo ID.
        
        Args:
            produto_id: ID do produto
            
        Returns:
            Instância de Produto ou None se não encontrado
        """
        try:
            result = execute_query(
                """
                SELECT p.*, c.nome as categoria_nome 
                FROM produtos p
                LEFT JOIN categorias c ON p.categoria_id = c.id
                WHERE p.id = ?
                """,
                (produto_id,),
                fetch="one"
            )
            
            if result:
                return cls.from_dict(dict(result))
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar produto ID {produto_id}: {e}")
            return None
    
    @classmethod
    def buscar_por_codigo_barras(cls, codigo_barras: str) -> Optional['Produto']:
        """
        Busca um produto pelo código de barras.
        
        Args:
            codigo_barras: Código de barras do produto
            
        Returns:
            Instância de Produto ou None se não encontrado
        """
        try:
            result = execute_query(
                """
                SELECT p.*, c.nome as categoria_nome 
                FROM produtos p
                LEFT JOIN categorias c ON p.categoria_id = c.id
                WHERE p.codigo_barras = ?
                """,
                (codigo_barras,),
                fetch="one"
            )
            
            if result:
                return cls.from_dict(dict(result))
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar produto por código de barras {codigo_barras}: {e}")
            return None
    
    @classmethod
    def buscar_todos(cls, filtro: str = '', categoria_id: int = None, apenas_ativos: bool = True) -> List['Produto']:
        """
        Busca todos os produtos com opções de filtro.
        
        Args:
            filtro: Texto para busca no nome ou descrição
            categoria_id: ID da categoria para filtrar
            apenas_ativos: Se True, retorna apenas produtos ativos
            
        Returns:
            Lista de Produtos
        """
        try:
            query = """
                SELECT p.*, c.nome as categoria_nome 
                FROM produtos p
                LEFT JOIN categorias c ON p.categoria_id = c.id
                WHERE 1=1
            """
            params = []
            
            if apenas_ativos:
                query += " AND p.ativo = 1"
                
            if filtro:
                query += " AND (p.nome LIKE ? OR p.descricao LIKE ? OR p.codigo_barras = ?)"
                params.extend([f'%{filtro}%', f'%{filtro}%', filtro])
                
            if categoria_id is not None:
                query += " AND p.categoria_id = ?"
                params.append(categoria_id)
                
            query += " ORDER BY p.nome"
            
            results = execute_query(query, tuple(params), fetch="all")
            return [cls.from_dict(dict(row)) for row in results]
            
        except Exception as e:
            logger.error(f"Erro ao buscar produtos: {e}")
            return []
    
    def salvar(self) -> bool:
        """
        Salva o produto no banco de dados.
        
        Returns:
            True se o produto foi salvo com sucesso, False caso contrário
        """
        try:
            if self.id is None:
                # Inserir novo produto
                query = """
                    INSERT INTO produtos (
                        codigo_barras, nome, descricao, preco_compra, preco_venda,
                        estoque, estoque_minimo, categoria_id, ativo
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    self.codigo_barras or None,
                    self.nome.strip(),
                    self.descricao.strip(),
                    self.preco_compra,
                    self.preco_venda,
                    self.estoque,
                    self.estoque_minimo,
                    self.categoria_id,
                    1 if self.ativo else 0
                )
                
                self.id = execute_query(query, params, fetch="lastrowid")
                logger.info(f"Produto criado com sucesso: {self.nome} (ID: {self.id})")
                
            else:
                # Atualizar produto existente
                query = """
                    UPDATE produtos SET
                        codigo_barras = ?,
                        nome = ?,
                        descricao = ?,
                        preco_compra = ?,
                        preco_venda = ?,
                        estoque = ?,
                        estoque_minimo = ?,
                        categoria_id = ?,
                        ativo = ?
                    WHERE id = ?
                """
                params = (
                    self.codigo_barras or None,
                    self.nome.strip(),
                    self.descricao.strip(),
                    self.preco_compra,
                    self.preco_venda,
                    self.estoque,
                    self.estoque_minimo,
                    self.categoria_id,
                    1 if self.ativo else 0,
                    self.id
                )
                
                execute_query(query, params, fetch="none")
                logger.info(f"Produto atualizado: {self.nome} (ID: {self.id})")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar produto {self.nome}: {e}")
            return False
    
    def excluir(self) -> bool:
        """
        Marca o produto como inativo no banco de dados.
        
        Returns:
            True se o produto foi marcado como inativo, False caso contrário
        """
        if self.id is None:
            return False
            
        try:
            # Verifica se o produto está em alguma venda
            result = execute_query(
                "SELECT COUNT(*) as total FROM itens_venda WHERE produto_id = ?",
                (self.id,),
                fetch="value"
            )
            
            if result and result > 0:
                # Se o produto estiver em alguma venda, apenas marca como inativo
                execute_query(
                    "UPDATE produtos SET ativo = 0 WHERE id = ?",
                    (self.id,),
                    fetch="none"
                )
                logger.info(f"Produto marcado como inativo: {self.nome} (ID: {self.id})")
            else:
                # Se não estiver em nenhuma venda, remove do banco
                execute_query(
                    "DELETE FROM produtos WHERE id = ?",
                    (self.id,),
                    fetch="none"
                )
                logger.info(f"Produto removido: {self.nome} (ID: {self.id})")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao excluir produto ID {self.id}: {e}")
            return False
    
    def atualizar_estoque(self, quantidade: int, tipo: str = 'entrada') -> bool:
        """
        Atualiza o estoque do produto.
        
        Args:
            quantidade: Quantidade a ser adicionada ou removida
            tipo: 'entrada' para adicionar, 'saida' para remover
            
        Returns:
            True se o estoque foi atualizado com sucesso, False caso contrário
        """
        if self.id is None:
            return False
            
        try:
            if tipo.lower() == 'entrada':
                self.estoque += quantidade
            else:  # saída
                if self.estoque < quantidade:
                    logger.warning(f"Estoque insuficiente para o produto ID {self.id}")
                    return False
                self.estoque -= quantidade
            
            # Atualiza o estoque no banco de dados
            execute_query(
                "UPDATE produtos SET estoque = ? WHERE id = ?",
                (self.estoque, self.id),
                fetch="none"
            )
            
            logger.info(f"Estoque do produto ID {self.id} atualizado: {tipo} de {quantidade} unidades")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao atualizar estoque do produto ID {self.id}: {e}")
            return False

# Testes unitários
if __name__ == "__main__":
    # Teste de criação de produto
    produto = Produto(
        nome="Produto de Teste",
        descricao="Descrição do produto de teste",
        preco_compra=10.50,
        preco_venda=25.90,
        estoque=100,
        categoria_id=1
    )
    
    print(f"Produto criado: {produto.nome}")
    print(f"Preço de venda formatado: {format_currency(produto.preco_venda)}")
    
    # Teste de conversão para dicionário
    produto_dict = produto.to_dict()
    print(f"Produto como dicionário: {produto_dict}")
    
    # Teste de criação a partir de dicionário
    novo_produto = Produto.from_dict(produto_dict)
    print(f"Novo produto a partir de dicionário: {novo_produto.nome}")
    
    # Teste de busca
    produtos = Produto.buscar_todos(filtro="teste")
    print(f"Produtos encontrados: {len(produtos)}")
