import sqlite3
import pandas as pd

def load_fund_data(db_path='bluestock_mf.db'):
    """Loads and merges mutual fund performance and metadata."""
    conn = sqlite3.connect(db_path)
    df_fund = pd.read_sql_query("SELECT amfi_code, scheme_name, fund_house, category, risk_category FROM dim_fund", conn)
    df_perf = pd.read_sql_query("SELECT amfi_code, return_3yr_pct, sharpe_ratio, expense_ratio_pct FROM fact_performance", conn)
    conn.close()
    
    merged_df = pd.merge(df_fund, df_perf, on='amfi_code')
    # Rename risk_category to risk_grade for consistent naming
    merged_df['risk_grade'] = merged_df['risk_category']
    return merged_df

def recommend_funds(risk_appetite: str, df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Recommends top 3 mutual funds based on user's risk appetite sorted by Sharpe ratio.
    
    Parameters:
        risk_appetite (str): 'Low', 'Moderate', or 'High'
        df (pd.DataFrame): Optional performance dataframe. If None, loads from SQLite DB.
        
    Returns:
        pd.DataFrame: Top 3 recommended funds sorted by Sharpe ratio descending.
    """
    if df is None:
        df = load_fund_data()
        
    user_risk = risk_appetite.strip().lower()
    
    # Flexible risk matching (e.g. High includes High and Very High)
    if user_risk == 'low':
        target_grades = ['low', 'low to moderate', 'low to moderate risk']
    elif user_risk == 'moderate':
        target_grades = ['moderate', 'moderately high', 'moderate risk']
    elif user_risk == 'high':
        target_grades = ['high', 'very high', 'high risk']
    else:
        target_grades = [user_risk]
        
    # Filter matching risk grade
    filtered_df = df[df['risk_grade'].str.lower().isin(target_grades)].copy()
    
    # Fallback to fuzzy substring match if exact match is empty
    if filtered_df.empty:
        filtered_df = df[df['risk_grade'].str.lower().str.contains(user_risk)].copy()
        
    if filtered_df.empty:
        print(f"No funds found matching risk grade: '{risk_appetite}'.")
        return pd.DataFrame()
        
    # Sort by sharpe_ratio in descending order and select top 3
    top_3_funds = filtered_df.sort_values(by='sharpe_ratio', ascending=False).head(3).copy()
    
    # Select and format display columns
    display_cols = ['amfi_code', 'scheme_name', 'category', 'risk_grade', 'sharpe_ratio', 'return_3yr_pct', 'expense_ratio_pct']
    display_cols = [c for c in display_cols if c in top_3_funds.columns]
    
    recommendation_table = top_3_funds[display_cols].reset_index(drop=True)
    
    print("\n" + "="*85)
    print(f" RECOMMENDATION REPORT: TOP 3 FUNDS FOR RISK APPETITE [{risk_appetite.upper()}]")
    print("="*85)
    print(recommendation_table.to_string(index=False))
    print("="*85 + "\n")
    
    return recommendation_table

if __name__ == '__main__':
    # Demonstrate recommendation for Low, Moderate, and High risk appetites
    for appetite in ['Low', 'Moderate', 'High']:
        recommend_funds(appetite)
