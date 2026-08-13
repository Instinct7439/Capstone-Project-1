"""
Database Loader Module

Reads processed CSV files from data/processed/, builds a SQLite relational star schema 
(bluestock_mf.db), populates dimension tables (dim_fund, dim_date) and fact tables 
(fact_nav, fact_performance, fact_transactions).
"""

import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DB_PATH = BASE_DIR / "data" / "db" / "bluestock_mf.db"
SCHEMA_PATH = BASE_DIR / "sql" / "schema.sql"

STAR_SCHEMA_FILE_MAP = {
    "01_fund_master.csv": "dim_fund",
    "02_nav_history.csv": "fact_nav",
    "07_scheme_performance.csv": "fact_performance",
    "08_investor_transactions.csv": "fact_transactions",
}

STAR_SCHEMA_COLUMNS = {
    "dim_fund": [
        "amfi_code",
        "fund_house",
        "scheme_name",
        "category",
        "sub_category",
        "plan",
        "risk_category",
        "benchmark",
        "morningstar_rating",
    ],
    "fact_nav": ["amfi_code", "date", "nav"],
    "fact_performance": [
        "amfi_code",
        "date",
        "return_1yr_pct",
        "return_3yr_pct",
        "return_5yr_pct",
        "benchmark_3yr_pct",
        "alpha",
        "beta",
        "sharpe_ratio",
        "sortino_ratio",
        "std_dev_ann_pct",
        "max_drawdown_pct",
        "aum_crore",
        "expense_ratio_pct",
    ],
    "fact_transactions": [
        "investor_id",
        "amfi_code",
        "date",
        "transaction_type",
        "amount_inr",
        "state",
        "city",
        "city_tier",
        "age_group",
        "gender",
        "annual_income_lakh",
        "payment_mode",
        "kyc_status",
    ],
}

DATE_COLUMNS_TO_SCAN = [
    "date",
    "transaction_date",
    "portfolio_date",
]


def load_schema(engine) -> None:
    """
    Executes the DDL schema SQL script against the SQLite database engine.

    Parameters:
        engine (Engine): SQLAlchemy database engine connection.
    """
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

    print(f"Loading star schema from {SCHEMA_PATH}")
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with engine.begin() as conn:
        raw_connection = conn.connection
        raw_connection.executescript(schema_sql)


def clean_table_columns(table_name: str, df: pd.DataFrame) -> pd.DataFrame:
    """
    Filters DataFrame columns to strictly match expected SQLite star schema columns.

    Parameters:
        table_name (str): Target table name.
        df (pd.DataFrame): Input DataFrame.

    Returns:
        pd.DataFrame: Cleaned DataFrame with aligned schema columns.
    """
    expected_columns = STAR_SCHEMA_COLUMNS.get(table_name)
    if not expected_columns:
        return df

    df = df.copy()
    if table_name == "fact_transactions" and "transaction_date" in df.columns:
        df = df.rename(columns={"transaction_date": "date"})

    available_columns = [col for col in expected_columns if col in df.columns]
    missing_columns = [col for col in expected_columns if col not in available_columns]
    if missing_columns:
        print(f"  Warning: table {table_name} is missing columns {missing_columns}; they will be left NULL if the table schema allows it.")
    return df[available_columns]


def build_dim_date(engine) -> int:
    """
    Scans processed dataset CSV files for date fields and populates the dim_date table.

    Parameters:
        engine (Engine): SQLAlchemy database engine connection.

    Returns:
        int: Count of inserted date dimension records.
    """
    print("Building dim_date from processed CSV date columns")
    all_dates = set()
    for csv_path in sorted(PROCESSED_DIR.glob("*.csv")):
        df = pd.read_csv(csv_path)
        for date_col in DATE_COLUMNS_TO_SCAN:
            if date_col in df.columns:
                parsed = pd.to_datetime(df[date_col], errors="coerce")
                formatted = parsed.dt.strftime("%Y-%m-%d").dropna().unique()
                all_dates.update(formatted)


    date_rows = []
    for date_value in sorted(all_dates):
        parsed = pd.to_datetime(date_value, format="%Y-%m-%d", errors="coerce")
        if pd.isna(parsed):
            continue
        fiscal_year = f"FY{parsed.year if parsed.month >= 4 else parsed.year - 1}-{parsed.year + 1 if parsed.month >= 4 else parsed.year}"
        date_rows.append(
            {
                "date": parsed.strftime("%Y-%m-%d"),
                "year": int(parsed.year),
                "quarter": int(parsed.quarter),
                "month": int(parsed.month),
                "day": int(parsed.day),
                "day_of_week": int(parsed.dayofweek),
                "is_weekend": int(parsed.dayofweek >= 5),
                "fiscal_year": fiscal_year,
            }
        )

    if not date_rows:
        print("  No date values found for dim_date population.")
        return 0

    date_df = pd.DataFrame(date_rows)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM dim_date"))
    date_df.to_sql("dim_date", engine, if_exists="append", index=False)
    print(f"  Loaded {len(date_df)} rows into dim_date")
    return len(date_df)


def load_csv_to_table(engine, csv_path: Path, table_name: str) -> int:
    """
    Reads a processed CSV file and writes its contents into the corresponding SQLite database table.

    Parameters:
        engine (Engine): SQLAlchemy database engine connection.
        csv_path (Path): Path to the processed CSV file.
        table_name (str): Target SQLite table name.

    Returns:
        int: Number of rows inserted into the table.
    """
    print(f"Loading {csv_path.name} into table {table_name}")
    df = pd.read_csv(csv_path)
    if table_name in STAR_SCHEMA_COLUMNS:
        df = clean_table_columns(table_name, df)
        if df.empty:
            print(f"  Warning: no data available for {table_name}")
        with engine.begin() as conn:
            conn.execute(text(f"DELETE FROM \"{table_name}\""))
        df.to_sql(table_name, engine, if_exists="append", index=False)
    else:
        df.to_sql(table_name, engine, if_exists="replace", index=False)
    print(f"  Wrote {len(df)} rows to {table_name}")
    return len(df)


def main() -> None:
    """
    Orchestrates SQLite database creation, schema loading, and data insertion from data/processed/.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed existing database at {DB_PATH}")

    engine = create_engine(f"sqlite:///{DB_PATH}")
    print(f"Using SQLite database at {DB_PATH}")

    if not PROCESSED_DIR.exists():
        raise FileNotFoundError(f"Processed data directory not found: {PROCESSED_DIR}")

    load_schema(engine)

    table_counts = {}
    for csv_path in sorted(PROCESSED_DIR.glob("*.csv")):
        table_name = STAR_SCHEMA_FILE_MAP.get(csv_path.name)
        if table_name:
            table_counts[table_name] = load_csv_to_table(engine, csv_path, table_name)
        else:
            raw_table_name = f"raw_{csv_path.stem.lower().replace('-','_')}"
            table_counts[raw_table_name] = load_csv_to_table(engine, csv_path, raw_table_name)

    dim_date_count = build_dim_date(engine)
    if dim_date_count is not None:
        table_counts["dim_date"] = dim_date_count

    print("\nVerification: row counts in SQLite tables")
    with engine.connect() as conn:
        for table_name, source_count in table_counts.items():
            result = conn.execute(text(f"SELECT COUNT(*) AS row_count FROM \"{table_name}\""))
            row_count = result.scalar_one()
            print(f"  {table_name}: database={row_count}, source_csv={source_count}")

    print("DB load complete.")


if __name__ == "__main__":
    main()

