import streamlit as st
import pandas as pd
from datetime import datetime
from modulos import Cliente
from utils.helpers import format_phone, format_cpf, validate_cpf, validate_email, format_date

def clientes_page():
    """Página de gerenciamento de clientes do sistema PDV"""
    st.title("👥 Clientes")
    
    # Verifica se o usuário está autenticado
    if 'user' not in st.session_state:
        st.warning("Por favor, faça login para acessar esta página.")
        st.stop()
    
    # Inicializa o estado da sessão para o formulário de cliente
    if 'cliente_editando' not in st.session_state:
        st.session_state.cliente_editando = None
    
    # Barra lateral com filtros e ações
    st.sidebar.header("Ações")
    
    # Botão para adicionar novo cliente
    if st.sidebar.button("➕ Novo Cliente"):
        st.session_state.cliente_editando = None
        st.experimental_rerun()
    
    # Filtros
    st.sidebar.subheader("Filtros")
    
    # Filtro por nome
    filtro_nome = st.sidebar.text_input("Nome do Cliente")
    
    # Filtro por CPF
    filtro_cpf = st.sidebar.text_input("CPF")
    
    # Filtro por status
    status_filtro = st.sidebar.radio(
        "Status",
        ["Todos", "Ativos", "Inativos"],
        index=0
    )
    
    # Busca os clientes com base nos filtros
    clientes = Cliente.buscar_por_filtros(
        nome=filtro_nome if filtro_nome else None,
        cpf=filtro_cpf if filtro_cpf else None,
        ativo=None if status_filtro == "Todos" else (status_filtro == "Ativos")
    )
    
    # Se não há clientes cadastrados ou filtro não retornou resultados
    if not clientes:
        if filtro_nome or filtro_cpf or status_filtro != "Todos":
            st.info("Nenhum cliente encontrado com os filtros selecionados.")
        else:
            st.info("Nenhum cliente cadastrado ainda. Use o botão 'Novo Cliente' para começar.")
    
    # Se há um cliente sendo editado ou um novo cliente está sendo adicionado
    if st.session_state.cliente_editando is not None:
        # Se é uma edição, carrega os dados do cliente
        if st.session_state.cliente_editando:
            cliente = next((c for c in clientes if c.id == st.session_state.cliente_editando), None)
            if not cliente:
                st.error("Cliente não encontrado.")
                st.session_state.cliente_editando = None
                st.experimental_rerun()
            titulo_form = "Editar Cliente"
            modo_edicao = True
        else:
            # Novo cliente
            cliente = Cliente()
            titulo_form = "Novo Cliente"
            modo_edicao = False
        
        # Formulário de cadastro/edição
        with st.form(key='form_cliente', clear_on_submit=not modo_edicao):
            st.subheader(titulo_form)
            
            # Dados básicos
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("Nome Completo *", 
                                  value=cliente.nome if cliente.nome else "",
                                  max_length=100)
                
                email = st.text_input("E-mail", 
                                    value=cliente.email if cliente.email else "",
                                    max_length=100)
                
                data_nascimento = st.date_input(
                    "Data de Nascimento",
                    value=datetime.strptime(cliente.data_nascimento, "%Y-%m-%d").date() if cliente.data_nascimento else None,
                    format="DD/MM/YYYY"
                )
            
            with col2:
                cpf = st.text_input(
                    "CPF *",
                    value=cliente.cpf if cliente.cpf else "",
                    max_length=14,
                    help="Formato: 000.000.000-00"
                )
                
                telefone = st.text_input(
                    "Telefone",
                    value=format_phone(cliente.telefone) if cliente.telefone else "",
                    max_length=15,
                    help="Formato: (00) 00000-0000"
                )
                
                sexo = st.selectbox(
                    "Sexo",
                    ["Não informado", "Masculino", "Feminino", "Outro"],
                    index=0 if not cliente.sexo else ["Não informado", "Masculino", "Feminino", "Outro"].index(cliente.sexo)
                )
            
            # Endereço
            st.subheader("Endereço")
            
            col1, col2 = st.columns(2)
            
            with col1:
                cep = st.text_input(
                    "CEP",
                    value=cliente.cep if cliente.cep else "",
                    max_length=9,
                    help="Formato: 00000-000"
                )
                
                logradouro = st.text_input(
                    "Logradouro",
                    value=cliente.logradouro if cliente.logradouro else "",
                    max_length=100
                )
                
                numero = st.text_input(
                    "Número",
                    value=cliente.numero if cliente.numero else "",
                    max_length=10
                )
                
                complemento = st.text_input(
                    "Complemento",
                    value=cliente.complemento if cliente.complemento else "",
                    max_length=100
                )
            
            with col2:
                bairro = st.text_input(
                    "Bairro",
                    value=cliente.bairro if cliente.bairro else "",
                    max_length=50
                )
                
                cidade = st.text_input(
                    "Cidade",
                    value=cliente.cidade if cliente.cidade else "",
                    max_length=50
                )
                
                estado = st.selectbox(
                    "Estado",
                    ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", 
                     "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", 
                     "RS", "RO", "RR", "SC", "SP", "SE", "TO"],
                    index=0 if not cliente.estado else 
                          ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", 
                           "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", 
                           "RS", "RO", "RR", "SC", "SP", "SE", "TO"].index(cliente.estado)
                )
            
            # Observações
            observacoes = st.text_area(
                "Observações",
                value=cliente.observacoes if cliente.observacoes else "",
                max_length=500,
                height=100
            )
            
            # Status (apenas para edição)
            if modo_edicao:
                ativo = st.toggle("Cliente Ativo", value=cliente.ativo)
            else:
                ativo = True  # Novo cliente é ativo por padrão
            
            # Botões do formulário
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                submit = st.form_submit_button("💾 Salvar")
            
            with col2:
                if st.form_submit_button("❌ Cancelar"):
                    st.session_state.cliente_editando = None
                    st.experimental_rerun()
            
            # Validação e salvamento
            if submit:
                # Validações
                erros = []
                
                if not nome.strip():
                    erros.append("O campo Nome Completo é obrigatório.")
                
                if not cpf.strip():
                    erros.append("O campo CPF é obrigatório.")
                elif not validate_cpf(cpf):
                    erros.append("CPF inválido. Formato esperado: 000.000.000-00")
                
                if email and not validate_email(email):
                    erros.append("E-mail inválido.")
                
                # Verifica se o CPF já existe (apenas para novo cliente)
                if not modo_edicao:
                    cpf_limpo = ''.join(filter(str.isdigit, cpf))
                    cliente_existente = Cliente.buscar_por_cpf(cpf_limpo)
                    if cliente_existente:
                        erros.append(f"Já existe um cliente cadastrado com o CPF {cpf}.")
                
                # Se não há erros, salva o cliente
                if not erros:
                    # Atualiza os dados do cliente
                    cliente.nome = nome.strip()
                    cliente.cpf = ''.join(filter(str.isdigit, cpf))
                    cliente.email = email.strip() if email else None
                    cliente.telefone = ''.join(filter(str.isdigit, telefone)) if telefone else None
                    cliente.data_nascimento = data_nascimento.strftime("%Y-%m-%d") if data_nascimento else None
                    cliente.sexo = sexo if sexo != "Não informado" else ""
                    
                    # Endereço
                    cliente.cep = ''.join(filter(str.isdigit, cep)) if cep else None
                    cliente.logradouro = logradouro.strip() if logradouro else None
                    cliente.numero = numero.strip() if numero else None
                    cliente.complemento = complemento.strip() if complemento else None
                    cliente.bairro = bairro.strip() if bairro else None
                    cliente.cidade = cidade.strip() if cidade else None
                    cliente.estado = estado if estado != "" else None
                    
                    # Outros
                    cliente.observacoes = observacoes.strip() if observacoes else None
                    cliente.ativo = ativo
                    
                    # Salva o cliente
                    if cliente.salvar():
                        st.success("Cliente salvo com sucesso!")
                        st.session_state.cliente_editando = None
                        st.experimental_rerun()
                    else:
                        st.error("Erro ao salvar o cliente. Por favor, tente novamente.")
                else:
                    # Exibe os erros de validação
                    for erro in erros:
                        st.error(erro)
        
        # Se não está em modo de edição, não mostra a lista de clientes
        return
    
    # Se chegou aqui, exibe a lista de clientes
    if clientes:
        # Prepara os dados para exibição
        dados = []
        for cliente in clientes:
            dados.append({
                "ID": cliente.id,
                "Nome": cliente.nome,
                "CPF": format_cpf(cliente.cpf) if cliente.cpf else "",
                "Telefone": format_phone(cliente.telefone) if cliente.telefone else "",
                "E-mail": cliente.email or "",
                "Cidade": cliente.cidade or "",
                "Estado": cliente.estado or "",
                "Status": "Ativo" if cliente.ativo else "Inativo",
                "Data Cadastro": format_date(cliente.data_cadastro) if cliente.data_cadastro else ""
            })
        
        # Cria o DataFrame
        df = pd.DataFrame(dados)
        
        # Exibe a tabela com os clientes
        st.dataframe(
            df,
            column_config={
                "ID": st.column_config.NumberColumn("ID", format="%d"),
                "Nome": "Nome",
                "CPF": "CPF",
                "Telefone": "Telefone",
                "E-mail": "E-mail",
                "Cidade": "Cidade",
                "Estado": "UF",
                "Status": "Status",
                "Data Cadastro": "Data Cadastro"
            },
            hide_index=True,
            use_container_width=True,
            height=600
        )
        
        # Adiciona botões de ação para cada cliente
        st.subheader("Ações")
        
        # Seleciona um cliente para ação
        cliente_id = st.selectbox(
            "Selecione um cliente para ação",
            [""] + [f"{c.id} - {c.nome}" for c in clientes],
            format_func=lambda x: x if x else "Selecione..."
        )
        
        if cliente_id:
            # Extrai o ID do cliente
            cliente_id = int(cliente_id.split(" - ")[0])
            cliente = next((c for c in clientes if c.id == cliente_id), None)
            
            if cliente:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("✏️ Editar", use_container_width=True):
                        st.session_state.cliente_editando = cliente.id
                        st.experimental_rerun()
                
                with col2:
                    # Botão para ativar/desativar
                    if cliente.ativo:
                        if st.button("🚫 Desativar", use_container_width=True):
                            if st.warning("Tem certeza que deseja desativar este cliente?"):
                                cliente.ativo = False
                                if cliente.salvar():
                                    st.success("Cliente desativado com sucesso!")
                                    st.experimental_rerun()
                                else:
                                    st.error("Erro ao desativar o cliente.")
                    else:
                        if st.button("✅ Ativar", use_container_width=True):
                            cliente.ativo = True
                            if cliente.salvar():
                                st.success("Cliente ativado com sucesso!")
                                st.experimental_rerun()
                            else:
                                st.error("Erro ao ativar o cliente.")
                
                with col3:
                    # Botão para excluir (apenas se o cliente não tiver compras)
                    if st.button("🗑️ Excluir", use_container_width=True):
                        # Verifica se o cliente tem vendas associadas
                        from modulos import Venda
                        vendas_cliente = Venda.buscar_por_cliente(cliente.id)
                        
                        if vendas_cliente:
                            st.error("Este cliente não pode ser excluído pois existem vendas associadas a ele.")
                        else:
                            if st.warning("Tem certeza que deseja excluir permanentemente este cliente? Esta ação não pode ser desfeita."):
                                if cliente.excluir():
                                    st.success("Cliente excluído com sucesso!")
                                    st.experimental_rerun()
                                else:
                                    st.error("Erro ao excluir o cliente.")
                
                # Exibe os detalhes do cliente
                st.subheader("Detalhes do Cliente")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Nome:** {cliente.nome}")
                    st.write(f"**CPF:** {format_cpf(cliente.cpf) if cliente.cpf else 'Não informado'}")
                    st.write(f"**E-mail:** {cliente.email or 'Não informado'}")
                    st.write(f"**Telefone:** {format_phone(cliente.telefone) if cliente.telefone else 'Não informado'}")
                    
                    if cliente.data_nascimento:
                        st.write(f"**Data de Nascimento:** {format_date(cliente.data_nascimento)}")
                    if cliente.sexo:
                        st.write(f"**Sexo:** {cliente.sexo}")
                
                with col2:
                    # Endereço
                    st.write("**Endereço:**")
                    endereco_parts = []
                    if cliente.logradouro:
                        endereco_parts.append(cliente.logradouro)
                        if cliente.numero:
                            endereco_parts.append(f", {cliente.numero}")
                        if cliente.complemento:
                            endereco_parts.append(f" - {cliente.complemento}")
                    
                    if endereco_parts:
                        st.write("".join(endereco_parts))
                    
                    if cliente.bairro:
                        st.write(cliente.bairro)
                    
                    cidade_estado = []
                    if cliente.cidade:
                        cidade_estado.append(cliente.cidade)
                    if cliente.estado:
                        cidade_estado.append(cliente.estado)
                    
                    if cidade_estado:
                        st.write(" - ".join(cidade_estado))
                    
                    if cliente.cep:
                        st.write(f"CEP: {cliente.cep}")
                
                # Observações
                if cliente.observacoes:
                    st.subheader("Observações")
                    st.write(cliente.observacoes)
                
                # Histórico de compras
                st.subheader("Histórico de Compras")
                
                from modulos import Venda
                vendas_cliente = Venda.buscar_por_cliente(cliente.id)
                
                if vendas_cliente:
                    dados_vendas = []
                    for venda in vendas_cliente:
                        dados_vendas.append({
                            "ID": venda.id,
                            "Data": format_date(venda.data_venda),
                            "Valor Total": f"R$ {venda.valor_total:.2f}",
                            "Forma de Pagamento": venda.forma_pagamento or "Não informada",
                            "Status": venda.status
                        })
                    
                    df_vendas = pd.DataFrame(dados_vendas)
                    st.dataframe(
                        df_vendas,
                        column_config={
                            "ID": st.column_config.NumberColumn("ID", format="%d"),
                            "Data": "Data",
                            "Valor Total": "Valor Total",
                            "Forma de Pagamento": "Pagamento",
                            "Status": "Status"
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.info("Este cliente ainda não realizou nenhuma compra.")

# Se este arquivo for executado diretamente
if __name__ == "__main__":
    clientes_page()
