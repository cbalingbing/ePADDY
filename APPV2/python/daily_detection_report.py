import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import smtplib
import sys
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# ── CONFIG ──────────────────────────────────────────────────────────────────
CONFIG_FILE = "config.txt"   # ← path to your config file
TARGET_DATE = None           # ← set to "YYYY-MM-DD" or leave None for most recent
# ────────────────────────────────────────────────────────────────────────────


def load_config(config_path):
    config = {}
    with open(config_path, "r") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config


# Load config
config = load_config(CONFIG_FILE)
CSV_FILE = config.get("pred_csv_path", "")
CRED_PATH = config.get("app_pass", "")
RECIPIENT_EMAIL = config.get("email", "")  # ← add this to your config.txt

if not CSV_FILE:
    print("Error: 'pred_csv_path' not found in config.txt")
    sys.exit(1)

# Load email credentials from the cred file
sender_email, app_pass = None, None
if CRED_PATH and os.path.exists(CRED_PATH):
    with open(CRED_PATH, "r") as f:
        lines = f.readlines()
        sender_email = lines[0].strip()
        app_pass = lines[1].strip()
else:
    print("Warning: app_pass path not found or file missing — email will be skipped.")


def load_data(filepath):
    df = pd.read_csv(filepath)
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def filter_day(df, target_date=None):
    if target_date:
        date = pd.to_datetime(target_date).date()
    else:
        date = df["Date"].dt.date.max()
        print(f"No date specified — using most recent date found: {date}")

    day_df = df[df["Date"].dt.date == date].copy()

    if day_df.empty:
        print(f"No records found for {date}.")
        sys.exit(1)

    print(f"\nRecords found for {date}: {len(day_df)}")
    return day_df, date


def plot_daily_report(day_df, date):
    missing = [c for c in ["TD_RD", "TD_TC", "TD_SO"] if c not in day_df.columns]
    if missing:
        print(f"Warning: column(s) {missing} not found in data — skipping.")

    plot_cols = [c for c in ["TD_RD", "TD_TC", "TD_SO"] if c in day_df.columns]

    if "Title" in day_df.columns:
        x_labels = day_df["Title"].astype(str).tolist()
    else:
        x_labels = day_df["Date"].dt.strftime("%H:%M").tolist()

    x = range(len(x_labels))
    bar_width = 0.25
    colors = {"TD_RD": "#2196F3", "TD_TC": "#4CAF50", "TD_SO": "#FF9800"}
    labels = {"TD_RD": "TD_RD", "TD_TC": "TD_TC", "TD_SO": "TD_SO"}

    fig, ax = plt.subplots(figsize=(max(10, len(x_labels) * 0.9), 6))

    for i, col in enumerate(plot_cols):
        offset = [xi + i * bar_width for xi in x]
        bars = ax.bar(offset, day_df[col].fillna(0), width=bar_width,
                      label=labels.get(col, col), color=colors.get(col, None),
                      edgecolor="white", linewidth=0.5)
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.annotate(f"{int(height)}",
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3), textcoords="offset points",
                            ha="center", va="bottom", fontsize=8)

    center_offset = bar_width * (len(plot_cols) - 1) / 2
    ax.set_xticks([xi + center_offset for xi in x])
    ax.set_xticklabels(x_labels, rotation=45, ha="right", fontsize=9)
    ax.set_xlabel("Time Period", fontsize=11)
    ax.set_ylabel("Total Detection", fontsize=11)
    ax.set_title(f"Daily Report of Total Detection\n{date}", fontsize=14, fontweight="bold")
    ax.legend(fontsize=10)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)

    plt.tight_layout()

    output_file = f"daily_report_{date}.png"
    plt.savefig(output_file, dpi=150)
    print(f"\nChart saved to: {output_file}")
    plt.show()

    return output_file


def send_email(chart_path, date, totals):
    if not sender_email or not app_pass:
        print("Email skipped: no credentials loaded.")
        return
    if not RECIPIENT_EMAIL:
        print("Email skipped: 'recipient_email' not set in config.txt.")
        return

    print(f"\nSending email to {RECIPIENT_EMAIL} ...")

    # Build plain-text body with day totals
    totals_text = "\n".join([f"  {col}: {int(val)}" for col, val in totals.items()])
    body = (
        f"Daily Detection Report — {date}\n\n"
        f"Day Totals:\n{totals_text}\n\n"
        f"Please see the attached chart for the full breakdown.\n"
    )

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = f"Daily Detection Report — {date}"
    msg.attach(MIMEText(body, "plain"))

    # Attach the chart image
    with open(chart_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(chart_path)}")
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, app_pass)
        server.sendmail(sender_email, RECIPIENT_EMAIL, msg.as_string())

    print("Email sent successfully!")


def main():
    if not os.path.exists(CSV_FILE):
        print(f"File not found: {CSV_FILE}")
        sys.exit(1)

    df = load_data(CSV_FILE)
    day_df, date = filter_day(df, TARGET_DATE)

    # Print summary table
    summary_cols = ["Title"] + [c for c in ["TD_RD", "TD_TC", "TD_SO"] if c in day_df.columns]
    print("\n── Daily Summary ──────────────────────────────")
    print(day_df[summary_cols].to_string(index=False))
    print("───────────────────────────────────────────────")

    totals = day_df[[c for c in ["TD_RD", "TD_TC", "TD_SO"] if c in day_df.columns]].sum()
    print("\n── Day Totals ──")
    for col, val in totals.items():
        print(f"  {col}: {int(val)}")

    chart_path = plot_daily_report(day_df, date)
    send_email(chart_path, date, totals)


if __name__ == "__main__":
    main()
