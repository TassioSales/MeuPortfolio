from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import streamlit as st
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import altair as alt
from fpdf import FPDF
import qrcode
from . import db_data_manager as dm
from logger import logger
from babel.numbers import format_currency

def inject_global_styles():
    st.markdown("""
        <style>
            :root {
                --bg-color: #111827;
                --card-bg-color: #1F2937;
                --border-color: #374151;
                --primary-color: #3B82F6;
                --accent-color: #F59E0B;
                --text-color: #F9FAFB;
                --text-muted-color: #9CA3AF;
            }
            .metric-card {
                background: var(--card-bg-color);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                padding: 16px;
                text-align: center;
                height: 100%;
            }
            .metric-value {
                font-size: 2em;
                font-weight: 800;
                color: var(--primary-color);
            }
            .metric-label {
                font-size: 0.9em;
                color: var(--text-muted-color);
                text-transform: uppercase;
            }
            .stButton>button {
                border-radius: 8px; font-weight: 600;
            }
            .num-box { 
                display: inline-flex; align-items: center; justify-content: center; 
                width: 100%; height: 44px; margin-bottom: 8px; border-radius: 8px; 
                font-weight: 600; font-size: 0.9em; user-select: none;
                border: 1px solid var(--border-color); text-decoration: none;
            }
            .num-box.free { background: #374151; color: var(--text-color); }
            .num-box.sold { background: #991B1B; color: #FECACA; }
            .num-box.reserved { background: var(--accent-color); color: #111827; }
        </style>
    """, unsafe_allow_html=True)

def _render_metric(label: str, value: Any):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def renderizar_sidebar(user: Optional[Dict] = None) -> Optional[str]:
    st.sidebar.header("Plataforma de Rifas PRO")

    # Lista rifas por usuário (se logado), ou todas se None
    rifas = dm.listar_rifas_do_usuario(user['id']) if user and 'id' in user else dm.listar_rifas()
    selected = st.sidebar.selectbox("Selecione uma rifa", options=["(Nenhuma)"] + rifas)
    selected = None if selected == "(Nenhuma)" else selected
    
    with st.sidebar.expander("Criar nova rifa"):
        with st.form("form_criar_rifa", clear_on_submit=True):
            nome = st.text_input("Nome da rifa")
            col1, col2 = st.columns(2)
            with col1:
                valor = st.number_input("Valor por número (R$)", min_value=0.0, step=0.5, value=10.0)
            with col2:
                total = st.number_input("Total de números", min_value=1, step=1, value=100)
            submitted = st.form_submit_button("Criar rifa", use_container_width=True)
        if submitted:
            if user and 'id' in user:
                ok, msg = dm.salvar_nova_rifa_com_owner(nome, valor, int(total), owner_id=int(user['id']))
            else:
                ok, msg = dm.salvar_nova_rifa(nome, valor, int(total))
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    # Assumir rifas sem dono (claim)
    if user and 'id' in user:
        with st.sidebar.expander("Assumir rifas sem dono"):
            sem_dono = dm.listar_rifas_sem_dono()
            if not sem_dono:
                st.caption("Nenhuma rifa sem dono disponível.")
            else:
                escolha = st.selectbox("Selecione a rifa para assumir", options=sem_dono, key="claim_select")
                if st.button("Assumir rifa selecionada", use_container_width=True):
                    ok, msg = dm.claim_rifa(escolha, int(user['id']))
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
    return selected

def renderizar_dashboard(nome_rifa: str, dados: Dict[str, str], cfg: Dict):
    inject_global_styles()
    total = int(cfg.get("total_numeros", 0))
    vendidos = len(dados)
    valor = float(cfg.get("valor_numero", 0.0))
    arrecadado = vendidos * valor
    perc = (vendidos / total * 100.0) if total > 0 else 0.0
    
    try:
        arrec_brl = format_currency(arrecadado, "BRL", locale="pt_BR")
    except Exception:
        arrec_brl = f"R$ {arrecadado:,.2f}"

    st.subheader(f"Dashboard: {nome_rifa}")
    cols = st.columns(4)
    with cols[0]:
        _render_metric("Vendidos / Total", f"{vendidos} / {total}")
    with cols[1]:
        _render_metric("Progresso", f"{perc:.1f}%")
    with cols[2]:
        _render_metric("Arrecadado", arrec_brl)
    with cols[3]:
        _render_metric("Disponíveis", total - vendidos)

    st.progress(perc / 100)

def _parse_ranges(texto: str) -> List[int]:
    resultado: Set[int] = set()
    if not texto: return []
    partes = [p.strip() for p in texto.replace(';', ',').split(',') if p.strip()]
    for p in partes:
        if '-' in p:
            try:
                a, b = map(int, p.split('-', 1))
                resultado.update(range(min(a, b), max(a, b) + 1))
            except ValueError: continue
        else:
            try: resultado.add(int(p))
            except ValueError: continue
    return sorted(list(resultado))


def renderizar_analytics_tab(nome_rifa: str) -> None:
    st.header(f"📈 Análise de Performance: {nome_rifa}")
    cfg = dm.get_config_rifa(nome_rifa) or {}
    dados = dm.carregar_dados_rifa(nome_rifa)

    # Filtro de período
    colp1, colp2, colp3 = st.columns([1,1,1])
    with colp1:
        preset = st.selectbox("Período", ["Últimas 24h", "7 dias", "30 dias", "Tudo", "Personalizado"], index=2, key="an_preset")
    start_iso = end_iso = None
    if preset == "Últimas 24h":
        start_iso = (pd.Timestamp.utcnow() - pd.Timedelta(days=1)).isoformat()
    elif preset == "7 dias":
        start_iso = (pd.Timestamp.utcnow() - pd.Timedelta(days=7)).isoformat()
    elif preset == "30 dias":
        start_iso = (pd.Timestamp.utcnow() - pd.Timedelta(days=30)).isoformat()
    elif preset == "Personalizado":
        with colp2:
            d_ini = st.date_input("Início", value=pd.Timestamp.utcnow().date() - pd.Timedelta(days=7), key="an_inicio")
        with colp3:
            d_fim = st.date_input("Fim", value=pd.Timestamp.utcnow().date(), key="an_fim")
        start_iso = pd.Timestamp(d_ini).isoformat()
        end_iso = (pd.Timestamp(d_fim) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)).isoformat()

    # KPIs
    total_vendidos = len(dados)
    valor_unit = float(cfg.get("valor_numero", 0))
    arrecadado = total_vendidos * valor_unit
    try:
        arrec_brl = format_currency(arrecadado, "BRL", locale="pt_BR")
    except Exception:
        arrec_brl = f"R$ {arrecadado:,.2f}"

    compradores_unicos = len(set(dados.values()))
    total_numeros = int(cfg.get("total_numeros", 0)) or 0
    sell_through = f"{(total_vendidos/total_numeros*100):.1f}%" if total_numeros > 0 else "0%"
    ticket_medio = (arrecadado/compradores_unicos) if compradores_unicos > 0 else 0.0
    try:
        ticket_brl = format_currency(ticket_medio, "BRL", locale="pt_BR")
    except Exception:
        ticket_brl = f"R$ {ticket_medio:,.2f}"

    meta_valor = float(cfg.get("meta_arrecadacao", 0.0))
    progresso = (arrecadado / meta_valor) if meta_valor > 0 else 0.0
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Vendidos", total_vendidos)
    with c2:
        st.metric("Arrecadado", arrec_brl)
    with c3:
        st.metric("Compradores Únicos", compradores_unicos)
    with c4:
        st.metric("Sell-through", sell_through)

    if meta_valor > 0:
        try:
            meta_brl = format_currency(meta_valor, "BRL", locale="pt_BR")
        except Exception:
            meta_brl = f"R$ {meta_valor:,.2f}"
        st.caption(f"Meta de arrecadação: {meta_brl}")
        st.progress(min(max(progresso, 0.0), 1.0), text=f"{progresso*100:.1f}% da meta")

    st.markdown("---")
    st.subheader("Receita por dia")
    try:
        rev_series = dm.get_revenue_by_day(nome_rifa, start_iso, end_iso)
    except Exception:
        rev_series = []
    if rev_series:
        dfr = pd.DataFrame(rev_series)
        if not dfr.empty:
            dfr["dia"] = pd.to_datetime(dfr["dia"]) 
            dfr = dfr.set_index("dia").sort_index()
            st.area_chart(dfr[["receita"]], width='stretch')
    else:
        st.info("Sem dados para receita por dia no período.")

    st.subheader("Receita acumulada")
    try:
        cum_series = dm.get_cumulative_revenue(nome_rifa, start_iso, end_iso)
    except Exception:
        cum_series = []
    if cum_series:
        dfc = pd.DataFrame(cum_series)
        if not dfc.empty:
            dfc["dia"] = pd.to_datetime(dfc["dia"]) 
            dfc = dfc.set_index("dia").sort_index()
            st.line_chart(dfc[["acumulado"]], width='stretch')
    else:
        st.info("Sem dados para receita acumulada no período.")

    st.subheader("Vendas por dia da semana (últimos 30 dias)")
    try:
        by_wd = dm.get_sales_by_weekday(nome_rifa, days=30)
    except Exception:
        by_wd = []
    if by_wd:
        dwd = pd.DataFrame(by_wd)
        if not dwd.empty:
            nomes = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
            dwd["dia_semana"] = dwd["dow"].apply(lambda i: nomes[i] if 0 <= int(i) < 7 else str(i))
            dwd = dwd.set_index("dia_semana")["quantidade"]
            st.bar_chart(dwd, width='stretch')
    else:
        st.info("Sem dados por dia da semana.")

    st.subheader("Vendas por hora")
    sel_days = st.selectbox("Janela", [7, 14, 30], index=0, key="an_hours_days")
    try:
        by_hour = dm.get_sales_by_hour(nome_rifa, days=int(sel_days))
    except Exception:
        by_hour = []
    if by_hour:
        dfh = pd.DataFrame(by_hour)
        if not dfh.empty:
            dfh = dfh.set_index("hora").sort_index()
            st.bar_chart(dfh, width='stretch')
    else:
        st.info("Sem dados suficientes para distribuição por hora.")

    st.markdown("---")
    st.subheader("Top compradores (qtd de números)")
    try:
        top = dm.get_top_buyers(nome_rifa)
    except Exception:
        top = []
    if top:
        dfb = pd.DataFrame(top)
        if not dfb.empty:
            dfb = dfb.set_index("comprador").sort_values("quantidade", ascending=False)
            st.bar_chart(dfb, width='stretch')
        # Ticket médio por comprador (aprox.)
        dfb2 = dfb.copy()
        dfb2["valor_aprox"] = dfb2["quantidade"] * valor_unit
        st.dataframe(dfb2.sort_values("quantidade", ascending=False).rename(columns={"quantidade": "qtd"}), width='stretch')
    else:
        st.info("Sem dados suficientes para ranking de compradores.")

    st.markdown("---")
    st.subheader("Heatmap: Dia da semana x Hora (últimos 30 dias)")
    try:
        heat = dm.get_sales_heatmap(nome_rifa, days=30)
    except Exception:
        heat = []
    if heat:
        dfhmap = pd.DataFrame(heat)
        if not dfhmap.empty:
            nomes = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
            dfhmap["dia"] = dfhmap["dow"].apply(lambda i: nomes[i] if 0 <= int(i) < 7 else str(i))
            # Altair heatmap
            try:
                chart = alt.Chart(dfhmap).mark_rect().encode(
                    x=alt.X('hour:O', title='Hora'),
                    y=alt.Y('dia:O', title='Dia'),
                    color=alt.Color('quantidade:Q', scale=alt.Scale(scheme='blues'), title='Vendas'),
                    tooltip=['dia', 'hour', 'quantidade']
                ).properties(width='container', height=240)
                st.altair_chart(chart, use_container_width=True)
            except Exception:
                piv = dfhmap.pivot_table(index="dia", columns="hour", values="quantidade", fill_value=0).sort_index()
                st.dataframe(piv, width='stretch')
    else:
        st.info("Sem dados suficientes para o heatmap.")

    st.markdown("---")
    st.subheader("Drill-down por dia")
    dia_sel = st.date_input("Escolha o dia", value=pd.Timestamp.utcnow().date())
    if dia_sel:
        start_d = pd.Timestamp(dia_sel).isoformat()
        end_d = (pd.Timestamp(dia_sel) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)).isoformat()
        try:
            vendas_dia = dm.get_sales_in_period(nome_rifa, start_d, end_d)
        except Exception:
            vendas_dia = []
        if vendas_dia:
            cdl, cdr = st.columns(2)
            with cdl:
                st.caption("Compradores do dia")
                dfc = pd.DataFrame(vendas_dia)
                repc = dfc.groupby("comprador").agg(qtd=("numero", "count")).reset_index().sort_values("qtd", ascending=False)
                st.dataframe(repc, width='stretch')
            with cdr:
                st.caption("Números vendidos do dia")
                nums = sorted([int(v['numero']) for v in vendas_dia])
                if nums:
                    chips = ", ".join(map(str, nums))
                    st.markdown(f"<div style='padding:8px;border:1px solid var(--border-color);border-radius:8px;'>" 
                                f"{chips}</div>", unsafe_allow_html=True)
                else:
                    st.info("Nenhum número vendido neste dia.")
            # Exportar CSV do dia
            csv_dia = pd.DataFrame(vendas_dia)
            csv_dia.rename(columns={"numero": "Número", "comprador": "Comprador", "contato": "Contato", "timestamp": "Data/Hora"}, inplace=True)
            st.download_button("Baixar CSV do dia", data=csv_dia.to_csv(index=False).encode('utf-8'), file_name=f"{nome_rifa}_vendas_{dia_sel}.csv", mime="text/csv")

            # Gerar PDF deste dia (consolidado por comprador)
            def _build_pdf_dia(vendas_list, cfg_local, tz_off: int):
                pdf = FPDF(orientation='P', unit='mm', format='A4')
                pdf.set_auto_page_break(auto=True, margin=12)
                logo_path = (cfg_local or {}).get("logo_path")
                qr_text = (cfg_local or {}).get("qr_text")
                obs = (cfg_local or {}).get("obs_padrao_pdf", "")
                valor_unit = float((cfg_local or {}).get("valor_numero", 0.0))
                # Agrupar por comprador
                by_buyer = {}
                for v in vendas_list:
                    by_buyer.setdefault(v['comprador'], []).append(v)
                for buyer, items in by_buyer.items():
                    numeros = sorted([int(x['numero']) for x in items])
                    contato = next((x.get('contato') for x in items if x.get('contato')), "")
                    qtd = len(numeros)
                    total = qtd * valor_unit
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 16)
                    if logo_path:
                        try: pdf.image(logo_path, x=12, y=10, w=28)
                        except Exception: pass
                    pdf.cell(0, 12, f"Comprovante de Compra - {nome_rifa}", ln=1, align='C')
                    pdf.set_font("Arial", size=12)
                    pdf.ln(4)
                    pdf.cell(0, 8, f"Comprador: {buyer}", ln=1)
                    if contato: pdf.cell(0, 8, f"Contato: {contato}", ln=1)
                    pdf.cell(0, 8, f"Quantidade: {qtd}", ln=1)
                    try:
                        pdf.cell(0, 8, f"Valor por número: R$ {valor_unit:,.2f}", ln=1)
                        pdf.cell(0, 8, f"Valor total: R$ {total:,.2f}", ln=1)
                    except Exception:
                        pdf.cell(0, 8, f"Valor por número: {valor_unit}", ln=1)
                        pdf.cell(0, 8, f"Valor total: {total}", ln=1)
                    nums_str = ", ".join(map(str, numeros))
                    pdf.multi_cell(0, 7, f"Números: {nums_str}")
                    # Mostrar um horário de referência (último do dia)
                    try:
                        ts_ref = max(pd.to_datetime(x['timestamp']) for x in items)
                        ts_local = ts_ref.tz_localize('UTC').tz_convert(None) + pd.Timedelta(hours=int(tz_off))
                        pdf.cell(0, 8, f"Gerado em (local): {ts_local.strftime('%Y-%m-%d %H:%M:%S')}", ln=1)
                    except Exception:
                        pass
                    if obs:
                        pdf.ln(2)
                        pdf.multi_cell(0, 7, obs)
                    if qr_text:
                        try:
                            img = qrcode.make(qr_text)
                            tmp = Path('.tmp_qr_day.png')
                            img.save(tmp)
                            pdf.image(str(tmp), x=170, y=10, w=28)
                            try: tmp.unlink(missing_ok=True)
                            except Exception: pass
                        except Exception:
                            pass
                out = pdf.output(dest='S')
                if isinstance(out, (bytes, bytearray)): return bytes(out)
                return out.encode('latin-1')

            tz_off = int(cfg.get('tz_offset_default', 0))
            if st.button("Gerar PDF deste dia"):
                pdf_bytes = _build_pdf_dia(vendas_dia, cfg, tz_off)
                fname = f"{nome_rifa}_comprovantes_{dia_sel}.pdf".replace(' ', '_')
                st.download_button("Baixar PDF do dia", data=pdf_bytes, file_name=fname, mime="application/pdf")
        else:
            st.info("Sem vendas neste dia.")

def renderizar_grid_vendas(nome_rifa: str, dados: Dict[str, str], cfg: Dict):
    total = int(cfg.get("total_numeros", 0))
    vendidos = set(map(int, dados.keys()))
    
    ttl_min = int(cfg.get("ttl_reserva_minutos", 15))
    ativos_det, expirados = dm.purge_expired_reservas(nome_rifa, ttl_min)
    if expirados:
        st.toast(f"Reservas expiradas liberadas: {sorted(expirados)}", icon="⏱️")
    
    reservados = set(ativos_det.keys())

    st.subheader("Venda e Reserva de Números")

    with st.form(key=f"form_venda_{nome_rifa}"):
        tipo = st.radio("Ação", ["Venda", "Reserva", "Cancelar reserva"], horizontal=True)
        numeros_txt = st.text_input("Números (ex: 1-10, 25, 30)")
        comprador = st.text_input("Nome do comprador", disabled=(tipo != "Venda"))
        contato = st.text_input("Contato (telefone/WhatsApp) (opcional)", disabled=(tipo != "Venda"))
        submitted = st.form_submit_button("Confirmar Ação", use_container_width=True)

    if submitted:
        nums = _parse_ranges(numeros_txt)
        if not nums:
            st.warning("Informe ao menos um número válido.")
            return

        if tipo == "Venda":
            if not comprador.strip():
                st.warning("Informe o nome do comprador.")
                return
            ok, detalhes, msg = dm.registrar_venda(nome_rifa, comprador.strip(), nums, contato=contato.strip() or None)
            if ok:
                st.success(f"{msg}: {detalhes}")
                st.rerun()
            else:
                st.error(f"{msg} | Detalhes: {detalhes}")

        elif tipo == "Reserva":
            novos = [n for n in nums if n not in vendidos and n not in reservados]
            if not novos:
                st.info("Todos os números informados já estão vendidos ou reservados.")
                return
            
            now_ts = datetime.now(timezone.utc).isoformat()
            for n in novos:
                ativos_det[n] = now_ts
            dm.salvar_reservas_detalhe(nome_rifa, ativos_det)
            st.success(f"Números reservados: {sorted(novos)}")
            st.rerun()
            
        elif tipo == "Cancelar reserva":
            cancelar = [n for n in nums if n in reservados]
            if not cancelar:
                st.info("Nenhum dos números informados está atualmente reservado.")
                return
                
            for n in cancelar:
                ativos_det.pop(n, None)
            dm.salvar_reservas_detalhe(nome_rifa, ativos_det)
            st.success(f"Reservas canceladas: {sorted(cancelar)}")
            st.rerun()

    # Grade de números com paginação
    st.markdown("---")
    per_page = st.selectbox("Números por página", options=[60, 120, 240], index=0)
    total_pages = max(1, (total + per_page - 1) // per_page)
    state_key = f"page_{nome_rifa}"
    if state_key not in st.session_state:
        st.session_state[state_key] = 1
    cols_ctrl = st.columns([1,2,2,2,1])
    with cols_ctrl[1]:
        if st.button("◀️ Anterior", disabled=(st.session_state[state_key] <= 1)):
            st.session_state[state_key] = max(1, st.session_state[state_key]-1)
    with cols_ctrl[2]:
        page = st.number_input("Página", min_value=1, max_value=total_pages, value=int(st.session_state[state_key]), step=1, key=f"num_page_{nome_rifa}")
        st.session_state[state_key] = int(page)
    with cols_ctrl[3]:
        if st.button("Próxima ▶️", disabled=(st.session_state[state_key] >= total_pages)):
            st.session_state[state_key] = min(total_pages, st.session_state[state_key]+1)

    # Ir para número específico
    with st.expander("Ir para número"):
        alvo = st.number_input("Número", min_value=1, max_value=total if total>0 else 1, value=1, step=1, key=f"goto_num_{nome_rifa}")
        if st.button("Ir", key=f"goto_btn_{nome_rifa}"):
            st.session_state[state_key] = int((int(alvo)-1)//per_page)+1
            st.rerun()

    page = int(st.session_state[state_key])
    start = (page - 1) * per_page + 1
    end = min(total, start + per_page - 1)

    cols = st.columns(cfg.get("grid_columns", 12))
    for n in range(start, end + 1):
        col = cols[(n - 1) % len(cols)]
        if n in vendidos:
            klass = "sold"
            title = dados.get(str(n), "Vendido")
        elif n in reservados:
            klass = "reserved"
            title = "Reservado"
        else:
            klass = "free"
            title = "Disponível"

        col.markdown(f'<div class="num-box {klass}" title="{title}">{n}</div>', unsafe_allow_html=True)


 