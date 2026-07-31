-- Analytical SQL queries for the mutual fund star schema

-- 1. Top 5 funds by latest reported AUM
-- Uses fact_performance to identify the most recently reported AUM for each fund.
SELECT
    f.amfi_code,
    f.scheme_name,
    f.fund_house,
    fp.aum_crore
FROM fact_performance fp
JOIN dim_fund f ON fp.amfi_code = f.amfi_code
WHERE fp.date = (
    SELECT MAX(fp2.date)
    FROM fact_performance fp2
    WHERE fp2.amfi_code = fp.amfi_code
)
ORDER BY fp.aum_crore DESC
LIMIT 5;

-- 2. Average NAV per month across all funds
SELECT
    d.year,
    d.month,
    ROUND(AVG(fn.nav), 4) AS average_nav
FROM fact_nav fn
JOIN dim_date d ON fn.date = d.date
GROUP BY d.year, d.month
ORDER BY d.year, d.month;

-- 3. SIP Year-over-Year growth in total SIP amount
WITH yearly_sip AS (
    SELECT
        d.year,
        SUM(ft.amount_inr) AS total_sip_amount
    FROM fact_transactions ft
    JOIN dim_date d ON ft.date = d.date
    WHERE ft.transaction_type = 'SIP'
    GROUP BY d.year
)
SELECT
    y.year,
    y.total_sip_amount,
    ROUND((y.total_sip_amount - p.total_sip_amount) * 100.0 / p.total_sip_amount, 2) AS yoy_growth_pct
FROM yearly_sip y
LEFT JOIN yearly_sip p ON p.year = y.year - 1
ORDER BY y.year;

-- 4. Transactions by state (count and total amount)
SELECT
    ft.state,
    COUNT(*) AS transaction_count,
    ROUND(SUM(ft.amount_inr), 2) AS total_transaction_amount
FROM fact_transactions ft
GROUP BY ft.state
ORDER BY total_transaction_amount DESC;

-- 5. Funds with expense_ratio below 1%
SELECT
    f.amfi_code,
    f.scheme_name,
    f.fund_house,
    fp.expense_ratio_pct
FROM fact_performance fp
JOIN dim_fund f ON fp.amfi_code = f.amfi_code
WHERE fp.expense_ratio_pct < 1.0
ORDER BY fp.expense_ratio_pct ASC;

-- 6. Top 10 funds by 3-year return, with risk category
SELECT
    f.amfi_code,
    f.scheme_name,
    f.risk_category,
    fp.return_3yr_pct
FROM fact_performance fp
JOIN dim_fund f ON fp.amfi_code = f.amfi_code
ORDER BY fp.return_3yr_pct DESC
LIMIT 10;

-- 7. Average transaction amount by transaction type
SELECT
    ft.transaction_type,
    COUNT(*) AS transaction_count,
    ROUND(AVG(ft.amount_inr), 2) AS avg_amount_inr,
    ROUND(SUM(ft.amount_inr), 2) AS total_amount_inr
FROM fact_transactions ft
GROUP BY ft.transaction_type
ORDER BY total_amount_inr DESC;

-- 8. Funds with the highest Sharpe ratio and acceptable expense ratio (< 1.5%)
SELECT
    f.amfi_code,
    f.scheme_name,
    f.category,
    fp.sharpe_ratio,
    fp.expense_ratio_pct
FROM fact_performance fp
JOIN dim_fund f ON fp.amfi_code = f.amfi_code
WHERE fp.expense_ratio_pct < 1.5
ORDER BY fp.sharpe_ratio DESC
LIMIT 10;

-- 9. Monthly NAV volatility summary by fund count
WITH monthly_nav AS (
    SELECT
        d.year,
        d.month,
        fn.amfi_code,
        fn.nav
    FROM fact_nav fn
    JOIN dim_date d ON fn.date = d.date
)
SELECT
    year,
    month,
    COUNT(DISTINCT amfi_code) AS fund_count,
    ROUND(AVG(nav), 4) AS avg_nav,
    ROUND(
        SQRT(
            AVG((nav - AVG(nav) OVER (PARTITION BY year, month)) * (nav - AVG(nav) OVER (PARTITION BY year, month)))
        ),
        4
    ) AS nav_stddev
FROM monthly_nav
GROUP BY year, month
ORDER BY year, month;

-- 10. Total transaction amount and count by investor, top 10 investors
SELECT
    ft.investor_id,
    COUNT(*) AS transaction_count,
    ROUND(SUM(ft.amount_inr), 2) AS total_invested_inr
FROM fact_transactions ft
GROUP BY ft.investor_id
ORDER BY total_invested_inr DESC
LIMIT 10;
