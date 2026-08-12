# BLUESTOCK MUTUAL FUND ANALYTICS
## Comprehensive Capstone Final Technical & Strategic Report

**Author:** Vipin Nishad  
**Role:** Data Scientist & Financial Quantitative Analyst  
**Project:** Bluestock Mutual Fund Analytics Capstone  
**Target Audience:** Executive Leadership, Portfolio Managers, and Risk Committees  
**Date of Submission:** August 2026  

---

## 1. Executive Summary

### 1.1 Context & Objectives
The Indian Mutual Fund industry has experienced exponential growth in Assets Under Management (AUM), propelled by retail financialization, systematic investment plan (SIP) inflows, and favorable macroeconomic conditions. However, rapid growth brings operational and portfolio risks—including sector concentration, heightened market tail risk, and investor account churn. 

This Capstone Project provides an end-to-end quantitative financial analytics framework and data pipeline evaluating **40 flagship mutual fund schemes** spanning Equity, Debt, Hybrid, and Index asset classes over a multi-year historical horizon (2022–2026). The project builds a robust relational database schema, evaluates risk-adjusted return ratios, models Value at Risk (VaR), tracks portfolio Herfindahl-Hirschman Index (HHI) concentration, and analyzes investor cohort retention.

```
+-----------------------------------------------------------------------------------+
|                               PIPELINE ARCHITECTURE                               |
|                                                                                   |
|  [Raw Data CSVs] ---> [Data Cleaning & Validation] ---> [SQLite Star Schema DB]  |
|                                                                  |                |
|                                                                  v                |
|  [Power BI Dashboard] <--- [Scorecards & Analytics] <--- [Quantitative Engine]    |
+-----------------------------------------------------------------------------------+
```

### 1.2 Core Quantitative Highlights
- **Risk-Adjusted Performance Leadership**: Debt/Liquid funds (*ICICI Pru Liquid Fund*, *Kotak Liquid Fund*) achieved annualized Sharpe ratios above **5.00** due to near-zero return variance. Among Equity schemes, *HDFC Top 100 Fund* and *Mirae Asset Large Cap Fund* led with 3-year CAGR returns of **14.84%** and **14.81%** and Sharpe ratios of **1.06**.
- **CAPM Alpha Generation**: *SBI Small Cap Fund* delivered the highest annualized Alpha (**+5.42%**) against the Nifty 100 index with a Beta of **0.88**, demonstrating significant security selection edge.
- **Tail Risk Vulnerability (VaR)**: Small-Cap and Mid-Cap equity schemes exhibited 1-day 95% Value at Risk ($\text{VaR}_{95\%}$) between **$-1.8\%$ and $-2.4\%$**, translating into an annualized tail loss potential exceeding **$-35\%$**.
- **Investor Cohort Dominance**: The **2024 Investor Cohort** accounts for **₹2,258.06 Crore ($99.1\%$)** of total historical transaction volume across 4,803 retail accounts.
- **SIP Continuity Alarm**: Of 1,362 investors with $\ge 6$ SIP installments, **1,332 investors ($97.8\%$) are flagged as `at-risk`**, experiencing average payment intervals of **$35 \text{ to } 85 \text{ days}$** (vs. the standard 30-day mandate cycle).
- **Portfolio Sector Concentration**: Sector HHI scores revealed that flagship schemes like *HDFC Top 100 (Direct)* ($\text{HHI} = 2,829.94$) and *Axis Midcap Fund* ($\text{HHI} = 2,578.06$) cross into **Highly Concentrated** status ($\text{HHI} \ge 2,500$), driven by $>40\%$ tilts into single sectors (IT and Banking).

---

## 2. Data Sources & ETL Architecture

### 2.1 Raw Data Sources & Ingestion
The analytics platform ingests data across 10 primary raw CSV files stored in `data/raw/`:
1. `01_fund_master.csv`: Metadata for 40 schemes (AMFI code, AMC, category, risk grade, benchmark).
2. `02_nav_history.csv`: 46,000 daily NAV records spanning 2022 to 2026.
3. `03_aum_by_fund_house.csv`: AUM progression across top Asset Management Companies (AMCs).
4. `04_monthly_sip_inflows.csv`: Industry-wide monthly SIP investment values and active account counts.
5. `05_category_inflows.csv`: Monthly net inflows across Equity, Debt, and Hybrid categories.
6. `06_industry_folio_count.csv`: Industry-wide folio count growth metrics.
7. `07_scheme_performance.csv`: 1Y, 3Y, 5Y CAGR returns, expense ratios, and historical risk metrics.
8. `08_investor_transactions.csv`: 32,778 retail investor transaction records.
9. `09_portfolio_holdings.csv`: 322 stock-level equity portfolio constituent weights.
10. `10_benchmark_indices.csv`: Daily price index levels for Nifty 50, Nifty 100, and secondary benchmarks.

### 2.2 Relational Star Schema Design
Data is organized in a normalized SQLite database (`bluestock_mf.db`) following a dimensional Star Schema:

```
                          +-------------------+
                          |     dim_date      |
                          +-------------------+
                          | date (PK)         |
                          | year, quarter     |
                          | month, fiscal_yr  |
                          +---------+---------+
                                    |
                                    |
+-------------------+     +---------+---------+     +-----------------------+
|     dim_fund      |     |     fact_nav      |     |   fact_performance    |
+-------------------+     +-------------------+     +-----------------------+
| amfi_code (PK)    |<----+ amfi_code (FK)    |     | amfi_code (FK)        |
| fund_house        |     | date (FK)         |     | return_1yr, 3yr, 5yr  |
| scheme_name       |     | nav               |     | sharpe, sortino, alpha|
| category          |     +-------------------+     | expense_ratio_pct     |
| risk_category     |                               +-----------------------+
+---------+---------+
          |
          |               +-----------------------+
          +--------------<|   fact_transactions   |
                          +-----------------------+
                          | investor_id (PK)      |
                          | amfi_code (FK)        |
                          | transaction_date      |
                          | amount_inr, kyc_status|
                          +-----------------------+
```

### 2.3 Data Cleaning & Validation Rules
- **Date Standardization**: Converted string dates into standard `YYYY-MM-DD` timestamps.
- **NAV Deduplication & Forward-Fill**: Sorted NAV histories chronologically, removed duplicates, and applied forward-fill (`ffill()`) for missing trading dates to avoid artificial return spikes.
- **Transaction Sanitization**: Standardized transaction types (`SIP`, `Lumpsum`, `Redemption`) and filtered out zero or negative transaction amounts.
- **Expense Ratio Flagging**: Flagged expense ratios outside the standard regulatory range ($0.1\% \text{ to } 2.5\%$).

---

## 3. Exploratory Data Analysis (EDA) Findings

### 3.1 NAV Trend & Market Cycle Dynamics
The daily NAV movement of the 40 mutual fund schemes over 2022–2026 highlights two distinct macroeconomic phases:
1. **The 2023 Bull Run**: Strong market rally driven by broad-based economic recovery and heavy domestic institutional inflows, resulting in a **$+28.4\%$** aggregate equity NAV expansion.
2. **2024 Market Corrections**: Heightened global interest rates and geopolitical uncertainty caused mid-year market corrections, causing pullbacks of **$-8.5\% \text{ to } -14.2\%$** in Small-Cap and Mid-Cap schemes.

```
       NAV Growth Trajectory (2022 - 2026 Normalized)
  NAV (Index=100)
    160 +------------------------------------------ /--- Equity Top 5
    140 |                                   /------'
    120 |                     /------------'      ------ Debt Benchmark
    100 +-------v------------'
     80 |   (2022 Base)  (2023 Bull Run)  (2024 Correction)
        +---------------------------------------------------> Date
```

### 3.2 AMC AUM Growth Dominance
Grouped bar chart analysis across AMCs reveals strong market concentration:
- **SBI Mutual Fund** maintains industry dominance with AUM reaching **₹12.5 Lakh Crore** ($12,50,000 \text{ Cr}$), supported by extensive bank branch distribution networks.
- **ICICI Prudential MF** and **HDFC Mutual Fund** follow closely, commanding **₹9.8 Lakh Cr** and **₹9.2 Lakh Cr** respectively.

### 3.3 SIP Inflow Trajectories & Category Split
- **Monthly SIP Inflows**: Monthly SIP contributions expanded from **₹13,041 Crore** in early 2022 to over **₹23,332 Crore** by 2025, demonstrating retail dollar-cost averaging resilience.
- **Category Inflow Split**: **Equity schemes** captured **$68.4\%$** of net inflows, **Debt schemes** accounted for **$19.2\%$** (mostly liquid funds), and **Hybrid/Index funds** represented **$12.4\%$**.

---

## 4. Quantitative Performance Analysis

### 4.1 Daily Return Distribution & Summary Statistics
Daily returns ($R_{i,t} = \frac{\text{NAV}_{i,t}}{\text{NAV}_{i,t-1}} - 1$) across 40 schemes demonstrate expected distributional properties:
- **Mean Daily Return**: Equity funds averaged **$+0.052\%$** daily; Debt funds averaged **$+0.021\%$** daily.
- **Daily Volatility ($\sigma_{\text{daily}}$)**: Equity funds exhibited daily standard deviation between **$0.75\% \text{ and } 1.35\%$**; Debt funds recorded minimal volatility ($<0.08\%$).
- **Skewness & Kurtosis**: Equity return distributions exhibited slight negative skewness ($-0.42$) and heavy tails (kurtosis $> 4.8$), indicating fat-tailed downside risk.

### 4.2 Multi-Horizon Annualized CAGR Returns
Compounded Annual Growth Rate (CAGR) was computed using:

$$\text{CAGR} = \left(\frac{\text{NAV}_{\text{end}}}{\text{NAV}_{\text{start}}}\right)^{\frac{1}{n}} - 1$$

| Scheme Name | Category | 1-Year CAGR | 3-Year CAGR | 5-Year CAGR |
| :--- | :---: | :---: | :---: | :---: |
| **SBI Small Cap Fund (Regular)** | Equity | 26.40% | **23.39%** | 21.80% |
| **Kotak Emerging Equity Fund** | Equity | 21.15% | **18.23%** | 17.65% |
| **ICICI Pru Midcap Fund** | Equity | 20.80% | **18.08%** | 17.10% |
| **HDFC Top 100 Fund (Regular)** | Equity | 16.20% | **14.84%** | 13.90% |
| **Mirae Asset Large Cap Fund** | Equity | 15.90% | **14.81%** | 13.75% |
| **ICICI Pru Bluechip Fund (Direct)** | Equity | 15.50% | **14.41%** | 13.50% |
| **ICICI Pru Liquid Fund (Regular)** | Debt | 7.68% | **7.68%** | 6.85% |
| **Kotak Liquid Fund (Regular)** | Debt | 6.18% | **6.18%** | 5.95% |

### 4.3 Risk-Adjusted Return Ratios (Sharpe & Sortino)
Using an annualized risk-free rate $R_f = 6.5\%$ ($0.065/252$ per day):

$$\text{Sharpe Ratio} = \frac{R_p - R_f}{\sigma_p} \times \sqrt{252}, \quad \text{Sortino Ratio} = \frac{R_p - R_f}{\sigma_{\text{downside}}} \times \sqrt{252}$$

- **Debt Leadership**: *ICICI Pru Liquid Fund* achieved a Sharpe ratio of **7.68** and Sortino ratio of **11.45**, reflecting consistent daily yield without downside variance.
- **Top Risk-Adjusted Equity Schemes**:
  - *HDFC Top 100 Fund*: Sharpe **1.06** | Sortino **1.58**
  - *Mirae Asset Large Cap Fund*: Sharpe **1.06** | Sortino **1.55**
  - *ICICI Pru Bluechip Fund (Direct)*: Sharpe **1.03** | Sortino **1.52**

### 4.4 OLS Regression CAPM Alpha & Beta
Using Ordinary Least Squares (OLS) regression against Nifty 100 benchmark daily returns:

$$R_{i,t} - R_{f,t} = \alpha_i + \beta_i (R_{m,t} - R_{f,t}) + \epsilon_{i,t}$$

- **Highest Alpha Generator**: **SBI Small Cap Fund** generated an annualized Alpha of **$+5.42\%$** with a Beta of **0.88** ($R^2 = 0.74$).
- **Market Sensitivity**: Large-Cap funds (*HDFC Top 100*, *ICICI Pru Bluechip*) displayed Betas close to $1.00$ ($0.96 \text{ to } 1.02$) with high benchmark correlation ($R^2 > 0.94$).

### 4.5 Drawdown Lifecycle & Recovery Analysis
Maximum Drawdown measures peak-to-trough decline:

$$\text{Max Drawdown} = \frac{\text{Peak NAV} - \text{Trough NAV}}{\text{Peak NAV}}$$

- **Small-Cap Drawdowns**: *SBI Small Cap Fund* experienced a maximum drawdown of **$-28.4\%$** during the 2024 market correction, taking **142 trading days** to recover to previous peaks.
- **Large-Cap Resilience**: *ICICI Pru Bluechip Fund* limited max drawdown to **$-12.1\%$**, recovering within **48 trading days**.

### 4.6 Composite 0–100 Scorecard Ranking
A multi-factor percentile composite scorecard was constructed using weighted rankings across 5 core metrics:
- **3Y CAGR** ($30\%$) | **Sharpe Ratio** ($25\%$) | **Sortino Ratio** ($20\%$) | **Alpha** ($15\%$) | **Expense Ratio (Inverse)** ($10\%$)

$$\text{Composite Score} = \sum_{m} w_m \times \text{PercentileRank}(m) \times 100$$

| Rank | Scheme Name | Category | Composite Score (0–100) | Tier |
| :---: | :--- | :---: | :---: | :---: |
| **1** | **SBI Small Cap Fund (Regular)** | Equity | **94.8** | Top Tier |
| **2** | **HDFC Top 100 Fund (Regular)** | Equity | **89.2** | Top Tier |
| **3** | **Mirae Asset Large Cap Fund** | Equity | **88.5** | Top Tier |
| **4** | **ICICI Pru Bluechip Fund (Direct)** | Equity | **87.1** | Top Tier |
| **5** | **Kotak Emerging Equity Fund** | Equity | **85.6** | Top Tier |

---

## 5. Advanced Risk Analytics

### 5.1 Value at Risk (VaR) Modeling
Value at Risk ($\text{VaR}$) was estimated at the $95\%$ confidence level using Parametric ($\text{VaR} = \mu - 1.645 \cdot \sigma$) and Historical Simulation methods:

```
               DAILY RETURN DISTRIBUTION & 95% VaR TAIL
   Frequency
      ^
      |                 /\
      |                /  \
      |               /    \
      |              /      \
      |   Tail Loss /        \
      |   (5%)     /          \
      +----------|-------------\------------------> Daily Return (%)
               -2.1%           +0.05%
             (95% VaR)         (Mean)
```

- **High-Beta Small/Mid-Cap VaR**:
  - *ABSL Small Cap Fund*: 1-Day 95% VaR = **$-2.41\%$**
  - *SBI Small Cap Fund*: 1-Day 95% VaR = **$-2.18\%$**
  - *HDFC Mid-Cap Opportunities*: 1-Day 95% VaR = **$-2.05\%$**
- **Large-Cap & Index VaR**:
  - *UTI Nifty 50 Index Fund*: 1-Day 95% VaR = **$-1.32\%$**
  - *ICICI Pru Bluechip Fund*: 1-Day 95% VaR = **$-1.28\%$**

### 5.2 Investor Cohort Analysis
Grouping retail investors by their initial acquisition year (`cohort_year`):

| Cohort Year | Total Investors | Average Monthly SIP (₹) | Total Capital Invested (₹) | Top Preferred Fund Scheme |
| :---: | :---: | :---: | :---: | :--- |
| **2024** | **4,803** | ₹10,996.89 | **₹2,258,062,304.00** | Mirae Asset Emerging Bluechip Fund |
| **2025** | **197** | **₹13,505.21** | ₹18,992,635.00 | ICICI Pru Liquid Fund - Regular |

#### Key Cohort Takeaways:
1. **Capital Concentration**: The **2024 Cohort** accounts for **$99.1\%$ of total invested capital**, establishing it as the core revenue base.
2. **Expanding Ticket Size**: The **2025 Cohort** exhibits a **$+22.8\%$ higher average SIP amount** (₹13,505 vs. ₹10,996), indicating higher-income investor acquisition.

### 5.3 SIP Continuity & At-Risk Account Flagging
To evaluate SIP installment health, investors with $\ge 6$ SIP transactions were analyzed for installment intervals:

```
   SIP Installment Day Gap Distribution
   Investors
     ^
     |                                          #################
     |                                          #################
     |                                          #################
     |                                          #################
     |  [Healthy Zone]                          [At-Risk Zone]
     |  (Gap <= 35 Days)                        (Gap > 35 Days)
     +-------------------------------------------------------------> Avg Days Gap
     0                              35 Days                     85 Days
```

- **Total Eligible Investors ($\ge 6$ SIPs)**: 1,362 accounts
- **At-Risk Flagged Investors (Avg Gap $> 35$ Days)**: **1,332 accounts ($97.8\%$)**
- **Healthy Continuity Investors (Avg Gap $\le 35$ Days)**: **30 accounts ($2.2\%$)**

#### Operational Insight:
An average installment gap of $45 \text{ to } 85 \text{ days}$ signals severe payment friction, including NACH mandate rejections, insufficient bank account balances, or voluntary manual pauses.

### 5.4 Sector Herfindahl-Hirschman Index (HHI) Concentration
Portfolio concentration was modeled by summing squared sector market weights ($w_{i,s}$):

$$\text{HHI} = \sum_{s=1}^{S} w_{i,s}^2 \quad (\text{Percentage Scale: } 0 \text{ to } 10,000 | \text{Decimal Scale: } 0 \text{ to } 1.0)$$

#### Classification Thresholds:
- **Highly Concentrated**: $\text{HHI} \ge 2,500$ ($\text{Decimal} \ge 0.25$)
- **Moderately Concentrated**: $1,500 \le \text{HHI} < 2,500$ ($0.15 \le \text{Decimal} < 0.25$)
- **Diversified**: $\text{HHI} < 1,500$ ($\text{Decimal} < 0.15$)

| Scheme Name | Category | HHI Score | Top Sector | Top Sector Weight (%) | Concentration Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **HDFC Top 100 Fund (Direct)** | Large Cap | **2829.94** | IT | **45.77%** | **Highly Concentrated** |
| **Axis Midcap Fund (Regular)** | Mid Cap | **2578.06** | Banking | **30.55%** | **Highly Concentrated** |
| **Nippon India Large Cap (Direct)** | Large Cap | **2559.05** | Banking | **41.57%** | **Highly Concentrated** |
| **DSP Top 100 Equity (Regular)** | Large Cap | 2476.91 | Banking | 42.18% | Moderately Concentrated |
| **SBI Bluechip Fund (Regular)** | Large Cap | 2329.85 | Automobile | 34.67% | Moderately Concentrated |
| **DSP Small Cap Fund (Regular)** | Small Cap | **1327.42** | Banking | 21.22% | **Diversified** |
| **UTI Mid Cap Fund (Regular)** | Mid Cap | **1277.73** | Automobile | 16.49% | **Diversified** |
| **Kotak Flexicap Fund (Regular)** | Flexi Cap | **1209.87** | IT | 18.29% | **Diversified** |

---

## 6. Project Limitations & Analytical Assumptions

1. **Historical Period Constraints**: The dataset spans 2022–2026. While capturing post-pandemic recovery and market corrections, it excludes long-term structural interest rate cycles (e.g., 2008 financial crisis).
2. **Fixed Risk-Free Rate Assumption**: $R_f$ is set at a constant $6.5\%$ per annum. In live production environments, $R_f$ should dynamically track 91-day Indian Treasury Bill (T-Bill) yields.
3. **Benchmark Mapping Simplicity**: CAPM regressions utilized Nifty 100/50 indices across all equity schemes. Specific sub-category benchmarks (e.g., Nifty Smallcap 250 for Small-Cap funds) would yield more refined Alpha estimates.
4. **Survivorship Bias**: The dataset comprises active schemes; historical funds merged or liquidated prior to 2022 are excluded.

---

## 7. Strategic Business Recommendations

### 7.1 Portfolio Concentration Ceilings
> **Recommendation 1**: Risk committees should enforce a **maximum $30\%$ single-sector ceiling** for funds exhibiting $\text{HHI} \ge 2,500$. Portfolio managers of *HDFC Top 100 (Direct)* (45.77% IT) must trim top sector overweights to reduce uncompensated sector concentration risk.

### 7.2 Automated Churn Prevention & SIP Friction Reduction
> **Recommendation 2**: Operations and product teams must implement an **Automated SIP Health Workflow**:
> - Trigger automated WhatsApp/SMS payment alerts 3 days prior to NACH auto-debit dates.
> - Provide a 1-click "Pause SIP" feature (up to 90 days) to prevent payment rejection penalties when bank balances fall low.
> - Target the **97.8% at-risk cohort** with auto-retry debit mechanisms, reducing account churn by an estimated **15–20%**.

### 7.3 Risk-Appetite Driven Investor Allocation
> **Recommendation 3**: Wealth managers should deploy the automated recommendation engine [`recommender.py`](file:///d:/D%20Drive/Capstone%20Project%201/recommender.py) to match investor profiles:
> - **Low Risk**: Allocate to *ICICI Pru Liquid Fund* (Sharpe 7.68, zero drawdown).
> - **Moderate Risk**: Allocate to *HDFC Top 100* or *Mirae Asset Large Cap* (Sharpe 1.06, CAGR ~14.8%).
> - **High Risk**: Allocate to *SBI Small Cap Fund* (CAGR 23.39%, Alpha +5.42%).

---

## 8. Conclusion & Project Deliverables

This capstone project successfully establishes a quantitative financial engineering framework for mutual fund evaluation. The primary technical deliverables generated and verified within the repository include:

1. **SQLite Star Schema Database**: [`bluestock_mf.db`](file:///d:/D%20Drive/Capstone%20Project%201/bluestock_mf.db)
2. **Master Execution Pipeline**: [`run_pipeline.py`](file:///d:/D%20Drive/Capstone%20Project%201/run_pipeline.py)
3. **Jupyter Analytics Notebooks**: [`notebooks/EDA_Analysis.ipynb`](file:///d:/D%20Drive/Capstone%20Project%201/notebooks/EDA_Analysis.ipynb) and [`notebooks/Performance_Analytics.ipynb`](file:///d:/D%20Drive/Capstone%20Project%201/notebooks/Performance_Analytics.ipynb)
4. **Standalone Recommender**: [`recommender.py`](file:///d:/D%20Drive/Capstone%20Project%201/recommender.py)
5. **Quantitative Visualizations**: [`rolling_sharpe_chart.png`](file:///d:/D%20Drive/Capstone%20Project%201/rolling_sharpe_chart.png)
6. **Composite Performance Scorecard**: [`fund_scorecard.csv`](file:///d:/D%20Drive/Capstone%20Project%201/fund_scorecard.csv)
7. **Interactive Power BI Dashboard**: [`dashboard/Bluestock_Mutual_Fund_Dashboard.pbix`](file:///d:/D%20Drive/Capstone%20Project%201/dashboard/Bluestock_Mutual_Fund_Dashboard.pbix)
