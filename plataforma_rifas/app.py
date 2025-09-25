from __future__ import annotations

import os
import streamlit as st
import pandas as pd
import uuid
from pathlib import Path
import random
from fpdf import FPDF
import qrcode

from modules import db_data_manager as dm
from modules import ui_components as ui
from logger import logger
from babel.numbers import format_currency
 
APP_TITLE = "🎟️ Plataforma de Rifas PRO"

def main():
    """Função principal da aplicação."""
    st.set_page_config(page_title=APP_TITLE, layout="wide", initial_sidebar_state="expanded")

    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())[:8]
    logger.info(f"Aplicação iniciada | session_id={st.session_state['session_id']}")

    # Migração automática de JSON para SQLite (one-shot)
    try:
        dm.migrate_from_json()
    except Exception:
        logger.warning("Falha ao migrar dados JSON→SQLite (ignorado).")

    # Autenticação (Login/Cadastro)
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
                        st.success("Bem-vindo(a), " + u["name"] + "!")
                        st.rerun()
                    else:
                        st.error(msg)
            with tab_signup:
                name_s = st.text_input("Nome", key="signup_name")
                email_s = st.text_input("E-mail", key="signup_email")
                password_s = st.text_input("Senha", type="password", key="signup_password")
                if st.button("Criar conta", use_container_width=True):
                    ok, msg, uid = dm.create_user(name_s, email_s, password_s)
                    if ok:
                        st.success("Conta criada! Faça login.")
                    else:
                        st.error(msg)
        else:
            st.success(f"Logado como: {user['name']} ({user['email']})")
            if st.button("Sair", use_container_width=True):
                st.session_state.pop("user")
                st.rerun()

    # Sidebar de rifas, sensível ao usuário
    user = st.session_state.get("user")
    nome_rifa = ui.renderizar_sidebar(user=user)

    if not nome_rifa:
        st.info("⬅️ Selecione ou crie uma rifa na barra lateral para começar.")
        st.stop()

    # Carrega dados essenciais uma vez
    cfg = dm.get_config_rifa(nome_rifa) or {}
    dados = dm.carregar_dados_rifa(nome_rifa)

    tab_titles = ["📊 Dashboard", "🔍 Consultar/Exportar", "📈 Analytics", "🏆 Sorteio", "⚙️ Gerenciamento", "👤 Minha Conta"]
    tabs = st.tabs(tab_titles)

    # Tab 1: Dashboard e Vendas
    with tabs[0]:
        try:
            ui.renderizar_dashboard(nome_rifa, dados, cfg)
            st.markdown("---")
            ui.renderizar_grid_vendas(nome_rifa, dados, cfg)

            # Últimas ações (histórico com filtro de período)
            st.markdown("---")
            st.subheader("🕒 Últimas ações")
            colf1, colf2, colf3 = st.columns([1,1,1])
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
                st.dataframe(df_hist.head(50), width='stretch')
            else:
                st.info("Sem ações no período.")
        except Exception as e:
            logger.exception(f"Erro ao renderizar dashboard para '{nome_rifa}': {e}")
            st.error("Erro ao carregar dashboard. Verifique os logs.")

    # Tab 2: Consultar e Exportar
    with tabs[1]:
        st.header("🔍 Consultar e Exportar Dados")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Consulta por número")
            num = st.number_input("Número", min_value=1, max_value=int(cfg.get("total_numeros", 1)), step=1)
            if st.button("Consultar número"):
                comprador = dados.get(str(int(num)))
                if comprador: st.success(f"Número {int(num)} vendido para: {comprador}")
                else: st.info(f"Número {int(num)} está disponível.")
        with col2:
            st.subheader("Consulta por nome")
            nome = st.text_input("Nome do comprador")
            if st.button("Consultar compras"):
                resultados = sorted([int(n) for n, c in dados.items() if nome.strip().lower() in c.lower()])
                if resultados: st.success(f"{nome} comprou: {resultados}")
                else: st.info(f"Nenhuma compra encontrada para '{nome}'.")

        st.markdown("---")
        st.subheader("Exportar CSV de Vendas")
        colp1, colp2, colp3 = st.columns([1,1,1])
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

        vendas = dm.get_sales_in_period(nome_rifa, start2, end2) if preset2 != "Tudo" else dm.get_all_sales(nome_rifa)
        # Filtro adicional por comprador (opcional)
        compradores_lista = sorted(list({v['comprador'] for v in vendas})) if vendas else []
        comprador_sel_csv = st.selectbox("Filtrar por comprador (opcional)", options=["(Todos)"] + compradores_lista, index=0)
        if vendas and comprador_sel_csv != "(Todos)":
            vendas = [v for v in vendas if v['comprador'] == comprador_sel_csv]
        # Ajuste de fuso nas exportações
        aplicar_tz = st.checkbox("Aplicar fuso horário local nas exportações", value=False)
        tz_default = int(cfg.get('tz_offset_default', 0))
        if aplicar_tz and vendas:
            for v in vendas:
                try:
                    ts_local = pd.to_datetime(v['timestamp']).tz_localize('UTC').tz_convert(None) + pd.Timedelta(hours=int(tz_default))
                    v['timestamp'] = ts_local.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    pass
        if vendas:
            df = pd.DataFrame(vendas)
            df.rename(columns={"numero": "Número", "comprador": "Comprador", "contato": "Contato", "timestamp": "Data/Hora"}, inplace=True)
            df['Número'] = pd.to_numeric(df['Número'])
            df = df.sort_values("Número").reset_index(drop=True)
            st.download_button("Baixar CSV Completo", df.to_csv(index=False).encode('utf-8'), f"{nome_rifa}_vendas.csv", "text/csv")
            # Excel (XLSX)
            from io import BytesIO
            xbio = BytesIO()
            with pd.ExcelWriter(xbio, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Vendas')
            st.download_button("Baixar Excel (XLSX)", data=xbio.getvalue(), file_name=f"{nome_rifa}_vendas.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("Não há vendas para exportar.")
        
        st.markdown("---")
        st.subheader("Relatório por Comprador")
        if vendas:
            dfr = pd.DataFrame(vendas)
            dfr.rename(columns={"numero": "Número", "comprador": "Comprador"}, inplace=True)
            dfr['Número'] = pd.to_numeric(dfr['Número'])
            rep = dfr.groupby("Comprador").agg(qtd=("Número", "count")).reset_index().sort_values("qtd", ascending=False)
            valor_unit = float(cfg.get("valor_numero", 0.0))
            rep["valor_total"] = rep["qtd"] * valor_unit
            # Paginação do relatório
            per_rep = st.selectbox("Itens por página", options=[10, 25, 50, 100], index=1)
            total_rep_pages = max(1, (len(rep) + per_rep - 1) // per_rep)
            rep_state_key = f"rep_page_{nome_rifa}"
            if rep_state_key not in st.session_state:
                st.session_state[rep_state_key] = 1
            cols_rep_nav = st.columns([1,1,2,1,1])
            with cols_rep_nav[0]:
                if st.button("◀️", disabled=(st.session_state[rep_state_key] <= 1)):
                    st.session_state[rep_state_key] = max(1, st.session_state[rep_state_key]-1)
            with cols_rep_nav[2]:
                st.session_state[rep_state_key] = st.number_input("Página do relatório", min_value=1, max_value=total_rep_pages, value=int(st.session_state[rep_state_key]), step=1)
            with cols_rep_nav[4]:
                if st.button("▶️", disabled=(st.session_state[rep_state_key] >= total_rep_pages)):
                    st.session_state[rep_state_key] = min(total_rep_pages, st.session_state[rep_state_key]+1)
            cur_page = int(st.session_state[rep_state_key])
            ini = (cur_page-1) * per_rep
            fim = min(len(rep), ini + per_rep)
            st.dataframe(rep.iloc[ini:fim].reset_index(drop=True), width='stretch')
            # Botão para gerar PDF apenas desta página do relatório
            compradores_pagina = set(rep.iloc[ini:fim]['Comprador'].tolist())
            if st.button("Gerar PDF desta página"):
                vendas_pagina = [v for v in (vendas or []) if v['comprador'] in compradores_pagina]
                pdf_bytes = _build_pdf_bytes(vendas_pagina or vendas, cfg)
                st.download_button("Baixar PDF (Página)", data=pdf_bytes, file_name=f"{nome_rifa}_comprovantes_pagina.pdf", mime="application/pdf")
        else:
            st.info("Sem dados para relatório por comprador.")

        st.markdown("---")
        st.subheader("Exportar PDF (Comprovantes)")
        # Seleção granular (números/comprador) e fuso horário
        colsel1, colsel2, colsel3 = st.columns([1,1,1])
        with colsel1:
            numeros_pdf_txt = st.text_input("Números (ex: 1-10, 25)")
        with colsel2:
            compradores_opts = ["(Todos)"] + (sorted(list({v['comprador'] for v in vendas})) if vendas else [])
            comprador_pdf = st.selectbox("Comprador", options=compradores_opts)
        with colsel3:
            tz_default = int(cfg.get('tz_offset_default', 0))
            tz_offset = st.number_input("Fuso horário (offset horas)", value=tz_default, step=1, min_value=-12, max_value=14)
        def _safe_fname(text: str) -> str:
            for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
                text = text.replace(ch, '-')
            return text.strip().replace(' ', '_')

        def _build_pdf_bytes(vendas_list, cfg_local, consolidate_buyer: str = None):
            logo_path = (cfg_local or {}).get("logo_path")
            qr_text = (cfg_local or {}).get("qr_text")
            obs = (cfg_local or {}).get("obs_padrao_pdf", "")
            valor_unit = float((cfg_local or {}).get("valor_numero", 0.0))
            pdf = FPDF(orientation='P', unit='mm', format='A4')
            pdf.set_auto_page_break(auto=True, margin=12)
            if consolidate_buyer:
                # Consolidar todos os números deste comprador em uma única página
                nums = sorted([int(v['numero']) for v in vendas_list if v['comprador'] == consolidate_buyer])
                contato_buyer = next((v.get('contato') for v in vendas_list if v['comprador'] == consolidate_buyer and v.get('contato')), "")
                total_qtd = len(nums)
                total_valor = total_qtd * valor_unit
                gerado_em = (pd.Timestamp.utcnow() + pd.Timedelta(hours=int(tz_offset))).strftime('%Y-%m-%d %H:%M:%S')

                pdf.add_page()
                pdf.set_font("Arial", "B", 16)
                if logo_path and os.path.exists(logo_path):
                    try:
                        pdf.image(logo_path, x=12, y=10, w=28)
                    except Exception:
                        pass
                pdf.cell(0, 12, f"Comprovante de Compra - {nome_rifa}", ln=1, align='C')
                pdf.set_font("Arial", size=12)
                pdf.ln(4)
                pdf.cell(0, 8, f"Comprador: {consolidate_buyer}", ln=1)
                if contato_buyer:
                    pdf.cell(0, 8, f"Contato: {contato_buyer}", ln=1)
                pdf.cell(0, 8, f"Quantidade de números: {total_qtd}", ln=1)
                try:
                    pdf.cell(0, 8, f"Valor por número: R$ {valor_unit:,.2f}", ln=1)
                    pdf.cell(0, 8, f"Valor total: R$ {total_valor:,.2f}", ln=1)
                except Exception:
                    pdf.cell(0, 8, f"Valor por número: {valor_unit}", ln=1)
                    pdf.cell(0, 8, f"Valor total: {total_valor}", ln=1)
                pdf.ln(2)
                # Lista de números em colunas (quebra automática)
                pdf.set_font("Arial", size=11)
                nums_str = ", ".join(map(str, nums))
                pdf.multi_cell(0, 7, f"Números: {nums_str}")
                pdf.ln(2)
                pdf.cell(0, 8, f"Gerado em (local): {gerado_em}", ln=1)
                pdf.ln(4)
                if obs:
                    pdf.multi_cell(0, 7, obs)
                if qr_text:
                    try:
                        qr_img = qrcode.make(qr_text)
                        tmp_path = Path(".tmp_qr.png")
                        qr_img.save(tmp_path)
                        pdf.image(str(tmp_path), x=170, y=10, w=28)
                        try:
                            tmp_path.unlink(missing_ok=True)
                        except Exception:
                            pass
                    except Exception:
                        pass
            else:
                for v in vendas_list:
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 16)
                    if logo_path and os.path.exists(logo_path):
                        try:
                            pdf.image(logo_path, x=12, y=10, w=28)
                        except Exception:
                            pass
                    pdf.cell(0, 12, f"Comprovante de Compra - {nome_rifa}", ln=1, align='C')
                    pdf.set_font("Arial", size=12)
                    pdf.ln(4)
                    pdf.cell(0, 8, f"Número: {v['numero']}", ln=1)
                    pdf.cell(0, 8, f"Comprador: {v['comprador']}", ln=1)
                    if v.get('contato'):
                        pdf.cell(0, 8, f"Contato: {v['contato']}", ln=1)
                    try:
                        ts_local = pd.to_datetime(v['timestamp']).tz_localize('UTC').tz_convert(None) + pd.Timedelta(hours=int(tz_offset))
                        ts_str = ts_local.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        ts_str = str(v['timestamp'])
                    pdf.cell(0, 8, f"Data/Hora: {ts_str}", ln=1)
                    pdf.ln(4)
                    if obs:
                        pdf.multi_cell(0, 7, obs)
                    if qr_text:
                        try:
                            qr_img = qrcode.make(qr_text)
                            tmp_path = Path(".tmp_qr.png")
                            qr_img.save(tmp_path)
                            pdf.image(str(tmp_path), x=170, y=10, w=28)
                            try:
                                tmp_path.unlink(missing_ok=True)
                            except Exception:
                                pass
                        except Exception:
                            pass
            data_out = pdf.output(dest='S')
            # fpdf2 pode retornar bytes/bytearray/str dependendo da versão/config
            if isinstance(data_out, (bytes, bytearray)):
                return bytes(data_out)
            else:
                return data_out.encode('latin-1')

        if vendas:
            # Aplica filtros de seleção
            vendas_sel = vendas
            if numeros_pdf_txt:
                nums = ui._parse_ranges(numeros_pdf_txt)
                vendas_sel = [v for v in vendas_sel if int(v['numero']) in set(nums)]
            if comprador_pdf and comprador_pdf != "(Todos)":
                vendas_sel = [v for v in vendas_sel if v['comprador'] == comprador_pdf]
            if st.button("Gerar PDF de comprovantes"):
                # Se um único comprador foi selecionado, gerar recibo consolidado com nome no arquivo
                if comprador_pdf and comprador_pdf != "(Todos)":
                    pdf_bytes = _build_pdf_bytes(vendas_sel or vendas, cfg, consolidate_buyer=comprador_pdf)
                    fname = f"{_safe_fname(nome_rifa)}_{_safe_fname(comprador_pdf)}_comprovante.pdf"
                else:
                    pdf_bytes = _build_pdf_bytes(vendas_sel or vendas, cfg)
                    fname = f"{_safe_fname(nome_rifa)}_comprovantes.pdf"
                st.download_button("Baixar PDF", data=pdf_bytes, file_name=fname, mime="application/pdf")
        
    # Tab 3: Analytics
    with tabs[2]:
        try:
            ui.renderizar_analytics_tab(nome_rifa)
        except Exception as e:
            logger.exception(f"Erro ao renderizar analytics: {e}")
            st.error("Erro ao carregar análises. Verifique os logs.")

    # Tab 4: Sorteio
    with tabs[3]:
        st.header("🏆 Sorteio")
        if cfg.get("sorteio_realizado"):
            st.success(f"🎉 Sorteio já realizado! 🎉")
            st.balloons()
            ui._render_metric("Número Vencedor", cfg.get('sorteio_numero'))
            ui._render_metric("Comprador Sortudo", cfg.get('sorteio_comprador'))
        else:
            st.warning("Atenção: o sorteio pode ser realizado apenas uma vez.")
            if st.button("🍀 Realizar Sorteio Agora!", type="primary"):
                ok, numero, comprador, msg = dm.escolher_vencedor(nome_rifa)
                if ok:
                    st.rerun()
                else:
                    st.error(msg)

            st.markdown("---")
            st.subheader("Simular Sorteio (não persiste)")
            if st.button("🎲 Simular sorteio"):
                vendidos = list(map(int, dados.keys()))
                if not vendidos:
                    st.info("Nenhum número vendido para simular.")
                else:
                    sorteado = random.choice(vendidos)
                    st.info(f"Número sorteado (simulação): {sorteado} | Comprador: {dados.get(str(sorteado))}")
    
    # Tab 5: Gerenciamento
    with tabs[4]:
        st.header("⚙️ Gerenciamento da Rifa")
        # Checagem de permissão de dono
        dono_ok = True
        if user and cfg.get('owner_id') is not None:
            dono_ok = int(user['id']) == int(cfg.get('owner_id'))
        if not dono_ok:
            st.warning("Você não é o dono desta rifa. Operações administrativas estão bloqueadas.")

        st.subheader("Operações de Venda")
        with st.expander("Cancelar venda de números"):
            numeros_cancelar = st.text_input("Números para cancelar (ex: 5, 12-15)")
            if st.button("Confirmar Cancelamento de Venda"):
                if not dono_ok:
                    st.error("Operação bloqueada para não-donos.")
                    st.stop()
                nums = ui._parse_ranges(numeros_cancelar)
                ok, detalhes, msg = dm.cancelar_venda(nome_rifa, nums)
                if ok: st.success(msg); st.rerun()
                else: st.error(msg)

        with st.expander("Transferir números para outro comprador"):
            numeros_transferir = st.text_input("Números para transferir (ex: 2, 40-45)")
            novo_comprador = st.text_input("Nome do novo comprador")
            if st.button("Confirmar Transferência"):
                if not dono_ok:
                    st.error("Operação bloqueada para não-donos.")
                    st.stop()
                nums = ui._parse_ranges(numeros_transferir)
                ok, detalhes, msg = dm.transferir_venda(nome_rifa, nums, novo_comprador)
                if ok: st.success(msg); st.rerun()
                else: st.error(msg)
        
        st.markdown("---")
        st.subheader("Configurações")
        ttl = st.number_input("Tempo de expiração de reservas (minutos, 0 para desativar)", min_value=0, value=cfg.get("ttl_reserva_minutos", 15))
        if ttl != cfg.get("ttl_reserva_minutos", 15):
            dm.atualizar_config_rifa(nome_rifa, {"ttl_reserva_minutos": ttl})
            st.toast("Tempo de expiração atualizado!")

        cols = st.number_input("Densidade da Grade (colunas)", min_value=4, max_value=20, value=cfg.get("grid_columns", 12))
        if cols != cfg.get("grid_columns", 12):
            dm.atualizar_config_rifa(nome_rifa, {"grid_columns": cols})
            st.toast("Densidade da grade atualizada!")

        tz_conf = st.number_input("Fuso horário padrão (horas)", min_value=-12, max_value=14, value=int(cfg.get('tz_offset_default', 0)))
        if tz_conf != int(cfg.get('tz_offset_default', 0)):
            dm.atualizar_config_rifa(nome_rifa, {"tz_offset_default": int(tz_conf)})
            st.toast("Fuso horário padrão atualizado!")

        st.markdown("---")
        st.subheader("Aparência e Comprovante")
        with st.expander("Logo e preferências do PDF"):
            colu1, colu2 = st.columns([2,2])
            with colu1:
                arquivo_logo = st.file_uploader("Upload de logo (PNG/JPG)", type=["png","jpg","jpeg"])
                if arquivo_logo is not None:
                    try:
                        assets_dir = Path(__file__).resolve().parent / "modules" / "assets"
                        assets_dir.mkdir(parents=True, exist_ok=True)
                        safe_name = arquivo_logo.name.replace('/', '_').replace('\\', '_')
                        destino = assets_dir / safe_name
                        destino.write_bytes(arquivo_logo.getvalue())
                        if not dono_ok:
                            st.error("Operação bloqueada para não-donos.")
                        else:
                            ok, msg = dm.atualizar_config_rifa(nome_rifa, {"logo_path": str(destino)})
                        if ok:
                            st.success("Logo atualizada.")
                            st.rerun()
                        else:
                            st.error(msg)
                    except Exception as e:
                        st.error(f"Falha ao salvar logo: {e}")
            with colu2:
                logo_atual = (cfg or {}).get("logo_path")
                if logo_atual:
                    try:
                        st.image(logo_atual, caption="Logo atual", width=120)
                    except Exception:
                        st.info("Logo configurada, mas não foi possível exibir.")

            qr_text_cfg = st.text_input("Texto/URL do QR padrão (opcional)", value=(cfg or {}).get("qr_text", ""))
            obs_padrao_cfg = st.text_area("Observação padrão do PDF (opcional)", value=(cfg or {}).get("obs_padrao_pdf", ""))
            if st.button("Salvar preferências do PDF"):
                if not dono_ok:
                    st.error("Operação bloqueada para não-donos.")
                else:
                    ok, msg = dm.atualizar_config_rifa(nome_rifa, {"qr_text": qr_text_cfg, "obs_padrao_pdf": obs_padrao_cfg})
                if ok:
                    st.success("Preferências salvas.")
                    st.rerun()
                else:
                    st.error(msg)

        st.markdown("---")
        st.subheader("Zona de Perigo")
        if st.button("Deletar Rifa Atual", type="primary"):
            st.session_state['confirm_delete_inline'] = True
        if st.session_state.get('confirm_delete_inline'):
            st.warning(f"Você tem certeza que deseja deletar a rifa "
                       f"{nome_rifa}? Esta ação é irreversível.")
            colc1, colc2 = st.columns(2)
            with colc1:
                if st.button("Sim, deletar DEFINITIVAMENTE"):
                    if not dono_ok:
                        st.error("Operação bloqueada para não-donos.")
                    else:
                        ok, msg = dm.deletar_rifa(nome_rifa)
                    st.session_state.pop('confirm_delete_inline')
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
            with colc2:
                if st.button("Cancelar exclusão"):
                    st.session_state.pop('confirm_delete_inline')

        st.markdown("---")
        st.subheader("Backup JSON (compatibilidade)")
        st.caption("Gera um ZIP com index.json e arquivos JSON de rifas.")
        if st.button("Exportar backup JSON"):
            data = dm.export_backup_json_zip()
            st.download_button("Baixar backup JSON", data=data, file_name=f"{nome_rifa}_backup_json.zip")

        with st.expander("Espelhamento JSON (avançado)"):
            st.caption("Ative apenas se precisar compatibilizar com ferramentas legadas. Em produção, mantenha desativado para evitar divergência de dados.")
            # Estado atual não é exposto pela lib; GUI oferece um toggle idempotente
            json_toggle = st.checkbox("Ativar JSON_MIRROR (espelhamento JSON)", value=False, help="Controla escrita simultânea em data/*.json.")
            if st.button("Aplicar estado do espelhamento"):
                try:
                    dm.set_json_mirror(bool(json_toggle))
                    st.success(f"Espelhamento JSON {'ativado' if json_toggle else 'desativado'} nesta sessão do servidor.")
                except Exception as e:
                    st.error(f"Falha ao ajustar espelhamento: {e}")

    # Tab 6: Minha Conta
    with tabs[5]:
        st.header(" Minha Conta")
        user = st.session_state.get("user")
        if not user:
            st.info("Faça login para gerenciar sua conta.")
        else:
            st.subheader("Atualizar nome")
            novo_nome = st.text_input("Novo nome", value=user.get("name", ""))
            if st.button("Salvar nome"):
                ok, msg = dm.update_user_name(int(user['id']), novo_nome)
                if ok:
                    st.success(msg)
                    st.session_state['user']['name'] = novo_nome
                else:
                    st.error(msg)
            st.markdown("---")
            st.subheader("Trocar senha")
            colps1, colps2 = st.columns(2)
            with colps1:
                senha_atual = st.text_input("Senha atual", type="password")
            with colps2:
                nova_senha = st.text_input("Nova senha", type="password")
            if st.button("Atualizar senha"):
                ok, msg = dm.update_user_password(int(user['id']), senha_atual, nova_senha)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

if __name__ == "__main__":
    main()