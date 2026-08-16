"""
Monte Carlo Simulation Module — 5-Year NAV Path Forecasting

Extracts historical NAV data for the top-performing equity mutual fund over the last 3 years from 
data/db/bluestock_mf.db, models logarithmic returns, drift, and volatility, and simulates 10,000 
Geometric Brownian Motion (GBM) random walk price paths over 1,260 trading days (5 years).

Exports the uncertainty bands chart to dashboard/exported_charts/monte_carlo_5yr.png.
"""

import os
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Workspace & Database Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "db" / "bluestock_mf.db"
OUTPUT_DIR = BASE_DIR / "dashboard" / "exported_charts"
OUTPUT_FILE = OUTPUT_DIR / "monte_carlo_5yr.png"

# Simulation Hyperparameters
NUM_SIMULATIONS = 10000
FORECAST_DAYS = 1260  # 5 years * 252 trading days/year
RANDOM_SEED = 42


def get_top_equity_fund(db_path: Path) -> dict:
    """
    Queries SQLite database for the top-performing equity fund based on 3-year CAGR.

    Parameters:
        db_path (Path): Path to SQLite database file.

    Returns:
        dict: Fund details (amfi_code, scheme_name, return_3yr_pct, sharpe_ratio).
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")

    conn = sqlite3.connect(db_path)
    query = """
        SELECT f.amfi_code, d.scheme_name, f.return_3yr_pct, f.sharpe_ratio
        FROM fact_performance f
        JOIN dim_fund d ON f.amfi_code = d.amfi_code
        WHERE d.category = 'Equity'
        ORDER BY f.return_3yr_pct DESC
        LIMIT 1
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        raise ValueError("No equity fund records found in fact_performance table.")

    row = df.iloc[0]
    return {
        "amfi_code": int(row["amfi_code"]),
        "scheme_name": str(row["scheme_name"]),
        "return_3yr_pct": float(row["return_3yr_pct"]),
        "sharpe_ratio": float(row["sharpe_ratio"]),
    }


def load_fund_nav_history(db_path: Path, amfi_code: int) -> pd.DataFrame:
    """
    Extracts daily historical NAV time-series for the specified AMFI code.

    Parameters:
        db_path (Path): Path to SQLite database.
        amfi_code (int): AMFI mutual fund identifier.

    Returns:
        pd.DataFrame: DataFrame containing date and nav columns.
    """
    conn = sqlite3.connect(db_path)
    query = """
        SELECT date, nav
        FROM fact_nav
        WHERE amfi_code = ?
        ORDER BY date ASC
    """
    df = pd.read_sql_query(query, conn, params=(amfi_code,))
    conn.close()

    if df.empty:
        raise ValueError(f"No NAV records found for AMFI code {amfi_code}")

    df["date"] = pd.to_datetime(df["date"])
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna(subset=["nav"])
    return df


def calculate_return_statistics(df_nav: pd.DataFrame) -> tuple:
    """
    Computes daily logarithmic returns, mean drift, daily standard deviation, and GBM drift.

    Parameters:
        df_nav (pd.DataFrame): NAV history DataFrame.

    Returns:
        tuple: (daily_mean, daily_std, gbm_drift, clean_nav_series)
    """
    nav_series = df_nav["nav"].copy()
    log_returns = np.log(nav_series / nav_series.shift(1)).dropna()

    # Filter out extreme single-day jump anomalies if any (|return| >= 15%)
    clean_log_returns = log_returns[np.abs(log_returns) < 0.15]

    daily_mean = clean_log_returns.mean()
    daily_std = clean_log_returns.std()

    # Geometric Brownian Motion drift correction: mu - 0.5 * sigma^2
    gbm_drift = daily_mean - (0.5 * (daily_std ** 2))

    return daily_mean, daily_std, gbm_drift, clean_log_returns


def run_monte_carlo_simulation(
    initial_nav: float,
    gbm_drift: float,
    daily_std: float,
    num_simulations: int = NUM_SIMULATIONS,
    forecast_days: int = FORECAST_DAYS,
    seed: int = RANDOM_SEED,
) -> np.ndarray:
    """
    Simulates random walk price trajectories using Geometric Brownian Motion (GBM).

    Parameters:
        initial_nav (float): Starting NAV price S_0.
        gbm_drift (float): Daily GBM drift parameter.
        daily_std (float): Daily volatility standard deviation parameter.
        num_simulations (int): Number of Monte Carlo path trials (10,000).
        forecast_days (int): Number of future trading days (1,260 days = 5 years).
        seed (int): Random seed for reproducibility.

    Returns:
        np.ndarray: Simulated price matrix of shape (forecast_days + 1, num_simulations).
    """
    np.random.seed(seed)

    # Generate random normal shocks Z ~ N(0, 1)
    random_shocks = np.random.normal(0, 1, (forecast_days, num_simulations))

    # Calculate daily exponential growth multipliers
    daily_multipliers = np.exp(gbm_drift + daily_std * random_shocks)

    # Initialize price matrix with starting initial NAV
    price_paths = np.zeros((forecast_days + 1, num_simulations))
    price_paths[0] = initial_nav

    # Compute cumulative product across time steps
    price_paths[1:] = initial_nav * np.cumprod(daily_multipliers, axis=0)

    return price_paths


def plot_and_export_simulation(
    price_paths: np.ndarray,
    fund_info: dict,
    output_path: Path,
    num_sample_paths: int = 100,
) -> None:
    """
    Plots the Monte Carlo simulation paths with 5th, 50th, and 95th percentile uncertainty bands.

    Parameters:
        price_paths (np.ndarray): Simulated price matrix.
        fund_info (dict): Fund metadata.
        output_path (Path): Destination PNG file path.
        num_sample_paths (int): Number of individual trajectory lines to visualize.
    """
    sns.set_theme(style="whitegrid", palette="deep")
    plt.rcParams.update(
        {
            "font.sans-serif": "Arial",
            "font.family": "sans-serif",
            "figure.autolayout": True,
        }
    )

    forecast_days = price_paths.shape[0] - 1
    trading_days = np.arange(forecast_days + 1)

    # Calculate percentiles across paths at each time step
    p5 = np.percentile(price_paths, 5, axis=1)
    p50 = np.percentile(price_paths, 50, axis=1)
    p95 = np.percentile(price_paths, 95, axis=1)

    initial_nav = price_paths[0, 0]
    final_p5 = p5[-1]
    final_p50 = p50[-1]
    final_p95 = p95[-1]

    fig, ax = plt.subplots(figsize=(13, 7))

    # Plot sample of individual simulation trajectories
    sample_indices = np.random.choice(price_paths.shape[1], size=num_sample_paths, replace=False)
    for idx in sample_indices:
        ax.plot(trading_days, price_paths[:, idx], color="#94A3B8", alpha=0.12, linewidth=0.8)

    # Shaded Uncertainty Band (5th to 95th percentile)
    ax.fill_between(
        trading_days,
        p5,
        p95,
        color="#3B82F6",
        alpha=0.18,
        label="90% Confidence Interval (5th – 95th Percentile)",
    )

    # Highlight Percentile Lines
    ax.plot(trading_days, p95, color="#10B981", linestyle="--", linewidth=2.2, label=f"95th Percentile (Optimistic: ₹{final_p95:.2f})")
    ax.plot(trading_days, p50, color="#1E3A8A", linestyle="-", linewidth=2.8, label=f"50th Percentile (Median Projection: ₹{final_p50:.2f})")
    ax.plot(trading_days, p5, color="#EF4444", linestyle="--", linewidth=2.2, label=f"5th Percentile (Pessimistic: ₹{final_p5:.2f})")

    # Titles & Labels
    scheme_label = fund_info["scheme_name"]
    cagr_label = fund_info["return_3yr_pct"]
    ax.set_title(
        f"Monte Carlo 5-Year NAV Path Simulation (10,000 Paths)\nTop Equity Scheme: {scheme_label} (3-Yr CAGR: {cagr_label:.2f}%)",
        fontsize=14,
        fontweight="bold",
        pad=15,
        color="#0F172A",
    )
    ax.set_xlabel("Trading Days (Next 5 Years / 1,260 Days)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Projected NAV (INR)", fontsize=11, fontweight="bold")

    # Legend & Metrics Text Box
    ax.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=10)

    stats_text = (
        f"Initial NAV: ₹{initial_nav:.2f}\n"
        f"Simulations: {NUM_SIMULATIONS:,}\n"
        f"Horizon: 5 Years ({FORECAST_DAYS} Days)\n"
        f"── Projected NAVs ──\n"
        f"95th %ile: ₹{final_p95:.2f}\n"
        f"50th %ile: ₹{final_p50:.2f}\n"
        f"5th  %ile: ₹{final_p5:.2f}"
    )
    ax.text(
        0.98,
        0.04,
        stats_text,
        transform=ax.transAxes,
        fontsize=9.5,
        verticalalignment="bottom",
        horizontalalignment="right",
        bbox=dict(boxstyle="round,pad=0.6", facecolor="#F8FAFC", edgecolor="#CBD5E1", alpha=0.95),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Successfully saved plot to: {output_path}")


def main() -> None:
    """
    Executes the end-to-end Monte Carlo simulation pipeline.
    """
    print("=" * 80)
    print("MONTE CARLO 5-YEAR NAV SIMULATION ENGINE")
    print("=" * 80)
    print(f"Database Path : {DB_PATH}")

    # 1. Retrieve top equity fund
    fund_info = get_top_equity_fund(DB_PATH)
    amfi_code = fund_info["amfi_code"]
    scheme_name = fund_info["scheme_name"]
    return_3yr = fund_info["return_3yr_pct"]

    print(f"\nTop Performing Equity Fund Selected:")
    print(f"  AMFI Code   : {amfi_code}")
    print(f"  Scheme Name : {scheme_name}")
    print(f"  3-Year Return: {return_3yr:.2f}%")

    # 2. Extract NAV history
    df_nav = load_fund_nav_history(DB_PATH, amfi_code)
    print(f"  Historical NAV Records Loaded: {len(df_nav)} rows")

    # Use latest valid NAV as starting price S_0
    initial_nav = df_nav["nav"].iloc[-1]
    # If latest single point is an anomaly vs 30-day mean, pick clean latest valid NAV
    if len(df_nav) > 30 and abs(initial_nav - df_nav["nav"].iloc[-30:].mean()) > (0.5 * df_nav["nav"].iloc[-30:].mean()):
        initial_nav = df_nav["nav"].iloc[-2]

    # 3. Calculate returns, drift, volatility
    daily_mean, daily_std, gbm_drift, clean_returns = calculate_return_statistics(df_nav)
    ann_return = daily_mean * 252 * 100
    ann_vol = daily_std * np.sqrt(252) * 100

    print(f"\nQuantitative Modeling Parameters:")
    print(f"  Initial Price S_0   : Rs. {initial_nav:.2f}")
    print(f"  Daily Return Mean   : {daily_mean:.6f} ({ann_return:.2f}% Annualized)")
    print(f"  Daily Volatility    : {daily_std:.6f} ({ann_vol:.2f}% Annualized Volatility)")
    print(f"  GBM Daily Drift     : {gbm_drift:.6f}")

    # 4. Run 10,000 Monte Carlo Simulations
    print(f"\nExecuting {NUM_SIMULATIONS:,} random walk price paths over {FORECAST_DAYS} trading days (5 years)...")
    price_paths = run_monte_carlo_simulation(
        initial_nav=initial_nav,
        gbm_drift=gbm_drift,
        daily_std=daily_std,
        num_simulations=NUM_SIMULATIONS,
        forecast_days=FORECAST_DAYS,
    )

    # 5. Extract final percentile statistics
    p5 = np.percentile(price_paths[-1], 5)
    p50 = np.percentile(price_paths[-1], 50)
    p95 = np.percentile(price_paths[-1], 95)

    print("\n5-Year Forecast Results (10,000 Paths):")
    print(f"  Pessimistic Case ( 5th %ile) : Rs. {p5:.2f} ({(p5/initial_nav - 1)*100:+.2f}%)")
    print(f"  Median Case      (50th %ile) : Rs. {p50:.2f} ({(p50/initial_nav - 1)*100:+.2f}%)")
    print(f"  Optimistic Case  (95th %ile) : Rs. {p95:.2f} ({(p95/initial_nav - 1)*100:+.2f}%)")

    # 6. Plot and export visualization
    plot_and_export_simulation(price_paths, fund_info, OUTPUT_FILE)

    print("=" * 80)
    print("MONTE CARLO SIMULATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
