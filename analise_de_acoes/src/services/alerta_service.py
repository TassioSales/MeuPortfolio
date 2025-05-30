"""
Módulo para gerenciamento de alertas de preço.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from decimal import Decimal
import logging
from sqlalchemy import and_, or_
from ..models.alerta import Alerta
from ..models.ativo import Ativo
from ..models.usuario import Usuario
from .. import db
from ..utils.logger import logger
from ..exceptions import (
    InvalidOperationError,
    AssetNotFoundError,
    ValidationError
)

class AlertaService:
    """Classe para gerenciar operações relacionadas a alertas de preço."""
    
    @staticmethod
    def criar_alerta(
        usuario_id: int,
        symbol: str,
        tipo: str,
        preco_alvo: float,
        condicao: str,
        mensagem: Optional[str] = None,
        ativo_id: Optional[int] = None
    ) -> Dict:
        """
        Cria um novo alerta de preço.
        
        Args:
            usuario_id (int): ID do usuário que está criando o alerta.
            symbol (str): Símbolo do ativo (ex: 'PETR4', 'BTCUSDT').
            tipo (str): Tipo de alerta ('compra' ou 'venda').
            preco_alvo (float): Preço alvo para o alerta.
            condicao (str): Condição do alerta ('acima' ou 'abaixo').
            mensagem (str, optional): Mensagem personalizada para o alerta.
            ativo_id (int, optional): ID do ativo no banco de dados.
            
        Returns:
            Dict: Dicionário com os detalhes do alerta criado.
            
        Raises:
            ValidationError: Se os dados fornecidos forem inválidos.
            AssetNotFoundError: Se o ativo não for encontrado no banco de dados.
        """
        try:
            # Valida os dados de entrada
            if tipo not in [Alerta.TIPO_COMPRA, Alerta.TIPO_VENDA]:
                raise ValidationError(f"Tipo de alerta inválido. Deve ser '{Alerta.TIPO_COMPRA}' ou '{Alerta.TIPO_VENDA}'.")
                
            if condicao not in [Alerta.CONDICAO_ACIMA, Alerta.CONDICAO_ABAIXO]:
                raise ValidationError(f"Condição inválida. Deve ser '{Alerta.CONDICAO_ACIMA}' ou '{Alerta.CONDICAO_ABAIXO}'.")
                
            if preco_alvo <= 0:
                raise ValidationError("O preço alvo deve ser maior que zero.")
                
            # Verifica se o ativo existe no banco de dados
            if ativo_id:
                ativo = Ativo.query.get(ativo_id)
                if not ativo:
                    raise AssetNotFoundError(f"Ativo com ID {ativo_id} não encontrado.")
            else:
                # Tenta encontrar o ativo pelo símbolo
                ativo = Ativo.query.filter_by(symbol=symbol).first()
                
            # Cria o alerta
            alerta = Alerta(
                usuario_id=usuario_id,
                symbol=symbol,
                ativo_id=ativo.id if ativo else None,
                tipo=tipo,
                preco_alvo=Decimal(str(preco_alvo)),
                condicao=condicao,
                mensagem=mensagem
            )
            
            db.session.add(alerta)
            db.session.commit()
            
            return alerta.to_dict()
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar alerta: {str(e)}")
            raise
    
    @staticmethod
    def listar_alertas_ativos(usuario_id: Optional[int] = None) -> List[Dict]:
        """
        Lista todos os alertas ativos.
        
        Args:
            usuario_id (int, optional): ID do usuário para filtrar os alertas. Se None, retorna todos os alertas ativos.
            
        Returns:
            List[Dict]: Lista de dicionários com os alertas ativos.
        """
        try:
            query = Alerta.query.filter_by(status=Alerta.STATUS_ATIVO)
            
            if usuario_id is not None:
                query = query.filter_by(usuario_id=usuario_id)
                
            alertas = query.order_by(Alerta.data_criacao.desc()).all()
            
            return [alerta.to_dict() for alerta in alertas]
            
        except Exception as e:
            logger.error(f"Erro ao listar alertas ativos: {str(e)}")
            raise
    
    @staticmethod
    def listar_alertas_por_usuario(usuario_id: int, status: Optional[str] = None) -> List[Dict]:
        """
        Lista os alertas de um usuário, com opção de filtrar por status.
        
        Args:
            usuario_id (int): ID do usuário.
            status (str, optional): Status para filtrar os alertas. Se None, retorna todos os alertas do usuário.
            
        Returns:
            List[Dict]: Lista de dicionários com os alertas do usuário.
        """
        try:
            query = Alerta.query.filter_by(usuario_id=usuario_id)
            
            if status is not None:
                query = query.filter_by(status=status)
                
            alertas = query.order_by(Alerta.data_criacao.desc()).all()
            
            return [alerta.to_dict() for alerta in alertas]
            
        except Exception as e:
            logger.error(f"Erro ao listar alertas do usuário {usuario_id}: {str(e)}")
            raise
    
    @staticmethod
    def atualizar_alerta(
        alerta_id: int,
        usuario_id: int,
        **kwargs
    ) -> Optional[Dict]:
        """
        Atualiza um alerta existente.
        
        Args:
            alerta_id (int): ID do alerta a ser atualizado.
            usuario_id (int): ID do usuário que está atualizando o alerta.
            **kwargs: Campos a serem atualizados (preco_alvo, condicao, mensagem, status).
            
        Returns:
            Optional[Dict]: Dicionário com os detalhes do alerta atualizado ou None se não for encontrado.
            
        Raises:
            ValidationError: Se os dados fornecidos forem inválidos.
            InvalidOperationError: Se o alerta não puder ser atualizado.
        """
        try:
            alerta = Alerta.query.filter_by(id=alerta_id, usuario_id=usuario_id).first()
            
            if not alerta:
                return None
                
            # Valida os campos que podem ser atualizados
            campos_permitidos = {'preco_alvo', 'condicao', 'mensagem', 'status'}
            
            for campo, valor in kwargs.items():
                if campo in campos_permitidos:
                    if campo == 'preco_alvo' and valor <= 0:
                        raise ValidationError("O preço alvo deve ser maior que zero.")
                        
                    if campo == 'condicao' and valor not in [Alerta.CONDICAO_ACIMA, Alerta.CONDICAO_ABAIXO]:
                        raise ValidationError(f"Condição inválida. Deve ser '{Alerta.CONDICAO_ACIMA}' ou '{Alerta.CONDICAO_ABAIXO}'.")
                        
                    if campo == 'status' and valor not in [Alerta.STATUS_ATIVO, Alerta.STATUS_DISPARADO, Alerta.STATUS_CANCELADO]:
                        raise ValidationError("Status inválido.")
                    
                    setattr(alerta, campo, valor)
            
            # Se o status foi alterado para ATIVO, limpa a data de disparo
            if 'status' in kwargs and kwargs['status'] == Alerta.STATUS_ATIVO:
                alerta.data_disparo = None
                alerta.preco_disparo = None
            
            db.session.commit()
            
            return alerta.to_dict()
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar alerta {alerta_id}: {str(e)}")
            raise
    
    @staticmethod
    def excluir_alerta(alerta_id: int, usuario_id: int) -> bool:
        """
        Exclui um alerta.
        
        Args:
            alerta_id (int): ID do alerta a ser excluído.
            usuario_id (int): ID do usuário que está excluindo o alerta.
            
        Returns:
            bool: True se o alerta foi excluído com sucesso, False caso contrário.
        """
        try:
            alerta = Alerta.query.filter_by(id=alerta_id, usuario_id=usuario_id).first()
            
            if not alerta:
                return False
                
            db.session.delete(alerta)
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao excluir alerta {alerta_id}: {str(e)}")
            raise
    
    @staticmethod
    def verificar_alertas() -> List[Dict]:
        """
        Verifica se algum alerta ativo deve ser disparado com base nos preços atuais dos ativos.
        
        Returns:
            List[Dict]: Lista de alertas que foram disparados.
        """
        try:
            from ..services import AtivoService  # Importação local para evitar importação circular
            
            # Obtém todos os alertas ativos
            alertas = Alerta.query.filter_by(status=Alerta.STATUS_ATIVO).all()
            
            if not alertas:
                return []
                
            # Agrupa os símbolos únicos para buscar os preços de uma vez
            simbolos = list({alerta.symbol for alerta in alertas})
            
            # Obtém os preços atuais dos ativos
            precos = AtivoService.obter_precos_atuais(simbolos)
            
            alertas_disparados = []
            
            for alerta in alertas:
                if alerta.symbol not in precos:
                    continue
                    
                preco_atual = precos[alerta.symbol]
                
                # Verifica se a condição do alerta foi atendida
                if alerta.condicao == Alerta.CONDICAO_ACIMA and preco_atual >= alerta.preco_alvo:
                    alerta.trigger(preco_atual)
                    alertas_disparados.append(alerta.to_dict())
                elif alerta.condicao == Alerta.CONDICAO_ABAIXO and preco_atual <= alerta.preco_alvo:
                    alerta.trigger(preco_atual)
                    alertas_disparados.append(alerta.to_dict())
            
            if alertas_disparados:
                db.session.commit()
                
            return alertas_disparados
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao verificar alertas: {str(e)}")
            raise

# Exemplo de uso:
if __name__ == "__main__":
    from .. import create_app
    app = create_app()
    
    with app.app_context():
        # Criar um alerta
        alerta = AlertaService.criar_alerta(
            usuario_id=1,
            symbol="PETR4",
            tipo="compra",
            preco_alvo=25.50,
            condicao="abaixo",
            mensagem="Comprar PETR4 se cair para R$ 25,50"
        )
        print(f"Alerta criado: {alerta}")
        
        # Listar alertas ativos
        alertas_ativos = AlertaService.listar_alertas_ativos()
        print(f"Alertas ativos: {alertas_ativos}")
        
        # Atualizar alerta
        if alertas_ativos:
            alerta_atualizado = AlertaService.atualizar_alerta(
                alerta_id=alertas_ativos[0]['id'],
                usuario_id=1,
                preco_alvo=25.00,
                mensagem="Atualizado: Comprar PETR4 se cair para R$ 25,00"
            )
            print(f"Alerta atualizado: {alerta_atualizado}")
        
        # Excluir alerta
        if alertas_ativos:
            excluido = AlertaService.excluir_alerta(
                alerta_id=alertas_ativos[0]['id'],
                usuario_id=1
            )
            print(f"Alerta excluído: {excluido}")
