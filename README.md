# Bluestock Mutual Fund Analytics — Capstone Project

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Database](https://img.shields.io/badge/SQLite-Star%20Schema-green.svg)
![Power BI](https://img.shields.io/badge/Power%20BI-Interactive%20Dashboard-yellow.svg)
![License](https://img.shields.io/badge/license-MIT-informational.svg)

A quantitative financial analytics platform and data pipeline designed for evaluating **Indian Mutual Fund performance, risk-adjusted returns, investor cohort behaviors, SIP continuity, and sector concentration risks**.

---

## 1. Project Overview

The **Mutual Fund Analytics Capstone Project** delivers an end-to-end quantitative financial engineering solution. It ingests multi-year historical Net Asset Values (NAV), fund master metadata, benchmark indices, and investor transaction logs, processing them through a relational SQLite Star Schema and interactive analytics engines.

### Key Capabilities & Engineering Highlights
* **Quantitative Risk Suite**: Annualized Sharpe Ratio, Sortino Ratio (downside risk), 1-day 95% Value at Risk (VaR), and OLS CAPM Alpha/Beta against Nifty 100/50 benchmarks.
* **Rolling Analytics**: 90-day rolling mean/std annualized Sharpe ratio time series analysis to track risk-adjusted performance volatility.
* **Portfolio Concentration**: Sector Herfindahl-Hirschman Index (HHI) concentration modeling ($\sum w_s^2$) to flag high single-sector exposure.
* **Investor Behavioral Intelligence**: Cohort analysis by investor acquisition year and SIP continuity tracking (flagging `at-risk` accounts with $>35$ day installment gaps).
* **Composite Ranking Engine**: Multi-factor 0–100 percentile composite scorecard incorporating CAGR, risk-adjusted ratios, drawdown recovery, and expense ratios.
* **Automated Master ETL Pipeline**: One-command execution (`python run_pipeline.py`) spanning ingestion, cleaning, validation, database loading, and reporting.

---

## 2. Dataset Descriptions

The platform processes datasets covering 40 mutual fund schemes across Equity, Debt, Hybrid, and Index categories:

| Dataset File | Primary Table | Description | Key Attributes |
| :--- | :--- | :--- | :--- |
| **`01_fund_master.csv`** | `dim_fund` | Master metadata for 40 schemes | `amfi_code`, `fund_house`, `category`, `sub_category`, `risk_category`, `benchmark` |
| **`02_nav_history.csv`** | `fact_nav` | Daily historical NAV time-series (2022–2026) | `amfi_code`, `date`, `nav` |
| **`04_monthly_sip_inflows.csv`** | `raw_04_monthly_sip_inflows` | Industry-wide monthly SIP investment trends | `year`, `month`, `sip_inflow_crore`, `num_sip_accounts` |
| **`07_scheme_performance.csv`** | `fact_performance` | Multi-horizon CAGR returns and expense ratios | `amfi_code`, `return_1yr_pct`, `return_3yr_pct`, `return_5yr_pct`, `expense_ratio_pct` |
| **`08_investor_transactions.csv`** | `fact_transactions` | Investor transaction logs & demographic metadata | `investor_id`, `amfi_code`, `transaction_date`, `transaction_type`, `amount_inr`, `kyc_status` |

---

## 3. Setup Instructions

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

---

## 4. Execution Guide

### Automated End-to-End Execution Pipeline
Run the master automated pipeline script to execute ingestion, cleaning, validation, database loading, quantitative analytics, and recommendation reporting in sequence:

```bash
python run_pipeline.py
```

#### Pipeline Steps Triggered:
1. **`data_ingestion.py`**: Scans raw datasets in `data/raw/` and inspects schemas.
2. **`data_cleaning.py`**: Standardizes categories, handles null NAVs, and exports to `data/processed/`.
3. **`validate_data.py`**: Validates AMFI codes and writes `reports/day1_data_quality_summary.md`.
4. **`db_loader.py`**: Builds `bluestock_mf.db` (SQLite Star Schema) and populates dimensions/facts.
5. **`calculate_rolling_sharpe.py`**: Generates 90-day rolling Sharpe time series plot (`rolling_sharpe_chart.png`).
6. **`recommender.py`**: Runs mutual fund recommendation engine across risk grades.

### Individual Script & Notebook Execution

- **Mutual Fund Recommender**:
  ```bash
  python recommender.py
  ```

- **Jupyter Analytics Notebooks**:
  ```bash
  jupyter notebook
  ```
  - Open `notebooks/EDA_Analysis.ipynb` for Exploratory Data Analysis & Visualizations.
  - Open `notebooks/Performance_Analytics.ipynb` for Risk Ratios, VaR, Alpha/Beta, Drawdown, and Composite Scorecards.

---

## 5. Dashboard & Reports Access

### Power BI Interactive Dashboard
1. Open **Microsoft Power BI Desktop**.
2. Navigate to `dashboard/` and open **`Bluestock_Mutual_Fund_Dashboard.pbix`**.
3. If prompted for data connection, point the SQLite database connector to `bluestock_mf.db`.

### Exported Charts & Reports
- **Exported High-Res Visualizations**: Located in `dashboard/exported_charts/`
  - `rolling_sharpe_chart.png` (90-Day Rolling Sharpe Time Series)
  - `benchmark_comparison.png` (3-Year Cumulative Returns vs. Nifty 100)
- **Data Quality Summary**: [`reports/day1_data_quality_summary.md`](file:///d:/D%20Drive/Capstone%20Project%201/reports/day1_data_quality_summary.md)
- **Composite Fund Scorecard**: [`fund_scorecard.csv`](file:///d:/D%20Drive/Capstone%20Project%201/fund_scorecard.csv)
- **CAPM Alpha & Beta Summary**: [`alpha_beta.csv`](file:///d:/D%20Drive/Capstone%20Project%201/alpha_beta.csv)

---

## License & Author
- **Project**: Mutual Fund Analytics Capstone
- **Author**: Capstone Data Science Team
- **License**: MIT License
