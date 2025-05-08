import sqlite3
from flask import jsonify, request, current_app
from .blueprint import alertas_manuais_bp
from .routes import get_db_connection
from . import logger

logger.info("Módulo de rotas da API de alertas inicializado")

@alertas_manuais_bp.route('/api/alertas')
def api_alertas():
    """API para listar alertas com filtros.
    
    Query Parameters:
        tipo (str, optional): Filtra por tipo de alerta
        categoria (str, optional): Filtra por categoria
        ativo (int, optional): Filtra por status ativo/inativo (1/0)
        
    Returns:
        JSON: Lista de alertas que correspondem aos filtros
    """
    logger.debug(f"Recebida requisição para API de alertas. Parâmetros: {dict(request.args)}")
    conn = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Parâmetros de filtro
        tipo = request.args.get('tipo')
        categoria = request.args.get('categoria')
        ativo = request.args.get('ativo', '1')
        
        logger.debug(f"Filtros aplicados - tipo: {tipo}, categoria: {categoria}, ativo: {ativo}")
        
        # Construir a consulta dinamicamente
        query = 'SELECT * FROM alertas_financas WHERE 1=1'
        params = []
        
        if tipo:
            query += ' AND tipo_alerta = ?'
            params.append(tipo)
            
        if categoria:
            query += ' AND categoria = ?'
            params.append(categoria)
            
        if ativo is not None:
            try:
                ativo_int = int(ativo)
                query += ' AND ativo = ?'
                params.append(ativo_int)
            except (ValueError, TypeError) as e:
                logger.warning(f"Valor inválido para parâmetro 'ativo': {ativo}")
        
        query += ' ORDER BY prioridade DESC, criado_em DESC'
        
        # Executar a consulta
        logger.debug(f"Executando consulta: {query}")
        logger.debug(f"Parâmetros: {params}")
        
        cursor.execute(query, params)
        alertas = []
        
        for alerta in cursor.fetchall():
            alertas.append(dict(alerta))
        
        logger.debug(f"Consulta retornou {len(alertas)} alertas")
        
        return jsonify({
            'status': 'success',
            'data': alertas,
            'count': len(alertas)
        })
        
    except sqlite3.Error as e:
        error_msg = f"Erro de banco de dados na API de alertas: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Erro ao acessar o banco de dados',
            'error': str(e)
        }), 500
    except Exception as e:
        error_msg = f"Erro inesperado na API de alertas: {str(e)}"
        logger.critical(error_msg, exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Ocorreu um erro inesperado ao processar sua solicitação.',
            'error': str(e)
        }), 500
    finally:
        if conn:
            try:
                conn.close()
                logger.debug("Conexão com o banco de dados fechada")
            except Exception as e:
                logger.error(f"Erro ao fechar conexão com o banco de dados: {str(e)}", exc_info=True)
