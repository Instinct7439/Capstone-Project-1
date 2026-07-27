import os
import pandas as pd


def load_csv(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    return pd.read_csv(path)


def print_unique_values(df, column_name):
    if column_name not in df.columns:
        print(f"Column '{column_name}' not found in dataset.")
        return
    unique_vals = df[column_name].dropna().unique()
    print(f"Unique values in '{column_name}' ({len(unique_vals)}):")
    print(sorted(unique_vals))
    print()


def main():
    fund_master_path = os.path.join(os.path.dirname(__file__), "data", "raw", "01_fund_master.csv")
    nav_history_path = os.path.join(os.path.dirname(__file__), "data", "raw", "02_nav_history.csv")

    try:
        fund_master = load_csv(fund_master_path)
        nav_history = load_csv(nav_history_path)
    except Exception as exc:
        print(f"Error loading data: {exc}")
        return

    print("Fund master unique value overview")
    print("----------------------------------")
    for column in ["fund_house", "category", "sub_category", "risk_grade"]:
        print_unique_values(fund_master, column)

    print("NAV history validation")
    print("-----------------------")
    fund_master_codes = set(fund_master["amfi_code"].dropna().astype(int).unique())
    nav_history_codes = set(nav_history["amfi_code"].dropna().astype(int).unique())

    missing_in_nav = sorted(fund_master_codes - nav_history_codes)
    shared_codes = sorted(fund_master_codes & nav_history_codes)

    print(f"Total unique AMFI codes in fund master: {len(fund_master_codes)}")
    print(f"Total unique AMFI codes in NAV history: {len(nav_history_codes)}")
    print(f"AMFI codes present in fund master and NAV history: {len(shared_codes)}")
    print(f"AMFI codes missing from NAV history: {len(missing_in_nav)}")

    if missing_in_nav:
        print("Missing AMFI codes:")
        print(missing_in_nav)
    else:
        print("All fund master AMFI codes are present in the NAV history dataset.")

    print()
    print("Data quality summary")
    print("--------------------")
    if missing_in_nav:
        print("Warning: Some AMFI codes defined in fund master do not appear in the NAV history dataset.")
        print("This could indicate incomplete NAV coverage or mismatched identifiers.")
    else:
        print("Validation passed: every AMFI code in fund master exists in NAV history.")
    print("Review the unique category and risk labels above to understand the scheme structure.")


if __name__ == "__main__":
    main()
