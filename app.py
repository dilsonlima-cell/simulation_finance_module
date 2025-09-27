# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO

# ---------------------------
# CSS - Estilos da Página
# ---------------------------
st.set_page_config(page_title="Simulador Financeiro Modular", layout="wide", initial_sidebar_state="expanded")
st.markdown(
    """
    <style>
    :root{
      --g1: linear-gradient(90deg,#ff7a45,#ffc75f,#9acd32);
      --card-bg: rgba(255,255,255,0.95);
    }
    /* body */
    .stApp { background: linear-gradient(180deg, #FFF 0%, #FFF7F0 100%); }
    /* header */
    .header-title { font-weight:700; font-size:28px; margin:0; }
    .subhead { color: #555; margin-top:4px; margin-bottom:8px; }
    /* KPI card */
    .kpi-card {
      background: var(--card-bg);
      border-radius: 12px;
      padding: 14px;
      box-shadow: 0 6px 18px rgba(15,23,42,0.06);
      border-left: 6px solid rgba(0,0,0,0.04);
    }
    .kpi-gradient {
      padding: 12px; border-radius: 12px;
      background: var(--g1);
      color: white;
      box-shadow: 0 6px 18px rgba(15,23,42,0.08);
    }
    .small-muted { color:#666; font-size:13px; }
    .pill { display:inline-block; padding:6px 10px; border-radius:999px; font-size:12px; background:#fff7ea; color:#b94a00; border:1px solid rgba(0,0,0,0.03); }
    /* responsive table small */
    table { border-collapse: collapse; width:100%;}
    th, td { padding: 8px; text-align: left; border-bottom: 1px solid #eee; font-size:13px;}
    </style>
    """, unsafe_allow_html=True
)

# ---------------------------
# Funções Utilitárias
# ---------------------------
def fmt_brl(v):
    return f"R$ {v:,.2f}"

def df_to_excel_bytes(df: pd.DataFrame):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Simulacao')
    processed_data = output.getvalue()
    return processed_data

# ---------------------------
# Lógica da Simulação (Atualizada)
# ---------------------------
def simulate(
    years: int,
    modules_init: int,
    cost_per_module: float,
    cost_correction_rate: float,
    revenue_per_module: float,
    maintenance_per_module: float,
    rent_value: float,
    rent_start_month: int,
    aportes: list,
    retiradas: list,
    fundos: list,
):
    months = years * 12
    rows = []
    
    # --- Estado inicial da simulação ---
    modules = modules_init
    caixa = 0.0 # Caixa começa em zero
    investimento_total = modules * cost_per_module # Investimento inicial
    fundo_ac = 0.0
    retiradas_ac = 0.0
    custo_modulo_atual = cost_per_module

    # Mapeia aportes para fácil acesso no loop
    aportes_map = {a["mes"]: a.get("valor", 0.0) for a in aportes}

    # --- Loop mensal da simulação ---
    for m in range(1, months + 1):
        # Variáveis do mês
        receita = modules * revenue_per_module
        manut = modules * maintenance_per_module
        aluguel = rent_value if m >= rent_start_month else 0.0
        novos_modulos_comprados = 0

        # Aplica aportes (adiciona ao caixa e ao investimento total)
        aporte_mes = aportes_map.get(m, 0.0)
        caixa += aporte_mes
        investimento_total += aporte_mes

        # Resultado operacional (soma e subtrai do caixa)
        caixa += receita - manut - aluguel

        # Aplica fundos de reserva (retirada mensal do caixa)
        fundo_mes_total = sum(f["valor"] for f in fundos if m >= f["mes"])
        caixa -= fundo_mes_total
        fundo_ac += fundo_mes_total

        # Aplica retiradas (percentual sobre o caixa positivo)
        retirada_mes_total = 0.0
        if caixa > 0:
            for r in retiradas:
                if m >= r["mes"]:
                    valor = caixa * (r["percentual"] / 100.0)
                    caixa -= valor
                    retirada_mes_total += valor
        retiradas_ac += retirada_mes_total

        # --- LÓGICA DE REINVESTIMENTO ANUAL ---
        # No final de cada ano (mês 12, 24, 36, etc.)
        if m % 12 == 0:
            # Verifica quantos módulos podem ser comprados com o caixa acumulado
            if caixa >= custo_modulo_atual:
                novos_modulos_comprados = int(caixa // custo_modulo_atual)
                custo_da_compra = novos_modulos_comprados * custo_modulo_atual
                
                # Atualiza o estado
                caixa -= custo_da_compra
                modules += novos_modulos_comprados
                investimento_total += custo_da_compra
            
            # Corrige o valor do módulo para o próximo ano
            custo_modulo_atual *= (1 + cost_correction_rate / 100.0)

        rows.append({
            "Mês": m,
            "Ano": (m - 1) // 12 + 1,
            "Módulos Ativos": modules,
            "Receita": receita,
            "Manutenção": manut,
            "Aluguel": aluguel,
            "Aporte": aporte_mes,
            "Fundo (Mês)": fundo_mes_total,
            "Retirada (Mês)": retirada_mes_total,
            "Caixa (Final Mês)": caixa,
            "Investimento Total Acumulado": investimento_total,
            "Fundo Acumulado": fundo_ac,
            "Retiradas Acumuladas": retiradas_ac,
            "Módulos Comprados no Ano": novos_modulos_comprados,
            "Custo Módulo (Próx. Ano)": custo_modulo_atual if m % 12 == 0 else np.nan,
        })

    df = pd.DataFrame(rows)
    # Preenche o valor do custo do módulo para visualização
    df["Custo Módulo (Próx. Ano)"] = df["Custo Módulo (Próx. Ano)"].ffill()
    
    return df

# ---------------------------
# Sidebar - Entradas do Usuário
# ---------------------------
with st.sidebar:
    st.markdown("<div style='display:flex; gap:10px; align-items:center'><div style='width:48px;height:48px;border-radius:10px;background:var(--g1)'></div><div><strong>Simulador Modular</strong><div style='font-size:12px;color:#444'>Projeção com reinvestimento</div></div></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.header("1. Configuração Geral")
    years = st.slider("Horizonte de investimento (anos)", 1, 30, 10)
    
    col1, col2 = st.columns(2)
    with col1:
        modules_init = st.number_input("Módulos iniciais", min_value=1, value=5, step=1)
        cost_per_module = st.number_input("Custo inicial por módulo (R$)", min_value=0.0, value=100_000.0, step=1000.0, format="%.2f")
    with col2:
        revenue_per_module = st.number_input("Receita mensal/módulo (R$)", min_value=0.0, value=4_500.0, step=100.0, format="%.2f")
        maintenance_per_module = st.number_input("Manutenção mensal/módulo (R$)", min_value=0.0, value=1_500.0, step=50.0, format="%.2f")
    
    cost_correction_rate = st.number_input("Correção anual do custo do módulo (%)", min_value=0.0, value=5.0, step=0.5, format="%.1f", help="Percentual de aumento do custo para compra de novos módulos a cada ano.")

    st.markdown("---")
    st.header("2. Custos Fixos")
    rent_value = st.number_input("Aluguel mensal do terreno (R$)", min_value=0.0, value=3_000.0, step=50.0, format="%.2f")
    rent_start_month = st.number_input("Mês de início do aluguel", min_value=1, max_value=years*12, value=6, step=1)

    st.markdown("---")
    st.header("3. Eventos Financeiros")
    
    # Inicialização das listas no session_state
    if "aportes" not in st.session_state:
        st.session_state.aportes = [{"mes": 3, "valor": 50_000.0}]
    if "retiradas" not in st.session_state:
        st.session_state.retiradas = [{"mes": 25, "percentual": 30.0}]
    if "fundos" not in st.session_state:
        st.session_state.fundos = [{"mes": 25, "valor": 5_000.0}]

    with st.expander("Aportes (investimentos pontuais)"):
        for i, a in enumerate(st.session_state.aportes):
            c1, c2, c3 = st.columns([1,2,1])
            a["mes"] = c1.number_input(f"Mês (aporte #{i+1})", min_value=1, max_value=years*12, value=a["mes"], key=f"ap_mes_{i}")
            a["valor"] = c2.number_input(f"Valor (R$) (aporte #{i+1})", min_value=0.0, value=a["valor"], step=1000.0, key=f"ap_val_{i}", format="%.2f")
            if c3.button("🗑️", key=f"ap_rem_{i}"):
                st.session_state.aportes.pop(i)
                st.rerun()
        if st.button("Adicionar Aporte"):
            st.session_state.aportes.append({"mes": 1, "valor": 10000.0})
            st.rerun()

    with st.expander("Retiradas (% sobre o caixa mensal)"):
        for i, r in enumerate(st.session_state.retiradas):
            c1, c2, c3 = st.columns([1,2,1])
            r["mes"] = c1.number_input(f"Mês início (retirada #{i+1})", min_value=1, max_value=years*12, value=r["mes"], key=f"re_mes_{i}")
            r["percentual"] = c2.number_input(f"% (retirada #{i+1})", min_value=0.0, max_value=100.0, value=r["percentual"], step=1.0, key=f"re_pct_{i}", format="%.1f")
            if c3.button("🗑️", key=f"re_rem_{i}"):
                st.session_state.retiradas.pop(i)
                st.rerun()
        if st.button("Adicionar Retirada"):
            st.session_state.retiradas.append({"mes": 1, "percentual": 10.0})
            st.rerun()

    with st.expander("Fundos de Reserva (valor fixo mensal)"):
        for i, f in enumerate(st.session_state.fundos):
            c1, c2, c3 = st.columns([1,2,1])
            f["mes"] = c1.number_input(f"Mês início (fundo #{i+1})", min_value=1, max_value=years*12, value=f["mes"], key=f"fu_mes_{i}")
            f["valor"] = c2.number_input(f"Valor mensal (R$) (fundo #{i+1})", min_value=0.0, value=f["valor"], step=100.0, key=f"fu_val_{i}", format="%.2f")
            if c3.button("🗑️", key=f"fu_rem_{i}"):
                st.session_state.fundos.pop(i)
                st.rerun()
        if st.button("Adicionar Fundo"):
            st.session_state.fundos.append({"mes": 1, "valor": 1000.0})
            st.rerun()

# ---------------------------
# Conteúdo Principal
# ---------------------------
# Executa a simulação com os parâmetros da sidebar
df = simulate(
    years=years,
    modules_init=modules_init,
    cost_per_module=cost_per_module,
    cost_correction_rate=cost_correction_rate,
    revenue_per_module=revenue_per_module,
    maintenance_per_module=maintenance_per_module,
    rent_value=rent_value,
    rent_start_month=rent_start_month,
    aportes=st.session_state.aportes,
    retiradas=st.session_state.retiradas,
    fundos=st.session_state.fundos,
)

# Título da página
st.markdown(f"<div style='display:flex; justify-content:space-between; align-items:center'><div><h1 class='header-title'>Simulador de Módulos — Projeção de {years} Anos</h1><div class='subhead'>Análise de fluxo de caixa com reinvestimento anual automático.</div></div><div><span class='pill'>✨ Novo: Reinvestimento</span></div></div>", unsafe_allow_html=True)

# KPIs (Indicadores Chave de Performance)
final = df.iloc[-1]
kpi_cols = st.columns(4)
kpi_cols[0].markdown(f"<div class='kpi-card'><div class='small-muted'>Investimento Inicial</div><div style='font-size:20px;font-weight:700'>{fmt_brl(modules_init * cost_per_module)}</div></div>", unsafe_allow_html=True)
kpi_cols[1].markdown(f"<div class='kpi-gradient'><div class='small-muted'>Módulos Finais</div><div style='font-size:20px;font-weight:700'>{int(final['Módulos Ativos'])}</div></div>", unsafe_allow_html=True)
kpi_cols[2].markdown(f"<div class='kpi-card'><div class='small-muted'>Retiradas Acumuladas</div><div style='font-size:20px;font-weight:700'>{fmt_brl(final['Retiradas Acumuladas'])}</div></div>", unsafe_allow_html=True)
kpi_cols[3].markdown(f"<div class='kpi-gradient'><div class='small-muted'>Caixa Final</div><div style='font-size:20px;font-weight:700'>{fmt_brl(final['Caixa (Final Mês)'])}</div></div>", unsafe_allow_html=True)

st.markdown("---")

# Gráficos
colA, colB = st.columns([2, 1])
with colA:
    st.subheader("Evolução Financeira ao Longo do Tempo")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Mês"], y=df["Caixa (Final Mês)"], mode="lines", name="Caixa", line=dict(color="#ff7a45", width=2.5)))
    fig.add_trace(go.Scatter(x=df["Mês"], y=df["Fundo Acumulado"], mode="lines", name="Fundo Acumulado", line=dict(color="#9acd32", width=1.5)))
    fig.add_trace(go.Scatter(x=df["Mês"], y=df["Retiradas Acumuladas"], mode="lines", name="Retiradas Acumuladas", line=dict(color="#ffc75f", width=1.5)))
    fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True)

with colB:
    st.subheader("Evolução dos Módulos")
    fig_mod = go.Figure()
    fig_mod.add_trace(go.Scatter(x=df["Mês"], y=df["Módulos Ativos"], mode="lines", name="Módulos", line=dict(color="#2a9d8f", width=2.5), fill='tozeroy'))
    fig_mod.update_layout(margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_mod, use_container_width=True)

st.markdown("---")

# Resumo por Ano (Dinâmico)
st.subheader("Resumo Consolidado por Ano")
col_res1, col_res2 = st.columns([1, 3])

with col_res1:
    summary_year = st.number_input(
        "Selecione o ano para detalhar",
        min_value=1,
        max_value=years,
        value=min(5, years), # Padrão para ano 5 ou o último, se for menor
        step=1
    )

def get_summary_for_year(df, year):
    # Pega o último mês daquele ano
    target_month = year * 12
    if target_month > len(df):
        target_month = len(df)
    
    data = df[df["Mês"] == target_month].iloc[0]
    return {
        "Marco": f"Final do Ano {year}",
        "Módulos": f"{int(data['Módulos Ativos'])}",
        "Caixa": fmt_brl(data['Caixa (Final Mês)']),
        "Fundo": fmt_brl(data['Fundo Acumulado']),
        "Retiradas": fmt_brl(data['Retiradas Acumuladas']),
        "Investimento Total": fmt_brl(data['Investimento Total Acumulado'])
    }

with col_res2:
    summary_data = []
    # Adiciona o resumo para o ano selecionado
    summary_data.append(get_summary_for_year(df, summary_year))
    
    # Adiciona o resumo do ano final, se for diferente do selecionado
    if summary_year != years:
        summary_data.append(get_summary_for_year(df, years))
    
    summary_df = pd.DataFrame(summary_data)
    st.table(summary_df)

st.markdown("---")

# Tabela de Resultados e Download
st.subheader("Tabela Completa da Simulação")
with st.expander("Clique para expandir e ver todos os dados mensais"):
    # Formata colunas para exibição na tabela
    df_display = df.copy()
    for col in ["Receita", "Manutenção", "Aluguel", "Aporte", "Fundo (Mês)", "Retirada (Mês)", "Caixa (Final Mês)", "Investimento Total Acumulado", "Fundo Acumulado", "Retiradas Acumuladas", "Custo Módulo (Próx. Ano)"]:
        df_display[col] = df_display[col].apply(lambda x: fmt_brl(x) if pd.notna(x) else "-")
    st.dataframe(df_display, use_container_width=True)

excel_bytes = df_to_excel_bytes(df)
st.download_button(
    "📥 Baixar Relatório Completo (Excel)",
    data=excel_bytes,
    file_name=f"simulacao_modulos_{years}_anos.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
