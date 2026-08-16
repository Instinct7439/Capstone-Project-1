"""
Live NAV Fetcher Module

Fetches real-time mutual fund NAV history data from the public RapidAPI/MF API endpoint 
(mfapi.in) for predefined AMFI codes stored in the SQLite database and appends new 
NAV records into fact_nav in data/db/bluestock_mf.db.
"""

import os
import sqlite3
import time
from datetime import datetime
import requests

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(BASE_DIR, "data", "db", "bluestock_mf.db")
API_URL = "https://api.mfapi.in/mf/{amfi_code}"
DELAY_SECONDS = 0.3


def get_amfi_codes(db_path: str = DB_PATH) -> list:
    """
    Fetches the target list of AMFI codes from dim_fund table in SQLite DB.

    Parameters:
        db_path (str): File path to SQLite database.

    Returns:
        list: List of integer AMFI scheme codes.
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT amfi_code FROM dim_fund")
    codes = [row[0] for row in cursor.fetchall()]
    conn.close()
    return sorted(codes)


def ensure_unique_indexes(conn: sqlite3.Connection) -> None:
    """
    Ensures UNIQUE indexes exist on fact_nav(amfi_code, date) and dim_date(date)
    so INSERT OR IGNORE SQL statements function as idempotent appends.

    Parameters:
        conn (sqlite3.Connection): Active SQLite database connection.
    """
    cursor = conn.cursor()
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_fact_nav_amfi_date ON fact_nav(amfi_code, date)")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_date_date ON dim_date(date)")
    conn.commit()


def parse_date_to_iso(date_str: str) -> str:
    """
    Converts DD-MM-YYYY date string from mfapi.in into YYYY-MM-DD ISO format.

    Parameters:
        date_str (str): Date string formatted as 'DD-MM-YYYY'.

    Returns:
        str: ISO formatted date string 'YYYY-MM-DD'.
    """
    dt = datetime.strptime(date_str.strip(), "%d-%m-%Y")
    return dt.strftime("%Y-%m-%d")


def populate_dim_date(conn: sqlite3.Connection, iso_date: str) -> None:
    """
    Appends a new date entry into dim_date if it does not already exist.

    Parameters:
        conn (sqlite3.Connection): Database connection.
        iso_date (str): Date string in 'YYYY-MM-DD' format.
    """
    dt = datetime.strptime(iso_date, "%Y-%m-%d")
    fiscal_year = f"FY{dt.year if dt.month >= 4 else dt.year - 1}-{dt.year + 1 if dt.month >= 4 else dt.year}"

    query = """
        INSERT OR IGNORE INTO dim_date (date, year, quarter, month, day, day_of_week, is_weekend, fiscal_year)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        iso_date,
        dt.year,
        (dt.month - 1) // 3 + 1,
        dt.month,
        dt.day,
        dt.weekday(),
        1 if dt.weekday() >= 5 else 0,
        fiscal_year,
    )
    conn.execute(query, params)


def fetch_latest_nav(amfi_code: int) -> dict:
    """
    Hits mfapi.in API for a given AMFI scheme code and returns the latest NAV record dict.

    Parameters:
        amfi_code (int): AMFI scheme identifier.

    Returns:
        dict: Parsed NAV payload containing amfi_code, ISO date, float nav, and scheme_name.
    """
    url = API_URL.format(amfi_code=amfi_code)
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    payload = response.json()

    data = payload.get("data", [])
    if not data:
        return None

    latest_record = data[0]
    iso_date = parse_date_to_iso(latest_record["date"])
    nav_val = float(latest_record["nav"])

    return {
        "amfi_code": amfi_code,
        "date": iso_date,
        "nav": nav_val,
        "scheme_name": payload.get("meta", {}).get("scheme_name", ""),
    }


def update_live_navs(db_path: str = DB_PATH) -> None:
    """
    Iterates over target AMFI codes, fetches current NAV data, and executes INSERT OR IGNORE
    to append new daily NAV records into fact_nav table in data/db/bluestock_mf.db.

    Parameters:
        db_path (str): Path to SQLite database.
    """
    print("=" * 80)
    print("STARTING LIVE NAV FETCH & DATABASE SYNC")
    print("=" * 80)
    print(f"Target Database : {db_path}")

    codes = get_amfi_codes(db_path)
    print(f"Target AMFI Codes: {len(codes)} schemes retrieved from dim_fund")

    conn = sqlite3.connect(db_path)
    ensure_unique_indexes(conn)

    inserted_count = 0
    skipped_count = 0
    failed_count = 0

    for idx, amfi_code in enumerate(codes, start=1):
        try:
            nav_data = fetch_latest_nav(amfi_code)
            if not nav_data:
                print(f"[{idx:02d}/{len(codes)}] AMFI {amfi_code}: No data returned by API")
                failed_count += 1
                continue

            iso_date = nav_data["date"]
            nav_val = nav_data["nav"]

            # Populate date dimension
            populate_dim_date(conn, iso_date)

            # Insert into fact_nav using INSERT OR IGNORE
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO fact_nav (amfi_code, date, nav) VALUES (?, ?, ?)",
                (amfi_code, iso_date, nav_val),
            )

            if cursor.rowcount > 0:
                inserted_count += 1
                print(f"[{idx:02d}/{len(codes)}] AMFI {amfi_code}: INSERTED NAV {nav_val} for {iso_date}")
            else:
                skipped_count += 1
                print(f"[{idx:02d}/{len(codes)}] AMFI {amfi_code}: IGNORED (NAV for {iso_date} already present)")

            conn.commit()

        except Exception as exc:
            print(f"[{idx:02d}/{len(codes)}] AMFI {amfi_code}: ERROR - {exc}")
            failed_count += 1

        time.sleep(DELAY_SECONDS)

    conn.close()

    print("=" * 80)
    print("LIVE NAV FETCH & SYNC COMPLETE")
    print(f"  Inserted Records : {inserted_count}")
    print(f"  Skipped (Exists) : {skipped_count}")
    print(f"  Failed / No Data : {failed_count}")
    print("=" * 80)


if __name__ == "__main__":
    update_live_navs()
