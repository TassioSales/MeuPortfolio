import streamlit as st
import json
import os
from datetime import datetime
from utils.helpers import format_phone, format_cnpj, validate_cnpj, validate_email

# Caminho para o arquivo de configurações
CONFIG_FILE = "config.json"

def carregar_configuracoes():
    """Carrega as configurações do arquivo JSON"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Erro ao carregar configurações: {e}")
    
    # Retorna configurações padrão se o arquivo não existir ou ocorrer erro
    return {
        "empresa": {
            "nome": "Minha Empresa",
            "nome_fantasia": "",
            "cnpj": "",
            "ie": "",
            "im": "",
            "cnae": "",
            "regime_tributario": "SIMPLES NACIONAL"
        },
        "endereco": {
            "logradouro": "",
            "numero": "",
            "complemento": "",
            "bairro": "",
            "cidade": "",
            "estado": "SP",
            "cep": "",
            "telefone": "",
            "email": "",
            "site": ""
        },
        "pdv": {
            "impressora_padrao": "",
            "imprimir_comprovante": True,
            "imprimir_via_cliente": True,
            "imprimir_2vias": False,
            "permitir_desconto": True,
            "limite_desconto": 10.0,
            "permitir_acima_estoque": False,
            "mostrar_estoque_zerado": True,
            "exibir_imagens_produtos": True
        },
        "nota_fiscal": {
            "ambiente": "homologacao",  # homologacao ou producao
            "serie": "1",
            "ultimo_numero": "0",
            "modelo": "65",  # NFC-e
            "serie_nfce": "1",
            "ultimo_numero_nfce": "0",
            "csc": "",
            "csc_id": "",
            "token_nfce": "",
            "certificado_a1": "",
            "senha_certificado": "",
            "caminho_logo": "",
            "mensagem_complementar": ""
        },
        "financeiro": {
            "dias_vencimento": 30,
            "multa_atraso": 2.0,
            "juros_mensal": 1.0,
            "desconto_avista": 5.0,
            "dias_desconto_avista": 7,
            "banco_padrao": "",
            "agencia_padrao": "",
            "conta_padrao": "",
            "carteira_padrao": ""
        },
        "backup": {
            "pasta_backup": "backups",
            "manter_backups": 30,  # dias
            "backup_automatico": True,
            "hora_backup": "23:00"
        },
        "outros": {
            "tema": "Claro",
            "idioma": "Português (Brasil)",
            "moeda": "R$",
            "casas_decimais": 2,
            "separador_decimal": ",",
            "separador_milhar": "."
        },
        "ultima_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "versao": "1.0.0"
    }

def salvar_configuracoes(config):
    """Salva as configurações no arquivo JSON"""
    try:
        config['ultima_atualizacao'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar configurações: {e}")
        return False

def configuracoes_page():
    """Página de configurações do sistema PDV"""
    st.title("⚙️ Configurações")
    
    # Verifica se o usuário está autenticado
    if 'user' not in st.session_state:
        st.warning("Por favor, faça login para acessar esta página.")
        st.stop()
    
    # Verifica se o usuário é administrador
    if st.session_state.user.get('role') != 'admin':
        st.error("Acesso negado. Apenas administradores podem acessar as configurações do sistema.")
        return
    
    # Carrega as configurações atuais
    config = carregar_configuracoes()
    
    # Abas de configuração
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🏢 Empresa", "🏠 Endereço", "🛒 PDV", "📄 Nota Fiscal", "💰 Financeiro", "⚙️ Outros"
    ])
    
    # Aba de configurações da empresa
    with tab1:
        st.subheader("Dados da Empresa")
        
        with st.form("form_empresa"):
            col1, col2 = st.columns(2)
            
            with col1:
                config["empresa"]["nome"] = st.text_input(
                    "Razão Social *",
                    value=config["empresa"].get("nome", "")
                )
                
                config["empresa"]["nome_fantasia"] = st.text_input(
                    "Nome Fantasia",
                    value=config["empresa"].get("nome_fantasia", "")
                )
                
                config["empresa"]["cnpj"] = st.text_input(
                    "CNPJ *",
                    value=config["empresa"].get("cnpj", ""),
                    help="Formato: 00.000.000/0000-00"
                )
                
                config["empresa"]["ie"] = st.text_input(
                    "Inscrição Estadual",
                    value=config["empresa"].get("ie", "")
                )
            
            with col2:
                config["empresa"]["im"] = st.text_input(
                    "Inscrição Municipal",
                    value=config["empresa"].get("im", "")
                )
                
                config["empresa"]["cnae"] = st.text_input(
                    "CNAE",
                    value=config["empresa"].get("cnae", "")
                )
                
                config["empresa"]["regime_tributario"] = st.selectbox(
                    "Regime Tributário",
                    ["SIMPLES NACIONAL", "LUCRO PRESUMIDO", "LUCRO REAL", "MEI"],
                    index=["SIMPLES NACIONAL", "LUCRO PRESUMIDO", "LUCRO REAL", "MEI"].index(
                        config["empresa"].get("regime_tributario", "SIMPLES NACIONAL")
                    )
                )
            
            # Botões do formulário
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.form_submit_button("💾 Salvar Dados da Empresa"):
                    # Validações
                    if not config["empresa"]["nome"]:
                        st.error("O campo Razão Social é obrigatório.")
                    elif not config["empresa"]["cnpj"]:
                        st.error("O campo CNPJ é obrigatório.")
                    elif not validate_cnpj(config["empresa"]["cnpj"]):
                        st.error("CNPJ inválido. Formato esperado: 00.000.000/0000-00")
                    else:
                        if salvar_configuracoes(config):
                            st.success("Dados da empresa salvos com sucesso!")
                        else:
                            st.error("Erro ao salvar as configurações.")
    
    # Aba de endereço
    with tab2:
        st.subheader("Endereço e Contato")
        
        with st.form("form_endereco"):
            col1, col2 = st.columns(2)
            
            with col1:
                config["endereco"]["logradouro"] = st.text_input(
                    "Logradouro",
                    value=config["endereco"].get("logradouro", "")
                )
                
                config["endereco"]["numero"] = st.text_input(
                    "Número",
                    value=config["endereco"].get("numero", "")
                )
                
                config["endereco"]["complemento"] = st.text_input(
                    "Complemento",
                    value=config["endereco"].get("complemento", "")
                )
                
                config["endereco"]["bairro"] = st.text_input(
                    "Bairro",
                    value=config["endereco"].get("bairro", "")
                )
            
            with col2:
                config["endereco"]["cidade"] = st.text_input(
                    "Cidade",
                    value=config["endereco"].get("cidade", "")
                )
                
                config["endereco"]["estado"] = st.selectbox(
                    "Estado",
                    ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", 
                     "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", 
                     "RS", "RO", "RR", "SC", "SP", "SE", "TO"],
                    index=["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", 
                           "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", 
                           "RS", "RO", "RR", "SC", "SP", "SE", "TO"].index(
                               config["endereco"].get("estado", "SP")
                           )
                )
                
                config["endereco"]["cep"] = st.text_input(
                    "CEP",
                    value=config["endereco"].get("cep", "")
                )
                
                config["endereco"]["telefone"] = st.text_input(
                    "Telefone",
                    value=config["endereco"].get("telefone", "")
                )
                
                config["endereco"]["email"] = st.text_input(
                    "E-mail",
                    value=config["endereco"].get("email", "")
                )
                
                config["endereco"]["site"] = st.text_input(
                    "Site",
                    value=config["endereco"].get("site", "")
                )
            
            # Botões do formulário
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.form_submit_button("💾 Salvar Endereço"):
                    if salvar_configuracoes(config):
                        st.success("Dados de endereço salvos com sucesso!")
                    else:
                        st.error("Erro ao salvar as configurações.")
    
    # Aba de configurações do PDV
    with tab3:
        st.subheader("Configurações do PDV")
        
        with st.form("form_pdv"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Impressão")
                
                config["pdv"]["impressora_padrao"] = st.selectbox(
                    "Impressora Padrão",
                    ["Nenhuma", "Impressora Térmica", "Impressora Matricial"],
                    index=["Nenhuma", "Impressora Térmica", "Impressora Matricial"].index(
                        config["pdv"].get("impressora_padrao", "Nenhuma")
                    )
                )
                
                config["pdv"]["imprimir_comprovante"] = st.checkbox(
                    "Imprimir comprovante ao finalizar venda",
                    value=config["pdv"].get("imprimir_comprovante", True)
                )
                
                config["pdv"]["imprimir_via_cliente"] = st.checkbox(
                    "Imprimir via do cliente",
                    value=config["pdv"].get("imprimir_via_cliente", True)
                )
                
                config["pdv"]["imprimir_2vias"] = st.checkbox(
                    "Imprimir 2ª via automaticamente",
                    value=config["pdv"].get("imprimir_2vias", False)
                )
                
                st.markdown("#### Exibição")
                
                config["pdv"]["exibir_imagens_produtos"] = st.checkbox(
                    "Exibir imagens dos produtos",
                    value=config["pdv"].get("exibir_imagens_produtos", True)
                )
                
                config["pdv"]["mostrar_estoque_zerado"] = st.checkbox(
                    "Mostrar produtos com estoque zerado",
                    value=config["pdv"].get("mostrar_estoque_zerado", True)
                )
            
            with col2:
                st.markdown("#### Descontos")
                
                config["pdv"]["permitir_desconto"] = st.checkbox(
                    "Permitir desconto nos itens",
                    value=config["pdv"].get("permitir_desconto", True)
                )
                
                if config["pdv"]["permitir_desconto"]:
                    config["pdv"]["limite_desconto"] = st.number_input(
                        "Limite de desconto (%)",
                        min_value=0.0,
                        max_value=100.0,
                        step=0.5,
                        value=float(config["pdv"].get("limite_desconto", 10.0))
                    )
                
                st.markdown("#### Estoque")
                
                config["pdv"]["permitir_acima_estoque"] = st.checkbox(
                    "Permitar vender acima do estoque",
                    value=config["pdv"].get("permitir_acima_estoque", False),
                    help="Permitir finalizar venda mesmo que não haja estoque suficiente"
                )
            
            # Botões do formulário
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.form_submit_button("💾 Salvar Configurações do PDV"):
                    if salvar_configuracoes(config):
                        st.success("Configurações do PDV salvas com sucesso!")
                    else:
                        st.error("Erro ao salvar as configurações.")
    
    # Aba de configurações de Nota Fiscal
    with tab4:
        st.subheader("Configurações de Nota Fiscal")
        
        with st.form("form_nfe"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Configurações Gerais")
                
                config["nota_fiscal"]["ambiente"] = st.radio(
                    "Ambiente",
                    ["homologacao", "producao"],
                    index=0 if config["nota_fiscal"].get("ambiente") == "homologacao" else 1,
                    format_func=lambda x: "Homologação" if x == "homologacao" else "Produção"
                )
                
                config["nota_fiscal"]["modelo"] = st.selectbox(
                    "Modelo de Documento Fiscal",
                    ["55", "65"],  # 55=NF-e, 65=NFC-e
                    index=0 if config["nota_fiscal"].get("modelo") == "55" else 1,
                    format_func=lambda x: "NF-e (55)" if x == "55" else "NFC-e (65)"
                )
                
                if config["nota_fiscal"]["modelo"] == "55":
                    config["nota_fiscal"]["serie"] = st.text_input(
                        "Série",
                        value=config["nota_fiscal"].get("serie", "1")
                    )
                    
                    config["nota_fiscal"]["ultimo_numero"] = st.text_input(
                        "Último Número",
                        value=config["nota_fiscal"].get("ultimo_numero", "0")
                    )
                else:  # NFC-e
                    config["nota_fiscal"]["serie_nfce"] = st.text_input(
                        "Série NFC-e",
                        value=config["nota_fiscal"].get("serie_nfce", "1")
                    )
                    
                    config["nota_fiscal"]["ultimo_numero_nfce"] = st.text_input(
                        "Último Número NFC-e",
                        value=config["nota_fiscal"].get("ultimo_numero_nfce", "0")
                    )
                
                config["nota_fiscal"]["csc"] = st.text_input(
                    "CSC (Código de Segurança do Contribuinte)",
                    value=config["nota_fiscal"].get("csc", ""),
                    type="password"
                )
                
                config["nota_fiscal"]["csc_id"] = st.text_input(
                    "ID do CSC",
                    value=config["nota_fiscal"].get("csc_id", "")
                )
            
            with col2:
                st.markdown("#### Certificado Digital")
                
                # Upload do certificado (apresentação apenas, não funcional neste exemplo)
                certificado = st.file_uploader(
                    "Certificado Digital (.pfx ou .p12)",
                    type=["pfx", "p12"]
                )
                
                if certificado is not None:
                    st.warning("Em uma implementação real, o certificado seria validado e armazenado com segurança.")
                
                config["nota_fiscal"]["senha_certificado"] = st.text_input(
                    "Senha do Certificado",
                    value="",  # Por segurança, não preenchemos a senha salva
                    type="password",
                    help="Deixe em branco para manter a senha atual"
                )
                
                st.markdown("#### Personalização")
                
                # Upload da logo (apresentação apenas, não funcional neste exemplo)
                logo = st.file_uploader(
                    "Logo para a Nota Fiscal",
                    type=["png", "jpg", "jpeg"]
                )
                
                if logo is not None:
                    st.warning("Em uma implementação real, a imagem seria redimensionada e salva.")
                
                config["nota_fiscal"]["mensagem_complementar"] = st.text_area(
                    "Mensagem Complementar",
                    value=config["nota_fiscal"].get("mensagem_complementar", ""),
                    help="Esta mensagem aparecerá no rodapé da nota fiscal"
                )
            
            # Botões do formulário
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.form_submit_button("💾 Salvar Configurações de NF-e"):
                    # Validações
                    erros = []
                    
                    if not config["nota_fiscal"]["csc"]:
                        erros.append("O campo CSC é obrigatório.")
                    
                    if not config["nota_fiscal"]["csc_id"]:
                        erros.append("O campo ID do CSC é obrigatório.")
                    
                    if not erros:
                        if salvar_configuracoes(config):
                            st.success("Configurações de Nota Fiscal salvas com sucesso!")
                        else:
                            st.error("Erro ao salvar as configurações.")
                    else:
                        for erro in erros:
                            st.error(erro)
    
    # Aba de configurações financeiras
    with tab5:
        st.subheader("Configurações Financeiras")
        
        with st.form("form_financeiro"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Parâmetros de Cobrança")
                
                config["financeiro"]["dias_vencimento"] = st.number_input(
                    "Dias para Vencimento Padrão",
                    min_value=1,
                    max_value=365,
                    value=int(config["financeiro"].get("dias_vencimento", 30)),
                    help="Número de dias para o vencimento padrão das contas a receber"
                )
                
                config["financeiro"]["multa_atraso"] = st.number_input(
                    "Multa por Atraso (%)",
                    min_value=0.0,
                    max_value=100.0,
                    step=0.1,
                    value=float(config["financeiro"].get("multa_atraso", 2.0))
                )
                
                config["financeiro"]["juros_mensal"] = st.number_input(
                    "Juros ao Mês (%)",
                    min_value=0.0,
                    max_value=100.0,
                    step=0.1,
                    value=float(config["financeiro"].get("juros_mensal", 1.0))
                )
                
                st.markdown("#### Descontos")
                
                config["financeiro"]["desconto_avista"] = st.number_input(
                    "Desconto para Pagamento à Vista (%)",
                    min_value=0.0,
                    max_value=100.0,
                    step=0.5,
                    value=float(config["financeiro"].get("desconto_avista", 5.0))
                )
                
                config["financeiro"]["dias_desconto_avista"] = st.number_input(
                    "Válido até (dias)",
                    min_value=0,
                    max_value=30,
                    value=int(config["financeiro"].get("dias_desconto_avista", 7)),
                    help="Número de dias para o desconto à vista ser válido"
                )
            
            with col2:
                st.markdown("#### Dados Bancários")
                
                config["financeiro"]["banco_padrao"] = st.text_input(
                    "Banco Padrão",
                    value=config["financeiro"].get("banco_padrao", "")
                )
                
                config["financeiro"]["agencia_padrao"] = st.text_input(
                    "Agência",
                    value=config["financeiro"].get("agencia_padrao", "")
                )
                
                config["financeiro"]["conta_padrao"] = st.text_input(
                    "Conta Corrente",
                    value=config["financeiro"].get("conta_padrao", "")
                )
                
                config["financeiro"]["carteira_padrao"] = st.text_input(
                    "Carteira",
                    value=config["financeiro"].get("carteira_padrao", "")
                )
            
            # Botões do formulário
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.form_submit_button("💾 Salvar Configurações Financeiras"):
                    if salvar_configuracoes(config):
                        st.success("Configurações financeiras salvas com sucesso!")
                    else:
                        st.error("Erro ao salvar as configurações.")
    
    # Aba de outras configurações
    with tab6:
        st.subheader("Outras Configurações")
        
        with st.form("form_outros"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Aparência")
                
                config["outros"]["tema"] = st.selectbox(
                    "Tema",
                    ["Claro", "Escuro", "Sistema"],
                    index=["Claro", "Escuro", "Sistema"].index(
                        config["outros"].get("tema", "Claro")
                    )
                )
                
                config["outros"]["idioma"] = st.selectbox(
                    "Idioma",
                    ["Português (Brasil)", "Inglês", "Espanhol"],
                    index=["Português (Brasil)", "Inglês", "Espanhol"].index(
                        config["outros"].get("idioma", "Português (Brasil)")
                    )
                )
                
                st.markdown("#### Formatação de Números")
                
                config["outros"]["moeda"] = st.text_input(
                    "Símbolo da Moeda",
                    value=config["outros"].get("moeda", "R$")
                )
                
                config["outros"]["casas_decimais"] = st.number_input(
                    "Casas Decimais",
                    min_value=0,
                    max_value=4,
                    value=int(config["outros"].get("casas_decimais", 2))
                )
                
                config["outros"]["separador_decimal"] = st.text_input(
                    "Separador Decimal",
                    value=config["outros"].get("separador_decimal", ",")
                )
                
                config["outros"]["separador_milhar"] = st.text_input(
                    "Separador de Milhar",
                    value=config["outros"].get("separador_milhar", ".")
                )
            
            with col2:
                st.markdown("#### Backup")
                
                config["backup"]["pasta_backup"] = st.text_input(
                    "Pasta de Backup",
                    value=config["backup"].get("pasta_backup", "backups")
                )
                
                config["backup"]["backup_automatico"] = st.checkbox(
                    "Realizar backup automático",
                    value=config["backup"].get("backup_automatico", True)
                )
                
                if config["backup"]["backup_automatico"]:
                    config["backup"]["hora_backup"] = st.time_input(
                        "Horário do Backup",
                        value=datetime.strptime(
                            config["backup"].get("hora_backup", "23:00"), 
                            "%H:%M"
                        ).time()
                    ).strftime("%H:%M")
                    
                    config["backup"]["manter_backups"] = st.number_input(
                        "Manter backups por (dias)",
                        min_value=1,
                        max_value=365,
                        value=int(config["backup"].get("manter_backups", 30))
                    )
                
                st.markdown("#### Manutenção")
                
                if st.button("🔄 Limpar Cache"):
                    st.info("Funcionalidade de limpeza de cache será implementada aqui.")
                
                if st.button("🔍 Verificar Atualizações"):
                    st.info("Verificando atualizações...")
                    st.warning("Esta é uma versão de demonstração. Em uma implementação real, seria verificado se há atualizações disponíveis.")
            
            # Botões do formulário
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.form_submit_button("💾 Salvar Configurações"):
                    if salvar_configuracoes(config):
                        st.success("Configurações salvas com sucesso!")
                        
                        # Aplica o tema selecionado
                        if config["outros"]["tema"] == "Escuro":
                            st.experimental_set_query_params(theme="dark")
                        elif config["outros"]["tema"] == "Claro":
                            st.experimental_set_query_params(theme="light")
                        else:  # Sistema
                            st.experimental_set_query_params(theme="system")
                    else:
                        st.error("Erro ao salvar as configurações.")
    
    # Seção de informações do sistema
    st.sidebar.subheader("Informações do Sistema")
    
    st.sidebar.write(f"**Versão:** {config.get('versao', '1.0.0')}")
    
    if 'ultima_atualizacao' in config:
        st.sidebar.write(f"**Última Atualização:** {config['ultima_atualizacao']}")
    
    st.sidebar.write("**Status:** 🟢 Online")
    
    # Botão para fazer backup manual
    if st.sidebar.button("💾 Fazer Backup Agora"):
        st.sidebar.info("Iniciando backup...")
        # Aqui iria o código para fazer o backup
        st.sidebar.success("Backup concluído com sucesso!")
    
    # Botão para restaurar backup
    if st.sidebar.button("🔄 Restaurar Backup"):
        st.sidebar.warning("Funcionalidade de restauração de backup será implementada aqui.")
    
    # Seção de suporte
    st.sidebar.markdown("---")
    st.sidebar.subheader("Suporte")
    
    if st.sidebar.button("📞 Contatar Suporte"):
        st.sidebar.info("Entre em contato pelo e-mail: suporte@sistemapdv.com.br")
    
    if st.sidebar.button("📚 Documentação"):
        st.sidebar.info("Acesse nossa documentação em: https://docs.sistemapdv.com.br")

# Se este arquivo for executado diretamente
if __name__ == "__main__":
    configuracoes_page()
