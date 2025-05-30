"""
Ponto de entrada principal da aplicação Gerenciador de Ativos.
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Adiciona o diretório src ao PATH para garantir que os imports funcionem
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename

from config import get_config
from models import Ativo, Carteira
from services import YFinanceService, RelatorioService
from utils.formatters import formatar_moeda, formatar_percentual, formatar_data
from utils.validators import validar_ticker, validar_quantidade, validar_valor
from utils.logger import get_logger

# Configuração do logger
logger = get_logger(__name__)


# Inicialização da aplicação Flask
app = Flask(__name__)


# Carrega as configurações
config = get_config()
app.config.from_object(config)


# Inicialização dos serviços
yfinance_service = YFinanceService()
relatorio_service = RelatorioService()

# Caminho para o arquivo de dados da carteira
CARTAO_DE_DADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'carteira.json')

# Cria o diretório de dados se não existir
os.makedirs(os.path.dirname(CARTAO_DE_DADOS), exist_ok=True)

# Tenta carregar a carteira do arquivo, ou cria uma nova se não existir
try:
    if os.path.exists(CARTAO_DE_DADOS):
        carteira = Carteira.carregar_de_arquivo(CARTAO_DE_DADOS)
        logger.info(f"Carteira carregada de {CARTAO_DE_DADOS} com {len(carteira.itens)} ativos")
    else:
        carteira = Carteira(
            nome="Minha Carteira",
            descricao="Carteira de investimentos pessoal"
        )
        # Salva a carteira vazia
        carteira.salvar_para_arquivo(CARTAO_DE_DADOS)
        logger.info("Nova carteira criada")
except Exception as e:
    logger.error(f"Erro ao carregar a carteira: {str(e)}")
    # Cria uma nova carteira em caso de erro
    carteira = Carteira(
        nome="Minha Carteira",
        descricao="Carteira de investimentos pessoal"
    )

# Rotas da aplicação

@app.route('/excluir_ativo/<string:ticker>', methods=['POST'])
def excluir_ativo(ticker: str):
    """
    Remove um ativo da carteira.
    
    Args:
        ticker: Ticker do ativo a ser removido
        
    Returns:
        JSON com o resultado da operação
    """
    try:
        # Verifica se o ativo existe na carteira
        if ticker.upper() not in [item.ativo.ticker for item in carteira.itens.values()]:
            return jsonify({
                'sucesso': False,
                'mensagem': f'Ativo {ticker} não encontrado na carteira.'
            }), 404
            
        # Remove o ativo da carteira
        carteira.remover_ativo(ticker)
        
        # Salva as alterações no arquivo
        try:
            carteira.salvar_para_arquivo(CARTAO_DE_DADOS)
            logger.info(f"Carteira salva com sucesso após remoção em: {CARTAO_DE_DADOS}")
        except Exception as e:
            logger.error(f"Erro ao salvar carteira após remoção: {str(e)}", exc_info=True)
            return jsonify({
                'sucesso': False,
                'mensagem': f'Erro ao salvar carteira após remoção: {str(e)}'
            }), 500
        
        return jsonify({
            'sucesso': True,
            'mensagem': f'Ativo {ticker} removido com sucesso!',
            'redirect': url_for('listar_ativos')
        })
        
    except Exception as e:
        logger.error(f'Erro ao excluir ativo {ticker}: {str(e)}', exc_info=True)
        return jsonify({
            'sucesso': False,
            'mensagem': f'Erro ao excluir ativo: {str(e)}'
        }), 500

@app.route('/')
def index():
    """Página inicial com o resumo da carteira."""
    resumo = relatorio_service.gerar_resumo_carteira(carteira)
    
    # Obter relatório detalhado para pegar os ativos
    relatorio_detalhado = relatorio_service.gerar_relatorio_detalhado(carteira)
    
    # Adicionar ativos detalhados ao resumo
    if 'ativos_detalhados' in relatorio_detalhado:
        resumo['ativos_detalhados'] = relatorio_detalhado['ativos_detalhados']
        
        # Ordenar e limitar os top ativos
        if resumo['ativos_detalhados']:
            resumo['top_ativos'] = sorted(
                resumo['ativos_detalhados'],
                key=lambda x: x.get('valor_atual', 0),
                reverse=True
            )[:5]
        else:
            resumo['top_ativos'] = []
    else:
        resumo['ativos_detalhados'] = []
        resumo['top_ativos'] = []
        
    return render_template('index.html', resumo=resumo)


@app.route('/adicionar_ativo', methods=['GET', 'POST'])
def adicionar_ativo():
    """Adiciona um novo ativo à carteira."""
    if request.method == 'POST':
        logger.info("Iniciando processo de adição de ativo...")
        
        # Verifica se a requisição é JSON
        is_json_request = request.headers.get('Content-Type') == 'application/json'
        
        # Obtém os dados do formulário ou do JSON
        if is_json_request:
            data = request.get_json()
            ticker = data.get('ticker', '').strip()
            quantidade = str(data.get('quantidade', '0')).replace(',', '.')
            preco_medio = str(data.get('preco_medio', '0')).replace(',', '.')
            data_compra = data.get('data_compra', '')
        else:
            ticker = request.form.get('ticker', '').strip()
            quantidade = request.form.get('quantidade', '0').replace(',', '.')
            preco_medio = request.form.get('preco_medio', '0').replace(',', '.')
            data_compra = request.form.get('data_compra', '')
        
        logger.info(f"Dados recebidos - Ticker: {ticker}, Quantidade: {quantidade}, Preço Médio: {preco_medio}")
        
        # Função para retornar erro
        def retornar_erro(mensagem, status=400):
            if is_json_request or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                response = jsonify({'sucesso': False, 'mensagem': mensagem})
                response.headers['Content-Type'] = 'application/json'
                return response, status
            else:
                flash(mensagem, 'error')
                return render_template('adicionar_ativo.html', now=datetime.now())
        
        # Valida o ticker
        valido, mensagem = validar_ticker(ticker)
        if not valido:
            logger.warning(f"Ticker inválido: {mensagem}")
            return retornar_erro(f'Erro no ticker: {mensagem}')
        
        # Valida a quantidade
        valido, resultado = validar_quantidade(quantidade)
        if not valido:
            logger.warning(f"Quantidade inválida: {resultado}")
            return retornar_erro(f'Erro na quantidade: {resultado}')
        quantidade_float = float(resultado)
        
        # Valida o preço médio
        valido, resultado = validar_valor(preco_medio, minimo=0.01)
        if not valido:
            logger.warning(f"Preço médio inválido: {resultado}")
            return retornar_erro(f'Erro no preço médio: {resultado}')
        preco_medio_float = float(resultado)
        
        # Busca informações do ativo
        logger.info(f"Buscando informações para o ativo: {ticker}")
        ativo = yfinance_service.buscar_ativo(ticker)
        if not ativo:
            logger.error(f"Não foi possível encontrar informações para o ativo: {ticker}")
            return retornar_erro(f'Não foi possível encontrar informações para o ativo {ticker}', 404)
        
        logger.info(f"Ativo encontrado: {ativo.nome} (Tipo: {ativo.tipo}, Preço Atual: {ativo.preco_atual})")
        
        # Adiciona o ativo à carteira
        try:
            carteira.adicionar_ativo(ativo, quantidade_float, preco_medio_float)
            logger.info(f"Ativo {ticker} adicionado à carteira com sucesso!")
            logger.info(f"Total de itens na carteira: {len(carteira.itens)}")
            
            # Salva as alterações no arquivo
            try:
                carteira.salvar_para_arquivo(CARTAO_DE_DADOS)
                logger.info(f"Carteira salva com sucesso em: {CARTAO_DE_DADOS}")
            except Exception as e:
                logger.error(f"Erro ao salvar carteira: {str(e)}", exc_info=True)
                return retornar_erro(f'Erro ao salvar carteira: {str(e)}', 500)
            
            # Log dos itens atuais na carteira
            for ticker_item, item in carteira.itens.items():
                logger.info(f"Item na carteira - Ticker: {ticker_item}, Quantidade: {item.quantidade}, Preço Médio: {item.preco_medio}")
            
            if is_json_request:
                response = jsonify({
                    'sucesso': True, 
                    'mensagem': f'Ativo {ticker} adicionado com sucesso!',
                    'redirect': url_for('listar_ativos')
                })
                response.headers['Content-Type'] = 'application/json'
                return response
            else:
                flash(f'Ativo {ticker} adicionado com sucesso!', 'success')
                return redirect(url_for('listar_ativos'))
                
        except Exception as e:
            logger.error(f"Erro ao adicionar ativo à carteira: {str(e)}", exc_info=True)
            return retornar_erro(f'Erro ao adicionar ativo: {str(e)}', 500)
    
    # Se for uma requisição GET, renderiza o template normalmente
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response = jsonify({'erro': 'Método não permitido'})
        response.headers['Content-Type'] = 'application/json'
        return response, 405
    return render_template('adicionar_ativo.html', now=datetime.now())


@app.route('/ativos')
def listar_ativos():
    """Lista todos os ativos da carteira."""
    logger.info("Iniciando geração do relatório detalhado...")
    relatorio = relatorio_service.gerar_relatorio_detalhado(carteira)
    
    # Extrai os ativos e totais do relatório para usar no template
    ativos = relatorio.get('ativos_detalhados', [])
    logger.info(f"Total de ativos encontrados: {len(ativos)}")
    
    # Log dos ativos para depuração
    for i, ativo in enumerate(ativos, 1):
        logger.info(f"Ativo {i}: {ativo.get('ticker', 'N/A')} - {ativo.get('nome', 'N/A')}")
    
    totais = {
        'total_investido': relatorio.get('total_investido', 0.0),
        'valor_atual': relatorio.get('valor_atual', 0.0),
        'resultado_bruto': relatorio.get('resultado_bruto', 0.0),
        'resultado_percentual': relatorio.get('resultado_percentual', 0.0)
    }
    
    logger.info(f"Totais: {totais}")
    logger.info("Renderizando template listar_ativos.html...")
    
    return render_template('listar_ativos.html', ativos=ativos, totais=totais)


@app.route('/editar_ativo', methods=['POST'])
def editar_ativo():
    """Edita um ativo existente na carteira."""
    try:
        # Verifica se é uma requisição AJAX
        is_json_request = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Obtém os dados do formulário
        ticker_original = request.form.get('ticker_original', '').strip().upper()
        novo_ticker = request.form.get('ticker', '').strip().upper()
        quantidade = request.form.get('quantidade', '0').replace(',', '.')
        preco_medio = request.form.get('preco_medio', '0').replace(',', '.')
        
        # Validações
        if not ticker_original or not novo_ticker or not quantidade or not preco_medio:
            return jsonify({'sucesso': False, 'mensagem': 'Todos os campos são obrigatórios'}), 400
            
        try:
            quantidade_float = float(quantidade)
            preco_medio_float = float(preco_medio)
            
            if quantidade_float <= 0 or preco_medio_float <= 0:
                return jsonify({'sucesso': False, 'mensagem': 'Quantidade e preço médio devem ser maiores que zero'}), 400
                
        except ValueError:
            return jsonify({'sucesso': False, 'mensagem': 'Valores inválidos para quantidade ou preço médio'}), 400
        
        # Verifica se o ativo existe na carteira
        if ticker_original not in carteira.itens:
            return jsonify({'sucesso': False, 'mensagem': 'Ativo não encontrado na carteira'}), 404
        
        # Atualiza o ativo
        item = carteira.itens[ticker_original]
        
        # Se o ticker foi alterado, remove o antigo e adiciona um novo
        if ticker_original != novo_ticker:
            # Verifica se o novo ticker já existe (exceto se for o mesmo ativo com letras maiúsculas/minúsculas diferentes)
            if novo_ticker in carteira.itens and novo_ticker.upper() != ticker_original.upper():
                return jsonify({'sucesso': False, 'mensagem': 'Já existe um ativo com este ticker'}), 400
            
            # Remove o ativo antigo
            del carteira.itens[ticker_original]
            
            # Cria um novo ativo com os dados atualizados
            novo_ativo = Ativo(
                ticker=novo_ticker,
                nome=item.ativo.nome,  # Mantém o nome original
                tipo=item.ativo.tipo,  # Mantém o tipo original
                preco_atual=item.ativo.preco_atual,  # Mantém o preço atual
                moeda=item.ativo.moeda  # Mantém a moeda
            )
            
            # Adiciona o novo ativo à carteira
            carteira.adicionar_ativo(novo_ativo, quantidade_float, preco_medio_float)
        else:
            # Apenas atualiza a quantidade e o preço médio
            item.quantidade = quantidade_float
            item.preco_medio = preco_medio_float
        
        # Salva as alterações
        try:
            carteira.salvar_para_arquivo(CARTAO_DE_DADOS)
            logger.info(f"Carteira salva em {CARTAO_DE_DADOS}")
        except Exception as e:
            logger.error(f"Erro ao salvar a carteira: {str(e)}")
            return jsonify({'sucesso': False, 'mensagem': f'Erro ao salvar a carteira: {str(e)}'}), 500
        
        return jsonify({
            'sucesso': True, 
            'mensagem': f'Ativo {novo_ticker} atualizado com sucesso!',
            'redirect': url_for('listar_ativos')
        })
        
    except Exception as e:
        logger.error(f"Erro ao editar ativo: {str(e)}", exc_info=True)
        return jsonify({'sucesso': False, 'mensagem': f'Erro ao editar ativo: {str(e)}'}), 500


@app.route('/ativo/<ticker>')
def detalhar_ativo(ticker: str):
    """Exibe os detalhes de um ativo específico."""
    if ticker not in carteira.itens:
        flash('Ativo não encontrado na carteira.', 'error')
        return redirect(url_for('listar_ativos'))
    
    item = carteira.itens[ticker]
    historico = yfinance_service.buscar_historico(ticker, periodo='1y')
    
    # Get current timestamp in local timezone
    agora = datetime.now(timezone.utc).astimezone()
    
    return render_template(
        'detalhar_ativo.html', 
        item=item,
        historico=historico,
        formatar_moeda=formatar_moeda,
        formatar_percentual=formatar_percentual,
        formatar_data=formatar_data,
        agora=agora
    )


@app.route('/api/ativo/<ticker>/info')
def get_ativo_info(ticker: str):
    """Retorna informações em tempo real de um ativo."""
    try:
        # Busca informações do ativo
        ativo = yfinance_service.buscar_ativo(ticker)
        if not ativo:
            return jsonify({'erro': 'Ativo não encontrado'}), 404
        
        # Busca histórico recente para o gráfico
        historico = yfinance_service.buscar_historico(ticker, periodo='1mo', intervalo='1d')
        
        # Prepara os dados para o gráfico
        dados_grafico = []
        if historico and 'dados' in historico:
            dados_grafico = [{
                'data': dado['data'],
                'preco': float(dado['fechamento'])
            } for dado in historico['dados'] if 'fechamento' in dado and dado['fechamento'] is not None]
            
            # Ordena os dados por data para garantir a ordem correta
            dados_grafico.sort(key=lambda x: x['data'])
        
        # Prepara os dados principais
        dados_principal = {
            'ticker': ativo.ticker,
            'nome': ativo.nome,
            'tipo': ativo.tipo,
            'preco_atual': ativo.preco_atual,
            'variacao_dia': ativo.dados_mercado.get('regularMarketChangePercent', 0.0),
            'variacao_valor': ativo.dados_mercado.get('regularMarketChange', 0.0),
            'min_dia': ativo.dados_mercado.get('dayLow', ativo.preco_atual),
            'max_dia': ativo.dados_mercado.get('dayHigh', ativo.preco_atual),
            'abertura': ativo.dados_mercado.get('open', ativo.preco_atual),
            'fechamento_anterior': ativo.dados_mercado.get('previousClose', ativo.preco_atual),
            'volume': ativo.dados_mercado.get('volume', 0),
            'volume_medio': ativo.dados_mercado.get('averageVolume', 0),
            'market_cap': ativo.dados_mercado.get('marketCap', 0),
            'moeda': ativo.moeda,
            'ultima_atualizacao': ativo.ultima_atualizacao.isoformat() if ativo.ultima_atualizacao else None,
            'dividend_yield': ativo.dados_mercado.get('dividendYield'),
            'lpa': ativo.dados_mercado.get('trailingEps'),
            'p_l': ativo.dados_mercado.get('trailingPE')
        }
        
        # Dados adicionais específicos por tipo de ativo
        dados_especificos = {}
        if ativo.tipo.lower() in ['ação', 'stock']:
            dados_especificos = {
                'dividend_yield': ativo.dados_mercado.get('dividendYield', 0.0) * 100 if ativo.dados_mercado.get('dividendYield') else 0.0,
                'lpa': ativo.dados_mercado.get('trailingEps'),
                'p_l': ativo.dados_mercado.get('trailingPE'),
                'valor_mercado': ativo.dados_mercado.get('marketCap'),
                'ebitda': ativo.dados_mercado.get('ebitda'),
                'divida_liquida': ativo.dados_mercado.get('totalDebt'),
                'setor': ativo.setor,
                'empresa': ativo.dados_mercado.get('longBusinessSummary', '')
            }
        elif ativo.tipo.lower() in ['criptomoeda', 'crypto']:
            dados_especificos = {
                'fornecimento_circulante': ativo.dados_mercado.get('circulatingSupply'),
                'fornecimento_total': ativo.dados_mercado.get('totalSupply'),
                'max_supply': ativo.dados_mercado.get('maxSupply'),
                'volume_24h': ativo.dados_mercado.get('volume24Hr'),
                'variacao_24h': ativo.dados_mercado.get('regularMarketChangePercent', 0.0)
            }
        
        return jsonify({
            'sucesso': True,
            'dados': dados_principal,
            'dados_especificos': dados_especificos,
            'grafico': dados_grafico
        })
        
    except Exception as e:
        app.logger.error(f"Erro ao buscar informações do ativo {ticker}: {str(e)}")
        return jsonify({'erro': str(e)}), 500


@app.route('/exportar')
def exportar():
    """Exporta a carteira para diferentes formatos."""
    formato = request.args.get('formato', 'xlsx').lower()
    
    if formato not in ['xlsx', 'csv', 'json']:
        flash('Formato de exportação inválido.', 'error')
        return redirect(url_for('index'))
    
    # Gera o nome do arquivo
    nome_arquivo = f'carteira_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{formato}'
    caminho_arquivo = os.path.join(app.config['EXPORT_DIR'], nome_arquivo)
    
    # Exporta para o formato solicitado
    if formato == 'xlsx':
        sucesso = relatorio_service.exportar_para_excel(carteira, caminho_arquivo)
    # Adicionar suporte a CSV e JSON aqui
    else:
        sucesso = False
    
    if sucesso:
        return send_from_directory(
            app.config['EXPORT_DIR'],
            nome_arquivo,
            as_attachment=True
        )
    else:
        flash('Erro ao exportar a carteira.', 'error')
        return redirect(url_for('index'))


# Filtros de template personalizados
@app.template_filter('moeda')
def filtro_moeda(valor, moeda='R$'):
    """Filtro para formatar valores monetários."""
    return formatar_moeda(valor, moeda)


@app.template_filter('percentual')
def filtro_percentual(valor, casas=2):
    """Filtro para formatar percentuais."""
    return formatar_percentual(valor, casas_decimais=casas)


@app.template_filter('data')
def filtro_data(data, formato='%d/%m/%Y'):
    """Filtro para formatar datas."""
    return formatar_data(data, formato_saida=formato)


# Manipuladores de erro
@app.errorhandler(404)
def pagina_nao_encontrada(e):
    """Página não encontrada."""
    return render_template('erro.html', erro='Página não encontrada', codigo=404), 404


@app.errorhandler(500)
def erro_servidor(e):
    """Erro interno do servidor."""
    logger.error(f'Erro 500: {str(e)}', exc_info=True)
    return render_template('erro.html', erro='Erro interno do servidor', codigo=500), 500


if __name__ == '__main__':
    # Cria os diretórios necessários
    os.makedirs(app.config['EXPORT_DIR'], exist_ok=True)
    
    # Inicia o servidor de desenvolvimento
    app.run(debug=app.config['DEBUG'], host='0.0.0.0', port=5000)
