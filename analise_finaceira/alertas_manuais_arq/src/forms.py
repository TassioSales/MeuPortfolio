from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField, DateField, BooleanField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Optional, NumberRange

class AlertaForm(FlaskForm):
    id = HiddenField('ID')
    
    tipo_alerta = SelectField('Tipo de Alerta', 
                            choices=[
                                ('', 'Selecione...'),
                                ('RECEITA', 'Receita'),
                                ('DESPESA', 'Despesa')
                            ],
                            validators=[DataRequired(message='Selecione o tipo de alerta')])
    
    categoria = SelectField('Categoria', choices=[], validators=[Optional()])
    descricao = StringField('Descrição', validators=[DataRequired()])
    
    valor_referencia = DecimalField('Valor de Referência (R$)', 
                                  places=2,
                                  validators=[DataRequired(), NumberRange(min=0.01)])
    
    prioridade = SelectField('Prioridade',
                           choices=[
                               ('baixa', 'Baixa'),
                               ('media', 'Média'),
                               ('alta', 'Alta')
                           ],
                           default='media')
    
    data_inicio = DateField('Data Início (opcional)', 
                           format='%Y-%m-%d',
                           validators=[Optional()])
    
    data_fim = DateField('Data Fim (opcional)',
                       format='%Y-%m-%d',
                       validators=[Optional()])
    
    notificar_email = BooleanField('Notificar por E-mail', default=False)
    notificar_app = BooleanField('Notificar no Aplicativo', default=True)
    
    submit = SubmitField('Salvar Alerta')
    
    def to_dict(self):
        """Converte o formulário para dicionário para facilitar a inserção no banco."""
        data = {
            'id': int(self.id.data) if self.id.data else None,
            'tipo_alerta': self.tipo_alerta.data,
            'categoria': self.categoria.data or None,
            'descricao': self.descricao.data,
            'valor_referencia': float(self.valor_referencia.data),
            'prioridade': self.prioridade.data,
            'notificar_email': self.notificar_email.data,
            'notificar_app': self.notificar_app.data
        }
        
        # Adicionar datas apenas se forem fornecidas
        if self.data_inicio.data:
            data['data_inicio'] = self.data_inicio.data.strftime('%Y-%m-%d')
        if self.data_fim.data:
            data['data_fim'] = self.data_fim.data.strftime('%Y-%m-%d')
            
        return data
