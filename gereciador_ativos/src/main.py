"""
Ponto de entrada principal da aplicação Gerenciador de Ativos.
"""
import os
import sys
from pathlib import Path
from datetime import datetime

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

# Exemplo de carteira (substituir por banco de dados em produção)
carteira = Carteira(
    nome="Minha Carteira",
    descricao="Carteira de investimentos pessoal"
)

# Rotas da aplicação

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
        # Valida os dados do formulário
        ticker = request.form.get('ticker', '').strip()
        quantidade = request.form.get('quantidade', '0').replace(',', '.')
        preco_medio = request.form.get('preco_medio', '0').replace(',', '.')
        data_compra = request.form.get('data_compra', '')
        
        logger.info(f"Dados do formulário - Ticker: {ticker}, Quantidade: {quantidade}, Preço Médio: {preco_medio}")
        
        # Valida o ticker
        valido, mensagem = validar_ticker(ticker)
        if not valido:
            logger.warning(f"Ticker inválido: {mensagem}")
            flash(f'Erro no ticker: {mensagem}', 'error')
            return render_template('adicionar_ativo.html')
        
        # Valida a quantidade
        valido, resultado = validar_quantidade(quantidade)
        if not valido:
            logger.warning(f"Quantidade inválida: {resultado}")
            flash(f'Erro na quantidade: {resultado}', 'error')
            return render_template('adicionar_ativo.html')
        quantidade_float = float(resultado)
        
        # Valida o preço médio
        valido, resultado = validar_valor(preco_medio, minimo=0.01)
        if not valido:
            logger.warning(f"Preço médio inválido: {resultado}")
            flash(f'Erro no preço médio: {resultado}', 'error')
            return render_template('adicionar_ativo.html')
        preco_medio_float = float(resultado)
        
        # Busca informações do ativo
        logger.info(f"Buscando informações para o ativo: {ticker}")
        ativo = yfinance_service.buscar_ativo(ticker)
        if not ativo:
            logger.error(f"Não foi possível encontrar informações para o ativo: {ticker}")
            flash(f'Não foi possível encontrar informações para o ativo {ticker}', 'error')
            return render_template('adicionar_ativo.html', now=datetime.now())
        
        logger.info(f"Ativo encontrado: {ativo.nome} (Tipo: {ativo.tipo}, Preço Atual: {ativo.preco_atual})")
        
        # Adiciona o ativo à carteira
        try:
            carteira.adicionar_ativo(ativo, quantidade_float, preco_medio_float)
            logger.info(f"Ativo {ticker} adicionado à carteira com sucesso!")
            logger.info(f"Total de itens na carteira: {len(carteira.itens)}")
            
            # Log dos itens atuais na carteira
            for ticker_item, item in carteira.itens.items():
                logger.info(f"Item na carteira - Ticker: {ticker_item}, Quantidade: {item.quantidade}, Preço Médio: {item.preco_medio}")
            
            flash(f'Ativo {ticker} adicionado com sucesso!', 'success')
            return redirect(url_for('listar_ativos'))
        except Exception as e:
            logger.error(f"Erro ao adicionar ativo à carteira: {str(e)}", exc_info=True)
            flash(f'Erro ao adicionar ativo: {str(e)}', 'error')
            return render_template('adicionar_ativo.html', now=datetime.now())
    
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


@app.route('/ativo/<ticker>')
def detalhar_ativo(ticker: str):
    """Exibe os detalhes de um ativo específico."""
    if ticker not in carteira.itens:
        flash('Ativo não encontrado na carteira.', 'error')
        return redirect(url_for('listar_ativos'))
    
    item = carteira.itens[ticker]
    historico = yfinance_service.buscar_historico(ticker, periodo='1y')
    
    return render_template(
        'detalhar_ativo.html', 
        item=item,
        historico=historico,
        formatar_moeda=formatar_moeda,
        formatar_percentual=formatar_percentual,
        formatar_data=formatar_data
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
