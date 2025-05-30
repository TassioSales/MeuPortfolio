"""
Módulo para gerenciamento de ativos financeiros.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from decimal import Decimal
import logging
from sqlalchemy import func, and_, or_
from ..models.ativo import Ativo, HistoricoPreco
from ..models.usuario import Usuario
from .. import db
from ..utils.logger import logger
from ..exceptions import (
    InvalidOperationError,
    AssetNotFoundError,
    ValidationError
)

class AtivoService:
    """Classe para gerenciar operações relacionadas a ativos financeiros."""
    
    @staticmethod
    def obter_ativos(
        filtros: Optional[Dict] = None,
        pagina: int = 1,
        itens_por_pagina: int = 20,
        ordenar_por: str = 'symbol',
        ordem: str = 'asc'
    ) -> Dict:
        """
        Obtém uma lista paginada de ativos com base nos filtros fornecidos.
        
        Args:
            filtros (Dict, optional): Dicionário com os filtros a serem aplicados.
            pagina (int, optional): Número da página a ser retornada. Padrão: 1.
            itens_por_pagina (int, optional): Número de itens por página. Padrão: 20.
            ordenar_por (str, optional): Campo para ordenação. Padrão: 'symbol'.
            ordem (str, optional): Ordem de classificação ('asc' ou 'desc'). Padrão: 'asc'.
            
        Returns:
            Dict: Dicionário contendo os ativos e metadados de paginação.
        """
        try:
            query = Ativo.query
            
            # Aplica os filtros
            if filtros:
                if 'tipo' in filtros and filtros['tipo']:
                    query = query.filter(Ativo.tipo == filtros['tipo'])
                    
                if 'categoria' in filtros and filtros['categoria']:
                    query = query.filter(Ativo.categoria == filtros['categoria'])
                    
                if 'bolsa' in filtros and filtros['bolsa']:
                    query = query.filter(Ativo.bolsa == filtros['bolsa'])
                    
                if 'setor' in filtros and filtros['setor']:
                    query = query.filter(Ativo.setor == filtros['setor'])
                    
                if 'subsetor' in filtros and filtros['subsetor']:
                    query = query.filter(Ativo.subsetor == filtros['subsetor'])
                    
                if 'segmento' in filtros and filtros['segmento']:
                    query = query.filter(Ativo.segmento == filtros['segmento'])
                    
                if 'search' in filtros and filtros['search']:
                    search = f"%{filtros['search']}%"
                    query = query.filter(
                        or_(
                            Ativo.symbol.ilike(search),
                            Ativo.nome.ilike(search),
                            Ativo.nome_completo.ilike(search)
                        )
                    )
            
            # Ordenação
            order_field = getattr(Ativo, ordenar_por, Ativo.symbol)
            
            if ordem.lower() == 'desc':
                order_field = order_field.desc()
            
            query = query.order_by(order_field)
            
            # Paginação
            paginacao = query.paginate(page=pagina, per_page=itens_por_pagina, error_out=False)
            
            # Prepara os dados para retorno
            ativos = []
            for ativo in paginacao.items:
                ativos.append(ativo.to_dict())
            
            return {
                'itens': ativos,
                'pagina_atual': paginacao.page,
                'itens_por_pagina': paginacao.per_page,
                'total_itens': paginacao.total,
                'total_paginas': paginacao.pages
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter ativos: {str(e)}")
            raise
    
    @staticmethod
    def obter_por_id(ativo_id: int) -> Optional[Dict]:
        """
        Obtém um ativo pelo seu ID.
        
        Args:
            ativo_id (int): ID do ativo.
            
        Returns:
            Optional[Dict]: Dicionário com os dados do ativo ou None se não encontrado.
        """
        try:
            ativo = Ativo.query.get(ativo_id)
            
            if not ativo:
                return None
                
            return ativo.to_dict()
            
        except Exception as e:
            logger.error(f"Erro ao obter ativo {ativo_id}: {str(e)}")
            raise
    
    @staticmethod
    def obter_por_symbol(symbol: str) -> Optional[Dict]:
        """
        Obtém um ativo pelo seu símbolo.
        
        Args:
            symbol (str): Símbolo do ativo.
            
        Returns:
            Optional[Dict]: Dicionário com os dados do ativo ou None se não encontrado.
        """
        try:
            ativo = Ativo.query.filter_by(symbol=symbol).first()
            
            if not ativo:
                return None
                
            return ativo.to_dict()
            
        except Exception as e:
            logger.error(f"Erro ao obter ativo {symbol}: {str(e)}")
            raise
    
    @staticmethod
    def obter_precos_atuais(symbols: List[str]) -> Dict[str, float]:
        """
        Obtém os preços atuais de uma lista de símbolos.
        
        Args:
            symbols (List[str]): Lista de símbolos dos ativos.
            
        Returns:
            Dict[str, float]: Dicionário com os preços atuais dos ativos.
        """
        try:
            if not symbols:
                return {}
                
            # Remove duplicatas e converte para maiúsculas
            symbols = list({s.upper() for s in symbols if s})
            
            # Busca os ativos no banco de dados
            ativos = Ativo.query.filter(Ativo.symbol.in_(symbols)).all()
            
            # Cria um dicionário com os preços atuais
            precos = {ativo.symbol: float(ativo.preco_atual) for ativo in ativos if ativo.preco_atual is not None}
            
            return precos
            
        except Exception as e:
            logger.error(f"Erro ao obter preços atuais: {str(e)}")
            raise
    
    @staticmethod
    def obter_historico_precos(
        symbol: str,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
        intervalo: str = '1d',
        limit: int = 100
    ) -> List[Dict]:
        """
        Obtém o histórico de preços de um ativo.
        
        Args:
            symbol (str): Símbolo do ativo.
            data_inicio (datetime, optional): Data de início do histórico.
            data_fim (datetime, optional): Data de fim do histórico.
            intervalo (str, optional): Intervalo dos dados ('1d', '1w', '1m', '1y'). Padrão: '1d'.
            limit (int, optional): Número máximo de registros a retornar. Padrão: 100.
            
        Returns:
            List[Dict]: Lista de dicionários com o histórico de preços.
        """
        try:
            # Verifica se o ativo existe
            ativo = Ativo.query.filter_by(symbol=symbol).first()
            if not ativo:
                raise AssetNotFoundError(f"Ativo {symbol} não encontrado.")
            
            # Define as datas padrão se não fornecidas
            if not data_fim:
                data_fim = datetime.utcnow()
                
            if not data_inicio:
                # Define a data de início com base no intervalo
                intervalo_map = {
                    '1d': timedelta(days=1),
                    '1w': timedelta(weeks=1),
                    '1m': timedelta(days=30),
                    '3m': timedelta(days=90),
                    '6m': timedelta(days=180),
                    '1y': timedelta(days=365),
                    '2y': timedelta(days=730),
                    '5y': timedelta(days=1825),
                    'max': None
                }
                
                delta = intervalo_map.get(intervalo, timedelta(days=30))
                data_inicio = data_fim - delta if delta else datetime(1970, 1, 1)
            
            # Busca os dados históricos
            query = HistoricoPreco.query.filter(
                HistoricoPreco.ativo_id == ativo.id,
                HistoricoPreco.timestamp.between(data_inicio, data_fim)
            ).order_by(HistoricoPreco.timestamp.asc())
            
            if limit > 0:
                query = query.limit(limit)
            
            historico = query.all()
            
            # Formata os dados para retorno
            dados = []
            for registro in historico:
                dados.append({
                    'data': registro.timestamp.isoformat(),
                    'preco': float(registro.preco),
                    'volume': float(registro.volume) if registro.volume else None,
                    'ativo_id': registro.ativo_id
                })
            
            return dados
            
        except Exception as e:
            logger.error(f"Erro ao obter histórico de preços para {symbol}: {str(e)}")
            raise
    
    @staticmethod
    def atualizar_precos() -> Dict[str, int]:
        """
        Atualiza os preços de todos os ativos ativos no banco de dados.
        
        Returns:
            Dict[str, int]: Dicionário com o número de ativos atualizados e erros.
        """
        try:
            from ..services import BinanceService, BrapiService, YFinanceService
            
            # Obtém todos os ativos ativos
            ativos = Ativo.query.filter_by(ativo=True).all()
            
            if not ativos:
                return {'atualizados': 0, 'erros': 0}
            
            # Agrupa os ativos por fonte
            ativos_por_fonte = {}
            for ativo in ativos:
                if ativo.fonte not in ativos_por_fonte:
                    ativos_por_fonte[ativo.fonte] = []
                ativos_por_fonte[ativo.fonte].append(ativo)
            
            atualizados = 0
            erros = 0
            
            # Atualiza os preços por fonte
            for fonte, ativos_fonte in ativos_por_fonte.items():
                try:
                    if fonte == 'binance':
                        for ativo in ativos_fonte:
                            try:
                                preco = BinanceService.get_price(ativo.symbol)
                                if preco:
                                    ativo.preco_atual = Decimal(str(preco['preco']))
                                    ativo.ultima_atualizacao = datetime.utcnow()
                                    atualizados += 1
                            except Exception as e:
                                logger.error(f"Erro ao atualizar preço do ativo {ativo.symbol} na Binance: {str(e)}")
                                erros += 1
                                
                    elif fonte == 'brapi':
                        brapi = BrapiService()
                        for ativo in ativos_fonte:
                            try:
                                cotacao = brapi.get_quote(ativo.symbol)
                                if cotacao and 'current_price' in cotacao:
                                    ativo.preco_atual = Decimal(str(cotacao['current_price']))
                                    ativo.ultima_atualizacao = datetime.utcnow()
                                    atualizados += 1
                            except Exception as e:
                                logger.error(f"Erro ao atualizar preço do ativo {ativo.symbol} na Brapi: {str(e)}")
                                erros += 1
                                
                    elif fonte == 'yfinance':
                        for ativo in ativos_fonte:
                            try:
                                info = YFinanceService.get_ticker_info(ativo.symbol)
                                if info and 'preco' in info:
                                    ativo.preco_atual = Decimal(str(info['preco']))
                                    ativo.ultima_atualizacao = datetime.utcnow()
                                    atualizados += 1
                            except Exception as e:
                                logger.error(f"Erro ao atualizar preço do ativo {ativo.symbol} no Yahoo Finance: {str(e)}")
                                erros += 1
                    
                except Exception as e:
                    logger.error(f"Erro ao atualizar preços da fonte {fonte}: {str(e)}")
                    erros += len(ativos_fonte)
            
            # Salva as alterações no banco de dados
            db.session.commit()
            
            return {
                'atualizados': atualizados,
                'erros': erros,
                'total': len(ativos)
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar preços: {str(e)}")
            raise

# Exemplo de uso:
if __name__ == "__main__":
    from .. import create_app
    app = create_app()
    
    with app.app_context():
        # Listar ativos
        ativos = AtivoService.obter_ativos(
            filtros={'tipo': 'acao'},
            pagina=1,
            itens_por_pagina=10,
            ordenar_por='symbol',
            ordem='asc'
        )
        print(f"Ativos encontrados: {len(ativos['itens'])}")
        
        # Obter ativo por ID
        if ativos['itens']:
            ativo_id = ativos['itens'][0]['id']
            ativo = AtivoService.obter_por_id(ativo_id)
            print(f"Ativo por ID: {ativo['symbol']} - {ativo['nome']}")
        
        # Obter histórico de preços
        historico = AtivoService.obter_historico_precos(
            symbol='PETR4',
            intervalo='1m',
            limit=30
        )
        print(f"Histórico de preços: {len(historico)} registros")
        
        # Atualizar preços
        resultado = AtivoService.atualizar_precos()
        print(f"Preços atualizados: {resultado['atualizados']} de {resultado['total']} (erros: {resultado['erros']})")
