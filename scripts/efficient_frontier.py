"""
Markowitz Efficient Frontier Portfolio Optimization Module

Queries SQLite database data/db/bluestock_mf.db for daily historical NAV returns of the top 5
mutual funds with the highest composite scores from fund_scorecard.csv. Computes the annualized 
covariance matrix, mean returns, and uses scipy.optimize to calculate optimal portfolio weights 
that maximize the Sharpe Ratio and minimize portfolio variance.

Outputs optimal percentage allocations to terminal and saves the Efficient Frontier plot to
dashboard/exported_charts/efficient_frontier.png.
"""

import os
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.optimize import minimize

# Workspace & Database Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "db" / "bluestock_mf.db"
SCORECARD_PATH = BASE_DIR / "data" / "processed" / "fund_scorecard.csv"
if not SCORECARD_PATH.exists():
    SCORECARD_PATH = BASE_DIR / "fund_scorecard.csv"

OUTPUT_DIR = BASE_DIR / "dashboard" / "exported_charts"
OUTPUT_FILE = OUTPUT_DIR / "efficient_frontier.png"

# Optimization Hyperparameters
RISK_FREE_RATE = 0.06  # 6.0% Indian G-Sec Benchmark Risk-Free Rate
TRADING_DAYS = 252
NUM_RANDOM_PORTFOLIOS = 5000
RANDOM_SEED = 42


def get_top_5_funds(scorecard_path: Path, db_path: Path) -> pd.DataFrame:
    """
    Retrieves metadata and scheme names for the top 5 funds based on composite rank.

    Parameters:
        scorecard_path (Path): Path to fund_scorecard.csv.
        db_path (Path): Path to SQLite database.

    Returns:
        pd.DataFrame: Top 5 funds DataFrame.
    """
    if not scorecard_path.exists():
        raise FileNotFoundError(f"Scorecard file not found at {scorecard_path}")

    df_score = pd.read_csv(scorecard_path)
    if "final_rank" in df_score.columns:
        df_top5 = df_score.sort_values("final_rank").head(5).copy()
    else:
        df_top5 = df_score.sort_values("composite_score", ascending=False).head(5).copy()

    # Join with dim_fund to get category & short scheme names if available
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        df_dim = pd.read_sql_query("SELECT amfi_code, fund_house, category FROM dim_fund", conn)
        conn.close()
        df_top5 = pd.merge(df_top5, df_dim, on="amfi_code", how="left")

    return df_top5


def load_daily_returns(db_path: Path, amfi_codes: list) -> tuple:
    """
    Extracts historical NAV series for the specified AMFI codes and computes daily returns.

    Parameters:
        db_path (Path): Path to SQLite database.
        amfi_codes (list): List of target AMFI integer scheme codes.

    Returns:
        tuple: (daily_returns_df, scheme_name_mapping)
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found at {db_path}")

    conn = sqlite3.connect(db_path)
    codes_str = ",".join(map(str, amfi_codes))
    query = f"""
        SELECT f.amfi_code, d.scheme_name, f.date, f.nav
        FROM fact_nav f
        JOIN dim_fund d ON f.amfi_code = d.amfi_code
        WHERE f.amfi_code IN ({codes_str})
        ORDER BY f.date ASC
    """
    df_nav = pd.read_sql_query(query, conn)
    conn.close()

    if df_nav.empty:
        raise ValueError("No historical NAV records retrieved for selected top 5 funds.")

    # Shorten scheme names for visual clarity in tables & charts
    scheme_name_map = {}
    for code, group in df_nav.groupby("amfi_code"):
        full_name = group["scheme_name"].iloc[0]
        # Shorten long name strings
        short_name = full_name.split("-")[0].strip() if "-" in full_name else full_name[:25]
        scheme_name_map[code] = short_name

    # Pivot into wide matrix: rows = dates, columns = amfi_code
    df_pivot = df_nav.pivot(index="date", columns="amfi_code", values="nav")
    df_pivot = df_pivot.dropna()

    # Calculate daily percentage returns
    daily_returns = df_pivot.pct_change().dropna()

    # Clean outlier single-day jumps (|return| >= 15%)
    valid_mask = (np.abs(daily_returns) < 0.15).all(axis=1)
    clean_returns = daily_returns[valid_mask].copy()

    return clean_returns, scheme_name_map


def portfolio_performance(weights: np.ndarray, mean_returns: np.ndarray, cov_matrix: np.ndarray) -> tuple:
    """
    Calculates expected portfolio annualized return and annualized volatility.

    Parameters:
        weights (np.ndarray): Portfolio allocation weights vector.
        mean_returns (np.ndarray): Annualized mean return vector.
        cov_matrix (np.ndarray): Annualized covariance matrix.

    Returns:
        tuple: (portfolio_return, portfolio_volatility)
    """
    p_return = np.sum(mean_returns * weights)
    p_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
    return p_return, p_volatility


def negative_sharpe_ratio(
    weights: np.ndarray,
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
    risk_free_rate: float = RISK_FREE_RATE,
) -> float:
    """
    Objective function for SLSQP optimizer to minimize (-Sharpe Ratio).
    """
    p_return, p_vol = portfolio_performance(weights, mean_returns, cov_matrix)
    return -(p_return - risk_free_rate) / p_vol


def minimize_volatility(weights: np.ndarray, cov_matrix: np.ndarray) -> float:
    """
    Objective function to minimize portfolio volatility (Minimum Variance Portfolio).
    """
    return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))


def optimize_max_sharpe(
    mean_returns: np.ndarray, cov_matrix: np.ndarray, risk_free_rate: float = RISK_FREE_RATE
) -> tuple:
    """
    Solves for the optimal Markowitz portfolio weights that maximize Sharpe Ratio.
    """
    num_assets = len(mean_returns)
    args = (mean_returns, cov_matrix, risk_free_rate)
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
    bounds = tuple((0.0, 1.0) for _ in range(num_assets))
    init_guess = num_assets * [1.0 / num_assets]

    result = minimize(
        negative_sharpe_ratio,
        init_guess,
        args=args,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
    )
    if not result.success:
        raise RuntimeError(f"Sharpe optimization failed: {result.message}")

    opt_weights = result.x
    opt_ret, opt_vol = portfolio_performance(opt_weights, mean_returns, cov_matrix)
    opt_sharpe = (opt_ret - risk_free_rate) / opt_vol

    return opt_weights, opt_ret, opt_vol, opt_sharpe


def optimize_min_variance(mean_returns: np.ndarray, cov_matrix: np.ndarray) -> tuple:
    """
    Solves for the Minimum Variance Portfolio weights.
    """
    num_assets = len(mean_returns)
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
    bounds = tuple((0.0, 1.0) for _ in range(num_assets))
    init_guess = num_assets * [1.0 / num_assets]

    result = minimize(
        minimize_volatility,
        init_guess,
        args=(cov_matrix,),
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
    )
    if not result.success:
        raise RuntimeError(f"Minimum Variance optimization failed: {result.message}")

    min_weights = result.x
    min_ret, min_vol = portfolio_performance(min_weights, mean_returns, cov_matrix)
    min_sharpe = (min_ret - RISK_FREE_RATE) / min_vol

    return min_weights, min_ret, min_vol, min_sharpe


def generate_efficient_frontier_curve(
    mean_returns: np.ndarray, cov_matrix: np.ndarray, num_points: int = 100
) -> tuple:
    """
    Computes the Efficient Frontier curve by minimizing portfolio volatility for target returns.
    """
    num_assets = len(mean_returns)
    target_returns = np.linspace(mean_returns.min(), mean_returns.max(), num_points)
    target_volatilities = []
    bounds = tuple((0.0, 1.0) for _ in range(num_assets))
    init_guess = num_assets * [1.0 / num_assets]

    for target in target_returns:
        constraints = (
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            {"type": "eq", "fun": lambda w, r=target: np.sum(mean_returns * w) - r},
        )
        res = minimize(
            minimize_volatility,
            init_guess,
            args=(cov_matrix,),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )
        if res.success:
            target_volatilities.append(res.fun)
        else:
            target_volatilities.append(np.nan)

    return np.array(target_returns), np.array(target_volatilities)


def simulate_random_portfolios(
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
    num_portfolios: int = NUM_RANDOM_PORTFOLIOS,
    seed: int = RANDOM_SEED,
) -> tuple:
    """
    Simulates 5,000 random portfolio weight combinations to populate the Risk-Return space.
    """
    np.random.seed(seed)
    num_assets = len(mean_returns)
    returns = np.zeros(num_portfolios)
    volatilities = np.zeros(num_portfolios)
    sharpe_ratios = np.zeros(num_portfolios)

    for i in range(num_portfolios):
        w = np.random.random(num_assets)
        w /= np.sum(w)

        ret, vol = portfolio_performance(w, mean_returns, cov_matrix)
        sharpe = (ret - RISK_FREE_RATE) / vol

        returns[i] = ret
        volatilities[i] = vol
        sharpe_ratios[i] = sharpe

    return returns, volatilities, sharpe_ratios


def plot_efficient_frontier(
    target_returns: np.ndarray,
    target_volatilities: np.ndarray,
    sim_returns: np.ndarray,
    sim_vols: np.ndarray,
    sim_sharpes: np.ndarray,
    opt_ret: float,
    opt_vol: float,
    opt_sharpe: float,
    min_ret: float,
    min_vol: float,
    asset_names: list,
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
    output_path: Path,
) -> None:
    """
    Plots the Markowitz Efficient Frontier, simulated portfolio scatter, and key optimal markers.
    """
    sns.set_theme(style="whitegrid", palette="deep")
    plt.rcParams.update({"font.sans-serif": "Arial", "font.family": "sans-serif"})

    fig, ax = plt.subplots(figsize=(12, 7))

    # Scatter plot of random portfolios colored by Sharpe ratio
    scatter = ax.scatter(
        sim_vols * 100,
        sim_returns * 100,
        c=sim_sharpes,
        cmap="viridis",
        marker="o",
        s=12,
        alpha=0.45,
        edgecolors="none",
        label="Simulated Portfolios (5,000 Trials)",
    )
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("Annualized Sharpe Ratio (Rf = 6.0%)", fontsize=10, fontweight="bold")

    # Plot individual constituent assets
    asset_vols = np.sqrt(np.diag(cov_matrix))
    for name, ret, vol in zip(asset_names, mean_returns, asset_vols):
        ax.scatter(vol * 100, ret * 100, color="#E11D48", s=60, zorder=5)
        ax.annotate(
            name,
            (vol * 100, ret * 100),
            textcoords="offset points",
            xytext=(6, 6),
            ha="left",
            fontsize=8.5,
            fontweight="bold",
            color="#1E293B",
        )

    # Plot Efficient Frontier Curve
    ax.plot(
        target_volatilities * 100,
        target_returns * 100,
        color="#1E3A8A",
        linestyle="-",
        linewidth=3.0,
        label="Markowitz Efficient Frontier Curve",
        zorder=4,
    )

    # Highlight Maximum Sharpe Ratio Portfolio
    ax.scatter(
        opt_vol * 100,
        opt_ret * 100,
        color="#F59E0B",
        marker="*",
        s=280,
        edgecolors="#000000",
        linewidths=1.2,
        label=f"Max Sharpe Ratio ({opt_sharpe:.2f})\nRet: {opt_ret*100:.2f}%, Vol: {opt_vol*100:.2f}%",
        zorder=6,
    )

    # Highlight Minimum Variance Portfolio
    ax.scatter(
        min_vol * 100,
        min_ret * 100,
        color="#10B981",
        marker="D",
        s=120,
        edgecolors="#000000",
        linewidths=1.0,
        label=f"Min Variance Portfolio\nRet: {min_ret*100:.2f}%, Vol: {min_vol*100:.2f}%",
        zorder=6,
    )

    ax.set_title(
        "Markowitz Efficient Frontier Portfolio Optimization\nTop 5 Composite Mutual Fund Asset Universe",
        fontsize=14,
        fontweight="bold",
        pad=15,
        color="#0F172A",
    )
    ax.set_xlabel("Annualized Portfolio Volatility / Standard Deviation (%)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Expected Annualized Return (%)", fontsize=11, fontweight="bold")
    ax.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=9.5)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"\nSuccessfully saved Efficient Frontier chart to: {output_path}")


def main() -> None:
    """
    Main execution pipeline for Markowitz Efficient Frontier optimization.
    """
    print("=" * 80)
    print("MARKOWITZ EFFICIENT FRONTIER PORTFOLIO OPTIMIZER")
    print("=" * 80)
    print(f"Database Path : {DB_PATH}")
    print(f"Scorecard Path: {SCORECARD_PATH}")

    # 1. Retrieve Top 5 funds
    df_top5 = get_top_5_funds(SCORECARD_PATH, DB_PATH)
    amfi_codes = df_top5["amfi_code"].tolist()
    print(f"\nTop 5 Composite Funds Identified:")
    for idx, row in df_top5.iterrows():
        rank = row.get("final_rank", idx + 1)
        score = row.get("composite_score", 0.0)
        print(f"  Rank #{rank:02d} | AMFI: {row['amfi_code']} | Score: {score:.1f} | {row['scheme_name']}")

    # 2. Extract daily returns matrix
    daily_returns, scheme_map = load_daily_returns(DB_PATH, amfi_codes)
    asset_codes = list(daily_returns.columns)
    asset_names = [scheme_map[code] for code in asset_codes]

    # Compute annualized mean returns and covariance matrix
    mean_returns_daily = daily_returns.mean()
    mean_returns_ann = (mean_returns_daily * TRADING_DAYS).values
    cov_matrix_ann = (daily_returns.cov() * TRADING_DAYS).values

    # 3. Solve for Max Sharpe Portfolio
    opt_weights, opt_ret, opt_vol, opt_sharpe = optimize_max_sharpe(mean_returns_ann, cov_matrix_ann, RISK_FREE_RATE)

    # 4. Solve for Min Variance Portfolio
    min_weights, min_ret, min_vol, min_sharpe = optimize_min_variance(mean_returns_ann, cov_matrix_ann)

    # 5. Output Optimal Allocation Table to Terminal
    print("\n" + "=" * 80)
    print("OPTIMAL PORTFOLIO ASSET ALLOCATIONS (MAX SHARPE RATIO)")
    print("=" * 80)
    print(f"{'AMFI Code':<10} | {'Scheme Short Name':<30} | {'Opt Weight (%)':<15} | {'Min Var Weight (%)':<18}")
    print("-" * 80)
    for code, name, w_opt, w_min in zip(asset_codes, asset_names, opt_weights, min_weights):
        print(f"{code:<10} | {name:<30} | {w_opt*100:>14.2f}% | {w_min*100:>17.2f}%")
    print("-" * 80)

    print("\nOptimal Max Sharpe Portfolio Performance Metrics:")
    print(f"  Expected Annual Return : {opt_ret*100:.2f}%")
    print(f"  Annualized Volatility  : {opt_vol*100:.2f}%")
    print(f"  Sharpe Ratio (Rf=6.0%) : {opt_sharpe:.4f}")

    print("\nMinimum Variance Portfolio Performance Metrics:")
    print(f"  Expected Annual Return : {min_ret*100:.2f}%")
    print(f"  Annualized Volatility  : {min_vol*100:.2f}%")
    print(f"  Sharpe Ratio (Rf=6.0%) : {min_sharpe:.4f}")

    # 6. Generate Efficient Frontier Curve & Random Portfolios
    print(f"\nTracing Efficient Frontier curve and simulating {NUM_RANDOM_PORTFOLIOS:,} random portfolios...")
    target_returns, target_vols = generate_efficient_frontier_curve(mean_returns_ann, cov_matrix_ann)
    sim_rets, sim_vols, sim_sharpes = simulate_random_portfolios(mean_returns_ann, cov_matrix_ann)

    # 7. Plot and export visualization
    plot_efficient_frontier(
        target_returns=target_returns,
        target_volatilities=target_vols,
        sim_returns=sim_rets,
        sim_vols=sim_vols,
        sim_sharpes=sim_sharpes,
        opt_ret=opt_ret,
        opt_vol=opt_vol,
        opt_sharpe=opt_sharpe,
        min_ret=min_ret,
        min_vol=min_vol,
        asset_names=asset_names,
        mean_returns=mean_returns_ann,
        cov_matrix=cov_matrix_ann,
        output_path=OUTPUT_FILE,
    )

    print("=" * 80)
    print("MARKOWITZ EFFICIENT FRONTIER OPTIMIZATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
