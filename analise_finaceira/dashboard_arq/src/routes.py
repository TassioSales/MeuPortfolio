from flask import (
    Blueprint, render_template, jsonify, request, 
    redirect, url_for, flash, session, 
    send_from_directory, send_file
)
from datetime import datetime, timedelta
import sqlite3
import pandas as pd
import os
from pathlib import Path
import sys

# Adiciona o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger, log_function, RequestContext
from .blueprint import dashboard_bp
from .inserir_dados import inserir_bp

# Configura o logger para este módulo
logger = get_logger("dashboard.routes")

# Importações de módulos locais
from . import despesas
from . import receitas
from . import transacoes
import json

# Importação opcional de gráficos
try:
    from . import graficos
except ImportError:
    graficos = None

# Configurações
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'banco', 'financas.db')

@dashboard_bp.route('/dashboard')
@dashboard_bp.endpoint('dashboard')
@log_function()
def dashboard():
    """
    Rota principal do dashboard
    
    Returns:
        Response: Página HTML renderizada do dashboard ou página de erro
    """
    # Configura o contexto da requisição
    RequestContext.update_context(
        endpoint=request.endpoint,
        ip=request.remote_addr,
        method=request.method,
        path=request.path,
        user_agent=request.user_agent.string
    )
    
    logger.info("Iniciando carregamento do dashboard")
    
    try:
        # Registrar parâmetros da requisição
        logger.debug(f"Parâmetros da requisição: {request.args}")
        
        # Obter dados para o dashboard com tratamento individual
        try:
            logger.debug("Obtendo totais de despesas dos últimos 12 meses...")
            total_despesas = despesas.obter_despesas_12_meses()
            logger.debug(f"Total de despesas dos últimos 12 meses: R$ {total_despesas:.2f}")
            
            logger.debug("Obtendo variação mensal de despesas...")
            variacao_despesas = 0.0  # Não calculamos variação mensal mais
            logger.debug(f"Variação de despesas: {variacao_despesas:.2f}%")
            
            logger.debug("Obtendo despesas por categoria dos últimos 12 meses...")
            despesas_por_categoria = despesas.obter_despesas_por_categoria()
            logger.debug(f"{len(despesas_por_categoria)} categorias de despesas encontradas")
            
            logger.debug("Obtendo totais de receitas...")
            total_receitas = receitas.obter_receitas_12_meses()
            logger.debug(f"Total de receitas dos últimos 12 meses: R$ {total_receitas:.2f}")
            
            logger.debug("Obtendo receitas por categoria dos últimos 12 meses...")
            receitas_por_categoria = receitas.obter_receitas_por_categoria()
            logger.debug(f"{len(receitas_por_categoria)} categorias de receitas encontradas")
            
            logger.debug("Obtendo saldo atual...")
            saldo_atual = transacoes.obter_saldo_atual()
            
            logger.debug("Obtendo transações recentes...")
            transacoes_recentes = transacoes.obter_transacoes_recentes(10)
            logger.debug(f"{len(transacoes_recentes)} transações recentes carregadas")
            
            # Calcular saldo do mês atual
            saldo_mes_atual = total_receitas - total_despesas
            
            # Verificar se o módulo de gráficos está disponível
            graficos_disponiveis = graficos is not None
            
            logger.info("Dados do dashboard carregados com sucesso")
            
            # Log de resumo
            logger.info(
                f"Resumo - Receitas: R$ {total_receitas:.2f} | "
                f"Despesas: R$ {total_despesas:.2f} | "
                f"Saldo: R$ {saldo_atual:.2f}"
            )
            
            # Caminhos para os gráficos
            grafico_receitas = url_for('dashboard.gerar_grafico_receitas')
            grafico_despesas = url_for('dashboard.gerar_grafico_despesas')
            grafico_fluxo = url_for('dashboard.gerar_grafico_fluxo_caixa')
            
            # Renderizar o template com os dados
            return render_template(
                'dashboard.html',
                active_page='dashboard',
                total_despesas=total_despesas,
                variacao_despesas=variacao_despesas,
                despesas_por_categoria=despesas_por_categoria,
                total_receitas=total_receitas,
                receitas_por_categoria=receitas_por_categoria,
                saldo_atual=saldo_atual,
                saldo_mes_atual=saldo_mes_atual,
                transacoes_recentes=transacoes_recentes,
                graficos_disponiveis=graficos_disponiveis,
                grafico_receitas=grafico_receitas,
                grafico_despesas=grafico_despesas,
                grafico_fluxo=grafico_fluxo,
                agora=datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            )
            
        except Exception as inner_e:
            logger.error(f"Erro ao carregar dados do dashboard: {str(inner_e)}", exc_info=True)
            raise
            
    except Exception as e:
        logger.critical("Falha crítica ao processar requisição do dashboard", exc_info=True)
        return render_template(
            'erro.html',
            mensagem="Ocorreu um erro inesperado ao carregar o dashboard.",
            detalhes=str(e)
        ), 500

@dashboard_bp.route('/gerar_grafico_despesas')
@log_function()
def gerar_grafico_despesas():
    """
    Rota para gerar e retornar o gráfico de despesas por categoria
    
    Query Params:
        meses_atras (int): Número de meses para análise (padrão: 12)
        
    Returns:
        Response: Arquivo HTML do gráfico ou mensagem de erro
    """
    # Configura o contexto da requisição
    RequestContext.update_context(
        endpoint=request.endpoint,
        ip=request.remote_addr,
        method=request.method,
        path=request.path,
        user_agent=request.user_agent.string,
        params=dict(request.args)
    )
    
    logger.info("Iniciando geração do gráfico de despesas por categoria")
    
    try:
        # Obter o parâmetro meses_atras da requisição (padrão: 12 meses)
        try:
            meses_atras = request.args.get('meses_atras', default=12, type=int)
            logger.debug(f"Parâmetro meses_atras: {meses_atras}")
            
            # Garantir que meses_atras seja no mínimo 1
            meses_atras = max(1, meses_atras)
            logger.debug(f"Meses a serem analisados: {meses_atras}")
            
        except ValueError as ve:
            logger.error(f"Valor inválido para meses_atras: {request.args.get('meses_atras')}", exc_info=True)
            return jsonify({
                "erro": f"Valor inválido para o parâmetro 'meses_atras': {request.args.get('meses_atras')}"
            }), 400
        
        # Garantir que o diretório de imagens existe
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            img_dir = os.path.join(base_dir, 'dashboard_arq', 'static', 'img')
            os.makedirs(img_dir, exist_ok=True)
            logger.debug(f"Diretório de imagens verificado/criado: {img_dir}")
            
        except Exception as dir_error:
            logger.critical(f"Falha ao criar diretório de imagens: {str(dir_error)}", exc_info=True)
            return jsonify({
                "erro": "Falha ao configurar o ambiente para geração do gráfico"
            }), 500
            
        # Gerar o gráfico
        try:
            logger.info("Importando módulo de geração de gráfico de despesas...")
            from .gerar_grafico_despesas import gerar_grafico_despesas_por_categoria
            
            logger.info(f"Gerando gráfico de despesas para os últimos {meses_atras} meses...")
            html_path = gerar_grafico_despesas_por_categoria(meses_atras=meses_atras)
            
            if not html_path:
                logger.error("O caminho do arquivo HTML retornado é inválido")
                return jsonify({"erro": "Falha ao gerar o gráfico: caminho inválido"}), 500
                
            if not os.path.exists(html_path):
                logger.error(f"Arquivo de gráfico não encontrado em: {html_path}")
                return jsonify({
                    "erro": f"Arquivo de gráfico não encontrado: {os.path.basename(html_path)}"
                }), 404
                
            logger.info(f"Grágico de despesas gerado com sucesso: {os.path.basename(html_path)}")
            
            # Configurar cabeçalhos para evitar cache
            response = send_file(
                html_path, 
                mimetype='text/html',
                as_attachment=False,
                download_name=os.path.basename(html_path)
            )
            
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            
            return response
            
        except ImportError as ie:
            logger.critical(f"Falha ao importar módulo de geração de gráficos: {str(ie)}", exc_info=True)
            return jsonify({
                "erro": "Módulo de geração de gráficos não disponível"
            }), 500
            
        except Exception as gen_error:
            logger.critical(f"Erro inesperado ao gerar gráfico: {str(gen_error)}", exc_info=True)
            return jsonify({
                "erro": f"Erro ao gerar gráfico: {str(gen_error)}"
            }), 500
            
    except Exception as e:
        logger.critical(f"Falha crítica ao processar requisição do gráfico: {str(e)}", exc_info=True)
        return jsonify({
            "erro": "Ocorreu um erro inesperado ao processar a requisição"
        }), 500



@dashboard_bp.route('/gerar_grafico_receitas')
@log_function()
def gerar_grafico_receitas():
    """
    Rota para gerar e retornar o gráfico de receitas
    
    Query Params:
        meses_atras (int): Número de meses para análise (padrão: 12)
        
    Returns:
        Response: Arquivo HTML do gráfico ou mensagem de erro
    """
    # Configura o contexto da requisição
    RequestContext.update_context(
        endpoint=request.endpoint,
        ip=request.remote_addr,
        method=request.method,
        path=request.path,
        user_agent=request.user_agent.string,
        params=dict(request.args)
    )
    
    logger.info("Iniciando geração do gráfico de receitas")
    
    try:
        # Obter o parâmetro meses_atras da requisição (padrão: 12 meses)
        try:
            meses_atras = request.args.get('meses_atras', default=12, type=int)
            logger.debug(f"Parâmetro meses_atras: {meses_atras}")
            
            # Garantir que meses_atras seja no mínimo 1
            meses_atras = max(1, meses_atras)
            logger.debug(f"Meses a serem analisados: {meses_atras}")
            
        except ValueError as ve:
            logger.error(f"Valor inválido para meses_atras: {request.args.get('meses_atras')}", exc_info=True)
            return jsonify({
                "erro": f"Valor inválido para o parâmetro 'meses_atras': {request.args.get('meses_atras')}"
            }), 400
        
        # Garantir que o diretório de imagens existe
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            img_dir = os.path.join(base_dir, 'dashboard_arq', 'static', 'img')
            os.makedirs(img_dir, exist_ok=True)
            logger.debug(f"Diretório de imagens verificado/criado: {img_dir}")
            
        except Exception as dir_error:
            logger.critical(f"Falha ao criar diretório de imagens: {str(dir_error)}", exc_info=True)
            return jsonify({
                "erro": "Falha ao configurar o ambiente para geração do gráfico"
            }), 500
            
        # Gerar o gráfico
        try:
            logger.info("Importando módulo de geração de gráfico de receitas...")
            from .gerar_grafico_receitas import gerar_grafico_receitas_por_categoria
            
            logger.info(f"Gerando gráfico de receitas para os últimos {meses_atras} meses...")
            html_path = gerar_grafico_receitas_por_categoria(meses_atras=meses_atras)
            
            if not html_path:
                logger.error("O caminho do arquivo HTML retornado é inválido")
                return jsonify({"erro": "Falha ao gerar o gráfico: caminho inválido"}), 500
                
            if not os.path.exists(html_path):
                logger.error(f"Arquivo de gráfico não encontrado em: {html_path}")
                return jsonify({
                    "erro": f"Arquivo de gráfico não encontrado: {os.path.basename(html_path)}"
                }), 404
                
            logger.info(f"Gráfico gerado com sucesso: {os.path.basename(html_path)}")
            
            # Configurar cabeçalhos para evitar cache
            response = send_file(
                html_path, 
                mimetype='text/html',
                as_attachment=False,
                download_name=os.path.basename(html_path)
            )
            
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            
            return response
            
        except ImportError as ie:
            logger.critical(f"Falha ao importar módulo de geração de gráficos: {str(ie)}", exc_info=True)
            return jsonify({
                "erro": "Módulo de geração de gráficos não disponível"
            }), 500
            
        except Exception as gen_error:
            logger.critical(f"Erro inesperado ao gerar gráfico: {str(gen_error)}", exc_info=True)
            return jsonify({
                "erro": f"Erro ao gerar gráfico: {str(gen_error)}"
            }), 500
            
    except Exception as e:
        logger.critical(f"Falha crítica ao processar requisição do gráfico: {str(e)}", exc_info=True)
        return jsonify({
            "erro": "Ocorreu um erro inesperado ao processar a requisição"
        }), 500

@dashboard_bp.route('/gerar_grafico_fluxo_caixa')
@log_function()
def gerar_grafico_fluxo_caixa():
    """
    Rota para gerar e retornar o gráfico de fluxo de caixa
    
    Returns:
        Response: Arquivo HTML do gráfico ou mensagem de erro
    """
    # Configura o contexto da requisição
    RequestContext.update_context(
        endpoint=request.endpoint,
        ip=request.remote_addr,
        method=request.method,
        path=request.path,
        user_agent=request.user_agent.string
    )
    
    logger.info("Iniciando geração do gráfico de fluxo de caixa")
    
    try:
        # Garantir que o diretório de imagens existe
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            img_dir = os.path.join(base_dir, 'dashboard_arq', 'static', 'img')
            os.makedirs(img_dir, exist_ok=True)
            logger.debug(f"Diretório de imagens verificado/criado: {img_dir}")
            
        except Exception as dir_error:
            logger.critical(f"Falha ao criar diretório de imagens: {str(dir_error)}", exc_info=True)
            return jsonify({
                "erro": "Falha ao configurar o ambiente para geração do gráfico"
            }), 500
        
        # Gerar o gráfico
        try:
            logger.info("Importando módulo de geração de gráfico de fluxo de caixa...")
            from .gerar_grafico_fluxo_caixa import gerar_grafico_fluxo_caixa as gerar_grafico
            
            logger.info("Gerando gráfico de fluxo de caixa...")
            caminho_grafico = gerar_grafico(meses_atras=12)
            
            if not caminho_grafico:
                logger.error("Falha ao gerar o gráfico: nenhum caminho retornado")
                return jsonify({"erro": "Falha ao gerar o gráfico de fluxo de caixa"}), 500
            
            logger.debug(f"Caminho do gráfico retornado: {caminho_grafico}")
            
            if not os.path.exists(caminho_grafico):
                logger.error(f"Arquivo de gráfico não encontrado em: {caminho_grafico}")
                return jsonify({
                    "erro": "Arquivo de gráfico não encontrado"
                }), 404
                
            logger.info(f"Gráfico gerado com sucesso: {os.path.basename(caminho_grafico)}")
            
            # Configurar cabeçalhos para evitar cache
            response = send_file(
                caminho_grafico, 
                mimetype='text/html',
                as_attachment=False,
                download_name=os.path.basename(caminho_grafico)
            )
            
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            
            return response
            
        except ImportError as ie:
            logger.critical(f"Falha ao importar módulo de geração de gráficos: {str(ie)}", exc_info=True)
            return jsonify({
                "erro": "Módulo de geração de gráficos não disponível"
            }), 500
            
        except Exception as gen_error:
            logger.critical(f"Erro inesperado ao gerar gráfico: {str(gen_error)}", exc_info=True)
            return jsonify({
                "erro": f"Erro ao gerar gráfico: {str(gen_error)}"
            }), 500
            
    except Exception as e:
        logger.critical(f"Falha crítica ao processar requisição do gráfico: {str(e)}", exc_info=True)
        return jsonify({
            "erro": "Ocorreu um erro inesperado ao processar a requisição"
        }), 500

@dashboard_bp.route('/api/transactions')
@log_function()
def get_transactions():
    """API para obter as transações"""
    try:
        logger.debug("Obtendo transações recentes")
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("""
            SELECT * FROM transacoes 
            ORDER BY data DESC 
            LIMIT 1000
        """, conn)
        logger.debug(f"Retornando {len(df)} transações")
        return jsonify(df.to_dict('records'))
    except Exception as e:
        error_msg = f"Erro ao obter transações: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({"error": error_msg}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@dashboard_bp.route('/api/limpar_dados', methods=['POST'])
@log_function()
def limpar_dados():
    """Rota para limpar os dados de transações do banco de dados, mantendo o histórico de uploads"""
    logger.warning("Iniciando limpeza dos dados de transações do banco de dados")
    logger.debug(f"Método da requisição: {request.method}")
    logger.debug(f"Headers: {dict(request.headers)}")
    logger.debug(f"Raw data: {request.data}")
    logger.debug(f"Content-Type: {request.content_type}")
    logger.debug(f"Content-Length: {request.content_length}")
    
    # Verifica se a requisição é JSON
    if not request.is_json:
        logger.error(f"Requisição não é JSON. Content-Type: {request.content_type}")
        return jsonify({
            "status": "error",
            "message": "O corpo da requisição deve ser JSON"
        }), 400
    
    try:
        # Tenta analisar o JSON
        data = request.get_json()
        logger.debug(f"Raw JSON data: {data}")
        
        if not isinstance(data, dict):
            logger.error(f"Dados JSON inválidos. Tipo recebido: {type(data)}")
            return render_template(
                'erro.html',
                mensagem="Erro ao limpar dados",
                detalhes=f"Dados JSON inválidos. Tipo recebido: {type(data)}"
            ), 400
        
        logger.debug(f"Dados recebidos: {data}")
        logger.debug(f"Keys em data: {list(data.keys())}")
        logger.debug(f"Values em data: {list(data.values())}")
    except Exception as e:
        logger.error(f"Erro ao processar JSON: {str(e)}", exc_info=True)
        logger.error(f"Raw data: {request.data}")
        logger.error(f"Headers: {dict(request.headers)}")
        logger.error(f"Request environ: {dict(request.environ)}")
        return render_template(
            'erro.html',
            mensagem="Erro ao limpar dados",
            detalhes=f"Erro ao processar dados JSON: {str(e)}"
        ), 400
    try:
        logger.debug("Conectando ao banco de dados...")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        logger.debug("Conexão com o banco de dados estabelecida com sucesso")
        
        # Verificar se a tabela de transações existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transacoes'")
        if not cursor.fetchone():
            logger.warning("A tabela 'transacoes' não foi encontrada no banco de dados")
            return jsonify({"status": "error", "message": "Tabela de transações não encontrada"}), 404
        
        # Contar registros antes de apagar
        cursor.execute("SELECT COUNT(*) FROM transacoes")
        total_registros = cursor.fetchone()[0]
        logger.info(f"Total de registros na tabela 'transacoes' antes da limpeza: {total_registros}")
        
        if total_registros == 0:
            logger.info("Nenhum dado para apagar - a tabela 'transacoes' já está vazia")
            return render_template(
                'dashboard.html',
                active_page='dashboard',
                mensagem_sucesso="Nenhum dado para apagar - a tabela 'transacoes' já está vazia"
            )
        
        # Desativa a verificação de chaves estrangeiras temporariamente
        cursor.execute("PRAGMA foreign_keys = OFF")
        logger.debug("Desativada verificação de chaves estrangeiras")
        
        try:
            # Limpa a tabela de transações
            cursor.execute("DELETE FROM transacoes")
            logger.info("Dados da tabela 'transacoes' removidos com sucesso")
            
            # Reinicia o contador de autoincremento
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='transacoes'")
            logger.debug("Contador de autoincremento resetado")
            
            # Confirma as alterações
            conn.commit()
            logger.debug("Transação commitada com sucesso")
            
            # Inicializar variáveis de estatísticas
            transacoes_recentes = 0
            transacoes_semana = 0
            ultima_transacao = None
            
            # Salva as variáveis em um dicionário para uso posterior
            estatisticas = {
                'transacoes_recentes_30d': transacoes_recentes,
                'transacoes_recentes_7d': transacoes_semana,
                'ultima_transacao': ultima_transacao
            }
            
            logger.warning(f"Dados da tabela 'transacoes' foram removidos com sucesso. {total_registros} registros removidos.")
            # Passar todas as variáveis necessárias para o template
            return render_template(
                'dashboard.html',
                active_page='dashboard',
                mensagem_sucesso=f"Dados limpos com sucesso! {total_registros} registros foram removidos.",
                total_registros=total_registros,
                estatisticas=estatisticas,
                total_receitas=0,
                total_despesas=0,
                saldo_mes_atual=0,
                transacoes_recentes=[],
                despesas_por_categoria={},
                receitas_por_categoria={}
            )
            
        except sqlite3.Error as e:
            error_msg = f"Erro ao limpar a tabela 'transacoes': {str(e)}"
            logger.error(error_msg, exc_info=True)
            conn.rollback()
            return render_template(
                'erro.html',
                mensagem="Erro ao limpar dados",
                detalhes=error_msg
            ), 500
            
        except Exception as e:
            error_msg = f"Erro inesperado ao processar dados: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return render_template(
                'erro.html',
                mensagem="Erro ao limpar dados",
                detalhes=error_msg
            ), 500
            
        finally:
            # Reativa a verificação de chaves estrangeiras
            cursor.execute("PRAGMA foreign_keys = ON")
            logger.debug("Reativada verificação de chaves estrangeiras")
            logger.debug("Reativada verificação de chaves estrangeiras")
            
    except Exception as e:
        error_msg = f"Erro ao conectar ao banco de dados: {str(e)}"
        logger.error(error_msg, exc_info=True)
        logger.error(f"Erro inesperado: {error_msg}")
        return render_template(
            'erro.html',
            mensagem="Erro ao limpar dados",
            detalhes=error_msg
        ), 500
        
    finally:
        if 'conn' in locals():
            conn.close()