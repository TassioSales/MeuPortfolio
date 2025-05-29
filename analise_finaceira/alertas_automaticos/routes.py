import os
import sys
import traceback
from pathlib import Path
from datetime import datetime
from flask import (
    render_template, request, redirect, url_for, flash, jsonify, current_app, g, Blueprint, make_response
)

# Adicionar o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger, log_function, LogLevel

# Importar o blueprint do pacote
from . import bp
from .src.alertasAutomaticos import GerenciadorAlertas

# Configurar logger
logger = get_logger('alertas_automaticos.routes')

@log_function(log_args=True, log_result=False, track_performance=True)
def get_db_connection():
    """Cria uma conexão com o banco de dados."""
    try:
        import sqlite3
        from pathlib import Path
        
        # Obtém o diretório raiz do projeto (dois níveis acima deste arquivo)
        project_root = Path(__file__).parent.parent
        db_path = project_root / 'banco' / 'financas.db'
        
        # Garante que o diretório do banco de dados existe
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"Conectando ao banco de dados em: {db_path}")
        
        # Conecta ao banco de dados SQLite
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        
        return conn
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco de dados: {str(e)}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise

@log_function(level=LogLevel.DEBUG, log_args=True, log_result=True)
def get_alertas_paginados(pagina=1, itens_por_pagina=20, tipo=None, prioridade=None, status=None):
    """
    Retorna os alertas automáticos com paginação e filtros opcionais.
    
    Args:
        pagina: Número da página atual
        itens_por_pagina: Quantidade de itens por página
        tipo: Filtro por tipo de alerta
        prioridade: Filtro por prioridade
        status: Filtro por status
        
    Returns:
        dict: Dicionário com os alertas e informações de paginação
    """
    logger.debug(f"Buscando alertas - Página: {pagina}, Itens por página: {itens_por_pagina}, "
                f"tipo: {tipo}, Prioridade: {prioridade}, Status: {status}")
    
    offset = (pagina - 1) * itens_por_pagina
    
    # Construir a consulta base
    query = """
        SELECT * FROM alertas_automaticos
        WHERE 1=1
    """
    params = []
    
    # Adicionar filtros
    if tipo:
        query += " AND tipo = ?"
        params.append(tipo)
        
    if prioridade:
        query += " AND prioridade = ?"
        params.append(prioridade.lower())
        
    if status:
        query += " AND status = ?"
        params.append(status.lower())
    
    # Ordenação
    query += " ORDER BY data_ocorrencia DESC, prioridade DESC"
    
    # Contar total de itens para paginação
    count_query = "SELECT COUNT(*) as total FROM (" + query.replace("SELECT *", "SELECT 1") + ")"
    
    # Adicionar paginação à consulta principal
    query += " LIMIT ? OFFSET ?"
    params.extend([itens_por_pagina, offset])
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Executar contagem total
        logger.debug(f"Executando contagem total: {count_query} com parâmetros: {params[:-2]}")
        cursor.execute(count_query, params[:-2])  # Remove os parâmetros de paginação
        total = cursor.fetchone()['total']
        logger.debug(f"Total de alertas encontrados: {total}")
        
        # Executar consulta principal
        logger.debug(f"Executando consulta: {query} com parâmetros: {params}")
        cursor.execute(query, params)
        alertas = [dict(row) for row in cursor.fetchall()]
        logger.debug(f"Alertas encontrados: {len(alertas)}")
        
        # Calcular informações de paginação
        total_paginas = (total + itens_por_pagina - 1) // itens_por_pagina
        
        result = {
            'alertas': alertas,
            'pagina_atual': pagina,
            'itens_por_pagina': itens_por_pagina,
            'total_itens': total,
            'total_paginas': total_paginas
        }
        
        logger.debug(f"Resultado da consulta: {len(alertas)} alertas, {total_paginas} páginas no total")
        return result
        
    except Exception as e:
        error_msg = f"Erro ao buscar alertas automáticos: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Traceback: {traceback.format_exc()}")
        
        return {
            'alertas': [],
            'pagina_atual': 1,
            'itens_por_pagina': itens_por_pagina,
            'total_itens': 0,
            'total_paginas': 1
        }
    finally:
        if 'conn' in locals():
            conn.close()

@bp.route('/executar-analise', methods=['POST'])
@log_function(level=LogLevel.INFO)
def executar_analise():
    """Executa a análise de alertas automáticos."""
    try:
        logger.info("Iniciando execução da análise de alertas automáticos")
        gerenciador = GerenciadorAlertas()
        total_alertas = gerenciador.executar_analise()
        logger.info(f"Análise concluída. {total_alertas} alertas gerados.")
        return jsonify({
            'sucesso': True,
            'total_alertas': total_alertas,
            'mensagem': f'Análise concluída. {total_alertas} alertas gerados.'
        })
    except Exception as e:
        logger.error(f"Erro ao executar análise: {str(e)}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'sucesso': False,
            'erro': str(e),
            'mensagem': 'Erro ao executar análise de alertas.'
        }), 500

@bp.route('/')
@log_function(level=LogLevel.INFO)
def index():
    """Rota principal que exibe a lista de alertas automáticos."""
    try:
        # Por padrão, não executa a análise automaticamente
        executar_analise_auto = False
        
        # Verifica se foi solicitada uma execução manual
        if 'executar_analise' in request.args and request.args.get('executar_analise').lower() == 'true':
            try:
                logger.info("Executando análise de alertas a pedido do usuário")
                gerenciador = GerenciadorAlertas()
                total_alertas = gerenciador.executar_analise()
                logger.info(f"Análise concluída. {total_alertas} alertas gerados.")
                
                # Se for uma requisição AJAX, retornar JSON
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'sucesso': True,
                        'mensagem': f'Análise concluída com sucesso! {total_alertas} alertas gerados.',
                        'total_alertas': total_alertas
                    })
                
                # Se não for AJAX, redireciona para a mesma URL sem o parâmetro
                return redirect(url_for('alertas_automaticos.index'))
            except Exception as e:
                logger.error(f"Erro na análise de alertas: {str(e)}")
                logger.debug(f"Traceback: {traceback.format_exc()}")
                flash(f"Erro ao executar análise: {str(e)}", 'danger')
        
        # Verificar se é uma requisição de exportação
        exportar_csv = request.args.get('_export') == 'csv'
        
        # Obter parâmetros de paginação (não usamos paginação para exportação CSV)
        pagina = 1 if exportar_csv else request.args.get('pagina', 1, type=int)
        itens_por_pagina = 1000 if exportar_csv else request.args.get('itens_por_pagina', 20, type=int)
        
        # Obter parâmetros de filtro
        tipo = request.args.get('tipo')
        prioridade = request.args.get('prioridade')
        status = request.args.get('status')
        
        # Obter dados paginados
        resultado = get_alertas_paginados(
            pagina=pagina,
            itens_por_pagina=itens_por_pagina,
            tipo=tipo,
            prioridade=prioridade,
            status=status
        )
        
        # Criar dicionário de filtros ativos (sem incluir parâmetros de paginação)
        filtros = {
            'tipo': tipo,
            'prioridade': prioridade,
            'status': status,
            'itens_por_pagina': itens_por_pagina  # Mantemos apenas itens_por_pagina aqui
        }
        
        # Criar parâmetros para paginação
        paginacao = {
            'pagina': pagina,
            'itens_por_pagina': itens_por_pagina,
            'total_paginas': resultado['total_paginas'],
            'total_itens': resultado['total_itens']
        }
        
        # Obter valores distintos para os filtros
        conn = get_db_connection()
        try:
            # tipos de alerta
            cursor = conn.execute("SELECT DISTINCT tipo FROM alertas_automaticos ORDER BY tipo")
            tipos = [row['tipo'] for row in cursor.fetchall() if row['tipo']]
            
            # Prioridades
            cursor = conn.execute("SELECT DISTINCT prioridade FROM alertas_automaticos ORDER BY prioridade")
            prioridades = [row['prioridade'] for row in cursor.fetchall() if row['prioridade']]
            
            # Status
            cursor = conn.execute("SELECT DISTINCT status FROM alertas_automaticos ORDER BY status")
            status_list = [row['status'] for row in cursor.fetchall() if row['status']]
            
        finally:
            conn.close()
        
        # Adicionar data/hora atual para o template
        from datetime import datetime
        now = datetime.now()
        
        # Se for uma requisição de exportação CSV
        if exportar_csv:
            import csv
            import io
            
            # Criar um buffer para o CSV
            si = io.StringIO()
            cw = csv.writer(si, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            
            # Escrever cabeçalho
            cw.writerow([
                'ID', 'Título', 'Descrição', 'Tipo', 'Prioridade', 'Status',
                'Data Criação', 'Data Ocorrência', 'Lido', 'Data Leitura',
                'Ações Tomadas'
            ])
            
            # Função auxiliar para formatar datas
            def formatar_data(data):
                if not data:
                    return ''
                if isinstance(data, str):
                    try:
                        # Tenta converter a string para datetime
                        from datetime import datetime
                        data_obj = datetime.strptime(data, '%Y-%m-%d %H:%M:%S')
                        return data_obj.strftime('%d/%m/%Y %H:%M:%S')
                    except (ValueError, TypeError):
                        return data
                elif hasattr(data, 'strftime'):
                    return data.strftime('%d/%m/%Y %H:%M:%S')
                return str(data)
                
            # Escrever dados
            for alerta in resultado['alertas']:
                cw.writerow([
                    alerta['id'],
                    alerta['titulo'],
                    alerta['descricao'],
                    alerta['tipo'],
                    alerta['prioridade'],
                    alerta['status'],
                    formatar_data(alerta.get('data_criacao')),
                    formatar_data(alerta.get('data_ocorrencia')),
                    'Sim' if alerta.get('lido') else 'Não',
                    formatar_data(alerta.get('data_leitura')),
                    alerta.get('acoes_tomadas', '') or ''
                ])
            
            # Configurar a resposta
            output = si.getvalue()
            si.close()
            
            # Criar nome do arquivo com data e hora
            from datetime import datetime
            filename = f'alertas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            
            response = make_response(output)
            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            response.headers['Content-type'] = 'text/csv; charset=utf-8-sig'
            return response
        
        # Se não for exportação, retornar o template normal
        template_vars = {
            'alertas': resultado['alertas'],
            'paginacao': paginacao,
            'filtros': filtros,
            'tipos': tipos,
            'prioridades': prioridades,
            'status_list': status_list,
            'executar_analise_auto': executar_analise_auto,
            'opcoes_filtro': {
                'tipos': tipos,
                'prioridades': prioridades,
                'status_list': status_list
            },
            'now': now
        }
        
        return render_template('alertas_automaticos/index_automatico.html', **template_vars)      
    except Exception as e:
        error_msg = f"Erro na rota de alertas automáticos: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Traceback: {traceback.format_exc()}")
        flash('Ocorreu um erro ao carregar os alertas automáticos.', 'danger')
        
        # Retornar template com valores padrão em caso de erro
        template_vars = {
            'alertas': [],
            'paginacao': {
                'pagina': 1,
                'itens_por_pagina': 20,
                'total_itens': 0,
                'total_paginas': 1
            },
            'filtros': {
                'tipo': None,
                'prioridade': None,
                'status': None,
                'itens_por_pagina': 20
            },
            'tipos': [],
            'prioridades': [],
            'status_list': [],
            'executar_analise_auto': False,
            'opcoes_filtro': {
                'tipos': [],
                'prioridades': [],
                'status_list': []
            },
            'now': datetime.now()
        }
        return render_template('alertas_automaticos/index_automatico.html', **template_vars)

@bp.route('/limpar-alertas', methods=['POST'])
@log_function(level=LogLevel.INFO)
def limpar_alertas():
    """Remove todos os alertas do banco de dados."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Contar quantos registros serão removidos
        cursor.execute("SELECT COUNT(*) FROM alertas_automaticos")
        total = cursor.fetchone()[0]
        
        if total == 0:
            return jsonify({
                'sucesso': True,
                'mensagem': 'Não há alertas para remover.',
                'total_removidos': 0
            })
            
        # Remover todos os registros
        cursor.execute("DELETE FROM alertas_automaticos")
        conn.commit()
        
        logger.info(f"Removidos {total} alertas do banco de dados.")
        
        return jsonify({
            'sucesso': True,
            'mensagem': f'Foram removidos {total} alertas com sucesso!',
            'total_removidos': total
        })
        
    except Exception as e:
        error_msg = f"Erro ao limpar alertas: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Traceback: {traceback.format_exc()}")
        
        if 'conn' in locals():
            conn.rollback()
            
        return jsonify({
            'sucesso': False,
            'erro': str(e),
            'mensagem': 'Erro ao limpar alertas.'
        }), 500
    finally:
        if 'conn' in locals():
            conn.close()

@bp.route('/api/alertas')
@log_function(level=LogLevel.INFO, log_args=True, log_result=True)
def api_alertas():
    """API para obter a lista de alertas em formato JSON."""
    try:
        logger.info("Recebida requisição para API de alertas")
        
        # Obter parâmetros da URL
        pagina = int(request.args.get('pagina', 1))
        itens_por_pagina = int(request.args.get('itens_por_pagina', 20))
        tipo = request.args.get('tipo')
        prioridade = request.args.get('prioridade')
        status = request.args.get('status')
        
        logger.debug(f"Parâmetros da API - Página: {pagina}, Itens: {itens_por_pagina}, "
                   f"tipo: {tipo}, Prioridade: {prioridade}, Status: {status}")
        
        # Obter alertas com paginação e filtros
        dados = get_alertas_paginados(pagina, itens_por_pagina, tipo, prioridade, status)
        logger.debug(f"Encontrados {len(dados['alertas'])} alertas na página {pagina} de {dados['total_paginas']}")
        
        # Converter os objetos Row em dicionários
        alertas = []
        for alerta in dados['alertas']:
            alerta_dict = dict(alerta)
            # Converter datetime para string
            for key, value in alerta_dict.items():
                if isinstance(value, datetime):
                    alerta_dict[key] = value.isoformat()
            alertas.append(alerta_dict)
        
        # Preparar resposta
        response_data = {
            'success': True,
            'data': {
                'alertas': alertas,
                'pagina_atual': dados['pagina_atual'],
                'itens_por_pagina': dados['itens_por_pagina'],
                'total_itens': dados['total_itens'],
                'total_paginas': dados['total_paginas']
            }
        }
        
        logger.debug(f"Resposta da API preparada com {len(alertas)} alertas")
        return jsonify(response_data)
        
    except Exception as e:
        error_msg = f"Erro na API de alertas automáticos: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Traceback: {traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'error': 'Ocorreu um erro ao buscar os alertas automáticos.',
            'details': str(e) if current_app.debug else None
        }), 500

@bp.route('/<int:alerta_id>/marcar-lido', methods=['POST'])
@log_function(level=LogLevel.INFO, log_args=True, log_result=True)
def marcar_como_lido(alerta_id):
    """Marca um alerta como lido."""
    conn = None
    try:
        logger.info(f"Solicitada marcação de alerta como lido - ID: {alerta_id}")
        
        # Verificar se o alerta existe
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar se o alerta existe
        cursor.execute("SELECT * FROM alertas_automaticos WHERE id = ?", (alerta_id,))
        alerta = cursor.fetchone()
        
        if not alerta:
            logger.warning(f"Tentativa de marcar alerta inexistente como lido - ID: {alerta_id}")
            return jsonify({'success': False, 'error': 'Alerta não encontrado'}), 404
        
        logger.debug(f"Alerta encontrado - ID: {alerta_id}, Status atual: {alerta['status']}")
        
        # Verificar se já está marcado como lido
        if alerta['status'] == 'lido':
            logger.info(f"Alerta {alerta_id} já está marcado como lido")
            return jsonify({
                'success': True,
                'message': 'Alerta já estava marcado como lido',
                'alerta_id': alerta_id
            })
        
        # Atualizar o status para 'lido' e a data de atualização
        cursor.execute(
            """
            UPDATE alertas_automaticos 
            SET status = 'lido', data_atualizacao = CURRENT_TIMESTAMP 
            WHERE id = ?
            """,
            (alerta_id,)
        )
        
        conn.commit()
        logger.info(f"Alerta {alerta_id} marcado como lido com sucesso")
        
        return jsonify({
            'success': True,
            'message': 'Alerta marcado como lido com sucesso',
            'alerta_id': alerta_id
        })
        
    except Exception as e:
        if conn:
            conn.rollback()
            
        error_msg = f"Erro ao marcar alerta {alerta_id} como lido: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Traceback: {traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'error': 'Ocorreu um erro ao marcar o alerta como lido.',
            'details': str(e) if current_app.debug else None
        }), 500
        
    finally:
        if conn:
            conn.close()
