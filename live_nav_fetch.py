"""
Live NAV Fetcher Module

Fetches real-time mutual fund NAV history data from the public RapidAPI/MF API endpoint 
and saves scheme-specific NAV CSV files to data/raw/.
"""

import os
import time
import requests
import pandas as pd


SCHEME_CODES = [125497, 119551, 120503, 118632, 119092, 120841]
BASE_URL = "https://api.mfapi.in/mf/{scheme_code}"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data", "raw")
DELAY_SECONDS = 1.0


def fetch_nav_data(scheme_code: int) -> list:
    """
    Fetches raw NAV JSON history records for a given AMFI scheme code via HTTP GET.

    Parameters:
        scheme_code (int): AMFI mutual fund scheme identifier.

    Returns:
        list: List of daily NAV dictionaries containing date and nav fields.
    """
    url = BASE_URL.format(scheme_code=scheme_code)
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    payload = response.json()
    if "data" not in payload:
        raise ValueError("API response did not contain expected 'data' field")
    return payload["data"]


def save_nav_csv(scheme_code: int, data_rows: list) -> str:
    """
    Saves fetched NAV history records as a CSV dataset in data/raw/.

    Parameters:
        scheme_code (int): AMFI scheme code.
        data_rows (list): List of NAV record dicts.

    Returns:
        str: Saved output file path.
    """
    df = pd.DataFrame(data_rows)
    output_path = os.path.join(OUTPUT_DIR, f"nav_{scheme_code}.csv")
    df.to_csv(output_path, index=False)
    return output_path


def main() -> None:
    """
    Iterates over target AMFI scheme codes to fetch and store live NAV histories.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for scheme_code in SCHEME_CODES:
        print(f"Fetching NAV history for scheme {scheme_code}...")
        try:
            data_rows = fetch_nav_data(scheme_code)
            csv_path = save_nav_csv(scheme_code, data_rows)
            print(f"Saved {len(data_rows)} rows to {csv_path}")
        except requests.RequestException as exc:
            print(f"Network error fetching data for {scheme_code}: {exc}")
        except ValueError as exc:
            print(f"Invalid response for {scheme_code}: {exc}")
        except Exception as exc:
            print(f"Unexpected error for {scheme_code}: {exc}")
        time.sleep(DELAY_SECONDS)


if __name__ == "__main__":
    main()

