# real_time.py

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Optional, Dict, Any

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
        """
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
        stock_symbol = symbol.upper()
        if not stock_symbol.endswith('.NS'):
            stock_symbol += '.NS'

        stock = yf.Ticker(stock_symbol)
        info = stock.info
        
        if not info or ('regularMarketPrice' not in info and 'currentPrice' not in info):
            return None

        try:
            income_statement = stock.financials.transpose().reset_index()
            balance_sheet = stock.balance_sheet.transpose().reset_index()
            cash_flow = stock.cashflow.transpose().reset_index()
            if income_statement.empty or balance_sheet.empty:
                return None
        except Exception:
            return None
            
        for df in [income_statement, balance_sheet, cash_flow]:
            df.rename(columns={'index': 'years'}, inplace=True)
            if 'years' in df.columns:
                df['years'] = pd.to_datetime(df['years']).dt.strftime('%Y')

        ratios = pd.DataFrame({'years': income_statement['years']})
        ratios['Net Profit Margin'] = self._safe_division(income_statement.get('Net Income', 0), income_statement.get('Total Revenue', 0))
        ratios['Return on Equity (ROE)'] = self._safe_division(income_statement.get('Net Income', 0), balance_sheet.get('Total Stockholder Equity', 0))
        ratios['Return on Assets (ROA)'] = self._safe_division(income_statement.get('Net Income', 0), balance_sheet.get('Total Assets', 0))
        ratios['Current Ratio'] = self._safe_division(balance_sheet.get('Total Current Assets', 0), balance_sheet.get('Total Current Liabilities', 0))
        ratios['Debt to Equity'] = self._safe_division(balance_sheet.get('Total Liab', 0), balance_sheet.get('Total Stockholder Equity', 0))
        
        for df in [ratios, income_statement, balance_sheet, cash_flow]:
            df.fillna(0, inplace=True)
        
        ebitda = info.get('ebitda', 0)
        enterprise_value = info.get('enterpriseValue', 0)
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
        prev_close = info.get('previousClose', current_price) # Fallback to current price if no prev_close

        data = {
            "symbol": stock_symbol,
            "company_name": info.get('longName', 'N/A'),
            "current_price": current_price,
            "change": current_price - prev_close,
            "change_percent": ((current_price / prev_close) - 1) * 100 if prev_close else 0,
            "market_cap": info.get('marketCap', 0),
            "book_value": info.get('bookValue', 0),
            "dividend_yield": info.get('dividendYield', 0),
            "pe_ratio": info.get('trailingPE', 0),
            "financials": {
                "ratios": ratios.to_dict('records'),
                "income_statement": income_statement.to_dict('records'),
                "balance_sheet": balance_sheet.to_dict('records'),
                "cash_flow": cash_flow.to_dict('records'),
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
        This method is now self-contained and fetches its own data.

        Args:
            symbol: The NSE stock symbol (e.g., "ITC").

        Returns:
            A matplotlib Figure object containing the charts, or None if data cannot be fetched.
        """
        data = self.get_screener_data(symbol)
        if not data:
            return None 

        CRORE = 1_00_00_000 
        
        try:
            df_income = pd.DataFrame(data['financials']['income_statement']).set_index('years')
            df_bs = pd.DataFrame(data['financials']['balance_sheet']).set_index('years')
            df_cf = pd.DataFrame(data['financials']['cash_flow']).set_index('years')
            df_ratios = pd.DataFrame(data['financials']['ratios']).set_index('years')
        except KeyError:
            return None

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
        colors = np.where(op_cash_flow < 0, 'salmon', 'seagreen')
        axes[1, 0].bar(op_cash_flow.index, op_cash_flow, label='Operating Cash Flow (Cr)', color=colors)
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
