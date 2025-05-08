import os
import sys
import sqlite3
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from werkzeug.security import generate_password_hash
from .forms import AlertaForm
from datetime import date

# Importa o blueprint
from .blueprint import alertas_manuais_bp

# Importa o logger configurado no __init__.py
from . import logger

logger.info("Módulo de rotas de alertas manuais inicializado")

# Função auxiliar para marcar a página ativa no menu
def get_active_page():
    try:
        logger.info("Chamando get_active_page()")
        result = {'active_page': 'alertas_manuais'}
        logger.info(f"get_active_page() retornando: {result}")
        return result
    except Exception as e:
        logger.error(f"Erro em get_active_page(): {str(e)}", exc_info=True)
        return {'active_page': 'alertas_manuais'}  # Retorna um valor padrão em caso de erro

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    logger.info("Iniciando conexão com o banco de dados")
    try:
        # Cria o diretório do banco de dados se não existir
        db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'banco')
        logger.debug(f"Diretório do banco de dados: {db_dir}")
        os.makedirs(db_dir, exist_ok=True)
        
        db_path = os.path.join(db_dir, 'financas.db')
        logger.debug(f"Caminho do banco de dados: {db_path}")
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        logger.info("Conexão com o banco de dados estabelecida com sucesso")
        
        # Verifica e cria as tabelas se não existirem
        cursor = conn.cursor()
        logger.debug("Verificando e criando tabelas se necessário")
        
        # Tabela de alertas_financas
        logger.debug("Verificando tabela 'alertas_financas'")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alertas_financas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                tipo_alerta TEXT NOT NULL,
                descricao TEXT NOT NULL,
                valor_referencia REAL NOT NULL,
                categoria TEXT,
                data_inicio DATE,
                data_fim DATE,
                prioridade TEXT NOT NULL,
                notificar_email BOOLEAN DEFAULT 0,
                notificar_app BOOLEAN DEFAULT 1,
                ativo BOOLEAN DEFAULT 1,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        logger.debug("Tabela 'alertas_financas' verificada/criada com sucesso")
        
        # Tabela de histórico de disparos
        logger.debug("Verificando tabela 'historico_disparos_alerta'")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historico_disparos_alerta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alerta_id INTEGER NOT NULL,
                disparado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                valor_observado DECIMAL(10, 2),
                mensagem_disparo TEXT,
                FOREIGN KEY (alerta_id) REFERENCES alertas_financas (id)
            )
        ''')
        logger.debug("Tabela 'historico_disparos_alerta' verificada/criada com sucesso")
        
        # Verificar se a tabela foi criada corretamente
        cursor.execute("PRAGMA table_info(historico_disparos_alerta)")
        columns = cursor.fetchall()
        
        # Verificar se a tabela precisa ser recriada
        expected_columns = {'id', 'alerta_id', 'disparado_em', 'valor_observado', 'mensagem_disparo'}
        actual_columns = {col[1] for col in columns}
        
        if not columns or not expected_columns.issubset(actual_columns):
            logger.warning("Tabela 'historico_disparos_alerta' não encontrada ou com estrutura incorreta, recriando...")
            cursor.execute('''
                DROP TABLE IF EXISTS historico_disparos_alerta;
                CREATE TABLE historico_disparos_alerta (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alerta_id INTEGER NOT NULL,
                    disparado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    valor_observado DECIMAL(10, 2),
                    mensagem_disparo TEXT,
                    FOREIGN KEY (alerta_id) REFERENCES alertas_financas (id)
                )
            ''')
            logger.info("Tabela 'historico_disparos_alerta' recriada com sucesso")
        
        conn.commit()
        logger.info("Conexão com o banco de dados configurada com sucesso")
        return conn
        
    except Exception as e:
        logger.critical(f"Erro crítico ao conectar ao banco de dados: {str(e)}", exc_info=True)
        raise

@alertas_manuais_bp.route('/')
def index():
    logger.info(f"Request path: {request.path}, args: {request.args}")
    """Página inicial de gerenciamento de alertas."""
    logger.info("Acessando página inicial de gerenciamento de alertas")
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar alertas ativos
        logger.debug("Buscando alertas ativos no banco de dados")
        cursor.execute('''
            SELECT * FROM alertas_financas 
            WHERE ativo = 1 
            ORDER BY prioridade DESC, criado_em DESC
        ''')
        alertas = cursor.fetchall()
        logger.info(f"Encontrados {len(alertas)} alertas ativos")

        # Exibir mensagem para cada alerta vigente (data_inicio <= hoje <= data_fim ou data_fim nula), sem duplicar
        hoje = date.today().isoformat()
        # Só exibe o flash se não houver querystring ou se tab=alertas
        if not request.args or request.args.get('tab', 'alertas') == 'alertas':
            ids_exibidos = set()
            for alerta in alertas:
                data_inicio = alerta['data_inicio']
                data_fim = alerta['data_fim']
                vigente = False
                if data_inicio and data_inicio <= hoje:
                    if not data_fim or data_fim >= hoje:
                        vigente = True
                alerta_id = alerta['id']
                if vigente and alerta_id not in ids_exibidos:
                    flash(f"Alerta vigente: {alerta['descricao']}", 'warning')
                    ids_exibidos.add(alerta_id)

                    # Registrar no histórico apenas se ainda não houver registro para este alerta
                    cursor.execute('SELECT COUNT(*) FROM historico_disparos_alerta WHERE alerta_id = ?', (alerta_id,))
                    ja_registrado = cursor.fetchone()[0]
                    if ja_registrado == 0:
                        cursor.execute('INSERT INTO historico_disparos_alerta (alerta_id, valor_observado, mensagem_disparo) VALUES (?, ?, ?)',
                            (alerta_id, alerta['valor_referencia'], f"Disparo do alerta: {alerta['descricao']}"))
                        conn.commit()
       
        # Buscar histórico recente de disparos
        logger.debug("Buscando histórico recente de disparos")
        try:
            cursor.execute('''
                SELECT h.id, h.alerta_id, h.disparado_em, h.valor_observado, h.mensagem_disparo,
                       a.descricao as alerta_descricao 
                FROM historico_disparos_alerta h
                JOIN alertas_financas a ON h.alerta_id = a.id
                ORDER BY h.disparado_em DESC
                LIMIT 6
            ''')
            historico = cursor.fetchall()
            logger.debug(f"Encontrados {len(historico)} registros no histórico de disparos")
        except Exception as e:
            logger.error(f"Erro ao buscar histórico de disparos: {str(e)}", exc_info=True)
            flash('Ocorreu um erro ao carregar o histórico de disparos.', 'warning')
            historico = []
        
        # Formatar dados para o template
        alertas_list = []
        logger.debug(f"Iniciando formatação de {len(alertas)} alertas")
        
        for alerta in alertas:
            try:
                # Tratamento seguro para valor_referencia
                try:
                    valor_ref = float(alerta['valor_referencia']) if alerta['valor_referencia'] is not None else 0.0
                    valor_formatado = f"R$ {valor_ref:,.2f}"
                except (ValueError, TypeError) as e:
                    logger.warning(f"Valor de referência inválido para alerta ID {alerta['id'] if 'id' in alerta.keys() else 'desconhecido'}: {alerta['valor_referencia'] if 'valor_referencia' in alerta.keys() else 'N/A'}")
                    valor_formatado = "R$ 0,00"
                
                prioridade = str(alerta['prioridade']).capitalize() if 'prioridade' in alerta.keys() and alerta['prioridade'] else 'Media'
                categoria = alerta['categoria'] if 'categoria' in alerta.keys() and alerta['categoria'] else 'Não definida'
                descricao = alerta['descricao'] if 'descricao' in alerta.keys() and alerta['descricao'] else 'Sem descrição'
                tipo_alerta = alerta['tipo_alerta'] if 'tipo_alerta' in alerta.keys() and alerta['tipo_alerta'] else 'Desconhecido'
                criado_em = alerta['criado_em'] if 'criado_em' in alerta.keys() and alerta['criado_em'] else 'Data não disponível'
                ativo = bool(alerta['ativo']) if 'ativo' in alerta.keys() else False

                alertas_list.append({
                    'id': alerta['id'],
                    'tipo_alerta': tipo_alerta,
                    'descricao': descricao,
                    'valor_referencia': valor_formatado,
                    'categoria': categoria,
                    'prioridade': prioridade,
                    'criado_em': criado_em,
                    'ativo': ativo
                })
                logger.debug(f"Alerta ID {alerta['id']} formatado com sucesso")
            except Exception as e:
                logger.error(f"Erro ao formatar alerta: {str(e)}", exc_info=True)
                try:
                    logger.debug(f"Dados do alerta com problema: {dict(alerta)}")
                except Exception:
                    logger.debug(f"Não foi possível converter alerta problemático para dict.")
        
        logger.info(f"Total de alertas formatados: {len(alertas_list)} de {len(alertas)}")
        
        # Formatar histórico
        historico_list = []
        logger.debug(f"Iniciando formatação de {len(historico)} registros de histórico")
        
        for hist in historico:
            try:
                # Tratamento seguro para valor_observado
                try:
                    valor_obs = float(hist['valor_observado']) if hist['valor_observado'] is not None else None
                    valor_obs_formatado = f"R$ {valor_obs:,.2f}" if valor_obs is not None else 'N/A'
                except (ValueError, TypeError) as e:
                    logger.warning(f"Valor observado inválido para histórico ID {hist['id'] if 'id' in hist.keys() else 'desconhecido'}: {hist['valor_observado'] if 'valor_observado' in hist.keys() else 'N/A'}")
                    valor_obs_formatado = 'N/A'

                alerta_descricao = hist['alerta_descricao'] if 'alerta_descricao' in hist.keys() and hist['alerta_descricao'] else 'Alerta desconhecido'
                disparado_em = hist['disparado_em'] if 'disparado_em' in hist.keys() and hist['disparado_em'] else 'Data não disponível'
                mensagem = hist['mensagem_disparo'] if 'mensagem_disparo' in hist.keys() and hist['mensagem_disparo'] else 'Sem mensagem'

                historico_list.append({
                    'id': hist['id'],
                    'alerta_id': hist['alerta_id'],
                    'alerta_descricao': alerta_descricao,
                    'disparado_em': disparado_em,
                    'valor_observado': valor_obs_formatado,
                    'mensagem': mensagem
                })
                logger.debug(f"Histórico ID {hist['id']} formatado com sucesso")
            except Exception as e:
                logger.error(f"Erro ao formatar histórico: {str(e)}", exc_info=True)
                try:
                    logger.debug(f"Dados do histórico com problema: {dict(hist)}")
                except Exception:
                    logger.debug(f"Não foi possível converter histórico problemático para dict.")
        
        logger.info(f"Total de registros de histórico formatados: {len(historico_list)} de {len(historico)}")
        
        logger.info("Página de alertas carregada com sucesso")
        return render_template(
            'alertas_manuais.html',
            alertas=alertas_list,
            historico=historico_list,
            **get_active_page()
        )
        
    except Exception as e:
        logger.critical(f"Erro crítico ao carregar a página de alertas: {str(e)}", exc_info=True)
        flash('Ocorreu um erro inesperado ao carregar a página de alertas. Por favor, tente novamente mais tarde.', 'danger')
        return render_template('alertas_manuais.html', alertas=[], historico=[], **get_active_page())
    finally:
        if conn:
            try:
                conn.close()
                logger.debug("Conexão com o banco de dados fechada")
            except Exception as e:
                logger.error(f"Erro ao fechar conexão com o banco de dados: {str(e)}", exc_info=True)

@alertas_manuais_bp.route('/novo', methods=['GET', 'POST'])
def novo_alerta():
    """Rota para criar um novo alerta manual."""
    logger.info("Acessando rota para criar novo alerta")
    form = AlertaForm()

    # Categorias disponíveis
    categorias_receita = [
        ('', 'Selecione...'),
        ('Salário', 'Salário'),
        ('Investimentos', 'Investimentos'),
        ('Freelance', 'Freelance'),
        ('Outros', 'Outros')
    ]
    categorias_despesa = [
        ('', 'Selecione...'),
        ('Alimentação', 'Alimentação'),
        ('Moradia', 'Moradia'),
        ('Transporte', 'Transporte'),
        ('Educação', 'Educação'),
        ('Lazer', 'Lazer'),
        ('Saúde', 'Saúde'),
        ('Outros', 'Outros')
    ]

    # Define as opções do select de categoria conforme o tipo selecionado (POST ou GET)
    tipo = form.tipo_alerta.data or request.form.get('tipo_alerta')
    if tipo == 'RECEITA':
        form.categoria.choices = categorias_receita
    elif tipo == 'DESPESA':
        form.categoria.choices = categorias_despesa
    else:
        form.categoria.choices = [('', 'Selecione...')]

    if form.validate_on_submit():
        logger.debug("Formulário validado com sucesso")
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Converter dados do formulário para dicionário
            dados = form.to_dict()
            logger.debug(f"Dados do formulário: {dados}")
            
            # Inserir novo alerta
            cursor.execute('''
                INSERT INTO alertas_financas (
                    usuario_id, tipo_alerta, descricao, valor_referencia, categoria,
                    data_inicio, data_fim, prioridade, notificar_email, notificar_app
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                1,  # ID do usuário atual (fixo por enquanto)
                dados['tipo_alerta'],
                dados['descricao'],
                dados['valor_referencia'],
                dados['categoria'],
                dados.get('data_inicio'),  # Pode ser None
                dados.get('data_fim'),     # Pode ser None
                dados['prioridade'],
                1 if dados['notificar_email'] else 0,
                1 if dados['notificar_app'] else 0
            ))
            
            alerta_id = cursor.lastrowid
            conn.commit()
            logger.info(f'Alerta ID {alerta_id} criado com sucesso')
            flash('Alerta criado com sucesso!', 'success')
            return redirect(url_for('alertas_manuais.index'))
            
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Erro de banco de dados ao criar alerta: {str(e)}", exc_info=True)
            flash('Erro ao salvar no banco de dados. Verifique os dados e tente novamente.', 'danger')
        except Exception as e:
            if conn:
                conn.rollback()
            logger.critical(f"Erro inesperado ao criar alerta: {str(e)}", exc_info=True)
            flash('Ocorreu um erro inesperado ao criar o alerta. Por favor, tente novamente.', 'danger')
        finally:
            if conn:
                try:
                    conn.close()
                    logger.debug("Conexão com o banco de dados fechada")
                except Exception as e:
                    logger.error(f"Erro ao fechar conexão com o banco de dados: {str(e)}", exc_info=True)
    elif request.method == 'POST':
        logger.warning(f"Erros de validação no formulário: {form.errors}")
        
    # GET ou POST com erros de validação
    categorias_receita = [
        ('', 'Selecione...'),
        ('Salário', 'Salário'),
        ('Investimentos', 'Investimentos'),
        ('Freelance', 'Freelance'),
        ('Outros', 'Outros')
    ]
    categorias_despesa = [
        ('', 'Selecione...'),
        ('Alimentação', 'Alimentação'),
        ('Moradia', 'Moradia'),
        ('Transporte', 'Transporte'),
        ('Educação', 'Educação'),
        ('Lazer', 'Lazer'),
        ('Saúde', 'Saúde'),
        ('Outros', 'Outros')
    ]
    context = {
        'form': form,
        'titulo': 'Novo Alerta',
        'action': url_for('alertas_manuais.novo_alerta'),
        'categorias_receita': categorias_receita,
        'categorias_despesa': categorias_despesa
    }
    context.update(get_active_page())
    return render_template('form_alerta.html', **context)

@alertas_manuais_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
def editar_alerta(id):
    """Edita um alerta existente.
    
    Args:
        id (int): ID do alerta a ser editado
        
    Returns:
        Response: Redireciona para a lista de alertas ou exibe o formulário de edição
    """
    logger.info(f"Iniciando edição do alerta ID: {id}")
    form = AlertaForm()
    conn = None
    
    if form.validate_on_submit():
        logger.debug("Formulário validado com sucesso")
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verificar se o alerta existe e está ativo
            logger.debug(f"Verificando existência do alerta {id}")
            cursor.execute('SELECT id, ativo FROM alertas_financas WHERE id = ?', (id,))
            alerta = cursor.fetchone()
            
            if not alerta:
                logger.warning(f'Tentativa de editar alerta {id} que não existe')
                flash('Alerta não encontrado.', 'danger')
                return redirect(url_for('alertas_manuais.index'))
                
            if alerta['ativo'] == 0:
                logger.warning(f'Tentativa de editar alerta {id} que está inativo')
                flash('Não é possível editar um alerta inativo.', 'warning')
                return redirect(url_for('alertas_manuais.index'))
            
            # Converter dados do formulário para dicionário
            dados = form.to_dict()
            logger.debug(f"Dados do formulário para atualização: {dados}")
            
            # Atualizar alerta
            cursor.execute('''
                UPDATE alertas_financas 
                SET tipo_alerta = ?,
                    descricao = ?,
                    valor_referencia = ?,
                    categoria = ?,
                    data_inicio = ?,
                    data_fim = ?,
                    prioridade = ?,
                    notificar_email = ?,
                    notificar_app = ?,
                    atualizado_em = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                dados['tipo_alerta'],
                dados['descricao'],
                dados['valor_referencia'],
                dados['categoria'],
                dados['data_inicio'],
                dados['data_fim'],
                dados['prioridade'],
                1 if dados['notificar_email'] else 0,
                1 if dados['notificar_app'] else 0,
                id
            ))
            
            if cursor.rowcount == 0:
                raise Exception("Nenhum registro foi atualizado")
                
            conn.commit()
            logger.info(f'Alerta {id} atualizado com sucesso')
            flash('Alerta atualizado com sucesso!', 'success')
            return redirect(url_for('alertas_manuais.index'))
            
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Erro de banco de dados ao atualizar alerta {id}: {str(e)}", exc_info=True)
            flash('Erro ao atualizar o alerta no banco de dados. Tente novamente.', 'danger')
        except Exception as e:
            if conn:
                conn.rollback()
            logger.critical(f"Erro inesperado ao atualizar alerta {id}: {str(e)}", exc_info=True)
            flash('Ocorreu um erro inesperado ao atualizar o alerta. Por favor, tente novamente.', 'danger')
        finally:
            if conn:
                try:
                    conn.close()
                    logger.debug("Conexão com o banco de dados fechada")
                except Exception as e:
                    logger.error(f"Erro ao fechar conexão com o banco de dados: {str(e)}", exc_info=True)
    elif request.method == 'POST':
        logger.warning(f"Erros de validação no formulário: {form.errors}")
    
    # Listas de categorias para seleção dinâmica
    categorias_receita = [
        ('', 'Selecione...'),
        ('Salário', 'Salário'),
        ('Investimentos', 'Investimentos'),
        ('Freelance', 'Freelance'),
        ('Outros', 'Outros')
    ]
    categorias_despesa = [
        ('', 'Selecione...'),
        ('Alimentação', 'Alimentação'),
        ('Moradia', 'Moradia'),
        ('Transporte', 'Transporte'),
        ('Educação', 'Educação'),
        ('Lazer', 'Lazer'),
        ('Saúde', 'Saúde'),
        ('Outros', 'Outros')
    ]
    # GET: Carregar dados do alerta no formulário
    try:
        logger.debug(f"Carregando dados do alerta {id} para edição")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar alerta pelo ID
        cursor.execute('SELECT * FROM alertas_financas WHERE id = ?', (id,))
        alerta = cursor.fetchone()
        
        if not alerta:
            logger.warning(f'Alerta {id} não encontrado')
            flash('Alerta não encontrado.', 'danger')
            return redirect(url_for('alertas_manuais.index'))
            
        if alerta['ativo'] == 0:
            logger.warning(f'Tentativa de editar alerta {id} que está inativo')
            flash('Não é possível editar um alerta inativo.', 'warning')
            return redirect(url_for('alertas_manuais.index'))
        
        # Preencher o formulário com os dados do alerta
        if request.method == 'GET':
            from datetime import datetime
            
            try:
                form.id.data = alerta['id']
                form.tipo_alerta.data = alerta['tipo_alerta']
                form.categoria.data = alerta['categoria'] or ''
                form.descricao.data = alerta['descricao']
                form.valor_referencia.data = float(alerta['valor_referencia'])
                form.prioridade.data = alerta['prioridade'] or 'media'
                
                # Converter strings de data para objetos date, se existirem
                if alerta['data_inicio']:
                    try:
                        form.data_inicio.data = datetime.strptime(alerta['data_inicio'], '%Y-%m-%d').date()
                    except (ValueError, TypeError) as e:
                        logger.error(f"Erro ao converter data_inicio do alerta {id}: {str(e)}")
                        form.data_inicio.data = None
                        
                if alerta['data_fim']:
                    try:
                        form.data_fim.data = datetime.strptime(alerta['data_fim'], '%Y-%m-%d').date()
                    except (ValueError, TypeError) as e:
                        logger.error(f"Erro ao converter data_fim do alerta {id}: {str(e)}")
                        form.data_fim.data = None
                    
                form.notificar_email.data = bool(alerta['notificar_email'])
                form.notificar_app.data = bool(alerta['notificar_app'])
                
                logger.debug(f"Formulário preenchido com dados do alerta {id}")
                
            except Exception as e:
                logger.error(f"Erro ao preencher formulário do alerta {id}: {str(e)}", exc_info=True)
                flash('Erro ao carregar os dados do alerta.', 'danger')
                return redirect(url_for('alertas_manuais.index'))
        
    except sqlite3.Error as e:
        logger.error(f"Erro de banco de dados ao carregar alerta {id}: {str(e)}", exc_info=True)
        flash('Erro ao acessar o banco de dados. Tente novamente.', 'danger')
        return redirect(url_for('alertas_manuais.index'))
    except Exception as e:
        logger.critical(f"Erro inesperado ao carregar alerta {id}: {str(e)}", exc_info=True)
        flash('Ocorreu um erro inesperado ao carregar o alerta.', 'danger')
        return redirect(url_for('alertas_manuais.index'))
    finally:
        if conn:
            try:
                conn.close()
                logger.debug("Conexão com o banco de dados fechada")
            except Exception as e:
                logger.error(f"Erro ao fechar conexão com o banco de dados: {str(e)}", exc_info=True)
    
    context = {
        'form': form,
        'titulo': 'Editar Alerta',
        'action': url_for('alertas_manuais.editar_alerta', id=id),
        'categorias_receita': categorias_receita,
        'categorias_despesa': categorias_despesa
    }
    context.update(get_active_page())
    return render_template('form_alerta.html', **context)

@alertas_manuais_bp.route('/<int:id>/excluir', methods=['POST', 'DELETE'])
def excluir_alerta(id):
    """Rota para excluir um alerta (desativação lógica).
    
    Args:
        id (int): ID do alerta a ser excluído/desativado
        
    Returns:
        Response: Redireciona para a lista de alertas com mensagem de status
        
    Notas:
        - Aceita tanto requisições POST quanto DELETE para maior compatibilidade
        - Realiza uma desativação lógica (soft delete) em vez de exclusão física
    """
    logger.info(f'Iniciando processo de exclusão do alerta ID: {id}')
    
    # Verificação de segurança CSRF para requisições POST
    if request.method == 'POST':
        csrf_token = request.form.get('csrf_token')
        logger.debug(f'Token CSRF recebido: {csrf_token}')
        
        if not csrf_token:
            logger.warning('Tentativa de exclusão sem token CSRF')
            flash('Token de segurança ausente. Por favor, tente novamente.', 'danger')
            return redirect(url_for('alertas_manuais.index'))
    
    conn = None
    try:
        # Registrar informações da requisição para debug
        logger.debug(f'Dados do formulário: {request.form}')
        logger.debug(f'Dados JSON: {request.get_json(silent=True)}')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verifica se o alerta existe e está ativo
        logger.debug(f'Verificando existência do alerta {id}')
        cursor.execute('SELECT id, descricao, ativo FROM alertas_financas WHERE id = ?', (id,))
        alerta = cursor.fetchone()
        
        if not alerta:
            logger.warning(f'Tentativa de excluir alerta {id} que não existe')
            flash('Alerta não encontrado.', 'warning')
            return redirect(url_for('alertas_manuais.index'))
            
        if alerta['ativo'] == 0:
            logger.warning(f'Tentativa de excluir alerta {id} que já está inativo')
            flash('Este alerta já foi removido anteriormente.', 'info')
            return redirect(url_for('alertas_manuais.index'))
        
        logger.info(f'Dados do alerta a ser desativado: {{id: {alerta["id"]}, descricao: {alerta["descricao"]}}}')
        
        # Desativa o alerta em vez de excluí-lo fisicamente (soft delete)
        cursor.execute('''
            UPDATE alertas_financas
            SET ativo = 0,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (id,))
        
        if cursor.rowcount == 0:
            raise Exception("Nenhum registro foi atualizado durante a desativação")
            
        conn.commit()
        logger.info(f'Alerta {id} desativado com sucesso')
        flash('Alerta desativado com sucesso!', 'success')
        
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Erro de banco de dados ao desativar alerta {id}: {str(e)}", exc_info=True)
        flash('Ocorreu um erro ao desativar o alerta no banco de dados. Por favor, tente novamente.', 'danger')
    except Exception as e:
        if conn:
            conn.rollback()
        logger.critical(f"Erro inesperado ao desativar alerta {id}: {str(e)}", exc_info=True)
        flash('Ocorreu um erro inesperado ao desativar o alerta. Por favor, tente novamente.', 'danger')
    finally:
        if conn:
            try:
                conn.close()
                logger.debug("Conexão com o banco de dados fechada")
            except Exception as e:
                logger.error(f"Erro ao fechar conexão com o banco de dados: {str(e)}", exc_info=True)
    
    return redirect(url_for('alertas_manuais.index'))
