import streamlit as st
import pandas as pd
from datetime import datetime
from modulos import Usuario
from utils.helpers import format_phone, format_cpf, validate_cpf, validate_email, format_date

def usuarios_page():
    """Página de gerenciamento de usuários do sistema PDV"""
    st.title("👤 Usuários")
    
    # Verifica se o usuário está autenticado
    if 'user' not in st.session_state:
        st.warning("Por favor, faça login para acessar esta página.")
        st.stop()
    
    # Verifica se o usuário é administrador
    if st.session_state.user.get('role') != 'admin':
        st.error("Acesso negado. Apenas administradores podem gerenciar usuários.")
        return
    
    # Inicializa o estado da sessão para o formulário de usuário
    if 'usuario_editando' not in st.session_state:
        st.session_state.usuario_editando = None
    
    # Barra lateral com filtros e ações
    st.sidebar.header("Ações")
    
    # Botão para adicionar novo usuário
    if st.sidebar.button("➕ Novo Usuário"):
        st.session_state.usuario_editando = None
        st.experimental_rerun()
    
    # Filtros
    st.sidebar.subheader("Filtros")
    
    # Filtro por nome
    filtro_nome = st.sidebar.text_input("Nome do Usuário")
    
    # Filtro por e-mail
    filtro_email = st.sidebar.text_input("E-mail")
    
    # Filtro por status
    status_filtro = st.sidebar.radio(
        "Status",
        ["Todos", "Ativos", "Inativos"],
        index=0
    )
    
    # Filtro por perfil
    perfil_filtro = st.sidebar.selectbox(
        "Perfil",
        ["Todos", "Administrador", "Vendedor", "Caixa"],
        index=0
    )
    
    # Mapeia os perfis para os valores no banco de dados
    perfil_map = {
        "Administrador": "admin",
        "Vendedor": "vendedor",
        "Caixa": "caixa"
    }
    
    # Busca os usuários com base nos filtros
    usuarios = Usuario.buscar_por_filtros(
        nome=filtro_nome if filtro_nome else None,
        email=filtro_email if filtro_email else None,
        ativo=None if status_filtro == "Todos" else (status_filtro == "Ativos"),
        perfil=perfil_map[perfil_filtro] if perfil_filtro != "Todos" else None
    )
    
    # Se não há usuários cadastrados ou filtro não retornou resultados
    if not usuarios:
        if filtro_nome or filtro_email or status_filtro != "Todos" or perfil_filtro != "Todos":
            st.info("Nenhum usuário encontrado com os filtros selecionados.")
        else:
            st.info("Nenhum usuário cadastrado. Use o botão 'Novo Usuário' para começar.")
    
    # Se há um usuário sendo editado ou um novo usuário está sendo adicionado
    if st.session_state.usuario_editando is not None:
        # Se é uma edição, carrega os dados do usuário
        if st.session_state.usuario_editando:
            usuario = next((u for u in usuarios if u.id == st.session_state.usuario_editando), None)
            if not usuario:
                st.error("Usuário não encontrado.")
                st.session_state.usuario_editando = None
                st.experimental_rerun()
            titulo_form = "Editar Usuário"
            modo_edicao = True
        else:
            # Novo usuário
            usuario = Usuario()
            titulo_form = "Novo Usuário"
            modo_edicao = False
        
        # Formulário de cadastro/edição
        with st.form(key='form_usuario', clear_on_submit=not modo_edicao):
            st.subheader(titulo_form)
            
            # Dados básicos
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("Nome Completo *", 
                                   value=usuario.nome if usuario.nome else "",
                                   max_length=100)
                
                email = st.text_input("E-mail *", 
                                    value=usuario.email if usuario.email else "",
                                    max_length=100)
                
                # Senha (obrigatória apenas para novo usuário)
                if not modo_edicao:
                    senha = st.text_input("Senha *", 
                                        type="password",
                                        help="A senha deve ter pelo menos 6 caracteres.")
                else:
                    senha = st.text_input("Nova Senha", 
                                        type="password",
                                        help="Deixe em branco para manter a senha atual.")
                
                # Confirmação de senha
                if not modo_edicao or senha:
                    confirmar_senha = st.text_input("Confirmar Senha", 
                                                  type="password",
                                                  help="Digite a mesma senha novamente.")
                else:
                    confirmar_senha = ""
            
            with col2:
                cpf = st.text_input(
                    "CPF *",
                    value=usuario.cpf if usuario.cpf else "",
                    max_length=14,
                    help="Formato: 000.000.000-00"
                )
                
                telefone = st.text_input(
                    "Telefone *",
                    value=format_phone(usuario.telefone) if usuario.telefone else "",
                    max_length=15,
                    help="Formato: (00) 00000-0000"
                )
                
                perfil = st.selectbox(
                    "Perfil *",
                    ["Administrador", "Gerente", "Vendedor", "Caixa"],
                    index=0 if not usuario.perfil else 
                          ["Administrador", "Gerente", "Vendedor", "Caixa"].index(usuario.perfil.capitalize())
                )
                
                # Status (apenas para edição e não pode desativar a si mesmo)
                if modo_edicao:
                    if usuario.id != st.session_state.user['id']:  # Não pode desativar a si mesmo
                        ativo = st.toggle("Usuário Ativo", value=usuario.ativo)
                    else:
                        ativo = True
                        st.write("**Status:** Ativo (você não pode desativar a si mesmo)")
                else:
                    ativo = True  # Novo usuário é ativo por padrão
            
            # Botões do formulário
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                submit = st.form_submit_button("💾 Salvar")
            
            with col2:
                if st.form_submit_button("❌ Cancelar"):
                    st.session_state.usuario_editando = None
                    st.experimental_rerun()
            
            # Validação e salvamento
            if submit:
                # Validações
                erros = []
                
                if not nome.strip():
                    erros.append("O campo Nome Completo é obrigatório.")
                
                if not email.strip():
                    erros.append("O campo E-mail é obrigatório.")
                elif not validate_email(email):
                    erros.append("E-mail inválido.")
                
                if not cpf.strip():
                    erros.append("O campo CPF é obrigatório.")
                elif not validate_cpf(cpf):
                    erros.append("CPF inválido. Formato esperado: 000.000.000-00")
                
                if not telefone.strip():
                    erros.append("O campo Telefone é obrigatório.")
                
                # Validação de senha
                if not modo_edicao and not senha:
                    erros.append("A senha é obrigatória para novo usuário.")
                
                if senha and len(senha) < 6:
                    erros.append("A senha deve ter pelo menos 6 caracteres.")
                
                if senha and senha != confirmar_senha:
                    erros.append("As senhas não conferem.")
                
                # Verifica se o e-mail já existe (apenas para novo usuário ou se o e-mail foi alterado)
                if not modo_edicao or email.lower() != usuario.email.lower():
                    usuario_existente = Usuario.buscar_por_email(email)
                    if usuario_existente and (not modo_edicao or usuario_existente.id != usuario.id):
                        erros.append(f"Já existe um usuário cadastrado com o e-mail {email}.")
                
                # Verifica se o CPF já existe (apenas para novo usuário ou se o CPF foi alterado)
                cpf_limpo = ''.join(filter(str.isdigit, cpf))
                if not modo_edicao or cpf_limpo != usuario.cpf:
                    cpf_existente = Usuario.buscar_por_cpf(cpf_limpo)
                    if cpf_existente and (not modo_edicao or cpf_existente.id != usuario.id):
                        erros.append(f"Já existe um usuário cadastrado com o CPF {cpf}.")
                
                # Se não há erros, salva o usuário
                if not erros:
                    # Atualiza os dados do usuário
                    usuario.nome = nome.strip()
                    usuario.email = email.strip().lower()
                    usuario.cpf = cpf_limpo
                    usuario.telefone = ''.join(filter(str.isdigit, telefone))
                    usuario.perfil = perfil.lower()
                    
                    # Atualiza a senha se fornecida
                    if senha:
                        usuario.set_senha(senha)
                    
                    # Status
                    if modo_edicao and usuario.id != st.session_state.user['id']:  # Não pode desativar a si mesmo
                        usuario.ativo = ativo
                    
                    # Salva o usuário
                    if usuario.salvar():
                        st.success("Usuário salvo com sucesso!")
                        st.session_state.usuario_editando = None
                        st.experimental_rerun()
                    else:
                        st.error("Erro ao salvar o usuário. Por favor, tente novamente.")
                else:
                    # Exibe os erros de validação
                    for erro in erros:
                        st.error(erro)
        
        # Se não está em modo de edição, não mostra a lista de usuários
        return
    
    # Se chegou aqui, exibe a lista de usuários
    if usuarios:
        # Prepara os dados para exibição
        dados = []
        for usuario in usuarios:
            dados.append({
                "ID": usuario.id,
                "Nome": usuario.nome,
                "E-mail": usuario.email,
                "CPF": format_cpf(usuario.cpf) if usuario.cpf else "",
                "Telefone": format_phone(usuario.telefone) if usuario.telefone else "",
                "Perfil": usuario.perfil.capitalize(),
                "Último Acesso": format_date(usuario.ultimo_acesso) if usuario.ultimo_acesso else "Nunca",
                "Status": "Ativo" if usuario.ativo else "Inativo"
            })
        
        # Cria o DataFrame
        df = pd.DataFrame(dados)
        
        # Exibe a tabela com os usuários
        st.dataframe(
            df,
            column_config={
                "ID": st.column_config.NumberColumn("ID", format="%d"),
                "Nome": "Nome",
                "E-mail": "E-mail",
                "CPF": "CPF",
                "Telefone": "Telefone",
                "Perfil": "Perfil",
                "Último Acesso": "Último Acesso",
                "Status": "Status"
            },
            hide_index=True,
            use_container_width=True,
            height=600
        )
        
        # Adiciona botões de ação para cada usuário
        st.subheader("Ações")
        
        # Seleciona um usuário para ação
        usuario_id = st.selectbox(
            "Selecione um usuário para ação",
            [""] + [f"{u.id} - {u.nome} ({u.perfil.capitalize()})" for u in usuarios],
            format_func=lambda x: x if x else "Selecione..."
        )
        
        if usuario_id:
            # Extrai o ID do usuário
            usuario_id = int(usuario_id.split(" - ")[0])
            usuario = next((u for u in usuarios if u.id == usuario_id), None)
            
            if usuario:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("✏️ Editar", use_container_width=True):
                        st.session_state.usuario_editando = usuario.id
                        st.experimental_rerun()
                
                with col2:
                    # Botão para ativar/desativar (não pode desativar a si mesmo)
                    if usuario.id == st.session_state.user['id']:
                        st.button("🚫 Desativar", disabled=True, help="Você não pode desativar a si mesmo", use_container_width=True)
                    else:
                        if usuario.ativo:
                            if st.button("🚫 Desativar", use_container_width=True):
                                usuario.ativo = False
                                if usuario.salvar():
                                    st.success("Usuário desativado com sucesso!")
                                    st.experimental_rerun()
                                else:
                                    st.error("Erro ao desativar o usuário.")
                        else:
                            if st.button("✅ Ativar", use_container_width=True):
                                usuario.ativo = True
                                if usuario.salvar():
                                    st.success("Usuário ativado com sucesso!")
                                    st.experimental_rerun()
                                else:
                                    st.error("Erro ao ativar o usuário.")
                
                with col3:
                    # Botão para redefinir senha
                    if st.button("🔑 Redefinir Senha", use_container_width=True):
                        # Gera uma senha aleatória
                        import random
                        import string
                        nova_senha = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                        
                        # Define a nova senha
                        usuario.set_senha(nova_senha)
                        
                        if usuario.salvar():
                            st.success("Senha redefinida com sucesso!")
                            st.info(f"Nova senha temporária: **{nova_senha}**")
                            st.warning("Recomenda-se que o usuário altere esta senha no próximo login.")
                        else:
                            st.error("Erro ao redefinir a senha.")
                
                # Exibe os detalhes do usuário
                st.subheader("Detalhes do Usuário")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Nome:** {usuario.nome}")
                    st.write(f"**E-mail:** {usuario.email}")
                    st.write(f"**CPF:** {format_cpf(usuario.cpf) if usuario.cpf else 'Não informado'}")
                    st.write(f"**Telefone:** {format_phone(usuario.telefone) if usuario.telefone else 'Não informado'}")
                
                with col2:
                    st.write(f"**Perfil:** {usuario.perfil.capitalize()}")
                    st.write(f"**Status:** {'Ativo' if usuario.ativo else 'Inativo'}")
                    st.write(f"**Data de Cadastro:** {format_date(usuario.data_cadastro) if usuario.data_cadastro else 'Não disponível'}")
                    st.write(f"**Último Acesso:** {format_date(usuario.ultimo_acesso) if usuario.ultimo_acesso else 'Nunca'}")
                
                # Estatísticas do usuário (se aplicável)
                if usuario.ultimo_acesso:
                    st.subheader("Estatísticas")
                    
                    # Aqui você pode adicionar estatísticas específicas do usuário, como:
                    # - Total de vendas realizadas
                    # - Valor total vendido
                    # - Média de vendas por dia
                    # etc.
                    
                    st.info("Estatísticas detalhadas do usuário serão exibidas aqui.")

# Se este arquivo for executado diretamente
if __name__ == "__main__":
    usuarios_page()
