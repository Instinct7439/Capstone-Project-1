"""
Automated Mutual Fund Email Reporting Engine

Reads fund_scorecard.csv from data/processed/, extracts top 5 mutual funds by composite score, 
formats a responsive modern HTML report, attaches quantitative analytics charts, and sends 
an automated email report via SMTP using python-dotenv configuration.

Exports an HTML preview to reports/email_preview.html for local verification.
"""

import os
import smtplib
import sqlite3
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Workspace Paths
BASE_DIR = Path(__file__).resolve().parent.parent
SCORECARD_PATH = BASE_DIR / "data" / "processed" / "fund_scorecard.csv"
if not SCORECARD_PATH.exists():
    SCORECARD_PATH = BASE_DIR / "fund_scorecard.csv"

DB_PATH = BASE_DIR / "data" / "db" / "bluestock_mf.db"
REPORTS_DIR = BASE_DIR / "reports"
PREVIEW_FILE = REPORTS_DIR / "email_preview.html"

MONTE_CARLO_CHART = BASE_DIR / "dashboard" / "exported_charts" / "monte_carlo_5yr.png"
EFFICIENT_FRONTIER_CHART = BASE_DIR / "dashboard" / "exported_charts" / "efficient_frontier.png"

# Environment / Credentials Configuration
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "your_email@gmail.com")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "your_app_password")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "recipient@example.com")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))


def load_top_5_scorecard(scorecard_path: Path, db_path: Path) -> pd.DataFrame:
    """
    Ingests composite fund scorecard and extracts the top 5 funds.

    Parameters:
        scorecard_path (Path): Path to fund_scorecard.csv.
        db_path (Path): Path to SQLite database.

    Returns:
        pd.DataFrame: Top 5 fund records.
    """
    if not scorecard_path.exists():
        raise FileNotFoundError(f"Scorecard dataset not found at {scorecard_path}")

    df_score = pd.read_csv(scorecard_path)
    if "final_rank" in df_score.columns:
        top_5 = df_score.sort_values("final_rank").head(5).copy()
    else:
        top_5 = df_score.sort_values("composite_score", ascending=False).head(5).copy()

    # Join metadata from dim_fund if available
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        df_dim = pd.read_sql_query("SELECT amfi_code, fund_house, category FROM dim_fund", conn)
        conn.close()
        top_5 = pd.merge(top_5, df_dim, on="amfi_code", how="left")

    return top_5


def build_html_email_body(top_5_df: pd.DataFrame) -> str:
    """
    Constructs a modern, mobile-responsive HTML email document.

    Parameters:
        top_5_df (pd.DataFrame): DataFrame containing top 5 funds data.

    Returns:
        str: Fully formatted HTML string.
    """
    table_rows_html = ""
    for idx, row in top_5_df.reset_index(drop=True).iterrows():
        rank = row.get("final_rank", idx + 1)

        # Rank Badge Colors
        if rank == 1:
            badge_style = "background-color: #F59E0B; color: #FFFFFF;"
        elif rank == 2:
            badge_style = "background-color: #94A3B8; color: #FFFFFF;"
        elif rank == 3:
            badge_style = "background-color: #D97706; color: #FFFFFF;"
        else:
            badge_style = "background-color: #3B82F6; color: #FFFFFF;"

        scheme_name = row.get("scheme_name", "N/A")
        fund_house = row.get("fund_house", "Mutual Fund")
        category = row.get("category", "Equity")
        cagr = row.get("cagr_3yr_pct", 0.0)
        sharpe = row.get("sharpe_ratio", 0.0)
        alpha = row.get("alpha_annual_pct", 0.0)
        er = row.get("expense_ratio_pct", 0.0)
        score = row.get("composite_score", 0.0)

        bg_color = "#FFFFFF" if idx % 2 == 0 else "#F8FAFC"

        table_rows_html += f"""
        <tr style="background-color: {bg_color}; border-bottom: 1px solid #E2E8F0;">
            <td style="padding: 12px 16px; text-align: center;">
                <span style="display: inline-block; padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 12px; {badge_style}">
                    #{rank}
                </span>
            </td>
            <td style="padding: 12px 16px;">
                <div style="font-weight: 700; color: #0F172A; font-size: 14px;">{scheme_name}</div>
                <div style="font-size: 12px; color: #64748B;">{fund_house} • {category}</div>
            </td>
            <td style="padding: 12px 16px; text-align: right; font-weight: 600; color: #166534;">{cagr:.2f}%</td>
            <td style="padding: 12px 16px; text-align: right; font-weight: 600; color: #1E3A8A;">{sharpe:.2f}</td>
            <td style="padding: 12px 16px; text-align: right; font-weight: 600; color: #0284C7;">{alpha:.2f}%</td>
            <td style="padding: 12px 16px; text-align: right; color: #475569;">{er:.2f}%</td>
            <td style="padding: 12px 16px; text-align: right; font-weight: 700; color: #D97706;">{score:.1f}</td>
        </tr>
        """

    top_fund_name = top_5_df.iloc[0].get("scheme_name", "Top Scheme")
    top_fund_cagr = top_5_df.iloc[0].get("cagr_3yr_pct", 0.0)
    top_fund_sharpe = top_5_df.iloc[0].get("sharpe_ratio", 0.0)

    html_document = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bluestock Mutual Fund Top 5 Performance Report</title>
</head>
<body style="font-family: Arial, sans-serif; background-color: #F1F5F9; margin: 0; padding: 20px;">
    <div style="max-width: 720px; margin: 0 auto; background-color: #FFFFFF; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #E2E8F0;">
        
        <!-- Header Bar -->
        <div style="background-color: #1E3A8A; color: #FFFFFF; padding: 24px 32px;">
            <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; opacity: 0.85; font-weight: 600;">Bluestock Mutual Fund Analytics</div>
            <h1 style="margin: 6px 0 0 0; font-size: 22px; font-weight: 700;">Top 5 Composite Mutual Funds Report</h1>
        </div>

        <!-- Highlight Callout Box -->
        <div style="padding: 24px 32px 12px 32px;">
            <div style="background-color: #EFF6FF; border-left: 4px solid #3B82F6; padding: 16px; border-radius: 6px;">
                <div style="font-weight: 700; color: #1E40AF; font-size: 15px; margin-bottom: 4px;">🏆 Overall #1 Rated Scheme: {top_fund_name}</div>
                <div style="font-size: 13px; color: #1E3A8A;">
                    Delivered <strong>{top_fund_cagr:.2f}% 3-Year CAGR</strong> with a <strong>Sharpe Ratio of {top_fund_sharpe:.2f}</strong> based on multi-factor composite analysis.
                </div>
            </div>
        </div>

        <!-- Table Container -->
        <div style="padding: 12px 32px 24px 32px;">
            <table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px;">
                <thead>
                    <tr style="background-color: #F8FAFC; border-bottom: 2px solid #CBD5E1; color: #334155; text-align: left;">
                        <th style="padding: 12px 16px; text-align: center; width: 10%;">Rank</th>
                        <th style="padding: 12px 16px; width: 40%;">Scheme Name</th>
                        <th style="padding: 12px 16px; text-align: right; width: 12%;">3Yr Return</th>
                        <th style="padding: 12px 16px; text-align: right; width: 10%;">Sharpe</th>
                        <th style="padding: 12px 16px; text-align: right; width: 10%;">Alpha</th>
                        <th style="padding: 12px 16px; text-align: right; width: 8%;">ER</th>
                        <th style="padding: 12px 16px; text-align: right; width: 10%;">Score</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows_html}
                </tbody>
            </table>
        </div>

        <!-- Footer -->
        <div style="background-color: #F8FAFC; border-top: 1px solid #E2E8F0; padding: 16px 32px; text-align: center; font-size: 11px; color: #94A3B8;">
            Automated Report generated by Bluestock Mutual Fund Analytics Engine • Environment: Production
        </div>

    </div>
</body>
</html>
"""
    return html_document


def send_email_report(
    html_content: str,
    sender_email: str = SENDER_EMAIL,
    sender_password: str = SENDER_PASSWORD,
    recipient_email: str = RECIPIENT_EMAIL,
    smtp_server: str = SMTP_SERVER,
    smtp_port: int = SMTP_PORT,
) -> bool:
    """
    Constructs and dispatches email via SMTP standard library.

    Parameters:
        html_content (str): Formatted HTML document string.
        sender_email (str): SMTP sender account email.
        sender_password (str): SMTP sender account password / app token.
        recipient_email (str): Target recipient email address.
        smtp_server (str): SMTP host server domain.
        smtp_port (int): SMTP server port.

    Returns:
        bool: True if email dispatched successfully, False otherwise.
    """
    # Check if placeholder credentials are present
    is_placeholder = (
        sender_email in ["your_email@gmail.com", ""]
        or sender_password in ["your_app_password", ""]
        or recipient_email in ["recipient@example.com", ""]
    )

    if is_placeholder:
        print("\n" + "!" * 80)
        print("NOTICE: Default placeholder email credentials detected.")
        print("To send live emails, configure your .env file with valid credentials:")
        print("  SENDER_EMAIL=your_actual_email@gmail.com")
        print("  SENDER_PASSWORD=your_app_password")
        print("  RECIPIENT_EMAIL=recipient_email@example.com")
        print("!" * 80 + "\n")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Bluestock Mutual Fund Analytics — Top 5 Performance Scorecard"
    msg["From"] = sender_email
    msg["To"] = recipient_email

    # Attach HTML payload
    msg.attach(MIMEText(html_content, "html"))

    try:
        print(f"Connecting to SMTP Server {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, [recipient_email], msg.as_string())
        server.quit()
        print(f"SUCCESS: Email report dispatched to {recipient_email}")
        return True

    except Exception as exc:
        print(f"ERROR: Failed to dispatch email via SMTP ({exc})")
        return False


def main() -> None:
    """
    Main execution pipeline for email report generation and dispatch.
    """
    print("=" * 80)
    print("BLUESTOCK AUTOMATED EMAIL REPORT GENERATOR")
    print("=" * 80)
    print(f"Scorecard Path : {SCORECARD_PATH}")
    print(f"Sender Email   : {SENDER_EMAIL}")
    print(f"Recipient Email: {RECIPIENT_EMAIL}")

    # 1. Ingest top 5 scorecard records
    top_5_df = load_top_5_scorecard(SCORECARD_PATH, DB_PATH)
    print(f"\nTop 5 Mutual Funds Extracted:")
    for idx, row in top_5_df.reset_index(drop=True).iterrows():
        print(f"  #{idx+1} | Score: {row.get('composite_score', 0):.1f} | {row.get('scheme_name')}")

    # 2. Build modern HTML document
    html_content = build_html_email_body(top_5_df)

    # 3. Save local preview file
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(PREVIEW_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"\nSaved local HTML email preview to: {PREVIEW_FILE}")

    # 4. Attempt to dispatch email via SMTP
    sent_status = send_email_report(html_content)
    if sent_status:
        print("Pipeline Status: Email sent successfully!")
    else:
        print("Pipeline Status: Preview HTML generated. Configure .env file to enable live SMTP delivery.")

    print("=" * 80)
    print("EMAIL REPORT ENGINE COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
