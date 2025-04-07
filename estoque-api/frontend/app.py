from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import requests
from flask_bootstrap import Bootstrap
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Necessário para flash messages
bootstrap = Bootstrap(app)

API_BASE_URL = 'http://localhost:8000'

def format_datetime(value):
    """Filtro Jinja2 para formatar datetime"""
    if value:
        return datetime.fromisoformat(value).strftime('%d/%m/%Y %H:%M')
    return ''

app.jinja_env.filters['datetime'] = format_datetime

@app.route('/')
def index():
    try:
        # Obtém dados do dashboard
        dashboard_response = requests.get(f'{API_BASE_URL}/products/dashboard')
        dashboard_response.raise_for_status()  # Lança exceção para status codes de erro
        dashboard = dashboard_response.json()
        
        # Obtém alertas
        alerts_response = requests.get(f'{API_BASE_URL}/products/alerts')
        alerts_response.raise_for_status()
        alerts = alerts_response.json()
        
        # Obtém produtos
        products_response = requests.get(f'{API_BASE_URL}/products/')
        products_response.raise_for_status()
        products = products_response.json()
        
        return render_template('index.html', 
                             products=products,
                             dashboard=dashboard,
                             alerts=alerts)
    except requests.RequestException as e:
        flash(f'Erro ao carregar dados: {str(e)}', 'danger')
        return render_template('index.html', 
                             products=[],
                             dashboard={'total_products': 0, 'total_value': 0, 'average_price': 0, 'low_stock_count': 0, 'out_of_stock_count': 0},
                             alerts=[])

@app.route('/product/new', methods=['GET', 'POST'])
def create_product():
    if request.method == 'POST':
        try:
            product_data = {
                'name': request.form['name'],
                'description': request.form['description'],
                'price': float(request.form['price']),
                'quantity': int(request.form['quantity']),
                'minimum_stock': int(request.form['minimum_stock']),
                'category': request.form['category'],
                'supplier': request.form['supplier'],
                'location': request.form['location']
            }
            response = requests.post(f'{API_BASE_URL}/products/', json=product_data)
            response.raise_for_status()
            flash('Produto criado com sucesso!', 'success')
            return redirect(url_for('index'))
        except requests.RequestException as e:
            error_detail = e.response.json().get('detail', str(e)) if e.response else str(e)
            flash(f'Erro ao criar produto: {error_detail}', 'danger')
    return render_template('create_product.html')

@app.route('/product/<int:product_id>/edit', methods=['GET', 'POST'])
def edit_product(product_id):
    if request.method == 'POST':
        try:
            product_data = {
                'name': request.form['name'],
                'description': request.form['description'],
                'price': float(request.form['price']),
                'quantity': int(request.form['quantity']),
                'minimum_stock': int(request.form['minimum_stock']),
                'category': request.form['category'],
                'supplier': request.form['supplier'],
                'location': request.form['location']
            }
            response = requests.put(f'{API_BASE_URL}/products/{product_id}', json=product_data)
            response.raise_for_status()
            flash('Produto atualizado com sucesso!', 'success')
            return redirect(url_for('index'))
        except requests.RequestException as e:
            error_detail = e.response.json().get('detail', str(e)) if e.response else str(e)
            flash(f'Erro ao atualizar produto: {error_detail}', 'danger')
    
    try:
        response = requests.get(f'{API_BASE_URL}/products/{product_id}')
        response.raise_for_status()
        product = response.json()
        return render_template('create_product.html', product=product)
    except requests.RequestException as e:
        flash(f'Erro ao carregar produto: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/product/<int:product_id>/delete')
def delete_product(product_id):
    try:
        response = requests.delete(f'{API_BASE_URL}/products/{product_id}')
        response.raise_for_status()
        flash('Produto deletado com sucesso!', 'success')
    except requests.RequestException as e:
        error_detail = e.response.json().get('detail', str(e)) if e.response else str(e)
        flash(f'Erro ao deletar produto: {error_detail}', 'danger')
    return redirect(url_for('index'))

@app.route('/product/<int:product_id>/stock', methods=['POST'])
def update_stock(product_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Dados inválidos. O corpo da requisição está vazio.'
            }), 400

        # Validação dos campos obrigatórios
        if 'quantity' not in data or 'reason' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Dados inválidos. Quantidade e motivo são obrigatórios.'
            }), 400

        # Validação do tipo e valor dos campos
        try:
            quantity = int(data['quantity'])
            reason = str(data['reason']).strip()
        except (ValueError, TypeError):
            return jsonify({
                'status': 'error',
                'message': 'Dados inválidos. Quantidade deve ser um número inteiro e motivo deve ser texto.'
            }), 400

        # Validação do motivo
        if not reason or len(reason) < 3 or len(reason) > 200:
            return jsonify({
                'status': 'error',
                'message': 'Motivo inválido. Deve ter entre 3 e 200 caracteres.'
            }), 400

        # Faz a requisição para a API
        response = requests.post(
            f'{API_BASE_URL}/products/{product_id}/stock',
            json={
                'quantity': quantity,
                'reason': reason
            },
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()
        
        result = response.json()
        return jsonify({
            'status': 'success',
            'message': 'Estoque atualizado com sucesso!',
            'data': result
        })
    except requests.RequestException as e:
        error_detail = e.response.json().get('detail', str(e)) if e.response else str(e)
        return jsonify({
            'status': 'error',
            'message': f'Erro: {error_detail}'
        }), e.response.status_code if e.response else 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erro interno: {str(e)}'
        }), 500

@app.route('/search')
def search_products():
    try:
        search = request.args.get('q', '')
        category = request.args.get('category', '')
        
        params = {'search': search}
        if category:
            params['category'] = category
        
        response = requests.get(f'{API_BASE_URL}/products/', params=params)
        response.raise_for_status()
        products = response.json()
        
        return render_template('products_table.html', products=products)
    except requests.RequestException as e:
        flash(f'Erro ao pesquisar produtos: {str(e)}', 'danger')
        return render_template('products_table.html', products=[])

if __name__ == '__main__':
    app.run(port=5000, debug=True)
