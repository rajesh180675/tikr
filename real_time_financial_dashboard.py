import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

class RealTimeFinancialDashboard:
    """
    A class to fetch, process, and visualize financial data for a given stock symbol
    using the yfinance library.
    """

    def __init__(self):
        """Initializes the dashboard class."""
        # Set a professional plot style
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (12, 6)
        plt.rcParams['axes.titlesize'] = 16
        plt.rcParams['axes.labelsize'] = 12
        plt.rcParams['xtick.labelsize'] = 10
        plt.rcParams['ytick.labelsize'] = 10
        plt.rcParams['legend.fontsize'] = 10

    def get_screener_data(self, symbol: str) -> dict:
        """
        Fetches comprehensive financial data for a given NSE stock symbol.

        Args:
            symbol: The NSE stock symbol (e.g., "ITC.NS").

        Returns:
            A dictionary containing structured financial data.
        """
        if not symbol.upper().endswith('.NS'):
            symbol += '.NS'
            
        stock = yf.Ticker(symbol)
        info = stock.info

        # --- Basic Info ---
        company_name = info.get('longName', 'N/A')
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
        previous_close = info.get('previousClose', 0)
        change = current_price - previous_close
        change_percent = (change / previous_close) * 100 if previous_close else 0
        market_cap = info.get('marketCap', 0)
        book_value = info.get('bookValue', 0)
        dividend_yield = info.get('dividendYield', 0)
        pe_ratio = info.get('trailingPE', 0)
        fifty_two_week_high = info.get('fiftyTwoWeekHigh', 0)
        fifty_two_week_low = info.get('fiftyTwoWeekLow', 0)

        # --- Financial Statements (Annual) ---
        income_statement = stock.financials.transpose().reset_index()
        balance_sheet = stock.balance_sheet.transpose().reset_index()
        cash_flow = stock.cashflow.transpose().reset_index()

        # Rename columns for clarity and format dates
        for df in [income_statement, balance_sheet, cash_flow]:
            df.rename(columns={'index': 'years'}, inplace=True)
            if 'years' in df.columns:
                df['years'] = pd.to_datetime(df['years']).dt.strftime('%Y')

        # --- Key Ratios ---
        # Calculate ratios manually for consistency
        ratios = pd.DataFrame()
        ratios['years'] = income_statement['years']
        
        # Profitability Ratios
        ratios['Net Profit Margin'] = income_statement.get('Net Income', 0) / income_statement.get('Total Revenue', np.nan)
        ratios['Return on Equity (ROE)'] = income_statement.get('Net Income', 0) / balance_sheet.get('Total Stockholder Equity', np.nan)
        ratios['Return on Assets (ROA)'] = income_statement.get('Net Income', 0) / balance_sheet.get('Total Assets', np.nan)
        
        # Liquidity Ratios
        ratios['Current Ratio'] = balance_sheet.get('Total Current Assets', 0) / balance_sheet.get('Total Current Liabilities', np.nan)
        
        # Leverage Ratios
        ratios['Debt to Equity'] = balance_sheet.get('Total Liab', 0) / balance_sheet.get('Total Stockholder Equity', np.nan)
        
        # Fill NaN with 0 for cleaner tables
        ratios.fillna(0, inplace=True)
        income_statement.fillna(0, inplace=True)
        balance_sheet.fillna(0, inplace=True)
        cash_flow.fillna(0, inplace=True)

        # --- Real-time Metrics Calculation ---
        ebitda = info.get('ebitda', 0)
        enterprise_value = info.get('enterpriseValue', 0)
        free_cashflow = info.get('freeCashflow', 0)
        debt_to_equity_realtime = info.get('debtToEquity', 0)
        return_on_equity_realtime = info.get('returnOnEquity', 0)

        data = {
            "symbol": symbol,
            "company_name": company_name,
            "current_price": current_price,
            "change": change,
            "change_percent": change_percent,
            "market_cap": market_cap,
            "book_value": book_value,
            "dividend_yield": dividend_yield,
            "pe_ratio": pe_ratio,
            "financials": {
                "ratios": ratios.to_dict('records'),
                "income_statement": income_statement.to_dict('records'),
                "balance_sheet": balance_sheet.to_dict('records'),
                "cash_flow": cash_flow.to_dict('records'),
            },
            "real_time_metrics": {
                "return_on_equity": return_on_equity_realtime,
                "debt_to_equity": debt_to_equity_realtime,
                "free_cashflow": free_cashflow,
                "enterprise_value": enterprise_value,
                "ev_to_ebitda": enterprise_value / ebitda if ebitda else 0,
                "fifty_two_week_high": fifty_two_week_high,
                "fifty_two_week_low": fifty_two_week_low,
            }
        }
        return data

    def create_comprehensive_dashboard(self, data: dict) -> plt.Figure:
        """
        Creates a 2x2 dashboard of key financial charts.

        Args:
            data: The processed financial data dictionary from get_screener_data.

        Returns:
            A matplotlib Figure object containing the charts.
        """
        df_income = pd.DataFrame(data['financials']['income_statement']).set_index('years')
        df_bs = pd.DataFrame(data['financials']['balance_sheet']).set_index('years')
        df_cf = pd.DataFrame(data['financials']['cash_flow']).set_index('years')

        fig, axes = plt.subplots(2, 2, figsize=(18, 12))
        fig.suptitle(f'Financial Health of {data["company_name"]}', fontsize=20, y=1.02)
        
        # Sort index to ensure correct plotting order
        df_income.sort_index(inplace=True)
        df_bs.sort_index(inplace=True)
        df_cf.sort_index(inplace=True)

        # 1. Revenue and Net Income
        ax1 = axes[0, 0]
        ax1.bar(df_income.index, df_income['Total Revenue'] / 1e7, label='Total Revenue (Cr)', color=sns.color_palette("viridis", 2)[0])
        ax1.plot(df_income.index, df_income['Net Income'] / 1e7, label='Net Income (Cr)', marker='o', color='red', linewidth=2)
        ax1.set_title("Revenue & Net Income Trend")
        ax1.set_ylabel("Amount (in Cr)")
        ax1.legend()
        ax1.tick_params(axis='x', rotation=45)

        # 2. Assets vs. Liabilities
        ax2 = axes[0, 1]
        ax2.plot(df_bs.index, df_bs['Total Assets'] / 1e7, label='Total Assets (Cr)', marker='o', linestyle='-', color=sns.color_palette("magma", 2)[0])
        ax2.plot(df_bs.index, df_bs['Total Liab'] / 1e7, label='Total Liabilities (Cr)', marker='^', linestyle='--', color=sns.color_palette("magma", 2)[1])
        ax2.set_title("Assets vs. Liabilities")
        ax2.set_ylabel("Amount (in Cr)")
        ax2.legend()
        ax2.tick_params(axis='x', rotation=45)

        # 3. Cash Flow from Operations
        ax3 = axes[1, 0]
        ax3.bar(df_cf.index, df_cf['Total Cash From Operating Activities'] / 1e7, label='Operating Cash Flow (Cr)', color=sns.color_palette("coolwarm", 1))
        ax3.set_title("Operating Cash Flow")
        ax3.set_ylabel("Amount (in Cr)")
        ax3.axhline(0, color='black', linewidth=0.8, linestyle='--')
        ax3.tick_params(axis='x', rotation=45)

        # 4. Debt to Equity Ratio
        ax4 = axes[1, 1]
        debt_to_equity = df_bs.get('Total Liab', 0) / df_bs.get('Total Stockholder Equity', np.nan)
        debt_to_equity.fillna(0, inplace=True)
        ax4.plot(debt_to_equity.index, debt_to_equity, label='Debt-to-Equity Ratio', marker='s', color='purple')
        ax4.set_title("Debt-to-Equity Ratio")
        ax4.set_ylabel("Ratio")
        ax4.legend()
        ax4.tick_params(axis='x', rotation=45)

        plt.tight_layout(rect=[0, 0, 1, 0.98])
        return fig

