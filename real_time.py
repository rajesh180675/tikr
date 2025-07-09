import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Optional, Dict, Any

# --- Best Practice: Use constants for dictionary keys to avoid typos ---
KEY_YEARS = 'years'
KEY_FINANCIALS = 'financials'
KEY_INCOME = 'income_statement'
KEY_BALANCE = 'balance_sheet'
KEY_CASH_FLOW = 'cash_flow'
KEY_RATIOS = 'ratios'

class RealTimeFinancialDashboard:
    """
    A class to fetch, process, and visualize financial data for a given stock symbol
    using the yfinance library.
    """

    def __init__(self):
        """Initializes the dashboard class and sets a professional plot style."""
        sns.set_style("whitegrid")
        plt.rcParams.update({
            'figure.figsize': (12, 6),
            'axes.titlesize': 16,
            'axes.labelsize': 12,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'legend.fontsize': 10
        })

    def _safe_division(self, numerator: pd.Series, denominator: pd.Series) -> pd.Series:
        """
        Performs division safely, returning np.nan where the denominator is zero.
        This prevents 'inf' values or ZeroDivisionError.
        """
        # Replace 0 in the denominator with NaN to avoid errors
        denominator_safe = denominator.replace(0, np.nan)
        return numerator / denominator_safe

    def get_screener_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetches comprehensive financial data for a given NSE stock symbol.

        Args:
            symbol: The NSE stock symbol (e.g., "ITC"). The ".NS" suffix is added automatically.

        Returns:
            A dictionary containing structured financial data, or None if the symbol is invalid
            or data is unavailable.
        """
        if not symbol.upper().endswith('.NS'):
            symbol += '.NS'

        stock = yf.Ticker(symbol)
        
        # --- Improvement 1: Robust check for invalid tickers ---
        # yf.Ticker doesn't fail on invalid symbols, but .info will be empty.
        info = stock.info
        if not info or 'regularMarketPrice' not in info and 'currentPrice' not in info:
            print(f"Error: Could not fetch data for symbol '{symbol}'. It may be an invalid ticker.")
            return None

        # --- Financial Statements (Annual) ---
        # Fetch first, then check for emptiness
        try:
            income_statement = stock.financials.transpose().reset_index()
            balance_sheet = stock.balance_sheet.transpose().reset_index()
            cash_flow = stock.cashflow.transpose().reset_index()
            if income_statement.empty or balance_sheet.empty:
                print(f"Warning: Financial statements are empty for {symbol}.")
                return None # Essential data is missing
        except Exception as e:
            print(f"Could not retrieve financial statements for {symbol}: {e}")
            return None
            
        # Rename columns and format dates
        for df in [income_statement, balance_sheet, cash_flow]:
            df.rename(columns={'index': KEY_YEARS}, inplace=True)
            if KEY_YEARS in df.columns:
                df[KEY_YEARS] = pd.to_datetime(df[KEY_YEARS]).dt.strftime('%Y')

        # --- Key Ratios Calculation ---
        ratios = pd.DataFrame()
        ratios[KEY_YEARS] = income_statement[KEY_YEARS]

        # Use the safe division helper function for robustness
        ratios['Net Profit Margin'] = self._safe_division(income_statement.get('Net Income', 0), income_statement.get('Total Revenue', 0))
        ratios['Return on Equity (ROE)'] = self._safe_division(income_statement.get('Net Income', 0), balance_sheet.get('Total Stockholder Equity', 0))
        ratios['Return on Assets (ROA)'] = self._safe_division(income_statement.get('Net Income', 0), balance_sheet.get('Total Assets', 0))
        ratios['Current Ratio'] = self._safe_division(balance_sheet.get('Total Current Assets', 0), balance_sheet.get('Total Current Liabilities', 0))
        ratios['Debt to Equity'] = self._safe_division(balance_sheet.get('Total Liab', 0), balance_sheet.get('Total Stockholder Equity', 0))
        
        # Fill NaN values with 0 after calculations are done
        for df in [ratios, income_statement, balance_sheet, cash_flow]:
            df.fillna(0, inplace=True)
        
        # --- Assemble Data Dictionary ---
        # Use .get() with default values for safety
        ebitda = info.get('ebitda', 0)
        enterprise_value = info.get('enterpriseValue', 0)

        data = {
            "symbol": symbol,
            "company_name": info.get('longName', 'N/A'),
            "current_price": info.get('currentPrice', info.get('regularMarketPrice', 0)),
            "change": info.get('currentPrice', 0) - info.get('previousClose', 0),
            "change_percent": (info.get('currentPrice', 0) / info.get('previousClose', 1) - 1) * 100,
            "market_cap": info.get('marketCap', 0),
            "book_value": info.get('bookValue', 0),
            "dividend_yield": info.get('dividendYield', 0),
            "pe_ratio": info.get('trailingPE', 0),
            KEY_FINANCIALS: {
                KEY_RATIOS: ratios.to_dict('records'),
                KEY_INCOME: income_statement.to_dict('records'),
                KEY_BALANCE: balance_sheet.to_dict('records'),
                KEY_CASH_FLOW: cash_flow.to_dict('records'),
            },
            "real_time_metrics": {
                "return_on_equity": info.get('returnOnEquity', 0),
                "debt_to_equity": info.get('debtToEquity', 0),
                "free_cashflow": info.get('freeCashflow', 0),
                "enterprise_value": enterprise_value,
                "ev_to_ebitda": enterprise_value / ebitda if ebitda else 0,
                "fifty_two_week_high": info.get('fiftyTwoWeekHigh', 0),
                "fifty_two_week_low": info.get('fiftyTwoWeekLow', 0),
            }
        }
        return data

    def create_comprehensive_dashboard(self, symbol: str) -> Optional[plt.Figure]:
        """
        Creates a 2x2 dashboard of key financial charts for a given symbol.

        Args:
            symbol: The NSE stock symbol (e.g., "ITC").

        Returns:
            A matplotlib Figure object containing the charts, or None if data cannot be fetched.
        """
        # --- Improvement 2: Better Encapsulation ---
        # This method is now self-contained. It fetches its own data.
        data = self.get_screener_data(symbol)
        if not data:
            return None # Return nothing if data fetching failed

        CRORE = 1_00_00_000 
        
        # Load dataframes from the fetched data
        df_income = pd.DataFrame(data[KEY_FINANCIALS][KEY_INCOME]).set_index(KEY_YEARS)
        df_bs = pd.DataFrame(data[KEY_FINANCIALS][KEY_BALANCE]).set_index(KEY_YEARS)
        df_cf = pd.DataFrame(data[KEY_FINANCIALS][KEY_CASH_FLOW]).set_index(KEY_YEARS)
        df_ratios = pd.DataFrame(data[KEY_FINANCIALS][KEY_RATIOS]).set_index(KEY_YEARS)

        fig, axes = plt.subplots(2, 2, figsize=(18, 12))
        fig.suptitle(f'Financial Health of {data["company_name"]}', fontsize=20, y=1.02)
        
        for df in [df_income, df_bs, df_cf, df_ratios]:
            df.sort_index(inplace=True)

        # 1. Revenue and Net Income
        axes[0, 0].bar(df_income.index, df_income['Total Revenue'] / CRORE, label='Total Revenue (Cr)', color='skyblue')
        axes[0, 0].plot(df_income.index, df_income['Net Income'] / CRORE, label='Net Income (Cr)', marker='o', color='crimson', linewidth=2.5)
        axes[0, 0].set_title("Revenue & Net Income Trend")
        axes[0, 0].set_ylabel("Amount (in Cr)")

        # 2. Assets vs. Liabilities
        axes[0, 1].plot(df_bs.index, df_bs['Total Assets'] / CRORE, label='Total Assets (Cr)', marker='o', linestyle='-', color='darkgreen')
        axes[0, 1].plot(df_bs.index, df_bs['Total Liab'] / CRORE, label='Total Liabilities (Cr)', marker='^', linestyle='--', color='orangered')
        axes[0, 1].set_title("Assets vs. Liabilities")
        axes[0, 1].set_ylabel("Amount (in Cr)")

        # 3. Cash Flow from Operations
        op_cash_flow = df_cf['Total Cash From Operating Activities'] / CRORE
        axes[1, 0].bar(op_cash_flow.index, op_cash_flow, label='Operating Cash Flow (Cr)', color=np.where(op_cash_flow < 0, 'salmon', 'seagreen'))
        axes[1, 0].set_title("Operating Cash Flow")
        axes[1, 0].set_ylabel("Amount (in Cr)")
        axes[1, 0].axhline(0, color='black', linewidth=0.8, linestyle='--')

        # 4. Debt to Equity Ratio
        axes[1, 1].plot(df_ratios.index, df_ratios['Debt to Equity'], label='Debt-to-Equity Ratio', marker='s', color='purple')
        axes[1, 1].set_title("Debt-to-Equity Ratio")
        axes[1, 1].set_ylabel("Ratio")

        for ax in axes.flat:
            ax.legend()
            ax.tick_params(axis='x', rotation=45)

        plt.tight_layout(rect=[0, 0, 1, 0.98])
        return fig

# Your excellent __main__ block, now updated to reflect the refactoring
if __name__ == '__main__':
    dashboard = RealTimeFinancialDashboard()
    stock_symbol = "RELIANCE"  # .NS is added automatically

    print(f"Fetching data for {stock_symbol}...")
    
    # --- Improvement 3: The plotting function is now self-sufficient ---
    fig = dashboard.create_comprehensive_dashboard(stock_symbol)
    
    if fig:
        print("Chart generated successfully. Displaying plot...")
        plt.show()
    else:
        print(f"\nCould not generate dashboard for {stock_symbol}. Please check the symbol and try again.")
