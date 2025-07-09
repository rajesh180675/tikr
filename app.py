import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import warnings
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# Import the custom dashboard class
from real_time import RealTimeFinancialDashboard

warnings.filterwarnings("ignore")

# --- Helper Function to display tables and charts ---
def display_financial_grid(df: pd.DataFrame, title: str, currency_symbol: str = "₹"):
    """
    Displays a financial dataframe in an AgGrid table and plots a bar chart
    for the selected row.

    Args:
        df (pd.DataFrame): The dataframe to display (e.g., income statement).
        title (str): The title for the subheader.
        currency_symbol (str): The currency symbol to use for y-axis labels.
    """
    st.subheader(title)
    
    # Transpose and prepare the dataframe
    df.set_index('years', inplace=True)
    df_t = df.transpose().reset_index()
    df_t.rename(columns={'index': 'Metric'}, inplace=True)
    
    # AgGrid configuration
    gb = GridOptionsBuilder.from_dataframe(df_t)
    gb.configure_selection('single', use_checkbox=True)
    
    # Add a JavaScript renderer to format numbers
    cellsytle_jscode = JsCode("""
    function(params) {
        if (typeof params.value === 'number') {
            return {
                'textAlign': 'right',
                'fontFamily': 'monospace'
            };
        }
    };
    """)
    gb.configure_default_column(cellStyle=cellsytle_jscode)
    
    grid_response = AgGrid(
        df_t,
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        theme='streamlit',
        allow_unsafe_jscode=True,
        height=400,
        fit_columns_on_grid_load=True
    )

    # Plot chart for selected row
    if grid_response['selected_rows']:
        row = grid_response['selected_rows'][0]
        metric = row['Metric']
        
        # Prepare data for plotting (ensure it's numeric)
        plot_data = pd.to_numeric(df_t[df_t['Metric'] == metric].iloc[0, 1:], errors='coerce')
        plot_data.sort_index(inplace=True) # Sort by year
        
        st.subheader(f"📈 Chart: {metric} over Years")
        fig, ax = plt.subplots(figsize=(12, 5))
        plot_data.plot(kind='bar', ax=ax, color='skyblue', edgecolor='black')
        
        ax.set_ylabel(f"{currency_symbol} in Cr" if currency_symbol else "Value")
        ax.set_xlabel("Year")
        ax.tick_params(axis='x', rotation=45)
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        st.pyplot(fig)

# --- Main Streamlit App ---

# Initialize the dashboard class
try:
    dashboard = RealTimeFinancialDashboard()
except Exception as e:
    st.error(f"Failed to initialize the dashboard. Please check dependencies. Error: {e}")
    st.stop()

# Streamlit UI setup
st.set_page_config(page_title="TIKR-Style Financial Dashboard", layout="wide")
st.title("📈 Real-Time Financial Dashboard (TIKR Style)")

# Sidebar controls
st.sidebar.header("Company Selector")
symbol_input = st.sidebar.text_input("Enter NSE Symbol (e.g., ITC, HDFCBANK):", value="RELIANCE")
run_dashboard = st.sidebar.button("Generate Dashboard")

if run_dashboard and symbol_input:
    with st.spinner(f"Fetching and processing data for {symbol_input.upper()}..."):
        try:
            # Append .NS for NSE stocks if not present
            ticker = symbol_input.upper()
            if not ticker.endswith('.NS'):
                ticker += '.NS'
            
            data = dashboard.get_screener_data(ticker)
            if not data or "financials" not in data or not data["financials"]["income_statement"]:
                raise ValueError("No financial data found. The symbol may be incorrect or delisted.")
        except Exception as e:
            st.error(f"❌ Error while fetching data for {symbol_input.upper()}: {e}")
            st.stop()

    # --- Header and Key Metrics ---
    st.markdown(f"## {data['company_name']} ({data['symbol']})")
    
    price_delta_color = "normal" if data['change'] >= 0 else "inverse"
    st.metric(
        "Current Price", 
        f"₹{data['current_price']:.2f}", 
        f"{data['change']:+.2f} ({data['change_percent']:+.2f}%)",
        delta_color=price_delta_color
    )

    # --- Tabs for different sections ---
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Key Ratios", "💰 Income Statement", "📘 Balance Sheet", 
        "💵 Cash Flow", "📈 Charts", "🧾 Summary"
    ])

    # --- Tab 1: Key Ratios ---
    with tab1:
        df_ratios = pd.DataFrame(data['financials']['ratios'])
        if not df_ratios.empty:
            display_financial_grid(df_ratios, "Key Financial Ratios", currency_symbol=None)
        else:
            st.warning("Key ratio data is not available.")

    # --- Tab 2: Income Statement ---
    with tab2:
        df_income = pd.DataFrame(data['financials']['income_statement'])
        if not df_income.empty:
            display_financial_grid(df_income, "Annual Income Statement")
        else:
            st.warning("Income statement data is not available.")

    # --- Tab 3: Balance Sheet ---
    with tab3:
        df_bs = pd.DataFrame(data['financials']['balance_sheet'])
        if not df_bs.empty:
            display_financial_grid(df_bs, "Annual Balance Sheet")
        else:
            st.warning("Balance sheet data is not available.")

    # --- Tab 4: Cash Flow ---
    with tab4:
        st.subheader("💵 Annual Cash Flow Statement")
        df_cf = pd.DataFrame(data['financials']['cash_flow'])
        if not df_cf.empty:
            df_cf.set_index('years', inplace=True)
            st.dataframe(df_cf.transpose().style.format("{:,.0f}"))
        else:
            st.warning("Cash flow data is not available.")

    # --- Tab 5: Charts ---
    with tab5:
        st.subheader("📈 Financial Summary Charts")
        try:
            fig = dashboard.create_comprehensive_dashboard(data)
            st.pyplot(fig)
        except Exception as chart_error:
            st.warning(f"⚠️ Could not render comprehensive charts: {chart_error}")

    # --- Tab 6: Summary ---
    with tab6:
        st.subheader("🧾 Company Snapshot")
        col1, col2 = st.columns(2)
        
        metrics = data['real_time_metrics']
        col1.metric("Market Cap", f"₹{data['market_cap']/1e7:,.0f} Cr")
        col1.metric("P/E Ratio", f"{data['pe_ratio']:.2f}")
        col1.metric("Book Value", f"₹{data['book_value']:.2f}")
        col1.metric("Dividend Yield", f"{data['dividend_yield']*100:.2f}%")
        
        col2.metric("Return on Equity (TTM)", f"{metrics.get('return_on_equity', 0)*100:.2f}%")
        col2.metric("Debt to Equity", f"{metrics.get('debt_to_equity', 0):.2f}")
        col2.metric("Enterprise Value", f"₹{metrics.get('enterprise_value', 0)/1e7:,.0f} Cr")
        col2.metric("EV/EBITDA", f"{metrics.get('ev_to_ebitda', 0):.2f}")

        st.markdown("---")
        col3, col4 = st.columns(2)
        col3.metric("52-Week High", f"₹{metrics.get('fifty_two_week_high', 0):.2f}")
        col4.metric("52-Week Low", f"₹{metrics.get('fifty_two_week_low', 0):.2f}")

    # --- Export section ---
    with st.expander("📥 Export Data to CSV"):
        st.download_button(
            label="Download Income Statement",
            data=pd.DataFrame(data['financials']['income_statement']).to_csv(index=False).encode(),
            file_name=f"{symbol_input.upper()}_Income_Statement.csv",
            mime='text/csv'
        )
        st.download_button(
            label="Download Balance Sheet",
            data=pd.DataFrame(data['financials']['balance_sheet']).to_csv(index=False).encode(),
            file_name=f"{symbol_input.upper()}_Balance_Sheet.csv",
            mime='text/csv'
        )
        st.download_button(
            label="Download Cash Flow Statement",
            data=pd.DataFrame(data['financials']['cash_flow']).to_csv(index=False).encode(),
            file_name=f"{symbol_input.upper()}_Cash_Flow.csv",
            mime='text/csv'
        )
else:
    st.info("Enter a valid NSE stock symbol in the sidebar and click 'Generate Dashboard' to begin.")

st.sidebar.markdown("---")
st.sidebar.info("This dashboard uses the `yfinance` library to fetch public stock data. Data accuracy and availability are subject to Yahoo Finance's terms of service.")
st.sidebar.caption("Made with ❤️ using Streamlit")
