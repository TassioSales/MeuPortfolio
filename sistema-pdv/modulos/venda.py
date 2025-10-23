"""
Módulo de modelo de Venda para o sistema PDV.
"""
from dataclasses import dataclass, asdict, field
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, List, Any, Union

# Importa funções auxiliares
from utils.helpers import format_currency, format_date
from utils.database import execute_query, DatabaseError
from utils.logger import logger

# Importa os modelos relacionados
from .produto import Produto
from .cliente import Cliente
from .usuario import Usuario

@dataclass
class ItemVenda:
    """
    Classe que representa um item de venda no sistema PDV.
    """
    id: Optional[int] = None
    venda_id: Optional[int] = None
    produto_id: int = 0
    produto_nome: str = ''
    quantidade: int = 1
    preco_unitario: float = 0.0
    desconto: float = 0.0
    subtotal: float = field(init=False)
    
    def __post_init__(self):
        """Calcula o subtotal do item."""
        self.calcular_subtotal()
    
    def calcular_subtotal(self) -> float:
        """
        Calcula o subtotal do item (quantidade * preço unitário - desconto).
        
        Returns:
            Valor do subtotal
        """
        self.subtotal = (self.quantidade * self.preco_unitario) - self.desconto
        if self.subtotal < 0:
            self.subtotal = 0.0
        return self.subtotal
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte o objeto para dicionário.
        
        Returns:
            Dicionário com os dados do item de venda
        """
        data = asdict(self)
        
        # Formata valores monetários
        data['preco_unitario_formatado'] = format_currency(self.preco_unitario)
        data['desconto_formatado'] = format_currency(self.desconto)
        data['subtotal_formatado'] = format_currency(self.subtotal)
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ItemVenda':
        """
        Cria uma instância de ItemVenda a partir de um dicionário.
        
        Args:
            data: Dicionário com os dados do item de venda
            
        Returns:
            Instância de ItemVenda
        """
        # Converte strings de preço para float
        for field in ['preco_unitario', 'desconto', 'subtotal']:
            if field in data and isinstance(data[field], str):
                data[field] = float(data[field].replace('R$', '').replace('.', '').replace(',', '.').strip())
        
        # Cria a instância do item de venda
        return cls(**data)

@dataclass
class Venda:
    """
    Classe que representa uma venda no sistema PDV.
    """
    id: Optional[int] = None
    codigo: str = ''
    cliente_id: Optional[int] = None
    cliente_nome: str = ''
    usuario_id: Optional[int] = None
    usuario_nome: str = ''
    data_venda: datetime = field(default_factory=datetime.now)
    subtotal: float = 0.0
    desconto: float = 0.0
    total: float = 0.0
    forma_pagamento: str = 'dinheiro'  # dinheiro, cartao_credito, cartao_debito, pix, etc.
    status: str = 'aberta'  # aberta, finalizada, cancelada
    observacoes: str = ''
    itens: List[ItemVenda] = field(default_factory=list)
    
    def __post_init__(self):
        """Inicializa campos calculados após a criação do objeto."""
        self.calcular_totais()
    
    def calcular_totais(self) -> Dict[str, float]:
        """
        Calcula os totais da venda com base nos itens.
        
        Returns:
            Dicionário com subtotal, desconto e total
        """
        self.subtotal = sum(item.subtotal for item in self.itens)
        self.total = self.subtotal - self.desconto
        
        # Garante que os valores não sejam negativos
        self.subtotal = max(0.0, self.subtotal)
        self.desconto = max(0.0, min(self.desconto, self.subtotal))  # Desconto não pode ser maior que o subtotal
        self.total = max(0.0, self.total)
        
        return {
            'subtotal': self.subtotal,
            'desconto': self.desconto,
            'total': self.total
        }
    
    def adicionar_item(self, produto: Produto, quantidade: int = 1, desconto: float = 0.0) -> bool:
        """
        Adiciona um item à venda.
        
        Args:
            produto: Instância do Produto a ser adicionado
            quantidade: Quantidade do produto
            desconto: Valor de desconto para este item
            
        Returns:
            True se o item foi adicionado, False caso contrário
        """
        if quantidade <= 0:
            logger.warning(f"Quantidade inválida: {quantidade}")
            return False
            
        if not produto or not produto.ativo or produto.estoque < quantidade:
            logger.warning(f"Produto inválido ou sem estoque suficiente: {produto.nome}")
            return False
        
        # Verifica se o produto já está na lista de itens
        for item in self.itens:
            if item.produto_id == produto.id:
                # Atualiza a quantidade e recalcula o subtotal
                item.quantidade += quantidade
                item.desconto += desconto
                item.calcular_subtotal()
                self.calcular_totais()
                return True
        
        # Se o produto não está na lista, adiciona um novo item
        novo_item = ItemVenda(
            produto_id=produto.id,
            produto_nome=produto.nome,
            quantidade=quantidade,
            preco_unitario=produto.preco_venda,
            desconto=desconto
        )
        
        self.itens.append(novo_item)
        self.calcular_totais()
        return True
    
    def remover_item(self, item_index: int) -> bool:
        """
        Remove um item da venda.
        
        Args:
            item_index: Índice do item a ser removido
            
        Returns:
            True se o item foi removido, False caso contrário
        """
        try:
            if 0 <= item_index < len(self.itens):
                self.itens.pop(item_index)
                self.calcular_totais()
                return True
            return False
        except Exception as e:
            logger.error(f"Erro ao remover item da venda: {e}")
            return False
    
    def atualizar_item(self, item_index: int, quantidade: int = None, desconto: float = None) -> bool:
        """
        Atualiza a quantidade ou desconto de um item da venda.
        
        Args:
            item_index: Índice do item a ser atualizado
            quantidade: Nova quantidade (opcional)
            desconto: Novo valor de desconto (opcional)
            
        Returns:
            True se o item foi atualizado, False caso contrário
        """
        try:
            if 0 <= item_index < len(self.itens):
                item = self.itens[item_index]
                
                if quantidade is not None and quantidade > 0:
                    item.quantidade = quantidade
                    
                if desconto is not None and desconto >= 0:
                    item.desconto = desconto
                
                item.calcular_subtotal()
                self.calcular_totais()
                return True
                
            return False
        except Exception as e:
            logger.error(f"Erro ao atualizar item da venda: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte o objeto para dicionário.
        
        Returns:
            Dicionário com os dados da venda
        """
        data = asdict(self)
        
        # Remove o campo 'itens' para processá-lo separadamente
        itens = data.pop('itens')
        
        # Converte datetime para string
        if 'data_venda' in data and data['data_venda'] and isinstance(data['data_venda'], datetime):
            data['data_venda_formatada'] = format_date(data['data_venda'], '%d/%m/%Y %H:%M:%S')
            data['data_venda'] = data['data_venda'].isoformat()
        
        # Formata valores monetários
        for field in ['subtotal', 'desconto', 'total']:
            if field in data:
                data[f"{field}_formatado"] = format_currency(data[field])
        
        # Adiciona os itens processados
        data['itens'] = [item.to_dict() for item in itens]
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Venda':
        """
        Cria uma instância de Venda a partir de um dicionário.
        
        Args:
            data: Dicionário com os dados da venda
            
        Returns:
            Instância de Venda
        """
        # Converte string de data para datetime
        if 'data_venda' in data and data['data_venda'] and isinstance(data['data_venda'], str):
            try:
                data['data_venda'] = datetime.fromisoformat(data['data_venda'])
            except (ValueError, TypeError):
                data['data_venda'] = datetime.now()
        
        # Processa os itens da venda
        itens_data = data.pop('itens', [])
        
        # Cria a instância da venda
        venda = cls(**data)
        
        # Adiciona os itens
        venda.itens = [ItemVenda.from_dict(item) for item in itens_data]
        
        return venda
    
    def validar(self) -> List[str]:
        """
        Valida os dados da venda.
        
        Returns:
            Lista de mensagens de erro (vazia se válido)
        """
        erros = []
        
        if not self.itens:
            erros.append("A venda deve conter pelo menos um item.")
        
        if self.cliente_id is None:
            erros.append("Um cliente deve ser selecionado.")
        
        if not self.forma_pagamento:
            erros.append("A forma de pagamento é obrigatória.")
        
        # Verifica se há estoque suficiente para todos os itens
        for item in self.itens:
            produto = Produto.buscar_por_id(item.produto_id)
            if not produto or produto.estoque < item.quantidade:
                erros.append(f"Estoque insuficiente para o produto: {item.produto_nome}")
        
        return erros
    
    # Métodos de persistência
    
    @classmethod
    def gerar_codigo_venda(cls) -> str:
        """
        Gera um código único para a venda.
        
        Returns:
            Código da venda no formato V{ano}{mês}{dia}{sequencial}
        """
        try:
            # Obtém o próximo número sequencial
            result = execute_query(
                "SELECT COALESCE(MAX(CAST(SUBSTR(codigo, 10) AS INTEGER)), 0) + 1 FROM vendas WHERE codigo LIKE ?",
                (f"V{datetime.now().strftime('%Y%m%d')}%",),
                fetch="value"
            )
            
            sequencial = result or 1
            return f"V{datetime.now().strftime('%Y%m%d')}{sequencial:04d}"
            
        except Exception as e:
            logger.error(f"Erro ao gerar código de venda: {e}")
            # Fallback: usa timestamp atual como código
            return f"V{int(datetime.now().timestamp())}"
    
    @classmethod
    def buscar_por_id(cls, venda_id: int) -> Optional['Venda']:
        """
        Busca uma venda pelo ID.
        
        Args:
            venda_id: ID da venda
            
        Returns:
            Instância de Venda ou None se não encontrada
        """
        try:
            # Busca os dados da venda
            venda_data = execute_query(
                """
                SELECT 
                    v.*,
                    c.nome as cliente_nome,
                    u.nome as usuario_nome
                FROM vendas v
                LEFT JOIN clientes c ON v.cliente_id = c.id
                LEFT JOIN usuarios u ON v.usuario_id = u.id
                WHERE v.id = ?
                """,
                (venda_id,),
                fetch="one"
            )
            
            if not venda_data:
                return None
            
            # Busca os itens da venda
            itens_data = execute_query(
                """
                SELECT 
                    iv.*,
                    p.nome as produto_nome
                FROM itens_venda iv
                JOIN produtos p ON iv.produto_id = p.id
                WHERE iv.venda_id = ?
                """,
                (venda_id,),
                fetch="all"
            )
            
            # Cria a instância da venda
            venda = cls.from_dict(dict(venda_data))
            venda.itens = [ItemVenda.from_dict(dict(item)) for item in itens_data]
            
            return venda
            
        except Exception as e:
            logger.error(f"Erro ao buscar venda ID {venda_id}: {e}")
            return None
    
    @classmethod
    def buscar_por_codigo(cls, codigo: str) -> Optional['Venda']:
        """
        Busca uma venda pelo código.
        
        Args:
            codigo: Código da venda
            
        Returns:
            Instância de Venda ou None se não encontrada
        """
        try:
            # Primeiro, busca o ID da venda pelo código
            result = execute_query(
                "SELECT id FROM vendas WHERE codigo = ?",
                (codigo,),
                fetch="one"
            )
            
            if not result:
                return None
                
            # Usa o método buscar_por_id para carregar a venda completa
            return cls.buscar_por_id(result['id'])
            
        except Exception as e:
            logger.error(f"Erro ao buscar venda por código {codigo}: {e}")
            return None
    
    @classmethod
    def buscar_por_periodo(
            cls,
            data_inicio: datetime,
            data_fim: datetime,
            status: Optional[str] = None,
            usuario_id: Optional[int] = None
        ) -> List['Venda']:
        """
        Busca vendas dentro de um período específico.
        
        Args:
            data_inicio: Data de início do período
            data_fim: Data de fim do período
            status: Status da venda (opcional)
            usuario_id: ID do usuário (vendedor) para filtro (opcional)
            
        Returns:
            Lista de Vendas que correspondem aos critérios
        """
        return cls.buscar_todas(
            data_inicio=data_inicio.date(),
            data_fim=data_fim.date(),
            status=status,
            usuario_id=usuario_id,
            ordenar_por='data_venda',
            ordem='DESC',
            limite=0  # Sem limite de registros
        )
        
    @classmethod
    def buscar_todas(
            cls,
            data_inicio: Optional[date] = None,
            data_fim: Optional[date] = None,
            cliente_id: Optional[int] = None,
            usuario_id: Optional[int] = None,
            status: Optional[str] = None,
            forma_pagamento: Optional[str] = None,
            ordenar_por: str = 'data_venda',
            ordem: str = 'DESC',
            limite: int = 100,
            offset: int = 0
        ) -> List['Venda']:
        """
        Busca vendas com base nos filtros fornecidos.
        
        Args:
            data_inicio: Data inicial para filtro
            data_fim: Data final para filtro
            cliente_id: ID do cliente para filtro
            usuario_id: ID do usuário (vendedor) para filtro
            status: Status da venda (aberta, finalizada, cancelada)
            forma_pagamento: Forma de pagamento para filtro
            ordenar_por: Campo para ordenação (data_venda, total, codigo)
            ordem: 'ASC' para ascendente, 'DESC' para descendente
            limite: Número máximo de registros por página (0 para sem limite)
            offset: Número de registros a pular
            
        Returns:
            Lista de Vendas que correspondem aos filtros
        """
        try:
            query = """
                SELECT v.*, c.nome as cliente_nome, u.nome as usuario_nome
                FROM vendas v
                LEFT JOIN clientes c ON v.cliente_id = c.id
                LEFT JOIN usuarios u ON v.usuario_id = u.id
                WHERE 1=1
            """
            params = []
            
            # Aplica filtros
            if data_inicio:
                query += " AND DATE(v.data_venda) >= ?"
                params.append(data_inicio.strftime('%Y-%m-%d'))
                
            if data_fim:
                query += " AND DATE(v.data_venda) <= ?"
                params.append(data_fim.strftime('%Y-%m-%d'))
                
            if cliente_id:
                query += " AND v.cliente_id = ?"
                params.append(cliente_id)
                
            if usuario_id:
                query += " AND v.usuario_id = ?"
                params.append(usuario_id)
                
            if status:
                query += " AND v.status = ?"
                params.append(status)
                
            if forma_pagamento:
                query += " AND v.forma_pagamento = ?"
                params.append(forma_pagamento)
                
            # Ordenação
            if ordenar_por in ['data_venda', 'total', 'codigo']:
                query += f" ORDER BY v.{ordenar_por} {ordem.upper()}"
            else:
                query += " ORDER BY v.data_venda DESC"
                
            # Paginação (apenas se limite > 0)
            if limite > 0:
                query += " LIMIT ? OFFSET ?"
                params.extend([limite, offset])
            
            # Executa a consulta
            resultados = execute_query(query, tuple(params), fetch="all")
            
            # Converte os resultados em objetos Venda
            vendas = []
            for venda_dict in resultados:
                venda = Venda.from_dict(venda_dict)
                venda.cliente_nome = venda_dict.get('cliente_nome', '')
                venda.usuario_nome = venda_dict.get('usuario_nome', '')
                
                # Busca os itens da venda
                itens_query = """
                    SELECT iv.*, p.nome as produto_nome, p.codigo_barras
                    FROM itens_venda iv
                    JOIN produtos p ON iv.produto_id = p.id
                    WHERE iv.venda_id = ?
                """
                itens = execute_query(itens_query, (venda.id,), fetch="all")
                venda.itens = [ItemVenda(**item) for item in itens]
                
                vendas.append(venda)
                
            return vendas
                
        except Exception as e:
            logger.error(f"Erro ao buscar vendas: {e}")
            return []
    
    def salvar(self, usuario_id: int) -> bool:
        """
        Salva a venda no banco de dados.
        
        Args:
            usuario_id: ID do usuário que está realizando a venda
            
        Returns:
            True se a venda foi salva com sucesso, False caso contrário
        """
        # Valida os dados antes de salvar
        erros = self.validar()
        if erros:
            logger.warning(f"Erros de validação ao salvar venda: {', '.join(erros)}")
            return False
            
        # Verifica se o usuário existe
        usuario = Usuario.buscar_por_id(usuario_id)
        if not usuario:
            logger.warning(f"Usuário ID {usuario_id} não encontrado")
            return False
            
        try:
            # Inicia uma transação
            with execute_query("BEGIN TRANSACTION") as conn:
                try:
                    if self.id is None:
                        # Nova venda
                        self.codigo = self.codigo or self.gerar_codigo()
                        self.usuario_id = usuario_id
                        self.usuario_nome = usuario.nome
                        
                        # Insere a venda
                        venda_id = execute_query(
                            """
                            INSERT INTO vendas (
                                codigo, cliente_id, usuario_id, data_venda,
                                subtotal, desconto, total, forma_pagamento,
                                status, observacoes
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                self.codigo,
                                self.cliente_id,
                                self.usuario_id,
                                self.data_venda.isoformat(),
                                self.subtotal,
                                self.desconto,
                                self.total,
                                self.forma_pagamento.lower(),
                                self.status.lower(),
                                self.observacoes
                            ),
                            fetch="lastrowid"
                        )
                        
                        self.id = venda_id
                        
                        # Insere os itens da venda
                        for item in self.itens:
                            execute_query(
                                """
                                INSERT INTO itens_venda (
                                    venda_id, produto_id, quantidade,
                                    preco_unitario, desconto, subtotal
                                )
                                VALUES (?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    self.id,
                                    item.produto_id,
                                    item.quantidade,
                                    item.preco_unitario,
                                    item.desconto,
                                    item.subtotal
                                ),
                                fetch="none"
                            )
                            
                            # Atualiza o estoque do produto
                            execute_query(
                                """
                                UPDATE produtos 
                                SET estoque = estoque - ?
                                WHERE id = ?
                                """,
                                (item.quantidade, item.produto_id),
                                fetch="none"
                            )
                        
                        logger.info(f"Nova venda cadastrada: {self.codigo} (ID: {self.id})")
                        
                    else:
                        # Atualização de venda existente
                        # Implementar lógica de atualização se necessário
                        pass
                    
                    # Confirma a transação
                    execute_query("COMMIT", fetch="none")
                    return True
                    
                except Exception as e:
                    # Desfaz a transação em caso de erro
                    execute_query("ROLLBACK", fetch="none")
                    logger.error(f"Erro ao salvar venda: {e}")
                    return False
                    
        except Exception as e:
            logger.error(f"Erro ao iniciar transação: {e}")
            return False
    
    def cancelar(self, motivo: str = '') -> bool:
        """
        Cancela uma venda, estornando os produtos ao estoque.
        
        Args:
            motivo: Motivo do cancelamento
            
        Returns:
            True se o cancelamento foi bem-sucedido, False caso contrário
        """
        if not self.id or self.status == 'cancelada':
            return False
            
        try:
            # Inicia uma transação
            with execute_query("BEGIN TRANSACTION") as conn:
                try:
                    # Estorna os itens ao estoque
                    for item in self.itens:
                        execute_query(
                            """
                            UPDATE produtos 
                            SET estoque = estoque + ?
                            WHERE id = ?
                            """,
                            (item.quantidade, item.produto_id),
                            fetch="none"
                        )
                    
                    # Atualiza o status da venda
                    execute_query(
                        """
                        UPDATE vendas 
                        SET status = 'cancelada',
                            observacoes = COALESCE(observacoes, '') || ?
                        WHERE id = ?
                        """,
                        (f"\nCancelada em {datetime.now().strftime('%d/%m/%Y %H:%M')}. Motivo: {motivo}", self.id),
                        fetch="none"
                    )
                    
                    # Atualiza o status na instância
                    self.status = 'cancelada'
                    self.observacoes = f"{self.observacoes or ''}\nCancelada em {datetime.now().strftime('%d/%m/%Y %H:%M')}. Motivo: {motivo}"
                    
                    # Confirma a transação
                    execute_query("COMMIT", fetch="none")
                    logger.info(f"Venda {self.codigo} cancelada com sucesso")
                    return True
                    
                except Exception as e:
                    # Desfaz a transação em caso de erro
                    execute_query("ROLLBACK", fetch="none")
                    logger.error(f"Erro ao cancelar venda {self.codigo}: {e}")
                    return False
                    
        except Exception as e:
            logger.error(f"Erro ao iniciar transação de cancelamento: {e}")
            return False
    
    def gerar_codigo(self) -> str:
        """
        Gera um código único para a venda.
        
        Returns:
            Código da venda no formato V{ano}{mês}{dia}{sequencial}
        """
        try:
            # Obtém o próximo número sequencial
            result = execute_query(
                "SELECT COALESCE(MAX(CAST(SUBSTR(codigo, 10) AS INTEGER)), 0) + 1 FROM vendas WHERE codigo LIKE ?",
                (f"V{datetime.now().strftime('%Y%m%d')}%",),
                fetch="value"
            )
            
            sequencial = result or 1
            return f"V{datetime.now().strftime('%Y%m%d')}{sequencial:04d}"
            
        except Exception as e:
            logger.error(f"Erro ao gerar código de venda: {e}")
            # Fallback: usa timestamp atual como código
            return f"V{int(datetime.now().timestamp())}"

# Testes unitários
if __name__ == "__main__":
    # Teste de criação de venda
    venda = Venda()
    
    # Adiciona itens à venda
    produto1 = Produto.buscar_por_id(1)  # Supondo que exista um produto com ID 1
    produto2 = Produto.buscar_por_id(2)  # Supondo que exista um produto com ID 2
    
    if produto1 and produto2:
        venda.adicionar_item(produto1, quantidade=2)
        venda.adicionar_item(produto2, quantidade=1, desconto=5.0)
        
        # Define os dados da venda
        venda.cliente_id = 1  # Supondo que exista um cliente com ID 1
        venda.forma_pagamento = 'cartao_credito'
        venda.observacoes = "Venda de teste"
        
        # Calcula totais
        venda.calcular_totais()
        
        print(f"Venda criada: {venda.codigo}")
        print(f"Total: {format_currency(venda.total)}")
        
        # Teste de serialização para dicionário
        venda_dict = venda.to_dict()
        print(f"Venda como dicionário: {venda_dict}")
        
        # Teste de criação a partir de dicionário
        nova_venda = Venda.from_dict(venda_dict)
        print(f"Nova venda a partir de dicionário: {nova_venda.codigo}")
    else:
        print("Produtos não encontrados para teste")
