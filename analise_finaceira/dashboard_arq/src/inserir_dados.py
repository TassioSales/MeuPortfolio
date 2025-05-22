import os
import sqlite3
import sys
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, DateField, SelectField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Optional

# Adiciona o diretório raiz ao path para importar o logger
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from logger import get_logger, RequestContext, LogLevel

# Configura o logger para este módulo
inserir_logger = get_logger("dashboard.inserir_dados")

# Cria o Blueprint
inserir_bp = Blueprint('inserir', __name__, url_prefix='/inserir')

# Lista de categorias comuns
CATEGORIAS_RECEITAS = [
    ('salario', 'Salário'),
    ('freelance', 'Freelance'),
    ('investimentos', 'Investimentos'),
    ('presente', 'Presente'),
    ('outros', 'Outros')
]

CATEGORIAS_DESPESAS = [
    ('alimentacao', 'Alimentação'),
    ('moradia', 'Moradia'),
    ('transporte', 'Transporte'),
    ('saude', 'Saúde'),
    ('educacao', 'Educação'),
    ('lazer', 'Lazer'),
    ('compras', 'Compras'),
    ('contas', 'Contas'),
    ('outros', 'Outros')
]

class TransacaoForm(FlaskForm):
    # Campos principais (obrigatórios)
    data = DateField('Data', validators=[DataRequired(message='A data é obrigatória')], format='%Y-%m-%d')
    descricao = TextAreaField('Descrição', validators=[DataRequired(message='A descrição é obrigatória')])
    valor = DecimalField('Valor', validators=[
        DataRequired(message='O valor é obrigatório'),
        NumberRange(min=0.01, message='O valor deve ser maior que zero')
    ], places=2)
    tipo = SelectField('Tipo', choices=[
        ('receita', 'Receita'),
        ('despesa', 'Despesa')
    ], validators=[DataRequired()])
    categoria = SelectField('Categoria', validators=[DataRequired()])
    
    # Campos de operação
    tipo_operacao = SelectField('Tipo de Operação', choices=[
        ('', 'Selecione...'),
        ('compra', 'Compra'),
        ('venda', 'Venda'),
        ('dividendo', 'Dividendo'),
        ('juros', 'Juros'),
        ('outro', 'Outro')
    ])
    ativo = StringField('Ativo')
    forma_pagamento = SelectField('Forma de Pagamento', choices=[
        ('', 'Selecione...'),
        ('dinheiro', 'Dinheiro'),
        ('cartao_credito', 'Cartão de Crédito'),
        ('cartao_debito', 'Cartão de Débito'),
        ('pix', 'PIX'),
        ('ted', 'TED/DOC'),
        ('outro', 'Outro')
    ])
    
    # Campos numéricos
    preco = DecimalField('Preço Unitário', places=4, validators=[
        Optional(),
        NumberRange(min=0.0001, message='O preço deve ser maior que zero')
    ])
    quantidade = DecimalField('Quantidade', places=6, validators=[
        Optional(),
        NumberRange(min=0.000001, message='A quantidade deve ser maior que zero')
    ])
    taxa = DecimalField('Taxa (%)', places=2, validators=[
        Optional(),
        NumberRange(min=0, message='A taxa não pode ser negativa')
    ])
    
    # Novos campos
    indicador1 = DecimalField('Indicador 1', places=4, validators=[
        Optional(),
        NumberRange(min=0, message='O indicador não pode ser negativo')
    ])
    indicador2 = DecimalField('Indicador 2', places=4, validators=[
        Optional(),
        NumberRange(min=0, message='O indicador não pode ser negativo')
    ])
    upload_id = StringField('ID do Upload', validators=[
        Optional()
    ])

    def __init__(self, *args, **kwargs):
        super(TransacaoForm, self).__init__(*args, **kwargs)
        self.atualizar_categorias()
    
    def atualizar_categorias(self):
        if self.tipo.data == 'receita':
            self.categoria.choices = CATEGORIAS_RECEITAS
        else:
            self.categoria.choices = CATEGORIAS_DESPESAS

def conectar_banco():
    """Conecta ao banco de dados SQLite."""
    try:
        # Obtém o diretório base do projeto
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # Define o caminho para o banco de dados
        db_path = os.path.join(base_dir, 'banco', 'financas.db')
        
        # Verifica se o diretório do banco existe, se não existir, cria
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            inserir_logger.info(f"Criando diretório do banco de dados: {db_dir}")
            os.makedirs(db_dir, exist_ok=True)
        
        # Conecta ao banco de dados
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        inserir_logger.debug(f"Conexão com o banco de dados estabelecida: {db_path}")
        return conn
    except sqlite3.Error as e:
        inserir_logger.error(f"Erro ao conectar ao banco de dados: {e}", exc_info=True)
        return None

@inserir_bp.route('/', methods=['GET'])
def index():
    return redirect(url_for('inserir.inserir_transacao'))

@inserir_bp.route('/transacao', methods=['GET', 'POST'])
def inserir_transacao():
    # Configura o contexto da requisição
    request_id = RequestContext.set_request_context()
    
    form = TransacaoForm()
    transactions = []  # Inicializa a lista de transações vazia
    
    # Atualiza as categorias baseadas no tipo selecionado
    form.atualizar_categorias()
    
    # Log da requisição
    inserir_logger.info("Iniciando processamento da requisição de inserção", extra={
        'method': request.method,
        'endpoint': request.endpoint,
        'request_id': request_id
    })
    
    # Conecta ao banco para buscar as transações existentes
    conn = conectar_banco()
    if conn:
        try:
            cursor = conn.cursor()
            # Busca as últimas 50 transações ordenadas por data (mais recentes primeiro)
            cursor.execute("""
                SELECT 
                    id, data, descricao, valor, categoria, tipo,
                    tipo_operacao, ativo, forma_pagamento, preco, 
                    quantidade, taxa, indicador1, indicador2, data_importacao, upload_id
                FROM transacoes 
                ORDER BY data DESC, rowid DESC
                LIMIT 50
            """)
            transactions = [dict(row) for row in cursor.fetchall()]
            inserir_logger.debug(f"Carregadas {len(transactions)} transações para exibição")
            
        except sqlite3.Error as e:
            error_msg = f"Erro ao buscar transações: {str(e)}"
            inserir_logger.error(error_msg, exc_info=True, extra={'request_id': request_id})
            flash('Erro ao carregar transações existentes.', 'error')
        finally:
            try:
                conn.close()
            except Exception as e:
                inserir_logger.error(f"Erro ao fechar conexão: {str(e)}", 
                                   extra={'request_id': request_id}, exc_info=True)
    
    if form.validate_on_submit():
        inserir_logger.info("Formulário validado com sucesso", 
                           extra={'request_id': request_id})
        
        conn = conectar_banco()
        if not conn:
            error_msg = 'Erro ao conectar ao banco de dados.'
            inserir_logger.error(error_msg, extra={'request_id': request_id})
            flash(error_msg, 'error')
            return render_template('inserir_transacao.html', form=form, transactions=transactions)
        
        try:
            cursor = conn.cursor()
            
            # Converte e valida o valor
            try:
                valor = float(form.valor.data) if form.valor.data else 0.0
                
                # Ajusta o valor para negativo se for despesa
                if form.tipo.data == 'despesa' and valor > 0:
                    valor_original = valor
                    valor = -valor
                    inserir_logger.debug(
                        "Valor convertido para negativo para despesa",
                        extra={
                            'valor_original': valor_original,
                            'valor_convertido': valor,
                            'tipo': form.tipo.data
                        }
                    )
                
                # Log dos dados da transação (sem dados sensíveis)
                inserir_logger.info(
                    "Preparando para inserir nova transação",
                    extra={
                        'tipo': form.tipo.data,
                        'categoria': form.categoria.data,
                        'valor': valor,
                        'data': form.data.data.strftime('%Y-%m-%d')
                    }
                )
                
            except (ValueError, TypeError) as e:
                error_msg = f'Valor inválido: {form.valor.data}'
                inserir_logger.error(error_msg, exc_info=True)
                flash(error_msg, 'error')
                return render_template('inserir_transacao.html', form=form, transactions=transactions)
            
            # Prepara os dados para inserção
            dados_transacao = {
                'data': form.data.data.strftime('%Y-%m-%d'),
                'descricao': form.descricao.data,
                'valor': valor,
                'categoria': form.categoria.data,
                'tipo': form.tipo.data,
                'tipo_operacao': form.tipo_operacao.data if form.tipo_operacao.data else None,
                'ativo': form.ativo.data if form.ativo.data else None,
                'forma_pagamento': form.forma_pagamento.data if form.forma_pagamento.data else None,
                'preco': float(form.preco.data) if form.preco.data else None,
                'quantidade': float(form.quantidade.data) if form.quantidade.data else None,
                'taxa': float(form.taxa.data) if form.taxa.data else None,
                'indicador1': float(form.indicador1.data) if form.indicador1.data else None,
                'indicador2': float(form.indicador2.data) if form.indicador2.data else None,
                'upload_id': None  # Sempre None para transações manuais
            }
            
            # Insere a transação no banco de dados
            cursor.execute("""
                INSERT INTO transacoes (
                    data, descricao, valor, categoria, tipo,
                    tipo_operacao, ativo, forma_pagamento, preco, 
                    quantidade, taxa, indicador1, indicador2, upload_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dados_transacao['data'],
                dados_transacao['descricao'],
                dados_transacao['valor'],
                dados_transacao['categoria'],
                dados_transacao['tipo'],
                dados_transacao['tipo_operacao'],
                dados_transacao['ativo'],
                dados_transacao['forma_pagamento'],
                dados_transacao['preco'],
                dados_transacao['quantidade'],
                dados_transacao['taxa'],
                dados_transacao['indicador1'],
                dados_transacao['indicador2'],
                dados_transacao['upload_id']
            ))
            
            conn.commit()
            inserir_logger.info("Transação inserida com sucesso", 
                               extra={
                                   'request_id': request_id,
                                   'tipo': form.tipo.data,
                                   'valor': valor,
                                   'categoria': form.categoria.data
                               })
            flash('Transação adicionada com sucesso!', 'success')
            return redirect(url_for('inserir.inserir_transacao'))
            
        except sqlite3.Error as e:
            conn.rollback()
            error_msg = f'Erro ao inserir transação: {e}'
            inserir_logger.error(error_msg, 
                              exc_info=True, 
                              extra={
                                  'request_id': request_id,
                                  'tipo': form.tipo.data if form.tipo.data else None,
                                  'valor': form.valor.data if form.valor.data else None
                              })
            flash('Ocorreu um erro ao salvar a transação. Por favor, tente novamente.', 'error')
            return render_template('inserir_transacao.html', form=form, transactions=transactions)
            
        finally:
            try:
                if conn:
                    conn.close()
            except Exception as e:
                inserir_logger.error(f"Erro ao fechar conexão: {str(e)}", 
                                   extra={'request_id': request_id}, exc_info=True)
    # Log antes de renderizar o template
    inserir_logger.debug("Renderizando template de inserção de transação",
                        extra={
                            'request_id': request_id,
                            'num_transacoes': len(transactions) if transactions else 0
                        })
    
    return render_template('inserir_transacao.html', form=form, transactions=transactions)

def init_app(app):
    """Registra o blueprint na aplicação."""
    app.register_blueprint(inserir_bp)
    inserir_logger.info("Blueprint 'inserir' registrado com sucesso")
    return app