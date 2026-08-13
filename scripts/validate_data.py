"""
Data Validation Module

Validates key relationships, cross-references AMFI identifiers between fund master 
and NAV history datasets, and exports a markdown data quality report.
"""

import os
import pandas as pd


def load_csv(path: str) -> pd.DataFrame:
    """
    Loads a CSV file into a pandas DataFrame, raising FileNotFoundError if missing.

    Parameters:
        path (str): File path to CSV.

    Returns:
        pd.DataFrame: Loaded DataFrame.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    return pd.read_csv(path)


def print_unique_values(df: pd.DataFrame, column_name: str) -> None:
    """
    Prints sorted unique values present in a specified DataFrame column.

    Parameters:
        df (pd.DataFrame): Target DataFrame.
        column_name (str): Column identifier.
    """
    if column_name not in df.columns:
        print(f"Column '{column_name}' not found in dataset.")
        return
    unique_vals = df[column_name].dropna().unique()
    print(f"  Unique values in '{column_name}' ({len(unique_vals)}): {sorted(unique_vals)}")


def main() -> None:
    """
    Runs data quality validation checks across raw datasets and outputs reports/day1_data_quality_summary.md.
    """
    fund_master_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw", "01_fund_master.csv"))
    nav_history_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw", "02_nav_history.csv"))

    try:
        fund_master = load_csv(fund_master_path)
        nav_history = load_csv(nav_history_path)
    except Exception as exc:
        print(f"Error loading data: {exc}")
        return

    print("=" * 80)
    print("STARTING DATA VALIDATION CHECKS")
    print("=" * 80)

    print("\nFund Master Unique Category Overview:")
    for column in ["fund_house", "category", "sub_category", "risk_category"]:
        print_unique_values(fund_master, column)

    fund_master_codes = set(fund_master["amfi_code"].dropna().astype(int).unique())
    nav_history_codes = set(nav_history["amfi_code"].dropna().astype(int).unique())

    missing_in_nav = sorted(fund_master_codes - nav_history_codes)
    missing_in_fund_master = sorted(nav_history_codes - fund_master_codes)
    shared_codes = sorted(fund_master_codes & nav_history_codes)

    print("\nAMFI Code Coverage Summary:")
    print(f"  Fund Master unique codes: {len(fund_master_codes)}")
    print(f"  NAV History unique codes: {len(nav_history_codes)}")
    print(f"  Shared AMFI codes: {len(shared_codes)}")
    print(f"  Missing from NAV History: {len(missing_in_nav)}")
    print(f"  Missing from Fund Master: {len(missing_in_fund_master)}")

    summary_lines = []
    summary_lines.append("# Day 1 Data Quality Summary\n")
    summary_lines.append("## Overview\n")
    summary_lines.append(f"- Total unique AMFI codes in fund master: {len(fund_master_codes)}")
    summary_lines.append(f"- Total unique AMFI codes in NAV history: {len(nav_history_codes)}")
    summary_lines.append(f"- AMFI codes present in both datasets: {len(shared_codes)}")
    summary_lines.append(f"- AMFI codes missing from NAV history: {len(missing_in_nav)}")
    summary_lines.append(f"- AMFI codes missing from fund master: {len(missing_in_fund_master)}\n")

    if missing_in_nav:
        summary_lines.append("## AMFI codes defined in fund master but not found in NAV history\n")
        summary_lines.append("```")
        summary_lines.extend([str(x) for x in missing_in_nav])
        summary_lines.append("```\n")

    if missing_in_fund_master:
        summary_lines.append("## AMFI codes present in NAV history but not defined in fund master\n")
        summary_lines.append("```")
        summary_lines.extend([str(x) for x in missing_in_fund_master])
        summary_lines.append("```\n")

    summary_lines.append("## Notes\n")
    if missing_in_nav or missing_in_fund_master:
        summary_lines.append("- Warning: Discrepancies found between fund_master and nav_history AMFI codes.")
    else:
        summary_lines.append("- Validation passed: AMFI codes are consistent between fund_master and nav_history.")
    summary_lines.append("- Review unique category and risk labels printed above.\n")

    summary_text = "\n".join(summary_lines)

    reports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))
    try:
        os.makedirs(reports_dir, exist_ok=True)
        summary_path = os.path.join(reports_dir, "day1_data_quality_summary.md")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary_text)
        print(f"\nWrote data quality summary report to: {summary_path}")
    except Exception as exc:
        print(f"Failed to write data quality summary: {exc}")

    print("=" * 80)
    print("DATA VALIDATION CHECKS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()

