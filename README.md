# Bluestock Mutual Fund Analytics — Capstone Project

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Database](https://img.shields.io/badge/SQLite-Star%20Schema-green.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-Interactive%20Terminal-FF4B4B.svg)
![Plotly](https://img.shields.io/badge/Plotly-Quantitative%20Charts-3F4F75.svg)
![Power BI](https://img.shields.io/badge/Power%20BI-Interactive%20Dashboard-yellow.svg)
![License](https://img.shields.io/badge/license-MIT-informational.svg)

A production-ready quantitative financial analytics platform, stochastic risk modeling suite, and ETL data pipeline designed for evaluating **Indian Mutual Fund performance, risk-adjusted returns, investor cohort behaviors, SIP continuity, sector concentration risks, and portfolio optimization**.

---

## 1. Project Overview

The **Mutual Fund Analytics Capstone Project** delivers an end-to-end quantitative financial engineering solution. It ingests multi-year historical Net Asset Values (NAV), fund master metadata, benchmark indices, and investor transaction logs, processing them through a relational SQLite Star Schema, interactive analytics engines, and stochastic risk models.

### Key Capabilities & Engineering Highlights
* **Quantitative Risk Suite**: Annualized Sharpe Ratio, Sortino Ratio (downside risk), 1-day 95% Value at Risk (VaR), and OLS CAPM Alpha/Beta against Nifty 100/50 benchmarks.
* **Rolling Analytics**: 90-day rolling mean/std annualized Sharpe ratio time series analysis to track risk-adjusted performance volatility.
* **Portfolio Concentration**: Sector Herfindahl-Hirschman Index (HHI) concentration modeling ($\sum w_s^2$) to flag high single-sector exposure.
* **Investor Behavioral Intelligence**: Cohort analysis by investor acquisition year and SIP continuity tracking (flagging `at-risk` accounts with $>35$ day installment gaps).
* **Composite Ranking Engine**: Multi-factor 0–100 percentile composite scorecard incorporating CAGR, risk-adjusted ratios, drawdown recovery, and expense ratios.
* **Automated Master ETL Pipeline**: One-command execution (`python scripts/etl_pipeline.py`) spanning ingestion, cleaning, validation, database loading, and reporting.

---

## 2. Bonus Challenges Implemented (B1 – B5)

In addition to core analytics, five advanced quantitative and automation modules have been fully implemented:

### 🌟 Bonus Challenge 1 (B1): Live NAV Ingestion Engine
* **Script**: [`scripts/live_nav_fetch.py`](scripts/live_nav_fetch.py)
* **Functionality**: Hits the public `mfapi.in` endpoint for 40 AMFI scheme codes, extracts the latest published NAV date and value, and performs idempotent `INSERT OR IGNORE` SQL queries into `data/db/bluestock_mf.db`.
* **Automation**: Configured for Windows Task Scheduler (`schtasks /Create /TN "Bluestock_Live_NAV_Fetch"`) and Cron (`0 20 * * 1-5`) to run every weekday at 8:00 PM.

### 🌟 Bonus Challenge 2 (B2): Streamlit Interactive Quant Terminal
* **Dashboard**: [`dashboard/app.py`](dashboard/app.py)
* **Functionality**: Dark-themed financial terminal application built with Streamlit and Plotly. Features dynamic sidebar AMC/Category filters, high-performance `@st.cache_data`, and 5 dedicated analytics tabs:
  1. **Executive Overview**: Treemap allocation across Categories & Fund Houses.
  2. **Quantitative Risk & Performance**: Interactive 90-Day Rolling Sharpe line chart, Alpha vs. Beta risk quadrant plot, and 1-Day 95% VaR histogram.
  3. **Monte Carlo 5-Year Simulation**: 1,000-path Geometric Brownian Motion (GBM) fan chart with confidence intervals.
  4. **Markowitz Efficient Frontier**: Mean-variance optimization curve, Capital Allocation Line (CAL), and optimal allocation donut charts.
  5. **Scorecard & Recommender**: Searchable composite fund scorecard with CSV export.
* **Launch Command**: `streamlit run dashboard/app.py`

### 🌟 Bonus Challenge 3 (B3): 5-Year Monte Carlo NAV Stochastic Simulation
* **Script**: [`scripts/monte_carlo.py`](scripts/monte_carlo.py)
* **Functionality**: Selects the top-performing equity scheme and runs **10,000 random walk price paths** using Geometric Brownian Motion (GBM) over **1,260 trading days** (5 years). Computes and plots the 5th percentile (Pessimistic), 50th percentile (Median), and 95th percentile (Optimistic) trajectory bands.
* **Exported Artifact**: [`dashboard/exported_charts/monte_carlo_5yr.png`](dashboard/exported_charts/monte_carlo_5yr.png)

### 🌟 Bonus Challenge 4 (B4): Markowitz Efficient Frontier Portfolio Optimization
* **Script**: [`scripts/efficient_frontier.py`](scripts/efficient_frontier.py)
* **Functionality**: Uses `scipy.optimize.minimize` (SLSQP solver) on historical returns of the top 5 funds. Solves for the **Max Sharpe Ratio Portfolio** and **Minimum Variance Portfolio**, generating the Markowitz Efficient Frontier curve and simulating 5,000 random weight combinations.
* **Exported Artifact**: [`dashboard/exported_charts/efficient_frontier.png`](dashboard/exported_charts/efficient_frontier.png)

### 🌟 Bonus Challenge 5 (B5): Automated HTML Email Report Engine
* **Script**: [`scripts/email_report.py`](scripts/email_report.py)
* **Functionality**: Reads `fund_scorecard.csv`, extracts the top 5 mutual funds, formats a modern responsive HTML report table with rank badge highlights, and dispatches email via standard `smtplib` and `email.mime` using environment variables managed by `python-dotenv`.
* **Exported Artifact**: [`reports/email_preview.html`](reports/email_preview.html)

---

## 3. Dataset Descriptions

The platform processes datasets covering 40 mutual fund schemes across Equity, Debt, Hybrid, and Index categories:

| Dataset File | Primary Table | Description | Key Attributes |
| :--- | :--- | :--- | :--- |
| **`01_fund_master.csv`** | `dim_fund` | Master metadata for 40 schemes | `amfi_code`, `fund_house`, `category`, `sub_category`, `risk_category`, `benchmark` |
| **`02_nav_history.csv`** | `fact_nav` | Daily historical NAV time-series (2022–2026) | `amfi_code`, `date`, `nav` |
| **`04_monthly_sip_inflows.csv`** | `raw_04_monthly_sip_inflows` | Industry-wide monthly SIP investment trends | `year`, `month`, `sip_inflow_crore`, `num_sip_accounts` |
| **`07_scheme_performance.csv`** | `fact_performance` | Multi-horizon CAGR returns and expense ratios | `amfi_code`, `return_1yr_pct`, `return_3yr_pct`, `return_5yr_pct`, `expense_ratio_pct` |
| **`08_investor_transactions.csv`** | `fact_transactions` | Investor transaction logs & demographic metadata | `investor_id`, `amfi_code`, `transaction_date`, `transaction_type`, `amount_inr`, `kyc_status` |

---

## 4. Setup Instructions

### Prerequisites
* **Python 3.10+** installed
* **Git** installed

### Step-by-Step Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Instinct7439/Capstone-Project-1.git
   cd "Capstone Project 1"
   ```

2. **Create & Activate Virtual Environment**
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install Dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Environment Variables Configuration (Optional for Email Reporting)**
   Create a `.env` file in the root directory:
   ```env
   SENDER_EMAIL=your_actual_email@gmail.com
   SENDER_PASSWORD=your_16_character_app_password
   RECIPIENT_EMAIL=where_to_send@gmail.com
   ```

---

## 5. Comprehensive Execution Guide

### 🚀 1. Master Automated Pipeline
Execute the full data pipeline spanning ingestion, cleaning, schema validation, database loading, rolling Sharpe calculations, and recommender output:
```bash
python scripts/etl_pipeline.py
```

### 📊 2. Streamlit Web Terminal Dashboard
Launch the interactive 5-tab quantitative terminal in your browser:
```bash
streamlit run dashboard/app.py
```

### 📡 3. Live NAV Ingestion Engine
Fetch the latest published NAV daily updates from `mfapi.in`:
```bash
python scripts/live_nav_fetch.py
```

### 🎲 4. Monte Carlo 5-Year Stochastic Simulation
Execute 10,000 Geometric Brownian Motion NAV paths for top equity fund:
```bash
python scripts/monte_carlo.py
```

### ⚖️ 5. Markowitz Efficient Frontier Optimization
Run mean-variance optimization and generate optimal asset allocations:
```bash
python scripts/efficient_frontier.py
```

### 📧 6. Automated HTML Email Report Engine
Generate local HTML preview and dispatch top-5 fund scorecard email:
```bash
python scripts/email_report.py
```

### 📓 7. Jupyter Analytics Notebooks
Launch interactive exploratory and quantitative notebooks:
```bash
jupyter notebook
```
- `notebooks/EDA_Analysis.ipynb`: Exploratory Data Analysis & Visualizations.
- `notebooks/Performance_Analytics.ipynb`: Risk Ratios, VaR, Alpha/Beta, Drawdown, and Composite Scorecards.

---

## 6. Dashboard & Reports Access

### Power BI Interactive Dashboard
1. Open **Microsoft Power BI Desktop**.
2. Navigate to `dashboard/` and open **`Bluestock_Mutual_Fund_Dashboard.pbix`**.
3. If prompted for data connection, point the SQLite database connector to `data/db/bluestock_mf.db`.

### Exported Charts, Reports & Presentations
- **Executive Presentation**: [`reports/Presentation.pptx`](reports/Presentation.pptx) (12 Widescreen Presentation Slides)
- **Final Comprehensive Report**: [`reports/Final_Report.pdf`](reports/Final_Report.pdf) & [`reports/Final_Report_Draft.md`](reports/Final_Report_Draft.md)
- **HTML Email Report Preview**: [`reports/email_preview.html`](reports/email_preview.html)
- **Exported Visualizations**: Located in `dashboard/exported_charts/`
  - `monte_carlo_5yr.png` (5-Year Monte Carlo 10,000 Path Simulation)
  - `efficient_frontier.png` (Markowitz Efficient Frontier & CAL Curve)
  - `rolling_sharpe_chart.png` (90-Day Rolling Sharpe Time Series)
  - `benchmark_comparison.png` (3-Year Cumulative Returns vs. Nifty 100)
- **Data Quality Summary**: [`reports/day1_data_quality_summary.md`](reports/day1_data_quality_summary.md)
- **Composite Fund Scorecard**: [`data/processed/fund_scorecard.csv`](data/processed/fund_scorecard.csv)
- **CAPM Alpha & Beta Summary**: [`data/processed/alpha_beta.csv`](data/processed/alpha_beta.csv)

---

## License & Author
- **Project**: Mutual Fund Analytics Capstone
- **Author**: Vipin Nishad (Capstone Data Science Team)
- **License**: MIT License
