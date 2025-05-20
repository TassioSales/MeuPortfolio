from flask import render_template, request, jsonify
from .services import AnaliseEstatisticaService
from .database import db_session

def analise():
    return render_template('analise_estatistica.html')

def analisar():
    try:
        # Obter dados do formulário
        data_inicio = request.form.get('data_inicio')
        data_fim = request.form.get('data_fim')
        tipos_analise = request.form.getlist('tipo_analise')

        # Validar dados
        if not data_inicio or not data_fim:
            return jsonify({'sucesso': False, 'mensagem': 'Datas são obrigatórias'}), 400

        # Criar serviço de análise
        service = AnaliseEstatisticaService(db_session)
        
        # Realizar análise
        resultados = service.analisar(data_inicio, data_fim, tipos_analise)
        
        return jsonify(resultados)

    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500

# Exportar as funções
__all__ = ['analise', 'analisar']