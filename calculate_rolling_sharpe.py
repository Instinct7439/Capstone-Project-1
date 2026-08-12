"""
Rolling Sharpe Ratio Analytics Module

Calculates the 90-day rolling annualized Sharpe ratio for selected mutual funds
and generates a time-series plot exported to rolling_sharpe_chart.png.
"""

import os
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


def calculate_rolling_sharpe(db_path: str = 'bluestock_mf.db') -> pd.DataFrame:
    """
    Computes rolling 90-day annualized Sharpe ratio for 5 selected mutual funds.

    Parameters:
        db_path (str): File path to SQLite database.

    Returns:
        pd.DataFrame: Processed DataFrame containing rolling Sharpe statistics.
    """
    if not os.path.exists(db_path) and os.path.exists('../bluestock_mf.db'):
        db_path = '../bluestock_mf.db'

    conn = sqlite3.connect(db_path)
    selected_amfi = [100016, 100033, 102885, 102887, 118632]

    query = f"""
        SELECT f.amfi_code, d.scheme_name, f.date, f.nav
        FROM fact_nav f
        JOIN dim_fund d ON f.amfi_code = d.amfi_code
        WHERE f.amfi_code IN ({','.join(map(str, selected_amfi))})
        ORDER BY f.amfi_code, f.date
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df['date'] = pd.to_datetime(df['date'])

    name_map = {
        100016: 'HDFC Top 100 Fund',
        100033: 'HDFC Mid-Cap Opportunities',
        102885: 'UTI Nifty 50 Index Fund',
        102887: 'UTI Flexi Cap Fund',
        118632: 'Nippon India Large Cap Fund'
    }
    df['fund_label'] = df['amfi_code'].map(name_map)
    df['daily_return'] = df.groupby('amfi_code')['nav'].pct_change()

    window_size = 90
    df['rolling_mean'] = df.groupby('amfi_code')['daily_return'].transform(
        lambda x: x.rolling(window=window_size, min_periods=window_size).mean()
    )
    df['rolling_std'] = df.groupby('amfi_code')['daily_return'].transform(
        lambda x: x.rolling(window=window_size, min_periods=window_size).std()
    )

    df['rolling_90d_sharpe'] = (df['rolling_mean'] / df['rolling_std']) * np.sqrt(252)
    return df.dropna(subset=['rolling_90d_sharpe']).copy()


def plot_rolling_sharpe(df_plot: pd.DataFrame) -> None:
    """
    Generates and exports the rolling 90-day Sharpe ratio time-series plot.

    Parameters:
        df_plot (pd.DataFrame): DataFrame containing rolling Sharpe time series data.
    """
    sns.set_theme(style="whitegrid", palette="tab10")
    plt.rcParams.update({
        'font.sans-serif': 'Arial',
        'font.family': 'sans-serif',
        'figure.titlesize': 14,
        'axes.labelsize': 11,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'figure.autolayout': True
    })

    plt.figure(figsize=(12, 6))

    for fund_label, group in df_plot.groupby('fund_label'):
        plt.plot(group['date'], group['rolling_90d_sharpe'], label=fund_label, linewidth=2.0)

    plt.axhline(0, color='gray', linestyle='--', linewidth=1, alpha=0.7, label='Zero Sharpe Threshold')

    plt.title('Rolling 90-Day Sharpe Ratio Analysis (5 Selected Mutual Funds)', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Annualized Sharpe Ratio (90-Day Rolling)', fontsize=12)
    plt.legend(title='Mutual Fund Scheme', bbox_to_anchor=(1.02, 1), loc='upper left', frameon=True)
    plt.tight_layout()

    output_file = 'rolling_sharpe_chart.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')

    exported_dir = 'dashboard/exported_charts'
    if os.path.exists(exported_dir):
        plt.savefig(os.path.join(exported_dir, 'rolling_sharpe_chart.png'), dpi=300, bbox_inches='tight')

    print(f"Successfully calculated 90-day rolling Sharpe ratio.")
    print(f"Saved figure as '{output_file}'.")


def main() -> None:
    """
    Executes the 90-day rolling Sharpe ratio calculation and plots the results.
    """
    df_plot = calculate_rolling_sharpe()
    plot_rolling_sharpe(df_plot)


if __name__ == "__main__":
    main()

