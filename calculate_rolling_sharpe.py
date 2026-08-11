import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Set visual style
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

# Connect to database
db_path = 'bluestock_mf.db'
if not os.path.exists(db_path) and os.path.exists('../bluestock_mf.db'):
    db_path = '../bluestock_mf.db'

conn = sqlite3.connect(db_path)

# Select 5 mutual funds
selected_amfi = [100016, 100033, 102885, 102887, 118632]

# Load daily NAV data
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

# Shorten scheme names for visual clarity on plot
name_map = {
    100016: 'HDFC Top 100 Fund',
    100033: 'HDFC Mid-Cap Opportunities',
    102885: 'UTI Nifty 50 Index Fund',
    102887: 'UTI Flexi Cap Fund',
    118632: 'Nippon India Large Cap Fund'
}
df['fund_label'] = df['amfi_code'].map(name_map)

# Calculate daily historical returns
df['daily_return'] = df.groupby('amfi_code')['nav'].pct_change()

# Calculate rolling 90-day mean, std, and Sharpe ratio using the specified formula:
# (rolling_90_day_mean / rolling_90_day_std) * sqrt(252)
window_size = 90

df['rolling_mean'] = df.groupby('amfi_code')['daily_return'].transform(
    lambda x: x.rolling(window=window_size, min_periods=window_size).mean()
)
df['rolling_std'] = df.groupby('amfi_code')['daily_return'].transform(
    lambda x: x.rolling(window=window_size, min_periods=window_size).std()
)

df['rolling_90d_sharpe'] = (df['rolling_mean'] / df['rolling_std']) * np.sqrt(252)

# Drop initial NaN rows due to 90-day rolling window
df_plot = df.dropna(subset=['rolling_90d_sharpe']).copy()

# Plot the rolling 90-day Sharpe ratio time series
plt.figure(figsize=(12, 6))

for fund_label, group in df_plot.groupby('fund_label'):
    plt.plot(group['date'], group['rolling_90d_sharpe'], label=fund_label, linewidth=2.0)

# Add reference zero line (break-even Sharpe)
plt.axhline(0, color='gray', linestyle='--', linewidth=1, alpha=0.7, label='Zero Sharpe Threshold')

plt.title('Rolling 90-Day Sharpe Ratio Analysis (5 Selected Mutual Funds)', fontsize=14, fontweight='bold', pad=15)
plt.xlabel('Date', fontsize=12)
plt.ylabel('Annualized Sharpe Ratio (90-Day Rolling)', fontsize=12)
plt.legend(title='Mutual Fund Scheme', bbox_to_anchor=(1.02, 1), loc='upper left', frameon=True)
plt.tight_layout()

# Save the figure exactly as rolling_sharpe_chart.png
output_file = 'rolling_sharpe_chart.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')

# Also save to dashboard/exported_charts/ if directory exists
exported_dir = 'dashboard/exported_charts'
if os.path.exists(exported_dir):
    plt.savefig(os.path.join(exported_dir, 'rolling_sharpe_chart.png'), dpi=300, bbox_inches='tight')

print(f"Successfully calculated 90-day rolling Sharpe ratio for {len(selected_amfi)} funds.")
print(f"Saved figure as '{output_file}'.")

# Print summary statistics of rolling Sharpe ratios
summary_stats = df_plot.groupby('fund_label')['rolling_90d_sharpe'].agg(
    ['mean', 'std', 'min', 'max']
).reset_index()
summary_stats.columns = ['Mutual Fund', 'Mean Sharpe', 'Std Dev', 'Min Sharpe', 'Max Sharpe']
print("\n=== ROLLING 90-DAY SHARPE RATIO SUMMARY STATS ===")
print(summary_stats.to_string(index=False))
