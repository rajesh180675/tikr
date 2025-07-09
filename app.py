import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import warnings
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# Import the custom dashboard class
from real_time import RealTimeFinancialDashboard

warnings.filterwarnings("ignore")

# --- UI/UX Helper Functions ---

def create_interactive_financial_grid(df_transposed: pd.DataFrame, title: str, is_ratio: bool = False):
    """
    Displays an interactive AgGrid table and a corresponding bar chart for a selected row.
    This improved version handles conditional chart coloring and better grid formatting.

    Args:
        df_transposed (pd.DataFrame): A pre-transposed dataframe with a 'Metric' column.
        title (str): The subheader title for the section.
        is_ratio (bool): If True, y-axis label will not show currency.
    """
    st.subheader(title)

    # --- AgGrid Configuration ---
    gb = GridOptionsBuilder.from_dataframe(df_transposed)
    gb.configure_selection('single', use_checkbox=True)
    
    # Right-align numbers and use monospace font for better readability
    cell_style_jscode = JsCode("""
    function(params) {
        if (typeof params.value === 'number') {
            return { 'textAlign': 'right', 'fontFamily': 'monospace' };
        }
    };
    """)
    gb.configure_column("Metric", headerName="Metric", flex=2, minWidth=250)
    for col in df_transposed.columns[1:]:
        gb.configure_column(
            col, type=["numericColumn", "numberColumnFilter"],
            valueFormatter="params.value == null ? '' : params.value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})",
            cellStyle=cell_style_jscode,
            flex=1, minWidth=120
        )
    
    grid_options = gb.build()
    
    grid_response = AgGrid(
        df_transposed,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        theme='streamlit',
        allow_unsafe_jscode=True,
        height=450,
        fit_columns_on_grid_load=True
    )

    # --- Charting for Selected Row ---
    if grid_response['selected_rows']:
        selected_row_data = grid_response['selected_rows'][0]
        metric = selected_row_data.pop('Metric')
        
        # Convert to a Series, ensuring years are strings and values are numeric
        plot_data = pd.Series(selected_row_data).astype(float)
        plot_data.sort_index(inplace=True)

        st.subheader(f"📈 Chart: {metric} over Years")
        fig, ax = plt.subplots(figsize=(12, 5))
        
        # Conditional coloring for positive/negative bars
        colors = ['#2ca02c' if val >= 0 else '#d62728' for val in plot_data]
        plot_data.plot(kind='bar', ax=ax, color=colors, edgecolor='black', alpha=0.8)
        
        ax.set_ylabel("Value" if is_ratio else "Amount (in Cr)")
        ax.set_xlabel("Year")
        ax.tick_params(axis='x', rotation=45, labelsize=12)
        ax.grid(axis='y', linestyle='--', alpha=0.6)
        
        # Add value labels on top of bars
        for p in ax.patches:
            ax.annotate(f'{p.get_height():,.2f}', (p.get_x() + p.get_width() / 2., p.get_height()),
                        ha='center', va='center', fontsize=9, color='black', xytext=(0, 10),
                        textcoords='offset points')
        
        plt.tight_layout()
        st.pyplot(fig)


# --- Main Streamlit App ---
st.set_page_config(page_title="TIKR-Style Financial Dashboard", layout="wide", initial_sidebar_state="expanded")

# Initialize the dashboard class in session state to avoid re-initialization on every script run
if 'dashboard' not in st.session_state:
    try:
        st.session_state.dashboard = RealTimeFinancialDashboard()
    except Exception as e:
        st.error(f"Fatal Error: Failed to initialize the dashboard backend. Please check dependencies. Error: {e}")
        st.stop()

st.title("📈 Real-Time Financial Dashboard (TIKR Style)")

# --- Sidebar Controls ---
st.sidebar.header("Company Selector")
symbol_input = st.sidebar.text_input("Enter NSE Symbol (e.g., ITC, HDFCBANK):", value="RELIANCE")
col1, col2 = st.sidebar.columns(2)
run_dashboard = col1.button("Generate Dashboard", use_container_width=True, type="primary")
clear_cache = col2.button("Clear Cache", use_container_width=True)

# Clear session state if button is pressed
if clear_cache:
    st.session_state.data = None
    st.experimental_rerun()

# --- Main Logic: Fetch data or use cached data ---
if run_dashboard and symbol_input:
    with st.spinner(f"Fetching and processing data for {symbol_input.upper()}..."):
        try:
            # The backend class handles the '.NS' suffix
            data = st.session_state.dashboard.get_screener_data(symbol_input.upper())
            if not data:
                raise ValueError("No data received. The symbol may be incorrect, delisted, or lack financial data on Yahoo Finance.")
            # Cache the data in session state
            st.session_state.data = data
        except Exception as e:
            st.error(f"❌ Error for {symbol_input.upper()}: {e}")
            st.session_state.data = None # Clear data on error
            st.stop()

# --- Display Dashboard if data is available in session state ---
if 'data' in st.session_state and st.session_state.data:
    data = st.session_state.data

    # --- Header and Key Metrics Display ---
    st.markdown(f"## {data['company_name']} ({data['symbol']})")
    
    price_delta_color = "normal" if data.get('change', 0) >= 0 else "inverse"
    metrics = data['real_time_metrics']
    
    cols = st.columns(5)
    cols[0].metric(
        "Current Price", f"₹{data.get('current_price', 0):.2f}",
        f"{data.get('change', 0):+.2f} ({data.get('change_percent', 0):+.2f}%)",
        delta_color=price_delta_color
    )
    cols[1].metric("Market Cap", f"₹{data.get('market_cap', 0)/1e7:,.0f} Cr")
    cols[2].metric("P/E Ratio (TTM)", f"{data.get('pe_ratio', 0):.2f}")
    cols[3].metric("EV/EBITDA (TTM)", f"{metrics.get('ev_to_ebitda', 0):.2f}")
    cols[4].metric("Dividend Yield", f"{data.get('dividend_yield', 0)*100:.2f}%")

    st.markdown("---")

    # --- Data Preparation (Do this once before creating tabs) ---
    def prepare_df(df_dict):
        df = pd.DataFrame(df_dict)
        if df.empty: return None
        df.set_index('years', inplace=True)
        df_t = df.transpose() / 1e7 # Convert to Crores
        return df_t.reset_index().rename(columns={'index': 'Metric'})

    df_income_t = prepare_df(data['financials']['income_statement'])
    df_bs_t = prepare_df(data['financials']['balance_sheet'])
    df_cf_t = prepare_df(data['financials']['cash_flow'])
    
    # Ratios don't need division by 1e7
    df_ratios_raw = pd.DataFrame(data['financials']['ratios'])
    if not df_ratios_raw.empty:
        df_ratios_t = df_ratios_raw.set_index('years').transpose().reset_index().rename(columns={'index': 'Metric'})
    else:
        df_ratios_t = None
        
    # --- Tabs for different sections ---
    tab_list = ["📊 Key Ratios", "💰 Income Statement", "📘 Balance Sheet", 
                "💵 Cash Flow", "📈 Charts", "🧾 Summary"]
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(tab_list)

    with tab1:
        if df_ratios_t is not None:
            create_interactive_financial_grid(df_ratios_t, "Key Financial Ratios", is_ratio=True)
        else: st.warning("Key ratio data is not available.")

    with tab2:
        if df_income_t is not None:
            create_interactive_financial_grid(df_income_t, "Annual Income Statement")
        else: st.warning("Income statement data is not available.")

    with tab3:
        if df_bs_t is not None:
            create_interactive_financial_grid(df_bs_t, "Annual Balance Sheet")
        else: st.warning("Balance sheet data is not available.")
    
    with tab4:
        if df_cf_t is not None:
            create_interactive_financial_grid(df_cf_t, "Annual Cash Flow Statement")
        else: st.warning("Cash flow data is not available.")

    with tab5:
        st.subheader("📈 Financial Summary Charts")
        try:
            fig = st.session_state.dashboard.create_comprehensive_dashboard(data['symbol'])
            st.pyplot(fig)
        except Exception as chart_error:
            st.warning(f"⚠️ Could not render comprehensive charts: {chart_error}")

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
    
    # --- Export section ---
    with st.expander("📥 Export Raw Data to CSV"):
        def to_csv(df_dict): return pd.DataFrame(df_dict).to_csv(index=False).encode('utf-8')
        
        st.download_button("Download Income Statement", to_csv(data['financials']['income_statement']), f"{data['symbol']}_Income.csv", "text/csv")
        st.download_button("Download Balance Sheet", to_csv(data['financials']['balance_sheet']), f"{data['symbol']}_BalanceSheet.csv", "text/csv")
        st.download_button("Download Cash Flow", to_csv(data['financials']['cash_flow']), f"{data['symbol']}_CashFlow.csv", "text/csv")

else:
    st.info("👋 Welcome! Enter a valid NSE stock symbol in the sidebar and click 'Generate Dashboard' to begin.")

st.sidebar.markdown("---")
st.sidebar.info("Data from `yfinance`. Accuracy is subject to Yahoo Finance's terms.")
st.sidebar.caption("Made with ❤️ using Streamlit")
