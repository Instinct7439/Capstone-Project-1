import os
import glob
import pandas as pd


def main():
    raw_data_dir = os.path.join(os.path.dirname(__file__), "data", "raw")
    csv_paths = sorted(glob.glob(os.path.join(raw_data_dir, "*.csv")))

    if not csv_paths:
        print(f"No CSV files found in {raw_data_dir}")
        return

    for csv_path in csv_paths:
        print("=" * 80)
        print(f"Reading: {csv_path}")
        try:
            df = pd.read_csv(csv_path)
            print(f"Shape: {df.shape}")
            print("Data types:")
            print(df.dtypes)
            print("Head:")
            print(df.head())
            print("Missing values by column:")
            print(df.isnull().sum())
        except Exception as exc:
            print(f"Failed to read {csv_path}: {exc}")


if __name__ == "__main__":
    main()
