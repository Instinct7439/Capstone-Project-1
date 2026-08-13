"""
Master ETL and Analytics Execution Pipeline

Sequentially runs the mutual fund data ingestion, cleaning, validation, database loading,
quantitative analytics, and recommendation engine scripts using the subprocess module.
"""

import sys
import os
import time
import subprocess


# List of pipeline scripts to execute sequentially
PIPELINE_STEPS = [
    {
        "name": "Step 1: Data Ingestion & Inspection",
        "script": "data_ingestion.py",
        "description": "Scans raw CSV files and reports dataset shapes, nulls, and duplicate counts."
    },
    {
        "name": "Step 2: Data Cleaning & Transformation",
        "script": "data_cleaning.py",
        "description": "Cleans NAV history, investor transactions, and saves datasets to data/processed/."
    },
    {
        "name": "Step 3: Data Quality Validation",
        "script": "validate_data.py",
        "description": "Cross-references AMFI scheme codes and exports quality report to reports/."
    },
    {
        "name": "Step 4: SQLite Database Loader",
        "script": "db_loader.py",
        "description": "Builds SQLite star schema (data/db/bluestock_mf.db) and loads dimension and fact tables."
    },
    {
        "name": "Step 5: Rolling Sharpe Quantitative Analytics",
        "script": "calculate_rolling_sharpe.py",
        "description": "Calculates 90-day rolling Sharpe ratios and exports rolling_sharpe_chart.png."
    },
    {
        "name": "Step 6: Mutual Fund Recommender",
        "script": "recommender.py",
        "description": "Generates top 3 mutual fund recommendations across Low, Moderate, and High risk grades."
    }
]


def run_script(script_path: str) -> bool:
    """
    Executes a single Python script via subprocess.run, returning True if successful.

    Parameters:
        script_path (str): File path to the Python script to execute.

    Returns:
        bool: True if execution succeeded with returncode 0, False otherwise.
    """
    python_executable = sys.executable
    try:
        result = subprocess.run(
            [python_executable, script_path],
            check=True,
            text=True,
            capture_output=False
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as exc:
        print(f"\n[ERROR] Command '{script_path}' failed with exit code {exc.returncode}.")
        return False
    except Exception as exc:
        print(f"\n[ERROR] Unexpected error running '{script_path}': {exc}")
        return False


def main() -> None:
    """
    Main function to execute the end-to-end data pipeline sequentially with logging and error checking.
    """
    root_dir = os.path.dirname(os.path.abspath(__file__))
    start_time = time.time()

    print("\n" + "=" * 90)
    print(" BLUESTOCK MUTUAL FUND ANALYTICS - MASTER EXECUTION PIPELINE")
    print("=" * 90)
    print(f" Python Environment : {sys.executable}")
    print(f" Working Directory  : {root_dir}")
    print(f" Total Pipeline Steps: {len(PIPELINE_STEPS)}")
    print("=" * 90 + "\n")

    successful_steps = 0

    for idx, step in enumerate(PIPELINE_STEPS, start=1):
        step_name = step["name"]
        script_file = step["script"]
        desc = step["description"]
        script_path = os.path.join(root_dir, script_file)

        print(f"\n>>> [{idx}/{len(PIPELINE_STEPS)}] RUNNING: {step_name}")
        print(f"    Script      : {script_file}")
        print(f"    Description : {desc}")
        print("-" * 90)

        if not os.path.exists(script_path):
            print(f"[ERROR] Script file not found: {script_path}")
            print("Aborting pipeline execution.")
            sys.exit(1)

        step_start = time.time()
        success = run_script(script_path)
        step_elapsed = time.time() - step_start

        if success:
            successful_steps += 1
            print("-" * 90)
            print(f"[SUCCESS] {step_name} completed in {step_elapsed:.2f} seconds.")
        else:
            print("-" * 90)
            print(f"[FAILED] Pipeline aborted at {step_name}.")
            sys.exit(1)

    total_elapsed = time.time() - start_time
    print("\n" + "=" * 90)
    print(" PIPELINE EXECUTION SUMMARY")
    print("=" * 90)
    print(f" Status             : ALL {successful_steps}/{len(PIPELINE_STEPS)} STEPS COMPLETED SUCCESSFULLY")
    print(f" Total Time Elapsed : {total_elapsed:.2f} seconds")
    print(f" Output Artifacts   : data/db/bluestock_mf.db, rolling_sharpe_chart.png, reports/day1_data_quality_summary.md")
    print("=" * 90 + "\n")


if __name__ == "__main__":
    main()
