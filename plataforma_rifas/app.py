from __future__ import annotations

import os
import sys
import traceback
import streamlit as st
import pandas as pd
import uuid
from pathlib import Path
import random
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timezone, timedelta

from fpdf import FPDF
import qrcode
from babel.numbers import format_currency

from modules import db_data_manager as dm
from modules.ui_components import _build_pdf_bytes, renderizar_relatorio_compradores
from modules import ui_components as ui
from logger import get_logger, log_exceptions, add_user_context

logger = get_logger(__name__)

APP_TITLE = "🎟️ Plataforma de Rifas PRO"

def _safe_fname(text: str) -> str:
    for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
        text = text.replace(ch, '-')
    return text.strip().replace(' ', '_')

# PDF generation function moved to ui_components.py

def main():
    st.set_page_config(page_title=APP_TITLE, layout="wide", initial_sidebar_state="expanded")
    
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())[:8]
    logger.info(f"Aplicação iniciada", session_id=st.session_state["session_id"])
    
    try:
        dm.migrate_from_json()
        logger.success("Migração JSON→SQLite executada com sucesso")
    except Exception as e:
        logger.warning("Falha ao migrar dados JSON→SQLite", exception=e)
    
    user = st.session_state.get("user")
    with st.sidebar:
        st.markdown("### Autenticação")
        if not user:
            tab_login, tab_signup = st.tabs(["Entrar", "Criar conta"])
            with tab_login:
                email = st.text_input("E-mail", key="login_email")
                password = st.text_input("Senha", type="password", key="login_password")
                if st.button("Entrar", use_container_width=True):
                    ok, msg, u = dm.authenticate(email, password)
                    if ok:
                        st.session_state["user"] = u
                        add_user_context(u["name"], str(u["id"]))
                        st.success(f"Bem-vindo(a), {u['name']}!")
                        logger.success(f"Usuário {u['email']} logado com sucesso", user_id=u["id"])
                        st.rerun()
                    else:
                        st.error(msg)
                        logger.warning(f"Falha no login para {email}", message=msg)
            with tab_signup:
                name_s = st.text_input("Nome", key="signup_name")
                email_s = st.text_input("E-mail", key="signup_email")
                password_s = st.text_input("Senha", type="password", key="signup_password")
                if st.button("Criar conta", use_container_width=True):
                    ok, msg, uid = dm.create_user(name_s, email_s, password_s)
                    if ok:
                        st.success("Conta criada! Faça login.")
                        logger.success(f"Conta criada para {email_s}", user_id=uid)
                    else:
                        st.error(msg)
                        logger.warning(f"Falha ao criar conta para {email_s}", message=msg)
        else:
            st.success(f"Logado como: {user['name']} ({user['email']})")
            if st.button("Sair", use_container_width=True):
                logger.info(f"Usuário {user['email']} deslogado", user_id=user['id'])
                st.session_state.pop("user")
                add_user_context("system", "none")
                st.rerun()
    
    nome_rifa = ui.renderizar_sidebar(user=user)
    if not nome_rifa:
        st.info("⬅️ Selecione ou crie uma rifa na barra lateral para começar.")
        logger.info("Nenhuma rifa selecionada, aplicação pausada")
        st.stop()
    
    try:
        cfg = dm.get_config_rifa(nome_rifa) or {}
        dados = dm.carregar_dados_rifa(nome_rifa)
        logger.debug(f"Dados da rifa {nome_rifa} carregados", config=cfg, vendas=len(dados))
    except Exception as e:
        logger.error(f"Falha ao carregar dados da rifa {nome_rifa}", exception=e)
        st.error("Erro ao carregar dados da rifa. Verifique os logs.")
        st.stop()
    
    tab_titles = ["📊 Dashboard", "🔍 Consultar/Exportar", "📈 Analytics", "🏆 Sorteio", "⚙️ Gerenciamento", "👤 Minha Conta"]
    tabs = st.tabs(tab_titles)
    
    with tabs[0]:
        try:
            ui.renderizar_dashboard(nome_rifa, dados, cfg)
            st.markdown("---")
            ui.renderizar_grid_vendas(nome_rifa, dados, cfg)
            st.markdown("---")
            st.subheader("🕒 Últimas ações")
            colf1, colf2, colf3 = st.columns([1, 1, 1])
            with colf1:
                preset = st.selectbox("Período", options=["Últimas 24h", "7 dias", "30 dias", "Tudo", "Personalizado"], index=1)
            start_iso = end_iso = None
            if preset == "Últimas 24h":
                start_iso = (pd.Timestamp.utcnow() - pd.Timedelta(days=1)).isoformat()
            elif preset == "7 dias":
                start_iso = (pd.Timestamp.utcnow() - pd.Timedelta(days=7)).isoformat()
            elif preset == "30 dias":
                start_iso = (pd.Timestamp.utcnow() - pd.Timedelta(days=30)).isoformat()
            elif preset == "Personalizado":
                with colf2:
                    d_ini = st.date_input("Início", value=pd.Timestamp.utcnow().date() - pd.Timedelta(days=7))
                with colf3:
                    d_fim = st.date_input("Fim", value=pd.Timestamp.utcnow().date())
                start_iso = pd.Timestamp(d_ini).isoformat()
                end_iso = (pd.Timestamp(d_fim) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)).isoformat()
            
            vendas_periodo = dm.get_sales_in_period(nome_rifa, start_iso, end_iso)
            if vendas_periodo:
                df_hist = pd.DataFrame(vendas_periodo)
                df_hist.rename(columns={"timestamp": "Data/Hora", "comprador": "Comprador", "numero": "Número", "contato": "Contato"}, inplace=True)
                df_hist = df_hist.sort_values("Data/Hora", ascending=False)
                st.dataframe(df_hist.head(50), use_container_width=True)
                logger.debug(f"Histórico de vendas exibido para rifa {nome_rifa}", period=preset)
            else:
                st.info("Sem ações no período.")
                logger.debug(f"Nenhuma venda encontrada no período {preset} para rifa {nome_rifa}")
        except Exception as e:
            logger.error(f"Erro ao renderizar dashboard para rifa {nome_rifa}", exception=e)
            st.error("Erro ao carregar dashboard. Verifique os logs.")
    
    with tabs[1]:
        st.header("🔍 Consultar e Exportar Dados")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Consulta por número")
            num = st.number_input("Número", min_value=1, max_value=int(cfg.get("total_numeros", 1)), step=1)
            if st.button("Consultar número"):
                comprador = dados.get(str(int(num)))
                if comprador:
                    st.success(f"Número {int(num)} vendido para: {comprador}")
                    logger.info(f"Consulta por número {num} na rifa {nome_rifa}", comprador=comprador)
                else:
                    st.info(f"Número {int(num)} está disponível.")
                    logger.info(f"Consulta por número {num} na rifa {nome_rifa}: disponível")
        
        with col2:
            st.subheader("Consulta por nome")
            nome = st.text_input("Nome do comprador")
            if st.button("Consultas compras"):
                resultados = sorted([int(n) for n, c in dados.items() if nome.strip().lower() in c.lower()])
                if resultados:
                    st.success(f"{nome} comprou: {resultados}")
                    logger.info(f"Consulta por comprador {nome} na rifa {nome_rifa}", resultados=resultados)
                else:
                    st.info(f"Nenhuma compra encontrada para '{nome}'.")
                    logger.info(f"Consulta por comprador {nome} na rifa {nome_rifa}: sem resultados")
        
        st.markdown("---")
        st.subheader("Exportar CSV de Vendas")
        colp1, colp2, colp3 = st.columns([1, 1, 1])
        with colp1:
            preset2 = st.selectbox("Período", options=["Últimas 24h", "7 dias", "30 dias", "Tudo", "Personalizado"], index=3, key="csv_preset")
        start2 = end2 = None
        if preset2 == "Últimas 24h":
            start2 = (pd.Timestamp.utcnow() - pd.Timedelta(days=1)).isoformat()
        elif preset2 == "7 dias":
            start2 = (pd.Timestamp.utcnow() - pd.Timedelta(days=7)).isoformat()
        elif preset2 == "30 dias":
            start2 = (pd.Timestamp.utcnow() - pd.Timedelta(days=30)).isoformat()
        elif preset2 == "Personalizado":
            with colp2:
                d_ini2 = st.date_input("Início", value=pd.Timestamp.utcnow().date() - pd.Timedelta(days=7), key="csv_inicio")
            with colp3:
                d_fim2 = st.date_input("Fim", value=pd.Timestamp.utcnow().date(), key="csv_fim")
            start2 = pd.Timestamp(d_ini2).isoformat()
            end2 = (pd.Timestamp(d_fim2) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)).isoformat()
        
        vendas = dm.get_sales_in_period(nome_rifa, start2, end2)
        if vendas:
            df = pd.DataFrame(vendas)
            df.rename(columns={"timestamp": "Data/Hora", "comprador": "Comprador", "numero": "Número", "contato": "Contato"}, inplace=True)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Baixar CSV", data=csv, file_name=f"{_safe_fname(nome_rifa)}_vendas.csv", mime="text/csv")
            logger.success(f"CSV de vendas gerado para rifa {nome_rifa}", period=preset2)
        
        st.markdown("---")
        st.subheader("Exportar PDF de Comprovantes")
        colsel1, colsel2, colsel3 = st.columns([1, 1, 1])
        with colsel1:
            numeros_pdf_txt = st.text_input("Números (ex: 1-10, 25)")
        with colsel2:
            compradores_opts = ["(Todos)"] + sorted(list({v['comprador'] for v in vendas})) if vendas else ["(Todos)"]
            comprador_pdf = st.selectbox("Comprador", options=compradores_opts)
        with colsel3:
            tz_default = int(cfg.get('tz_offset_default', 0))
            tz_offset = st.number_input("Fuso horário (offset horas)", value=tz_default, step=1, min_value=-12, max_value=14)
        
        if vendas:
            vendas_sel = vendas
            if numeros_pdf_txt:
                try:
                    nums = ui._parse_ranges(numeros_pdf_txt)
                    vendas_sel = [v for v in vendas_sel if int(v['numero']) in set(nums)]
                    logger.debug(f"Filtro de números aplicado para PDF", numeros=nums)
                except Exception as e:
                    logger.warning(f"Falha ao parsear números para PDF", exception=e)
                    st.error("Formato de números inválido.")
                    vendas_sel = []
            
            if comprador_pdf and comprador_pdf != "(Todos)":
                vendas_sel = [v for v in vendas_sel if v['comprador'] == comprador_pdf]
                logger.debug(f"Filtro de comprador {comprador_pdf} aplicado para PDF")
            
            if vendas_sel and st.button("Gerar PDF de comprovantes"):
                try:
                    if comprador_pdf and comprador_pdf != "(Todos)":
                        pdf_bytes = _build_pdf_bytes(
                            vendas_list=vendas_sel,
                            cfg_local=cfg,
                            consolidate_buyer=comprador_pdf,
                            nome_rifa=nome_rifa,
                            tz_offset=tz_offset
                        )
                        fname = f"{_safe_fname(nome_rifa)}_{_safe_fname(comprador_pdf)}_comprovante.pdf"
                    else:
                        pdf_bytes = _build_pdf_bytes(
                            vendas_list=vendas_sel,
                            cfg_local=cfg,
                            nome_rifa=nome_rifa,
                            tz_offset=tz_offset
                        )
                        fname = f"{_safe_fname(nome_rifa)}_comprovantes.pdf"
                    st.download_button("Baixar PDF", data=pdf_bytes, file_name=fname, mime="application/pdf")
                    logger.success(f"PDF de comprovantes gerado para rifa {nome_rifa}", comprador=comprador_pdf)
                except Exception as e:
                    logger.error(f"Falha ao gerar PDF para rifa {nome_rifa}", exception=e)
                    st.error(f"Erro ao gerar PDF: {str(e)}")
        
        # Adiciona o relatório de compradores
        st.markdown("---")
        st.subheader("📊 Relatório por Comprador")
        
        # Obtém todas as vendas para o relatório
        todas_vendas = dm.get_sales_in_period(nome_rifa, None, None)
        valor_unit = float(cfg.get("valor_numero", 0.0))
        
        if todas_vendas:
            renderizar_relatorio_compradores(nome_rifa, todas_vendas, valor_unit, cfg)
        else:
            st.info("Nenhuma venda encontrada para gerar o relatório.")
    
    with tabs[2]:
        try:
            ui.renderizar_analytics_tab(nome_rifa)
            logger.debug(f"Aba de analytics renderizada para rifa {nome_rifa}")
        except Exception as e:
            logger.error(f"Erro ao renderizar aba de analytics para rifa {nome_rifa}", exception=e)
            st.error("Erro ao carregar análises. Verifique os logs.")
    
    with tabs[3]:
        st.header("🏆 Sorteio")
        if cfg.get("sorteio_realizado"):
            st.success(f"🎉 Sorteio já realizado! 🎉")
            st.balloons()
            ui._render_metric("Número Vencedor", cfg.get('sorteio_numero'))
            ui._render_metric("Comprador Sortudo", cfg.get('sorteio_comprador'))
            logger.info(f"Sorteio já realizado exibido para rifa {nome_rifa}")
        else:
            st.warning("Atenção: o sorteio pode ser realizado apenas uma vez.")
            if st.button("🍀 Realizar Sorteio Agora!", type="primary"):
                try:
                    ok, numero, comprador, msg = dm.escolher_vencedor(nome_rifa)
                    if ok:
                        st.success(msg)
                        logger.success(f"Sorteio realizado para rifa {nome_rifa}", numero=numero, comprador=comprador)
                        st.rerun()
                    else:
                        st.error(msg)
                        logger.warning(f"Falha ao realizar sorteio para rifa {nome_rifa}", message=msg)
                except Exception as e:
                    logger.error(f"Erro ao realizar sorteio para rifa {nome_rifa}", exception=e)
                    st.error(f"Erro inesperado ao realizar sorteio: {str(e)}")
            
            st.markdown("---")
            st.subheader("Simular Sorteio (não persiste)")
            if st.button("🎲 Simular sorteio"):
                vendidos = list(map(int, dados.keys()))
                if not vendidos:
                    st.info("Nenhum número vendido para simular.")
                    logger.info(f"Simulação de sorteio não realizada para rifa {nome_rifa}: sem números vendidos")
                else:
                    sorteado = random.choice(vendidos)
                    st.info(f"Número sorteado (simulação): {sorteado} | Comprador: {dados.get(str(sorteado))}")
                    logger.info(f"Simulação de sorteio realizada para rifa {nome_rifa}", numero=sorteado, comprador=dados.get(str(sorteado)))
    
    with tabs[4]:
        st.header("⚙️ Gerenciamento da Rifa")
        dono_ok = True
        if user and cfg.get('owner_id') is not None:
            dono_ok = int(user['id']) == int(cfg.get('owner_id'))
        if not dono_ok:
            st.warning("Você não é o dono desta rifa. Operações administrativas estão bloqueadas.")
            logger.warning(f"Usuário {user.get('id') if user else 'anônimo'} tentou acessar gerenciamento da rifa {nome_rifa} sem permissão")
        
        st.subheader("Operações de Venda")
        with st.expander("Cancelar venda de números"):
            numeros_cancelar = st.text_input("Números para cancelar (ex: 5, 12-15)")
            if st.button("Confirmar Cancelamento de Venda"):
                if not dono_ok:
                    st.error("Operação bloqueada para não-donos.")
                    logger.warning(f"Usuário {user.get('id') if user else 'anônimo'} tentou cancelar venda sem permissão", rifa=nome_rifa)
                    st.stop()
                try:
                    nums = ui._parse_ranges(numeros_cancelar)
                    ok, detalhes, msg = dm.cancelar_venda(nome_rifa, nums)
                    if ok:
                        st.success(msg)
                        logger.success(f"Vendas canceladas para rifa {nome_rifa}", detalhes=detalhes)
                        st.rerun()
                    else:
                        st.error(msg)
                        logger.warning(f"Falha ao cancelar vendas para rifa {nome_rifa}", message=msg)
                except Exception as e:
                    logger.error(f"Erro ao parsear números para cancelamento na rifa {nome_rifa}", exception=e)
                    st.error(f"Formato de números inválido: {str(e)}")
        
        with st.expander("Transferir números para outro comprador"):
            numeros_transferir = st.text_input("Números para transferir (ex: 2, 40-45)")
            novo_comprador = st.text_input("Nome do novo comprador")
            if st.button("Confirmar Transferência"):
                if not dono_ok:
                    st.error("Operação bloqueada para não-donos.")
                    logger.warning(f"Usuário {user.get('id') if user else 'anônimo'} tentou transferir venda sem permissão", rifa=nome_rifa)
                    st.stop()
                try:
                    nums = ui._parse_ranges(numeros_transferir)
                    ok, detalhes, msg = dm.transferir_venda(nome_rifa, nums, novo_comprador)
                    if ok:
                        st.success(msg)
                        logger.success(f"Transferência realizada para rifa {nome_rifa}", novo_comprador=novo_comprador, detalhes=detalhes)
                        st.rerun()
                    else:
                        st.error(msg)
                        logger.warning(f"Falha ao transferir vendas para rifa {nome_rifa}", message=msg)
                except Exception as e:
                    logger.error(f"Erro ao parsear números para transferência na rifa {nome_rifa}", exception=e)
                    st.error(f"Formato de números inválido: {str(e)}")
        
        st.markdown("---")
        st.subheader("Configurações")
        ttl = st.number_input(
            "TTL para reservas (minutos, 0 para desativar)",
            min_value=0,
            value=int(cfg.get("reserva_ttl_minutos", 0)),
            step=1,
        )
        logo_path = st.text_input("Caminho do logo (opcional)", value=cfg.get("logo_path", ""))
        qr_text = st.text_area("Texto do QR code (use {rifa}, {numero}, {comprador}, {contato})", value=cfg.get("qr_text", ""))
        obs_pdf = st.text_area("Observação padrão no PDF", value=cfg.get("obs_padrao_pdf", ""))
        tz_offset = st.number_input(
            "Fuso horário padrão (offset horas)",
            min_value=-12,
            max_value=14,
            value=int(cfg.get("tz_offset_default", -3)),
            step=1,
        )
        if st.button("Salvar configurações"):
            if not dono_ok:
                st.error("Operação bloqueada para não-donos.")
                logger.warning(
                    f"Usuário {user.get('id') if user else 'anônimo'} tentou salvar configurações sem permissão",
                    rifa=nome_rifa
                )
                st.stop()
            try:
                updates = {
                    "reserva_ttl_minutos": ttl,
                    "logo_path": logo_path.strip() if logo_path else "",
                    "qr_text": qr_text.strip() if qr_text else "",
                    "obs_padrao_pdf": obs_pdf.strip() if obs_pdf else "",
                    "tz_offset_default": tz_offset,
                }
                ok, msg = dm.atualizar_config_rifa(nome_rifa, updates)
                if ok:
                    st.success(msg)
                    logger.success(f"Configurações atualizadas para rifa {nome_rifa}", updates=updates)
                    st.rerun()
                else:
                    st.error(msg)
                    logger.warning(f"Falha ao atualizar configurações para rifa {nome_rifa}", message=msg)
            except Exception as e:
                logger.error(f"Erro ao salvar configurações para rifa {nome_rifa}", exception=e)
                st.error(f"Erro ao salvar configurações: {str(e)}")

        st.markdown("---")
        st.subheader("Deletar Rifa")
        st.error("⚠️ Esta ação é irreversível!")
        confirm_delete = st.text_input(
            "Digite o nome da rifa para confirmar a deleção",
            placeholder=f"Digite '{nome_rifa}'"
        )
        if st.button("Deletar Rifa Permanentemente", type="primary"):
            if not dono_ok:
                st.error("Operação bloqueada para não-donos.")
                logger.warning(
                    f"Usuário {user.get('id') if user else 'anônimo'} tentou deletar rifa sem permissão",
                    rifa=nome_rifa
                )
                st.stop()
            if confirm_delete != nome_rifa:
                st.error("Nome da rifa não corresponde.")
                logger.warning(
                    f"Tentativa de deletar rifa {nome_rifa} com confirmação incorreta",
                    confirm_input=confirm_delete
                )
            else:
                try:
                    ok, msg = dm.deletar_rifa(nome_rifa)
                    if ok:
                        st.success(msg)
                        logger.success(f"Rifa {nome_rifa} deletada com sucesso")
                        st.session_state.pop("rifa_selecionada", None)
                        st.rerun()
                    else:
                        st.error(msg)
                        logger.warning(f"Falha ao deletar rifa {nome_rifa}", message=msg)
                except Exception as e:
                    logger.error(f"Erro ao deletar rifa {nome_rifa}", exception=e)
                    st.error(f"Erro ao deletar rifa: {str(e)}")

    with tabs[5]:
        st.header("👤 Minha Conta")
        if not user:
            st.warning("Você precisa estar logado para acessar esta seção.")
            logger.info("Acesso à aba 'Minha Conta' bloqueado: usuário não logado")
            st.stop()

        st.subheader("Atualizar Nome")
        new_name = st.text_input("Novo nome", value=user["name"])
        if st.button("Atualizar Nome"):
            try:
                ok, msg = dm.update_user_name(user["id"], new_name)
                if ok:
                    st.session_state["user"]["name"] = new_name
                    st.success(msg)
                    logger.success(f"Nome do usuário {user['id']} atualizado para {new_name}")
                    st.rerun()
                else:
                    st.error(msg)
                    logger.warning(f"Falha ao atualizar nome do usuário {user['id']}", message=msg)
            except Exception as e:
                logger.error(f"Erro ao atualizar nome do usuário {user['id']}", exception=e)
                st.error(f"Erro ao atualizar nome: {str(e)}")

        st.markdown("---")
        st.subheader("Atualizar Senha")
        old_password = st.text_input("Senha atual", type="password")
        new_password = st.text_input("Nova senha", type="password")
        if st.button("Atualizar Senha"):
            try:
                ok, msg = dm.update_user_password(user["id"], old_password, new_password)
                if ok:
                    st.success(msg)
                    logger.success(f"Senha do usuário {user['id']} atualizada com sucesso")
                else:
                    st.error(msg)
                    logger.warning(f"Falha ao atualizar senha do usuário {user['id']}", message=msg)
            except Exception as e:
                logger.error(f"Erro ao atualizar senha do usuário {user['id']}", exception=e)
                st.error(f"Erro ao atualizar senha: {str(e)}")

        st.markdown("---")
        st.subheader("Minhas Rifas")
        user_rifas = dm.listar_rifas_do_usuario(user["id"])
        if user_rifas:
            st.write("Rifas que você gerencia:")
            for rifa in user_rifas:
                st.write(f"- {rifa}")
            logger.debug(f"Rifas do usuário {user['id']} listadas", count=len(user_rifas))
        else:
            st.info("Você não gerencia nenhuma rifa.")
            logger.debug(f"Nenhuma rifa encontrada para o usuário {user['id']}")

        st.markdown("---")
        st.subheader("Reivindicar Rifa")
        rifas_sem_dono = dm.listar_rifas_sem_dono()
        if rifas_sem_dono:
            rifa_reivindicar = st.selectbox("Selecione uma rifa sem dono", options=rifas_sem_dono)
            if st.button("Reivindicar Rifa"):
                try:
                    ok, msg = dm.claim_rifa(rifa_reivindicar, user["id"])
                    if ok:
                        st.success(msg)
                        logger.success(f"Rifa {rifa_reivindicar} reivindicada pelo usuário {user['id']}")
                        st.rerun()
                    else:
                        st.error(msg)
                        logger.warning(
                            f"Falha ao reivindicar rifa {rifa_reivindicar} para usuário {user['id']}",
                            message=msg
                        )
                except Exception as e:
                    logger.error(
                        f"Erro ao reivindicar rifa {rifa_reivindicar} para usuário {user['id']}",
                        exception=e
                    )
                    st.error(f"Erro ao reivindicar rifa: {str(e)}")
        else:
            st.info("Não há rifas disponíveis para reivindicação.")
            logger.debug("Nenhuma rifa sem dono disponível para reivindicação")

        st.markdown("---")
        st.subheader("Exportar Backup (JSON)")
        if st.button("Gerar Backup"):
            try:
                backup_bytes = dm.export_backup_json_zip()
                st.download_button(
                    "Baixar Backup (ZIP)",
                    data=backup_bytes,
                    file_name=f"backup_rifas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip",
                )
                logger.success(f"Backup JSON ZIP gerado para usuário {user['id']}")
            except Exception as e:
                logger.error(f"Falha ao gerar backup JSON para usuário {user['id']}", exception=e)
                st.error(f"Erro ao gerar backup: {str(e)}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error("Erro crítico na aplicação", exception=e)
        st.error("Ocorreu um erro crítico. Verifique os logs para detalhes.")