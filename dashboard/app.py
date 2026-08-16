"""
Bluestock Mutual Fund Analytics — Enterprise Quantitative Financial Dashboard

Enterprise-grade Streamlit & Plotly dashboard connecting to data/db/bluestock_mf.db 
and data/processed/fund_scorecard.csv. Features dark terminal aesthetics, dynamic sidebar 
filtering, Executive Overview Treemaps, Quantitative Risk (Rolling Sharpe, Alpha-Beta 
Quadrants, 95% VaR), 1,000-path Monte Carlo 5-Year Simulations, SciPy Markowitz Efficient 
Frontier with CAL, and searchable Fund Scorecard CSV exports.
"""

import os
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.optimize import minimize
import streamlit as st

# Streamlit Page Setup
st.set_page_config(
    page_title="Bluestock Quant Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Workspace Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "db" / "bluestock_mf.db"
SCORECARD_PATH = BASE_DIR / "data" / "processed" / "fund_scorecard.csv"
if not SCORECARD_PATH.exists():
    SCORECARD_PATH = BASE_DIR / "fund_scorecard.csv"

# Global Financial Hyperparameters
RISK_FREE_RATE = 0.06  # 6.0% Indian G-Sec Benchmark
TRADING_DAYS = 252

# Custom Dark Terminal CSS Styling
st.markdown(
    """
    <style>
    /* Global App Dark Theme */
    .stApp {
        background-color: #0E1117;
        color: #E2E8F0;
    }
    
    /* Header Typography */
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        background: linear-gradient(90deg, #00F2FE 0%, #4FACFE 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    .sub-title {
        font-size: 1.05rem;
        color: #94A3B8;
        margin-bottom: 1.5rem;
    }
    
    /* Metric Cards */
    .metric-container {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    
    .metric-label {
        font-size: 0.8rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
        margin-bottom: 0.3rem;
    }
    
    .metric-val {
        font-size: 1.4rem;
        font-weight: 700;
        color: #F8FAFC;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .metric-sub {
        font-size: 0.8rem;
        color: #38BDF8;
        margin-top: 0.2rem;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #0E1117;
        border-bottom: 1px solid #334155;
    }

    .stTabs [data-baseweb="tab"] {
        height: 48px;
        white-space: pre;
        border-radius: 6px 6px 0 0;
        padding: 0 16px;
        font-weight: 600;
        color: #94A3B8;
        background-color: #1E293B;
    }

    .stTabs [aria-selected="true"] {
        color: #00F2FE !important;
        background-color: #0F172A !important;
        border-bottom: 2px solid #00F2FE !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# DATA LAYER & CACHING
# ==============================================================================

@st.cache_data(show_spinner=False)
def load_master_data(db_path: Path) -> pd.DataFrame:
    """
    Loads unified scheme performance and dimension metadata from SQLite DB.
    """
    if not db_path.exists():
        st.error(f"Database file not found at {db_path}. Run `python scripts/etl_pipeline.py` first.")
        return pd.DataFrame()

    conn = sqlite3.connect(db_path)
    query = """
        SELECT 
            d.amfi_code,
            d.scheme_name,
            d.fund_house,
            d.category,
            d.sub_category,
            d.risk_category,
            p.return_1yr_pct,
            p.return_3yr_pct,
            p.return_5yr_pct,
            p.alpha,
            p.beta,
            p.sharpe_ratio,
            p.sortino_ratio,
            p.std_dev_ann_pct,
            p.max_drawdown_pct,
            p.aum_crore,
            p.expense_ratio_pct
        FROM dim_fund d
        LEFT JOIN fact_performance p ON d.amfi_code = p.amfi_code
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


@st.cache_data(show_spinner=False)
def load_total_inflows(db_path: Path) -> float:
    """
    Computes total transaction inflows in INR from fact_transactions.
    """
    if not db_path.exists():
        return 0.0
    conn = sqlite3.connect(db_path)
    val = conn.execute("SELECT SUM(amount_inr) FROM fact_transactions").fetchone()[0]
    conn.close()
    return float(val) if val else 0.0


@st.cache_data(show_spinner=False)
def load_nav_history_df(db_path: Path, amfi_codes: tuple) -> pd.DataFrame:
    """
    Loads daily historical NAV data for given tuple of AMFI codes.
    """
    if not db_path.exists() or not amfi_codes:
        return pd.DataFrame()

    conn = sqlite3.connect(db_path)
    placeholders = ",".join(map(str, amfi_codes))
    query = f"""
        SELECT f.amfi_code, d.scheme_name, f.date, f.nav
        FROM fact_nav f
        JOIN dim_fund d ON f.amfi_code = d.amfi_code
        WHERE f.amfi_code IN ({placeholders})
        ORDER BY f.date ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


@st.cache_data(show_spinner=False)
def load_scorecard_dataset(scorecard_path: Path) -> pd.DataFrame:
    """
    Loads the composite fund scorecard CSV.
    """
    if not scorecard_path.exists():
        return pd.DataFrame()
    return pd.read_csv(scorecard_path)


# ==============================================================================
# HELPER MATHEMATICAL & QUANTITATIVE FUNCTIONS
# ==============================================================================

def compute_rolling_sharpe(df_nav: pd.DataFrame, window: int = 90) -> pd.DataFrame:
    """Calculates 90-day rolling Sharpe ratio time series."""
    if df_nav.empty:
        return pd.DataFrame()

    df = df_nav.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["daily_return"] = df.groupby("amfi_code")["nav"].pct_change()

    # Filter out extreme single-day jump anomalies
    df = df[np.abs(df["daily_return"]) < 0.15].copy()

    df["rolling_mean"] = df.groupby("amfi_code")["daily_return"].transform(
        lambda x: x.rolling(window=window, min_periods=window).mean()
    )
    df["rolling_std"] = df.groupby("amfi_code")["daily_return"].transform(
        lambda x: x.rolling(window=window, min_periods=window).std()
    )

    df["rolling_sharpe"] = (df["rolling_mean"] / df["rolling_std"]) * np.sqrt(252)
    return df.dropna(subset=["rolling_sharpe"]).copy()


def run_monte_carlo_gbm(
    initial_nav: float, daily_mean: float, daily_std: float, num_paths: int = 1000, num_days: int = 1260, seed: int = 42
) -> np.ndarray:
    """Simulates 1,000 Geometric Brownian Motion (GBM) random walk price paths."""
    np.random.seed(seed)
    gbm_drift = daily_mean - 0.5 * (daily_std ** 2)
    random_shocks = np.random.normal(0, 1, (num_days, num_paths))
    daily_multipliers = np.exp(gbm_drift + daily_std * random_shocks)

    paths = np.zeros((num_days + 1, num_paths))
    paths[0] = initial_nav
    paths[1:] = initial_nav * np.cumprod(daily_multipliers, axis=0)
    return paths


def optimize_portfolio(mean_returns: np.ndarray, cov_matrix: np.ndarray, risk_free_rate: float = RISK_FREE_RATE):
    """Calculates Max Sharpe and Minimum Variance portfolios using SciPy."""
    num_assets = len(mean_returns)
    init_guess = num_assets * [1.0 / num_assets]
    bounds = tuple((0.0, 1.0) for _ in range(num_assets))
    eq_constraint = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}

    # Max Sharpe
    def neg_sharpe(w):
        p_ret = np.sum(mean_returns * w)
        p_vol = np.sqrt(np.dot(w.T, np.dot(cov_matrix, w)))
        return -(p_ret - risk_free_rate) / p_vol

    res_sharpe = minimize(neg_sharpe, init_guess, method="SLSQP", bounds=bounds, constraints=eq_constraint)

    # Min Var
    def min_vol(w):
        return np.sqrt(np.dot(w.T, np.dot(cov_matrix, w)))

    res_minvar = minimize(min_vol, init_guess, method="SLSQP", bounds=bounds, constraints=eq_constraint)

    return res_sharpe.x, res_minvar.x


# ==============================================================================
# MAIN APPLICATION LIFE CYCLE
# ==============================================================================

def main():
    # Header Title
    st.markdown('<div class="main-title">Bluestock Quant Terminal</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Institutional Mutual Fund Quantitative Analytics & Portfolio Optimization Engine</div>',
        unsafe_allow_html=True,
    )

    # Load Master Data
    df_master = load_master_data(DB_PATH)
    if df_master.empty:
        st.stop()

    total_inflows_inr = load_total_inflows(DB_PATH)

    # Sidebar Controls
    st.sidebar.markdown("### 🎛️ Terminal Controls")
    
    categories = sorted(df_master["category"].dropna().unique())
    fund_houses = sorted(df_master["fund_house"].dropna().unique())

    selected_categories = st.sidebar.multiselect("Asset Category", options=categories, default=categories)
    selected_fund_houses = st.sidebar.multiselect("Fund House (AMC)", options=fund_houses, default=fund_houses)

    # Apply Sidebar Filters
    filtered_df = df_master.copy()
    if selected_categories:
        filtered_df = filtered_df[filtered_df["category"].isin(selected_categories)]
    if selected_fund_houses:
        filtered_df = filtered_df[filtered_df["fund_house"].isin(selected_fund_houses)]

    filtered_amfi_codes = filtered_df["amfi_code"].tolist()

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Filtered Schemes**: `{len(filtered_amfi_codes)} / {len(df_master)}`")

    # App Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "📊 Executive Overview",
            "📈 Risk & Performance",
            "🎲 Monte Carlo Simulation",
            "⚖️ Efficient Frontier",
            "🏆 Scorecard & Recommender",
        ]
    )

    # ==========================================================================
    # TAB 1: EXECUTIVE OVERVIEW
    # ==========================================================================
    with tab1:
        st.markdown("#### ⚡ Executive Performance Summary")
        
        # 4 Metric Cards
        col1, col2, col3, col4 = st.columns(4)
        
        active_schemes_cnt = len(filtered_df)
        total_aum_cr = filtered_df["aum_crore"].sum()
        avg_3yr_cagr = filtered_df["return_3yr_pct"].mean()
        med_expense_ratio = filtered_df["expense_ratio_pct"].median()

        with col1:
            st.container(border=True).markdown(
                f'<div class="metric-container"><div class="metric-label">Active Schemes</div><div class="metric-val">{active_schemes_cnt}</div><div class="metric-sub">Filtered Universe</div></div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.container(border=True).markdown(
                f'<div class="metric-container"><div class="metric-label">Total Inflows / AUM</div><div class="metric-val">₹{total_aum_cr:,.0f} Cr</div><div class="metric-sub">Investor Capital</div></div>',
                unsafe_allow_html=True,
            )
        with col3:
            st.container(border=True).markdown(
                f'<div class="metric-container"><div class="metric-label">Average 3Y Return</div><div class="metric-val">{avg_3yr_cagr:.2f}%</div><div class="metric-sub">Annualized CAGR</div></div>',
                unsafe_allow_html=True,
            )
        with col4:
            st.container(border=True).markdown(
                f'<div class="metric-container"><div class="metric-label">Median Expense Ratio</div><div class="metric-val">{med_expense_ratio:.2f}%</div><div class="metric-sub">AMC Management Fee</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("#### 🗺️ Asset Allocation Treemap Across Categories & Fund Houses")

        if not filtered_df.empty:
            treemap_df = filtered_df.dropna(subset=["category", "fund_house", "aum_crore"]).copy()
            treemap_df["aum_display"] = treemap_df["aum_crore"].apply(lambda x: max(x, 100.0))

            fig_treemap = px.treemap(
                treemap_df,
                path=[px.Constant("Mutual Fund Universe"), "category", "fund_house", "scheme_name"],
                values="aum_display",
                color="return_3yr_pct",
                color_continuous_scale="Viridis",
                title="Scheme Allocation Weighted by AUM (Color = 3Yr Return %)",
                template="plotly_dark",
            )
            fig_treemap.update_layout(margin=dict(t=40, l=10, r=10, b=10), height=550)
            st.plotly_chart(fig_treemap, use_container_width=True)
        else:
            st.warning("No data available for the current filter criteria.")

    # ==========================================================================
    # TAB 2: QUANTITATIVE RISK & PERFORMANCE
    # ==========================================================================
    with tab2:
        st.markdown("#### 📈 Risk-Adjusted Analytics & Value at Risk (VaR)")

        # Section 1: 90-Day Rolling Sharpe Time Series
        st.markdown("##### 1. 90-Day Rolling Sharpe Ratio Time Series")
        if filtered_amfi_codes:
            chart_codes = tuple(filtered_amfi_codes[:7])
            df_nav_hist = load_nav_history_df(DB_PATH, chart_codes)
            if not df_nav_hist.empty:
                df_rolling = compute_rolling_sharpe(df_nav_hist, window=90)
                if not df_rolling.empty:
                    fig_sharpe = px.line(
                        df_rolling,
                        x="date",
                        y="rolling_sharpe",
                        color="scheme_name",
                        title="90-Day Rolling Annualized Sharpe Ratio",
                        template="plotly_dark",
                        labels={"rolling_sharpe": "Rolling Sharpe Ratio", "date": "Date"},
                    )
                    fig_sharpe.add_hline(y=0.0, line_dash="dash", line_color="gray", annotation_text="Zero Sharpe Threshold")
                    fig_sharpe.update_layout(height=420, margin=dict(t=40, l=10, r=10, b=10))
                    st.plotly_chart(fig_sharpe, use_container_width=True)

        st.markdown("---")

        # Section 2: Alpha vs Beta Risk Quadrants
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("##### 2. CAPM Alpha vs. Beta Risk Quadrant Plot")
            plot_df = filtered_df.dropna(subset=["alpha", "beta", "aum_crore"]).copy()
            if not plot_df.empty:
                fig_alpha_beta = px.scatter(
                    plot_df,
                    x="beta",
                    y="alpha",
                    size="aum_crore",
                    color="category",
                    hover_name="scheme_name",
                    title="Alpha (Excess Return %) vs. Beta (Market Sensitivity)",
                    template="plotly_dark",
                    labels={"beta": "Beta (Market Sensitivity)", "alpha": "Alpha (% Annualized)"},
                )
                # Reference lines
                fig_alpha_beta.add_vline(x=1.0, line_dash="dash", line_color="#94A3B8")
                fig_alpha_beta.add_hline(y=0.0, line_dash="dash", line_color="#94A3B8")
                
                # Annotations for Quadrants
                fig_alpha_beta.add_annotation(x=0.5, y=plot_df["alpha"].max()*0.8, text="Outperform / Low Risk", showarrow=False, font=dict(color="#10B981"))
                fig_alpha_beta.add_annotation(x=1.5, y=plot_df["alpha"].max()*0.8, text="Aggressive Growth", showarrow=False, font=dict(color="#3B82F6"))

                fig_alpha_beta.update_layout(height=420, margin=dict(t=40, l=10, r=10, b=10))
                st.plotly_chart(fig_alpha_beta, use_container_width=True)

        # Section 3: 1-Day 95% Value at Risk (VaR) Distribution
        with col_right:
            st.markdown("##### 3. Daily Returns Distribution & 1-Day 95% VaR")
            if filtered_amfi_codes:
                all_nav_df = load_nav_history_df(DB_PATH, tuple(filtered_amfi_codes))
                if not all_nav_df.empty:
                    all_nav_df["daily_ret"] = all_nav_df.groupby("amfi_code")["nav"].pct_change()
                    clean_rets = all_nav_df["daily_ret"].dropna()
                    clean_rets = clean_rets[np.abs(clean_rets) < 0.15]

                    var_95 = np.percentile(clean_rets, 5)

                    fig_var = px.histogram(
                        clean_rets * 100,
                        nbins=60,
                        title=f"1-Day Daily Return Distribution (95% VaR = {var_95*100:.2f}%)",
                        template="plotly_dark",
                        labels={"value": "Daily Return (%)"},
                        color_discrete_sequence=["#38BDF8"],
                    )
                    fig_var.add_vline(
                        x=var_95 * 100,
                        line_dash="dash",
                        line_color="#EF4444",
                        line_width=2.5,
                        annotation_text=f"95% VaR Cutoff ({var_95*100:.2f}%)",
                        annotation_font_color="#EF4444",
                    )
                    fig_var.update_layout(height=420, showlegend=False, margin=dict(t=40, l=10, r=10, b=10))
                    st.plotly_chart(fig_var, use_container_width=True)

                    st.info(f"💡 **1-Day 95% Value at Risk (VaR)**: On any given trading day, there is a 95% confidence that maximum portfolio loss will not exceed **{abs(var_95)*100:.2f}%** (or ₹{abs(var_95)*100000:,.0f} per ₹100,000 invested).")

    # ==========================================================================
    # TAB 3: MONTE CARLO SIMULATION
    # ==========================================================================
    with tab3:
        st.markdown("#### 🎲 5-Year Geometric Brownian Motion Monte Carlo Engine")

        equity_funds = filtered_df[filtered_df["category"].str.contains("Equity|Growth", case=False, na=False)]
        if equity_funds.empty:
            equity_funds = filtered_df.copy()

        selected_scheme = st.selectbox(
            "Select Target Mutual Fund for Stochastic Path Simulation:",
            options=equity_funds["scheme_name"].tolist(),
            index=0 if not equity_funds.empty else None,
        )

        if selected_scheme:
            target_amfi = equity_funds[equity_funds["scheme_name"] == selected_scheme]["amfi_code"].iloc[0]
            df_target_nav = load_nav_history_df(DB_PATH, (target_amfi,))
            
            if not df_target_nav.empty:
                df_target_nav = df_target_nav.sort_values("date")
                df_target_nav["log_ret"] = np.log(df_target_nav["nav"] / df_target_nav["nav"].shift(1))
                clean_log_rets = df_target_nav["log_ret"].dropna()
                clean_log_rets = clean_log_rets[np.abs(clean_log_rets) < 0.15]

                daily_mean = clean_log_rets.mean()
                daily_std = clean_log_rets.std()
                initial_nav = df_target_nav["nav"].iloc[-1]

                # Run 1,000 paths
                mc_paths = run_monte_carlo_gbm(initial_nav, daily_mean, daily_std, num_paths=1000, num_days=1260)
                
                days_arr = np.arange(1261)
                p5 = np.percentile(mc_paths, 5, axis=1)
                p50 = np.percentile(mc_paths, 50, axis=1)
                p95 = np.percentile(mc_paths, 95, axis=1)

                # Metric Callout Cards
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                with col_m1:
                    st.container(border=True).metric("Current Starting NAV", f"₹{initial_nav:.2f}")
                with col_m2:
                    st.container(border=True).metric("50th %ile Median NAV", f"₹{p50[-1]:.2f}", f"{(p50[-1]/initial_nav - 1)*100:+.2f}%")
                with col_m3:
                    st.container(border=True).metric("95th %ile Optimistic", f"₹{p95[-1]:.2f}", f"{(p95[-1]/initial_nav - 1)*100:+.2f}%")
                with col_m4:
                    st.container(border=True).metric("5th %ile Pessimistic", f"₹{p5[-1]:.2f}", f"{(p5[-1]/initial_nav - 1)*100:+.2f}%")

                # Fan Chart
                fig_fan = go.Figure()

                # Shaded 90% Confidence Interval Band
                fig_fan.add_trace(go.Scatter(x=days_arr, y=p95, mode="lines", line=dict(color="#10B981", width=1.5, dash="dash"), name="95th Percentile (Optimistic)"))
                fig_fan.add_trace(go.Scatter(x=days_arr, y=p5, mode="lines", line=dict(color="#EF4444", width=1.5, dash="dash"), fill="tonexty", fillcolor="rgba(59, 130, 246, 0.15)", name="5th Percentile (Pessimistic)"))
                fig_fan.add_trace(go.Scatter(x=days_arr, y=p50, mode="lines", line=dict(color="#00F2FE", width=3.0), name="50th Percentile (Median Projection)"))

                fig_fan.update_layout(
                    title=f"1,000 Stochastic Path Simulation (5-Year Horizon) — {selected_scheme}",
                    xaxis_title="Trading Days (Next 1,260 Days / 5 Years)",
                    yaxis_title="Projected NAV (INR)",
                    template="plotly_dark",
                    height=500,
                    margin=dict(t=40, l=10, r=10, b=10),
                )
                st.plotly_chart(fig_fan, use_container_width=True)

    # ==========================================================================
    # TAB 4: MARKOWITZ EFFICIENT FRONTIER
    # ==========================================================================
    with tab4:
        st.markdown("#### ⚖️ Markowitz Mean-Variance Efficient Frontier & Capital Allocation Line (CAL)")

        # Select 3 to 7 funds
        scorecard_df = load_scorecard_dataset(SCORECARD_PATH)
        top_codes_default = scorecard_df.sort_values("final_rank")["amfi_code"].head(5).tolist() if not scorecard_df.empty else filtered_amfi_codes[:5]

        opt_selected_codes = st.multiselect(
            "Select 3 to 7 Mutual Funds for Portfolio Optimization:",
            options=filtered_amfi_codes,
            default=[c for c in top_codes_default if c in filtered_amfi_codes],
            max_selections=7,
        )

        if len(opt_selected_codes) >= 3:
            df_opt_nav = load_nav_history_df(DB_PATH, tuple(opt_selected_codes))
            if not df_opt_nav.empty:
                df_opt_pivot = df_opt_nav.pivot(index="date", columns="amfi_code", values="nav").dropna()
                rets = df_opt_pivot.pct_change().dropna()
                rets = rets[(np.abs(rets) < 0.15).all(axis=1)]

                mean_returns_ann = (rets.mean() * TRADING_DAYS).values
                cov_matrix_ann = (rets.cov() * TRADING_DAYS).values

                # Short asset names
                asset_names = [df_master[df_master["amfi_code"] == code]["scheme_name"].iloc[0].split("-")[0].strip() for code in opt_selected_codes]

                # Run Optimization
                w_sharpe, w_minvar = optimize_portfolio(mean_returns_ann, cov_matrix_ann, RISK_FREE_RATE)

                opt_ret = np.sum(mean_returns_ann * w_sharpe)
                opt_vol = np.sqrt(np.dot(w_sharpe.T, np.dot(cov_matrix_ann, w_sharpe)))
                opt_sr = (opt_ret - RISK_FREE_RATE) / opt_vol

                min_ret = np.sum(mean_returns_ann * w_minvar)
                min_vol = np.sqrt(np.dot(w_minvar.T, np.dot(cov_matrix_ann, w_minvar)))

                col_ef1, col_ef2 = st.columns([7, 5])

                with col_ef1:
                    # Simulate 3,000 Random Portfolios
                    np.random.seed(42)
                    sim_rets, sim_vols, sim_srs = [], [], []
                    for _ in range(3000):
                        w = np.random.random(len(opt_selected_codes))
                        w /= np.sum(w)
                        r_p = np.sum(mean_returns_ann * w)
                        v_p = np.sqrt(np.dot(w.T, np.dot(cov_matrix_ann, w)))
                        sim_rets.append(r_p)
                        sim_vols.append(v_p)
                        sim_srs.append((r_p - RISK_FREE_RATE) / v_p)

                    fig_ef = px.scatter(
                        x=np.array(sim_vols) * 100,
                        y=np.array(sim_rets) * 100,
                        color=np.array(sim_srs),
                        color_continuous_scale="Viridis",
                        title="Efficient Frontier & Capital Allocation Line (CAL)",
                        template="plotly_dark",
                        labels={"x": "Annualized Volatility (%)", "y": "Expected Return (%)", "color": "Sharpe"},
                    )

                    # CAL Line
                    cal_x = np.array([0, opt_vol * 1.3]) * 100
                    cal_y = np.array([RISK_FREE_RATE, RISK_FREE_RATE + opt_sr * opt_vol * 1.3]) * 100
                    fig_ef.add_trace(go.Scatter(x=cal_x, y=cal_y, mode="lines", line=dict(color="#F59E0B", width=2.5, dash="dash"), name="Capital Allocation Line (CAL)"))

                    # Max Sharpe & Min Var Markers
                    fig_ef.add_trace(go.Scatter(x=[opt_vol * 100], y=[opt_ret * 100], mode="markers", marker=dict(symbol="star", size=18, color="#F59E0B", line=dict(color="white", width=1)), name=f"Max Sharpe ({opt_sr:.2f})"))
                    fig_ef.add_trace(go.Scatter(x=[min_vol * 100], y=[min_ret * 100], mode="markers", marker=dict(symbol="diamond", size=14, color="#10B981", line=dict(color="white", width=1)), name="Minimum Variance"))

                    fig_ef.update_layout(height=480, margin=dict(t=40, l=10, r=10, b=10))
                    st.plotly_chart(fig_ef, use_container_width=True)

                with col_ef2:
                    st.markdown("##### 🍩 Max Sharpe Optimal Weight Allocation")
                    fig_donut = px.pie(
                        names=asset_names,
                        values=w_sharpe * 100,
                        hole=0.45,
                        title=f"Optimal Portfolio Allocation (Sharpe = {opt_sr:.2f})",
                        template="plotly_dark",
                        color_discrete_sequence=px.colors.qualitative.Plotly,
                    )
                    fig_donut.update_layout(height=480, margin=dict(t=40, l=10, r=10, b=10))
                    st.plotly_chart(fig_donut, use_container_width=True)
        else:
            st.info("Please select between 3 and 7 mutual funds to generate the Markowitz Efficient Frontier.")

    # ==========================================================================
    # TAB 5: RECOMMENDER & SCORECARDS
    # ==========================================================================
    with tab5:
        st.markdown("#### 🏆 Composite Fund Scorecard & Recommender Engine")
        
        df_scorecard_raw = load_scorecard_dataset(SCORECARD_PATH)
        if not df_scorecard_raw.empty:
            # Merge metadata
            df_scorecard_merged = pd.merge(df_scorecard_raw, df_master[["amfi_code", "fund_house", "category"]], on="amfi_code", how="left")
            
            # Apply Sidebar Filters
            if selected_categories:
                df_scorecard_merged = df_scorecard_merged[df_scorecard_merged["category"].isin(selected_categories)]
            if selected_fund_houses:
                df_scorecard_merged = df_scorecard_merged[df_scorecard_merged["fund_house"].isin(selected_fund_houses)]

            # Interactive Search Filter
            search_query = st.text_input("🔍 Search Scheme Name or AMFI Code:", placeholder="Type 'HDFC', 'Small Cap', '120505'...")
            if search_query:
                mask = (
                    df_scorecard_merged["scheme_name"].astype(str).str.contains(search_query, case=False, na=False)
                    | df_scorecard_merged["amfi_code"].astype(str).str.contains(search_query, case=False, na=False)
                )
                df_scorecard_merged = df_scorecard_merged[mask]

            st.dataframe(
                df_scorecard_merged.sort_values("composite_score", ascending=False).reset_index(drop=True),
                use_container_width=True,
                height=480,
                column_config={
                    "amfi_code": st.column_config.NumberColumn("AMFI Code", format="%d"),
                    "scheme_name": st.column_config.TextColumn("Scheme Name"),
                    "fund_house": st.column_config.TextColumn("Fund House"),
                    "category": st.column_config.TextColumn("Category"),
                    "cagr_3yr_pct": st.column_config.NumberColumn("3Yr CAGR (%)", format="%.2f%%"),
                    "sharpe_ratio": st.column_config.NumberColumn("Sharpe Ratio", format="%.2f"),
                    "alpha_annual_pct": st.column_config.NumberColumn("Alpha (%)", format="%.2f%%"),
                    "expense_ratio_pct": st.column_config.NumberColumn("Expense Ratio (%)", format="%.2f%%"),
                    "composite_score": st.column_config.NumberColumn("Composite Score (0-100)", format="%.1f"),
                    "final_rank": st.column_config.NumberColumn("Rank", format="#%d"),
                },
                hide_index=True,
            )

            # CSV Download Button
            csv_data = df_scorecard_merged.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Filtered Scorecard (CSV)",
                data=csv_data,
                file_name="filtered_bluestock_fund_scorecard.csv",
                mime="text/csv",
                type="primary",
            )
        else:
            st.warning("Scorecard dataset fund_scorecard.csv not found.")


if __name__ == "__main__":
    main()
