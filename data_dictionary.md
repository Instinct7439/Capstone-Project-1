# Mutual Fund Star Schema Data Dictionary

## dim_fund
| Column | Data Type | Business Definition | Source Reference |
|---|---|---|---|
| amfi_code | INTEGER | Unique AMFI code identifier for each mutual fund scheme. | `01_fund_master.csv` |
| scheme_name | TEXT | Official scheme name of the mutual fund. | `01_fund_master.csv` |
| fund_house | TEXT | Asset management company or fund house managing the scheme. | `01_fund_master.csv` |
| category | TEXT | Primary fund category or asset class (e.g., Equity, Debt, Hybrid). | `01_fund_master.csv` |
| sub_category | TEXT | More granular scheme classification within the category. | `01_fund_master.csv` |
| plan | TEXT | Plan type for the scheme, typically Regular or Direct. | `01_fund_master.csv` |
| risk_category | TEXT | Qualitative risk bucket assigned to the scheme. | `01_fund_master.csv` |
| benchmark | TEXT | Index benchmark used for scheme performance comparison. | `01_fund_master.csv` |
| morningstar_rating | INTEGER | Morningstar star rating score, if available. | `01_fund_master.csv` |

## dim_date
| Column | Data Type | Business Definition | Source Reference |
|---|---|---|---|
| date | TEXT | Canonical date key in `YYYY-MM-DD` format. | Derived from all processed date fields across CSVs |
| year | INTEGER | Calendar year extracted from the date. | Derived from date values |
| quarter | INTEGER | Calendar quarter extracted from the date. | Derived from date values |
| month | INTEGER | Calendar month extracted from the date. | Derived from date values |
| day | INTEGER | Day of month extracted from the date. | Derived from date values |
| day_of_week | INTEGER | Day of week where Monday = 0 and Sunday = 6. | Derived from date values |
| is_weekend | INTEGER | Binary indicator for weekend dates (1 = weekend, 0 = weekday). | Derived from date values |
| fiscal_year | TEXT | Fiscal year label based on Indian financial year boundaries. | Derived from date values |

## fact_nav
| Column | Data Type | Business Definition | Source Reference |
|---|---|---|---|
| nav_id | INTEGER | Surrogate primary key for NAV records. | Generated during schema load |
| amfi_code | INTEGER | Foreign key linking each NAV record to `dim_fund`. | `02_nav_history.csv` |
| date | TEXT | Foreign key linking each NAV record to `dim_date`. | `02_nav_history.csv` |
| nav | REAL | Net Asset Value per unit for the scheme on the given date. | `02_nav_history.csv` |

## fact_transactions
| Column | Data Type | Business Definition | Source Reference |
|---|---|---|---|
| transaction_id | INTEGER | Surrogate primary key for individual investor transactions. | Generated during schema load |
| investor_id | TEXT | Unique identifier for the investor executing the transaction. | `08_investor_transactions.csv` |
| amfi_code | INTEGER | Foreign key linking each transaction to `dim_fund`. | `08_investor_transactions.csv` |
| date | TEXT | Foreign key linking each transaction to `dim_date`. | `08_investor_transactions.csv` |
| transaction_type | TEXT | Normalized transaction type such as SIP, Lumpsum, or Redemption. | `08_investor_transactions.csv` |
| amount_inr | REAL | Transaction amount in Indian Rupees. | `08_investor_transactions.csv` |
| state | TEXT | Investor state of residence. | `08_investor_transactions.csv` |
| city | TEXT | Investor city of residence. | `08_investor_transactions.csv` |
| city_tier | TEXT | City tier classification, typically Tier 1/2/3. | `08_investor_transactions.csv` |
| age_group | TEXT | Investor age bucket grouping. | `08_investor_transactions.csv` |
| gender | TEXT | Investor gender. | `08_investor_transactions.csv` |
| annual_income_lakh | REAL | Investor annual income in lakhs of INR. | `08_investor_transactions.csv` |
| payment_mode | TEXT | Payment channel used for the transaction. | `08_investor_transactions.csv` |
| kyc_status | TEXT | Know Your Customer verification status. | `08_investor_transactions.csv` |

## fact_performance
| Column | Data Type | Business Definition | Source Reference |
|---|---|---|---|
| performance_id | INTEGER | Surrogate primary key for scheme performance records. | Generated during schema load |
| amfi_code | INTEGER | Foreign key linking each performance record to `dim_fund`. | `07_scheme_performance.csv` |
| date | TEXT | Foreign key linking performance records to `dim_date`, if available. | Derived as available from processed data |
| return_1yr_pct | REAL | One-year trailing return percentage. | `07_scheme_performance.csv` |
| return_3yr_pct | REAL | Three-year trailing return percentage. | `07_scheme_performance.csv` |
| return_5yr_pct | REAL | Five-year trailing return percentage. | `07_scheme_performance.csv` |
| benchmark_3yr_pct | REAL | Three-year benchmark return percentage. | `07_scheme_performance.csv` |
| alpha | REAL | Alpha coefficient relative to benchmark performance. | `07_scheme_performance.csv` |
| beta | REAL | Beta coefficient measuring volatility vs benchmark. | `07_scheme_performance.csv` |
| sharpe_ratio | REAL | Sharpe ratio assessing risk-adjusted returns. | `07_scheme_performance.csv` |
| sortino_ratio | REAL | Sortino ratio measuring downside risk-adjusted returns. | `07_scheme_performance.csv` |
| std_dev_ann_pct | REAL | Annualized standard deviation of returns. | `07_scheme_performance.csv` |
| max_drawdown_pct | REAL | Maximum drawdown percentage over the period. | `07_scheme_performance.csv` |
| aum_crore | REAL | Assets under management in crores of INR. | `07_scheme_performance.csv` |
| expense_ratio_pct | REAL | Annual expense ratio percentage. | `07_scheme_performance.csv` |
