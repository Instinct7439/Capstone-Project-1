"""
Data Cleaning Module

Performs data transformation, data type coercion, standardizing transaction and 
KYC categories, forward-filling missing NAV values, and saving cleaned datasets to data/processed/.
"""

import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
DATASET_FILES = [
    "01_fund_master.csv",
    "02_nav_history.csv",
    "03_aum_by_fund_house.csv",
    "04_monthly_sip_inflows.csv",
    "05_category_inflows.csv",
    "06_industry_folio_count.csv",
    "07_scheme_performance.csv",
    "08_investor_transactions.csv",
    "09_portfolio_holdings.csv",
    "10_benchmark_indices.csv",
]

TRANSACTION_TYPE_MAP = {
    "sip": "SIP",
    "sips": "SIP",
    "lumpsum": "Lumpsum",
    "lump sum": "Lumpsum",
    "lump-sum": "Lumpsum",
    "lump": "Lumpsum",
    "redemption": "Redemption",
    "redeem": "Redemption",
    "redemptions": "Redemption",
}

KYC_STATUS_MAP = {
    "verified": "Verified",
    "pending": "Pending",
    "rejected": "Rejected",
    "expired": "Expired",
    "not verified": "Not Verified",
    "not_verified": "Not Verified",
}


def standardize_transaction_type(raw_value: str) -> str:
    """
    Standardizes transaction type labels into canonical categories: SIP, Lumpsum, Redemption.

    Parameters:
        raw_value (str): Uncleaned transaction type string.

    Returns:
        str: Standardized transaction type category or 'Unknown'.
    """
    if pd.isna(raw_value):
        return "Unknown"
    normalized = str(raw_value).strip().lower()
    normalized = normalized.replace("_", " ").replace("-", " ")
    if normalized in TRANSACTION_TYPE_MAP:
        return TRANSACTION_TYPE_MAP[normalized]
    if "sip" in normalized:
        return "SIP"
    if "lump" in normalized:
        return "Lumpsum"
    if "redempt" in normalized:
        return "Redemption"
    return "Unknown"


def standardize_kyc_status(raw_value: str) -> str:
    """
    Standardizes KYC status string values into clean status categories.

    Parameters:
        raw_value (str): Uncleaned KYC status value.

    Returns:
        str: Standardized status string or 'Unknown'.
    """
    if pd.isna(raw_value):
        return "Unknown"
    normalized = str(raw_value).strip().lower()
    normalized = normalized.replace("_", " ")
    return KYC_STATUS_MAP.get(normalized, "Unknown")



def clean_nav_history(source_path: Path, dest_path: Path) -> pd.DataFrame:
    """
    Cleans daily NAV history datasets by sorting by date, removing duplicate entries, 
    forward-filling missing NAV values, and filtering non-positive NAV numbers.

    Parameters:
        source_path (Path): Path to raw NAV history CSV file.
        dest_path (Path): Destination path for processed CSV output.

    Returns:
        pd.DataFrame: Cleaned NAV history DataFrame.
    """
    print(f"Cleaning NAV history: {source_path.name}")
    df = pd.read_csv(source_path)

    if "date" not in df.columns or "nav" not in df.columns or "amfi_code" not in df.columns:
        raise ValueError("NAV history file must contain amfi_code, date, and nav columns.")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    bad_dates = df["date"].isna().sum()
    if bad_dates:
        print(f"  Warning: {bad_dates} rows with invalid or missing dates will remain NaT.")

    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    if df["nav"].isna().any():
        print(f"  Found {df['nav'].isna().sum()} rows with missing or non-numeric NAV values before forward fill.")

    df = df.sort_values(["amfi_code", "date"])
    df = df.drop_duplicates(["amfi_code", "date"], keep="last")

    df["nav"] = df.groupby("amfi_code")["nav"].ffill()

    missing_nav_after = df["nav"].isna().sum()
    if missing_nav_after:
        print(f"  After forward fill, {missing_nav_after} rows still have missing NAV values.")

    invalid_nav = df["nav"] <= 0
    if invalid_nav.any():
        print(f"  Warning: {invalid_nav.sum()} rows contain non-positive NAV values and will be removed.")
        df = df.loc[~invalid_nav].copy()

    df.to_csv(dest_path, index=False)
    print(f"  Saved cleaned NAV history to {dest_path.name}")
    return df


def clean_investor_transactions(source_path: Path, dest_path: Path) -> pd.DataFrame:
    """
    Cleans investor transaction records, standardizing transaction types, 
    verifying positive transaction amounts, and parsing KYC status.

    Parameters:
        source_path (Path): Path to raw investor transactions CSV file.
        dest_path (Path): Destination path for processed CSV output.

    Returns:
        pd.DataFrame: Cleaned investor transactions DataFrame.
    """
    print(f"Cleaning investor transactions: {source_path.name}")
    df = pd.read_csv(source_path)

    if "transaction_date" not in df.columns or "transaction_type" not in df.columns or "amount_inr" not in df.columns:
        raise ValueError("Investor transactions file must contain transaction_date, transaction_type, and amount_inr columns.")

    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    invalid_dates = df["transaction_date"].isna().sum()
    if invalid_dates:
        print(f"  Warning: {invalid_dates} rows had invalid transaction dates and will be preserved as NaT.")

    df["transaction_type"] = df["transaction_type"].apply(standardize_transaction_type)
    unknown_types = (df["transaction_type"] == "Unknown").sum()
    if unknown_types:
        print(f"  Warning: {unknown_types} rows have unrecognized transaction_type values and were marked Unknown.")

    df["amount_inr"] = pd.to_numeric(df["amount_inr"], errors="coerce")
    invalid_amounts = df["amount_inr"] <= 0
    invalid_amounts = invalid_amounts | df["amount_inr"].isna()
    if invalid_amounts.any():
        print(f"  Warning: {invalid_amounts.sum()} rows have invalid amount_inr values and will be removed.")
        df = df.loc[~invalid_amounts].copy()

    df["kyc_status"] = df["kyc_status"].apply(standardize_kyc_status)
    unknown_kyc = (df["kyc_status"] == "Unknown").sum()
    if unknown_kyc:
        print(f"  Warning: {unknown_kyc} rows have unrecognized KYC status values and were marked Unknown.")

    df.to_csv(dest_path, index=False)
    print(f"  Saved cleaned investor transactions to {dest_path.name}")
    return df


def clean_scheme_performance(source_path: Path, dest_path: Path) -> pd.DataFrame:
    """
    Validates and cleans mutual fund scheme performance metrics, flagging out-of-range 
    expense ratios and numeric CAGR metrics.

    Parameters:
        source_path (Path): Path to raw scheme performance CSV file.
        dest_path (Path): Destination path for processed CSV output.

    Returns:
        pd.DataFrame: Cleaned scheme performance DataFrame.
    """
    print(f"Cleaning scheme performance: {source_path.name}")
    df = pd.read_csv(source_path)

    return_columns = [
        "return_1yr_pct",
        "return_3yr_pct",
        "return_5yr_pct",
    ]
    for column in return_columns:
        if column not in df.columns:
            raise ValueError(f"Scheme performance file must contain '{column}' column.")

    for column in return_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")
        bad_count = df[column].isna().sum()
        if bad_count:
            print(f"  Warning: {bad_count} rows have non-numeric values in '{column}'.")

    if "expense_ratio_pct" not in df.columns:
        raise ValueError("Scheme performance file must contain expense_ratio_pct column.")

    df["expense_ratio_pct"] = pd.to_numeric(df["expense_ratio_pct"], errors="coerce")
    out_of_range = ~df["expense_ratio_pct"].between(0.1, 2.5)
    issue_count = out_of_range.sum()
    if issue_count:
        print(f"  Warning: {issue_count} rows have expense_ratio_pct outside the accepted range (0.1 - 2.5).")

    df["expense_ratio_flag"] = np.where(out_of_range, "OUT_OF_RANGE", "OK")
    df.to_csv(dest_path, index=False)
    print(f"  Saved cleaned scheme performance to {dest_path.name}")
    return df


def copy_raw_file(source_path: Path, dest_path: Path) -> None:
    """
    Copies verified raw CSV files directly to the data/processed directory.

    Parameters:
        source_path (Path): Source raw file path.
        dest_path (Path): Destination processed file path.
    """
    print(f"Copying raw dataset: {source_path.name}")
    shutil.copy2(source_path, dest_path)
    print(f"  Copied {source_path.name} to processed folder")


def main() -> None:
    """
    Executes data cleaning pipeline across all raw CSV files in data/raw/.
    """
    try:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Processing files from {RAW_DIR} to {PROCESSED_DIR}")

        actual_files = [p.name for p in RAW_DIR.glob("*.csv") if p.name in DATASET_FILES]
        missing_files = sorted(set(DATASET_FILES) - set(actual_files))
        if missing_files:
            raise FileNotFoundError(f"Required raw dataset files missing: {missing_files}")

        for filename in DATASET_FILES:
            source = RAW_DIR / filename
            destination = PROCESSED_DIR / filename

            if filename == "02_nav_history.csv":
                clean_nav_history(source, destination)
            elif filename == "08_investor_transactions.csv":
                clean_investor_transactions(source, destination)
            elif filename == "07_scheme_performance.csv":
                clean_scheme_performance(source, destination)
            else:
                copy_raw_file(source, destination)

        output_files = list(PROCESSED_DIR.glob("*.csv"))
        print(f"Finished processing. {len(output_files)} CSV files are available in {PROCESSED_DIR}")

    except Exception as exc:
        print(f"Error during data cleaning: {exc}")


if __name__ == "__main__":
    main()

