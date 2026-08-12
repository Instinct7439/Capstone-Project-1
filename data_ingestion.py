"""
Data Ingestion Module

Scans the raw data directory for CSV datasets, inspects schema definitions, 
evaluates missing values, and checks for row duplicates.
"""

import os
import glob
import pandas as pd


def inspect_csv_file(csv_path: str) -> None:
    """
    Inspects a single CSV file, displaying its shape, schema data types, 
    null value counts, duplicate count, and descriptive statistics.

    Parameters:
        csv_path (str): File path to the raw CSV dataset.
    """
    print(f"Reading: {os.path.basename(csv_path)}")
    try:
        df = pd.read_csv(csv_path)
        print(f"  Shape: {df.shape}")
        
        dup_count = int(df.duplicated().sum())
        null_count = int(df.isnull().sum().sum())
        print(f"  Missing values: {null_count} | Duplicate rows: {dup_count}")

    except Exception as exc:
        print(f"  Failed to read {csv_path}: {exc}")


def main() -> None:
    """
    Orchestrates the ingestion scan across all raw CSV files in data/raw/.
    """
    raw_data_dir = os.path.join(os.path.dirname(__file__), "data", "raw")
    csv_paths = sorted(glob.glob(os.path.join(raw_data_dir, "*.csv")))

    if not csv_paths:
        print(f"No CSV files found in {raw_data_dir}")
        return

    print("=" * 80)
    print(f"STARTING DATA INGESTION SCAN ({len(csv_paths)} CSV files found)")
    print("=" * 80)

    for csv_path in csv_paths:
        inspect_csv_file(csv_path)

    print("=" * 80)
    print("DATA INGESTION SCAN COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()

