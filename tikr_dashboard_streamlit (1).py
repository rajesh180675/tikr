import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from real_time import RealTimeFinancialDashboard
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import warnings

warnings.filterwarnings("ignore")

# --- Helper Function for DRY Principle ---
def display_financial_table_and_chart(title: str, df: pd.DataFrame, y_label: str = "Value"):
    """
    Displays an interactive AgGrid table and a corresponding bar chart for a selected row.
    This function helps avoid repeating code across multiple tabs.

    Args:
        title (str): The subheader title for the section.
        df (pd.DataFrame): The dataframe to display. Must contain a 'years' column.
        y_label (str): The label for the y-axis of the chart.
    """
    st.subheader(title)
    
    # Prepare the dataframe for display
    df_display = df.copy()
    df_display.set_index('years', inplace=True)
    df_transposed = df_display.transpose().reset_index().rename(columns={'index': 'Metric'})

    # Configure the interactive grid
    gb = GridOptionsBuilder.from_dataframe(df_transposed)
    gb.configure_selection('single', use_checkbox=True)
    gb.configure_column("Metric", headerName="Metric", flex=2, minWidth=250)
    for col in df_transposed.columns[1:]:
         gb.configure_column(col, type=["numericColumn", "numberColumnFilter", "customNumericFormat"], flex=1, minWidth=120)
    
    grid_options = gb.build()
    
    grid_response = AgGrid(
        df_transposed,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        theme='streamlit',
        allow_unsafe_jscode=True,
        height=500,
        fit_columns_on_grid_load=True
    )

    # Plot chart for the selected row
    if grid_response['selected_rows']:
        selected_row = grid_response['selected_rows'][0]
        metric = selected_row['Metric']
        st.subheader(f"📉 Chart: {metric} over Years")
        
        fig, ax = plt.subplots(figsize=(10, 4))
        
        # Prepare data for plotting (ensure it's numeric)
        plot_data = pd.to_numeric(df_transposed[df_transposed['Metric'] == metric].iloc[0, 1:], errors='coerce')
        plot_data.plot(kind='bar', ax=ax, color='skyblue')
        
        ax.set_ylabel(y_label)
        ax.set_xlabel("Year")
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        st.pyplot(fig)


# --- Streamlit App ---

# Initialize the dashboard class
try:
    dashboard = RealTimeFinancialDashboard()
except Exception as e:
    st.error(f"Failed to initialize the dashboard backend: {e}")
    st.stop()

# Streamlit UI setup
st.set_page_config(page_title="TIKR-Style Financial Dashboard", layout="wide")
st.title("📈 Real-Time Financial Dashboard (TIKR Style)")

# Sidebar controls
st.sidebar.header("Company Selector")
symbol_input = st.sidebar.text_input("Enter NSE Symbol (e.g., ITC, HDFCBANK):", value="ITC")
run_dashboard = st.sidebar.button("Generate Dashboard")

if run_dashboard and symbol_input:
    with st.spinner(f"Fetching and processing data for {symbol_input}..."):
        try:
            data = dashboard.get_screener_data(symbol_input.upper())
            if not data or "financials" not in data:
                raise ValueError("Empty or invalid data received from live source.")
        except Exception as e:
            st.error(f"❌ Error while fetching data for {symbol_input.upper()}: {str(e)}")
            st.stop()

    # --- Data Preparation (CRITICAL FIX) ---
    # Define dataframes here to make them available to both tabs and the export section
    try:
        df_ratios = pd.DataFrame(data['financials']['ratios'])
        df_income = pd.DataFrame(data['financials']['income_statement'])
        df_bs = pd.DataFrame(data['financials']['balance_sheet'])
        df_cf = pd.DataFrame(data['financials']['cash_flow'])
    except KeyError as e:
        st.error(f"Data structure is missing a required key: {e}. Cannot build dashboard.")
        st.stop()


    # --- Header and Price Info ---
    st.markdown(f"## {data.get('company_name', 'N/A')} ({data.get('symbol', 'N/A')})")
    col1, col2 = st.columns([2, 1])
    col1.metric("Current Price", f"₹{data.get('current_price', 0):.2f}",
                f"{data.get('change', 0):+.2f} ({data.get('change_percent', 0):+.2f}%)")
    col2.metric("Market Cap (Cr)", f"₹{data.get('market_cap', 0)/1e7:.0f}", "")

    # --- Tabs for different sections ---
    tab_list = ["📊 Key Ratios", "💰 Income Statement", "📘 Balance Sheet", "💵 Cash Flow", "📈 Charts", "🧾 Summary"]
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(tab_list)

    # --- Tab 1: Key Ratios ---
    with tab1:
        display_financial_table_and_chart(
            title="📊 Key Ratios",
            df=df_ratios,
            y_label="Value"
        )

    # --- Tab 2: Income Statement ---
    with tab2:
        display_financial_table_and_chart(
            title="💰 Income Statement",
            df=df_income,
            y_label="₹ in Cr"
        )

    # --- Tab 3: Balance Sheet ---
    with tab3:
        display_financial_table_and_chart(
            title="📘 Balance Sheet",
            df=df_bs,
            y_label="₹ in Cr"
        )

    # --- Tab 4: Cash Flow ---
    with tab4:
        display_financial_table_and_chart(
            title="💵 Cash Flow Statement",
            df=df_cf,
            y_label="₹ in Cr"
        )

    # --- Tab 5: Charts ---
    with tab5:
        st.subheader("📈 Financial Charts")
        try:
            # BUG FIX: The returned figure must be displayed
            fig = dashboard.create_comprehensive_dashboard(symbol_input.upper())
            if fig:
                 st.pyplot(fig) # Display the figure
            else:
                 st.info("No comprehensive chart available for this symbol.")
        except Exception as chart_error:
            st.warning(f"⚠️ Chart rendering failed: {chart_error}")

    # --- Tab 6: Summary ---
    with tab6:
        st.subheader("🧾 Company Summary")
        try:
            # Using a dictionary for cleaner data organization
            summary_data = {
                "Book Value": f"₹{data.get('book_value', 0):.2f}",
                "Dividend Yield": f"{data.get('dividend_yield', 0)*100:.2f}%",
                "P/E Ratio": f"{data.get('pe_ratio', 0):.1f}",
                "ROE": f"{data['real_time_metrics'].get('return_on_equity', 0)*100:.1f}%",
                "Debt/Equity": f"{data['real_time_metrics'].get('debt_to_equity', 0):.2f}",
                "Free Cash Flow (Cr)": f"₹{data['real_time_metrics'].get('free_cashflow', 0)/1e7:.0f}",
                "Enterprise Value (Cr)": f"₹{data['real_time_metrics'].get('enterprise_value', 0)/1e7:.0f}",
                "EV/EBITDA": f"{data['real_time_metrics'].get('ev_to_ebitda', 0):.2f}",
                "52W High": f"₹{data['real_time_metrics'].get('fifty_two_week_high', 0):.2f}",
                "52W Low": f"₹{data['real_time_metrics'].get('fifty_two_week_low', 0):.2f}"
            }
            df_summary = pd.DataFrame(summary_data.items(), columns=["Metric", "Value"])
            st.table(df_summary)
        except (KeyError, TypeError) as e:
            st.warning(f"⚠️ Could not display some summary metrics. Data might be incomplete. Error: {e}")

    # --- Export section ---
    with st.expander("📥 Export Options"):
        st.download_button(
            label="Download Income Statement (CSV)",
            data=df_income.transpose().to_csv().encode('utf-8'),
            file_name=f"{symbol_input.upper()}_Income_Statement.csv",
            mime='text/csv'
        )
        st.download_button(
            label="Download Balance Sheet (CSV)",
            data=df_bs.transpose().to_csv().encode('utf-8'),
            file_name=f"{symbol_input.upper()}_Balance_Sheet.csv",
            mime='text/csv'
        )
        st.download_button(
            label="Download Cash Flow (CSV)",
            data=df_cf.transpose().to_csv().encode('utf-8'),
            file_name=f"{symbol_input.upper()}_Cash_Flow.csv",
            mime='text/csv'
        )
        st.download_button(
            label="Download Key Ratios (CSV)",
            data=df_ratios.transpose().to_csv().encode('utf-8'),
            file_name=f"{symbol_input.upper()}_Key_Ratios.csv",
            mime='text/csv'
        )


st.sidebar.markdown("---")
st.sidebar.info("This dashboard uses real-time data which may have occasional delays or inaccuracies.")
st.sidebar.caption("Made with ❤️ using Streamlit + Yahoo Finance")
