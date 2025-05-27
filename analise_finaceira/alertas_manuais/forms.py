import os
import sys
from pathlib import Path
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, ValidationError

# Adicionar o diretório raiz ao path para importar o logger
root_dir = str(Path(__file__).parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from logger import get_logger, LogLevel

# Configurar logger
logger = get_logger('alertas_manuais.forms')

class AlertaForm(FlaskForm):
    """Formulário para criação e edição de alertas."""
    
    # Opções para os campos de seleção
    PRIORIDADE_CHOICES = [
        ('baixa', 'Baixa'),
        ('média', 'Média'),
        ('alta', 'Alta')
    ]
    
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('inativo', 'Inativo'),
        ('resolvido', 'Resolvido')
    ]
    
    # Campos do formulário
    titulo = StringField(
        'Título',
        validators=[
            DataRequired(message='O título é obrigatório'),
            Length(min=3, max=100, message='O título deve ter entre 3 e 100 caracteres')
        ],
        render_kw={"placeholder": "Digite um título para o alerta"}
    )
    
    descricao = TextAreaField(
        'Descrição',
        validators=[
            Optional(),
            Length(max=500, message='A descrição não pode ter mais que 500 caracteres')
        ],
        render_kw={
            "placeholder": "Forneça detalhes sobre o alerta (opcional)",
            "rows": 4
        }
    )
    
    prioridade = SelectField(
        'Prioridade',
        choices=PRIORIDADE_CHOICES,
        default='média',
        validators=[DataRequired(message='Selecione uma prioridade')]
    )
    
    status = SelectField(
        'Status',
        choices=STATUS_CHOICES,
        default='ativo',
        validators=[DataRequired(message='Selecione um status')]
    )
    
    submit = SubmitField('Salvar')
    
    def __init__(self, *args, **kwargs):
        """Inicializa o formulário com os argumentos fornecidos."""
        logger.debug('Inicializando formulário de alerta')
        super(AlertaForm, self).__init__(*args, **kwargs)
    
    def validate_titulo(self, field):
        """Validação personalizada para o título."""
        try:
            if field.data:
                # Remover espaços em branco extras
                original = field.data
                field.data = ' '.join(original.strip().split())
                
                if original != field.data:
                    logger.debug(f'Texto do título normalizado: "{original}" -> "{field.data}"')
                    
        except Exception as e:
            logger.error(f'Erro ao validar título: {e}', exc_info=True)
            raise ValidationError('Erro ao processar o título. Por favor, tente novamente.')
    
    def to_dict(self):
        """Converte os dados do formulário para dicionário."""
        try:
            data = {
                'titulo': self.titulo.data,
                'descricao': self.descricao.data,
                'prioridade': self.prioridade.data,
                'status': self.status.data
            }
            logger.debug(f'Convertendo formulário para dicionário: {data}')
            return data
            
        except Exception as e:
            logger.error(f'Erro ao converter formulário para dicionário: {e}', exc_info=True)
            raise
