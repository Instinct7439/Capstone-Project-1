"""
Mutual Fund Recommender Module

Filters mutual funds by user risk appetite (Low, Moderate, High) 
and returns the top 3 recommended schemes sorted by Sharpe ratio.
"""

import sqlite3
import pandas as pd


def load_fund_data(db_path: str = 'bluestock_mf.db') -> pd.DataFrame:
    """
    Loads and merges mutual fund performance data from the database.

    Parameters:
        db_path (str): File path to SQLite database.

    Returns:
        pd.DataFrame: Merged DataFrame containing fund metadata and performance metrics.
    """
    conn = sqlite3.connect(db_path)
    df_fund = pd.read_sql_query(
        "SELECT amfi_code, scheme_name, fund_house, category, risk_category FROM dim_fund", 
        conn
    )
    df_perf = pd.read_sql_query(
        "SELECT amfi_code, return_3yr_pct, sharpe_ratio, expense_ratio_pct FROM fact_performance", 
        conn
    )
    conn.close()
    
    merged_df = pd.merge(df_fund, df_perf, on='amfi_code')
    merged_df['risk_grade'] = merged_df['risk_category']
    return merged_df


def recommend_funds(risk_appetite: str, df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Recommends top 3 mutual funds matching a user's risk appetite sorted by Sharpe ratio.
    
    Parameters:
        risk_appetite (str): Target risk grade ('Low', 'Moderate', or 'High')
        df (pd.DataFrame): Optional performance DataFrame. If None, loads from SQLite DB.
        
    Returns:
        pd.DataFrame: Top 3 recommended funds sorted by Sharpe ratio in descending order.
    """
    if df is None:
        df = load_fund_data()
        
    user_risk = risk_appetite.strip().lower()
    
    if user_risk == 'low':
        target_grades = ['low', 'low to moderate']
    elif user_risk == 'moderate':
        target_grades = ['moderate', 'moderately high']
    elif user_risk == 'high':
        target_grades = ['high', 'very high']
    else:
        target_grades = [user_risk]
        
    filtered_df = df[df['risk_grade'].str.lower().isin(target_grades)].copy()
    
    if filtered_df.empty:
        filtered_df = df[df['risk_grade'].str.lower().str.contains(user_risk)].copy()
        
    if filtered_df.empty:
        print(f"No funds found matching risk grade: '{risk_appetite}'.")
        return pd.DataFrame()
        
    top_3_funds = filtered_df.sort_values(by='sharpe_ratio', ascending=False).head(3).copy()
    
    display_cols = ['amfi_code', 'scheme_name', 'category', 'risk_grade', 'sharpe_ratio', 'return_3yr_pct', 'expense_ratio_pct']
    recommendation_table = top_3_funds[[c for c in display_cols if c in top_3_funds.columns]].reset_index(drop=True)
    
    print("\n" + "=" * 90)
    print(f" RECOMMENDATION REPORT: TOP 3 FUNDS FOR RISK APPETITE [{risk_appetite.upper()}]")
    print("=" * 90)
    print(recommendation_table.to_string(index=False))
    print("=" * 90 + "\n")
    
    return recommendation_table


if __name__ == '__main__':
    for appetite in ['Low', 'Moderate', 'High']:
        recommend_funds(appetite)
