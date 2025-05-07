import os
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, DateField, SelectField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Optional

# Adiciona o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger

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
    form = TransacaoForm()
    
    # Atualiza as categorias baseadas no tipo selecionado
    form.atualizar_categorias()
    
    if form.validate_on_submit():
        conn = conectar_banco()
        if not conn:
            flash('Erro ao conectar ao banco de dados.', 'error')
            return render_template('inserir_transacao.html', form=form)
        
        try:
            cursor = conn.cursor()
            
            # Ajusta o valor para negativo se for despesa
            valor = float(form.valor.data)
            if form.tipo.data == 'despesa':
                valor = -abs(valor)
            
            # Log dos dados da transação (sem dados sensíveis)
            inserir_logger.info(
                f"Inserindo nova transação - Tipo: {form.tipo.data}, "
                f"Categoria: {form.categoria.data}, Valor: {valor}"
            )
            
            # Insere a transação no banco de dados
            cursor.execute("""
                INSERT INTO transacoes (data, descricao, valor, categoria, tipo)
                VALUES (?, ?, ?, ?, ?)
            """, (
                form.data.data.strftime('%Y-%m-%d'),
                form.descricao.data,
                valor,
                form.categoria.data,
                form.tipo.data
            ))
            
            conn.commit()
            inserir_logger.info("Transação inserida com sucesso")
            flash('Transação adicionada com sucesso!', 'success')
            return redirect(url_for('inserir.inserir_transacao'))
            
        except sqlite3.Error as e:
            conn.rollback()
            error_msg = f'Erro ao inserir transação: {e}'
            inserir_logger.error(error_msg, exc_info=True)
            flash(error_msg, 'error')
            return render_template('inserir_transacao.html', form=form)
            
        finally:
            conn.close()
    
    return render_template('inserir_transacao.html', form=form)

def init_app(app):
    """Registra o blueprint na aplicação."""
    app.register_blueprint(inserir_bp)
    inserir_logger.info("Blueprint 'inserir' registrado com sucesso")
    return app
