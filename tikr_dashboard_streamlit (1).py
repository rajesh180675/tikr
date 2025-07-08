import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

from real_time import RealTimeFinancialDashboard
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# Initialize the dashboard class
dashboard = RealTimeFinancialDashboard()

# Streamlit UI setup
st.set_page_config(page_title="TIKR-Style Financial Dashboard", layout="wide")
st.title("📈 Real-Time Financial Dashboard (TIKR Style)")

# Sidebar controls
st.sidebar.header("Company Selector")
symbol_input = st.sidebar.text_input("Enter NSE Symbol (e.g., ITC, HDFCBANK):", value="ITC")
run_dashboard = st.sidebar.button("Generate Dashboard")

if run_dashboard:
    with st.spinner(f"Fetching and processing data for {symbol_input}..."):
        try:
            data = dashboard.get_screener_data(symbol_input.upper())
            if not data or "financials" not in data:
                raise ValueError("Empty or invalid data received from live source.")
        except Exception as e:
            st.error(f"❌ Error while fetching data for {symbol_input.upper()}: {str(e)}")
            st.stop()

    # Header and price change
    st.markdown(f"## {data['company_name']} ({data['symbol']})")
    col1, col2 = st.columns([2, 1])
    col1.metric("Current Price", f"₹{data['current_price']:.2f}", 
                f"{data['change']:+.2f} ({data['change_percent']:+.2f}%)")
    col2.metric("Market Cap (Cr)", f"₹{data['market_cap']/1e7:.0f}", "")

    # Tabs for sections
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Key Ratios", "💰 Income Statement", "📘 Balance Sheet", 
        "💵 Cash Flow", "📈 Charts", "🧾 Summary"])

    # --- Tab 1: Key Ratios ---
    with tab1:
        st.subheader("📊 Key Ratios")
        df_ratios = pd.DataFrame(data['financials']['ratios'])
        df_ratios.set_index('years', inplace=True)
        df_ratios_t = df_ratios.transpose().reset_index()

        gb = GridOptionsBuilder.from_dataframe(df_ratios_t)
        gb.configure_selection('single')
        grid_response = AgGrid(
            df_ratios_t,
            gridOptions=gb.build(),
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            theme='streamlit'
        )

        if grid_response['selected_rows']:
            row = grid_response['selected_rows'][0]
            metric = row['index']
            st.subheader(f"📉 Chart: {metric} over Years")
            fig, ax = plt.subplots(figsize=(10, 4))
            df_ratios_t[df_ratios_t['index'] == metric].iloc[0, 1:].plot(kind='bar', ax=ax)
            ax.set_ylabel("Value")
            st.pyplot(fig)

    # --- Tab 2: Income Statement ---
    with tab2:
        st.subheader("💰 Income Statement")
        df_income = pd.DataFrame(data['financials']['income_statement'])
        df_income.set_index('years', inplace=True)
        df_income_t = df_income.transpose().reset_index()

        gb2 = GridOptionsBuilder.from_dataframe(df_income_t)
        gb2.configure_selection('single')
        grid_response2 = AgGrid(
            df_income_t,
            gridOptions=gb2.build(),
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            theme='streamlit'
        )

        if grid_response2['selected_rows']:
            row = grid_response2['selected_rows'][0]
            metric = row['index']
            st.subheader(f"📉 Chart: {metric} over Years")
            fig, ax = plt.subplots(figsize=(10, 4))
            df_income_t[df_income_t['index'] == metric].iloc[0, 1:].plot(kind='bar', ax=ax)
            ax.set_ylabel("₹ in Cr")
            st.pyplot(fig)

    # --- Tab 3: Balance Sheet ---
    with tab3:
        st.subheader("📘 Balance Sheet")
        df_bs = pd.DataFrame(data['financials']['balance_sheet'])
        df_bs.set_index('years', inplace=True)
        df_bs_t = df_bs.transpose().reset_index()

        gb3 = GridOptionsBuilder.from_dataframe(df_bs_t)
        gb3.configure_selection('single')
        grid_response3 = AgGrid(
            df_bs_t,
            gridOptions=gb3.build(),
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            theme='streamlit'
        )

        if grid_response3['selected_rows']:
            row = grid_response3['selected_rows'][0]
            metric = row['index']
            st.subheader(f"📉 Chart: {metric} over Years")
            fig, ax = plt.subplots(figsize=(10, 4))
            df_bs_t[df_bs_t['index'] == metric].iloc[0, 1:].plot(kind='bar', ax=ax)
            ax.set_ylabel("₹ in Cr")
            st.pyplot(fig)

    # --- Tab 4: Cash Flow ---
    with tab4:
        st.subheader("💵 Cash Flow Statement")
        df_cf = pd.DataFrame(data['financials']['cash_flow'])
        df_cf.set_index('years', inplace=True)
        st.dataframe(df_cf.transpose().style.format("{:.2f}"))

    # --- Tab 5: Charts ---
    with tab5:
        st.subheader("📈 Financial Charts")
        try:
            fig = dashboard.create_comprehensive_dashboard(symbol_input.upper())
        except Exception as chart_error:
            st.warning(f"⚠️ Chart rendering failed: {chart_error}")

    # --- Tab 6: Summary ---
    with tab6:
        st.subheader("🧾 Company Summary")
        summary = [
            ["Book Value", f"₹{data['book_value']:.2f}"],
            ["Dividend Yield", f"{data['dividend_yield']*100:.2f}%"],
            ["P/E Ratio", f"{data['pe_ratio']:.1f}"],
            ["ROE", f"{data['real_time_metrics']['return_on_equity']*100:.1f}%"],
            ["Debt/Equity", f"{data['real_time_metrics']['debt_to_equity']:.2f}"],
            ["Free Cash Flow", f"₹{data['real_time_metrics']['free_cashflow']/1e7:.0f} Cr"],
            ["Enterprise Value", f"₹{data['real_time_metrics']['enterprise_value']/1e7:.0f} Cr"],
            ["EV/EBITDA", f"{data['real_time_metrics']['ev_to_ebitda']:.2f}"],
            ["52W High", f"₹{data['real_time_metrics']['fifty_two_week_high']:.2f}"],
            ["52W Low", f"₹{data['real_time_metrics']['fifty_two_week_low']:.2f}"]
        ]
        df_summary = pd.DataFrame(summary, columns=["Metric", "Value"])
        st.table(df_summary)

    # --- Export section ---
    with st.expander("📥 Export Options"):
        st.download_button(
            label="Download Income Statement (CSV)",
            data=df_income.transpose().to_csv().encode(),
            file_name=f"{symbol_input.upper()}_Income_Statement.csv",
            mime='text/csv'
        )
        st.download_button(
            label="Download Balance Sheet (CSV)",
            data=df_bs.transpose().to_csv().encode(),
            file_name=f"{symbol_input.upper()}_Balance_Sheet.csv",
            mime='text/csv'
        )
        st.download_button(
            label="Download Cash Flow (CSV)",
            data=df_cf.transpose().to_csv().encode(),
            file_name=f"{symbol_input.upper()}_Cash_Flow.csv",
            mime='text/csv'
        )

st.sidebar.markdown("---")
st.sidebar.caption("Made with ❤️ using Streamlit + Yahoo Finance")
