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

            # Anomaly detection: report duplicate rows and summary statistics
            try:
                dup_count = int(df.duplicated().sum())
                print(f"Total duplicate rows: {dup_count}")
            except Exception as e:
                print(f"Failed to compute duplicate rows: {e}")

            print("Summary statistics (describe):")
            try:
                # include='all' to show stats for non-numeric columns as well
                print(df.describe(include='all'))
            except Exception as e:
                print(f"Failed to produce describe(): {e}")
        except Exception as exc:
            print(f"Failed to read {csv_path}: {exc}")


if __name__ == "__main__":
    main()
