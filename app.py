# app.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import warnings
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

from real_time import RealTimeFinancialDashboard

warnings.filterwarnings("ignore")

def create_interactive_financial_grid(df_transposed: pd.DataFrame, title: str, is_ratio: bool = False):
    """Displays an interactive AgGrid table and a corresponding bar chart for a selected row."""
    st.subheader(title)

    gb = GridOptionsBuilder.from_dataframe(df_transposed)
    gb.configure_selection('single', use_checkbox=True)
    
    cell_style_jscode = JsCode("function(params) { if (typeof params.value === 'number') { return { 'textAlign': 'right', 'fontFamily': 'monospace' }; } };")
    gb.configure_column("Metric", headerName="Metric", flex=2, minWidth=250)
    for col in df_transposed.columns[1:]:
        gb.configure_column(
            col, type=["numericColumn", "numberColumnFilter"],
            valueFormatter="params.value == null ? '' : params.value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})",
            cellStyle=cell_style_jscode, flex=1, minWidth=120
        )
    
    grid_response = AgGrid(
        df_transposed, gridOptions=gb.build(), update_mode=GridUpdateMode.SELECTION_CHANGED,
        theme='streamlit', allow_unsafe_jscode=True, height=450, fit_columns_on_grid_load=True
    )

    if grid_response['selected_rows']:
        selected_row_data = grid_response['selected_rows'][0]
        metric = selected_row_data.pop('Metric')
        plot_data = pd.Series(selected_row_data).astype(float).sort_index()

        st.subheader(f"📈 Chart: {metric} over Years")
        fig, ax = plt.subplots(figsize=(12, 5))
        
        colors = ['#2ca02c' if val >= 0 else '#d62728' for val in plot_data]
        plot_data.plot(kind='bar', ax=ax, color=colors, edgecolor='black', alpha=0.8)
        
        ax.set_ylabel("Value" if is_ratio else "Amount (in Cr)")
        ax.set_xlabel("Year")
        ax.tick_params(axis='x', rotation=45, labelsize=12)
        ax.grid(axis='y', linestyle='--', alpha=0.6)
        
        for p in ax.patches:
            ax.annotate(f'{p.get_height():,.2f}', (p.get_x() + p.get_width() / 2., p.get_height()),
                        ha='center', va='center', fontsize=9, color='black', xytext=(0, 10),
                        textcoords='offset points')
        
        plt.tight_layout()
        st.pyplot(fig)

st.set_page_config(page_title="TIKR-Style Financial Dashboard", layout="wide", initial_sidebar_state="expanded")

if 'dashboard' not in st.session_state:
    st.session_state.dashboard = RealTimeFinancialDashboard()

st.title("📈 Real-Time Financial Dashboard (TIKR Style)")

st.sidebar.header("Company Selector")
symbol_input = st.sidebar.text_input("Enter NSE Symbol (e.g., ITC, HDFCBANK):", value="RELIANCE")
col1, col2 = st.sidebar.columns(2)
run_dashboard = col1.button("Generate", use_container_width=True, type="primary")
if col2.button("Clear", use_container_width=True):
    st.session_state.data = None
    # **THIS IS THE FIX for the AttributeError**: Use st.rerun()
    st.rerun()

if run_dashboard and symbol_input:
    with st.spinner(f"Fetching and processing data for {symbol_input.upper()}..."):
        data = st.session_state.dashboard.get_screener_data(symbol_input.upper())
        if not data:
            st.error(f"❌ Error for {symbol_input.upper()}: No data received. The symbol may be incorrect, delisted, or lack financial data on Yahoo Finance.")
            st.session_state.data = None
        else:
            st.session_state.data = data

if 'data' in st.session_state and st.session_state.data:
    data = st.session_state.data

    st.markdown(f"## {data['company_name']} ({data['symbol']})")
    price_delta_color = "normal" if data.get('change', 0) >= 0 else "inverse"
    metrics = data['real_time_metrics']
    
    cols = st.columns(5)
    cols[0].metric("Current Price", f"₹{data.get('current_price', 0):.2f}", f"{data.get('change', 0):+.2f} ({data.get('change_percent', 0):+.2f}%)", delta_color=price_delta_color)
    cols[1].metric("Market Cap", f"₹{data.get('market_cap', 0)/1e7:,.0f} Cr")
    cols[2].metric("P/E Ratio (TTM)", f"{data.get('pe_ratio', 0):.2f}")
    cols[3].metric("EV/EBITDA (TTM)", f"{metrics.get('ev_to_ebitda', 0):.2f}")
    cols[4].metric("Dividend Yield", f"{data.get('dividend_yield', 0)*100:.2f}%")
    st.markdown("---")

    def prepare_df(df_dict, in_crores=True):
        df = pd.DataFrame(df_dict)
        if df.empty: return None
        df.set_index('years', inplace=True)
        df_t = df.transpose()
        if in_crores: df_t = df_t / 1e7
        return df_t.reset_index().rename(columns={'index': 'Metric'})

    df_income_t = prepare_df(data['financials']['income_statement'])
    df_bs_t = prepare_df(data['financials']['balance_sheet'])
    df_cf_t = prepare_df(data['financials']['cash_flow'])
    df_ratios_t = prepare_df(data['financials']['ratios'], in_crores=False)
        
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 Key Ratios", "💰 Income Statement", "📘 Balance Sheet", "💵 Cash Flow", "📈 Charts", "🧾 Summary"])

    with tab1:
        if df_ratios_t is not None: create_interactive_financial_grid(df_ratios_t, "Key Financial Ratios", is_ratio=True)
        else: st.warning("Key ratio data is not available.")
    with tab2:
        if df_income_t is not None: create_interactive_financial_grid(df_income_t, "Annual Income Statement")
        else: st.warning("Income statement data is not available.")
    with tab3:
        if df_bs_t is not None: create_interactive_financial_grid(df_bs_t, "Annual Balance Sheet")
        else: st.warning("Balance sheet data is not available.")
    with tab4:
        if df_cf_t is not None: create_interactive_financial_grid(df_cf_t, "Annual Cash Flow Statement")
        else: st.warning("Cash flow data is not available.")
    with tab5:
        st.subheader("📈 Financial Summary Charts")
        # **THIS IS THE FIX for the TypeError**: Pass the symbol string, not the whole data dict.
        fig = st.session_state.dashboard.create_comprehensive_dashboard(data['symbol'])
        if fig: st.pyplot(fig)
        else: st.warning("Could not generate comprehensive charts due to missing data.")
    with tab6:
        st.subheader("🧾 Company Snapshot")
        col1, col2 = st.columns(2)
        col1.metric("Book Value / Share", f"₹{data.get('book_value', 0):.2f}")
        col1.metric("Debt to Equity", f"{metrics.get('debt_to_equity', 0):.2f}")
        col1.metric("Return on Equity (TTM)", f"{metrics.get('return_on_equity', 0)*100:.2f}%")
        col2.metric("Enterprise Value", f"₹{metrics.get('enterprise_value', 0)/1e7:,.0f} Cr")
        col2.metric("Free Cash Flow (TTM)", f"₹{metrics.get('free_cashflow', 0)/1e7:,.0f} Cr")
        st.markdown("---")
        col3, col4 = st.columns(2)
        col3.metric("52-Week High", f"₹{metrics.get('fifty_two_week_high', 0):.2f}")
        col4.metric("52-Week Low", f"₹{metrics.get('fifty_two_week_low', 0):.2f}")
    
    with st.expander("📥 Export Raw Data to CSV"):
        def to_csv(df_dict): return pd.DataFrame(df_dict).to_csv(index=False).encode('utf-8')
        st.download_button("Download Income Statement", to_csv(data['financials']['income_statement']), f"{data['symbol']}_Income.csv", "text/csv")
        st.download_button("Download Balance Sheet", to_csv(data['financials']['balance_sheet']), f"{data['symbol']}_BalanceSheet.csv", "text/csv")
        st.download_button("Download Cash Flow", to_csv(data['financials']['cash_flow']), f"{data['symbol']}_CashFlow.csv", "text/csv")
else:
    st.info("👋 Welcome! Enter a valid NSE stock symbol and click 'Generate' to begin.")

st.sidebar.markdown("---")
st.sidebar.info("Data from `yfinance`. Subject to Yahoo Finance's terms.")
st.sidebar.caption("Made with ❤️ using Streamlit")
