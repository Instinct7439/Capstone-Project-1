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
    for column in ["fund_house", "category", "sub_category", "risk_category"]:
        print_unique_values(fund_master, column)

    print("NAV history validation")
    print("-----------------------")
    fund_master_codes = set(fund_master["amfi_code"].dropna().astype(int).unique())
    nav_history_codes = set(nav_history["amfi_code"].dropna().astype(int).unique())

    # AMFI codes defined in fund_master but missing from nav_history
    missing_in_nav = sorted(fund_master_codes - nav_history_codes)
    # AMFI codes present in nav_history but not defined in fund_master (two-way validation)
    missing_in_fund_master = sorted(nav_history_codes - fund_master_codes)
    shared_codes = sorted(fund_master_codes & nav_history_codes)

    print(f"Total unique AMFI codes in fund master: {len(fund_master_codes)}")
    print(f"Total unique AMFI codes in NAV history: {len(nav_history_codes)}")
    print(f"AMFI codes present in both datasets: {len(shared_codes)}")
    print(f"AMFI codes missing from NAV history (defined in fund master but not in NAV): {len(missing_in_nav)}")
    print(f"AMFI codes missing from fund master (present in NAV history but not defined in fund master): {len(missing_in_fund_master)}")

    if missing_in_nav:
        print("Missing AMFI codes in NAV history (listed from fund master):")
        print(missing_in_nav)
    else:
        print("All fund master AMFI codes are present in the NAV history dataset.")

    if missing_in_fund_master:
        print("AMFI codes found in NAV history but missing from fund master:")
        print(missing_in_fund_master)
    else:
        print("All AMFI codes in NAV history are defined in fund master.")

    print()
    print("Data quality summary")
    print("--------------------")

    # Build a markdown-friendly summary
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
        summary_lines.append("- Warning: Discrepancies found between fund_master and nav_history AMFI codes. Investigate identifier mapping and coverage of NAV history files.")
    else:
        summary_lines.append("- Validation passed: AMFI codes are consistent between fund_master and nav_history.")
    summary_lines.append("- Review the unique category and risk labels printed above to understand the scheme structure.\n")

    summary_text = "\n".join(summary_lines)

    # Ensure reports directory exists and write the markdown summary
    reports_dir = os.path.join(os.path.dirname(__file__), "reports")
    try:
        os.makedirs(reports_dir, exist_ok=True)
        summary_path = os.path.join(reports_dir, "day1_data_quality_summary.md")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary_text)
        print(f"Wrote data quality summary to: {summary_path}")
    except Exception as exc:
        print(f"Failed to write data quality summary: {exc}")


if __name__ == "__main__":
    main()
