"""
seed_db.py — ePADDY Dummy Data Seeder
======================================
Creates and populates the database with fake detection records
for local dashboard testing on MacBook.

Run:
    python seed_db.py
"""

import os
import sys
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from init_database import init_db, get_connection

# ── Config ────────────────────────────────────────────────────────────────────
DAYS        = 14          # how many days of data to generate
RECORDS_PER_DAY = 6       # detections per day per node
NODES = [
    {"id": "1", "area": "120.9842,14.5995"},   # Manila area
    {"id": "2", "area": "121.0244,14.5547"},   # Nearby node
]

random.seed(42)

def random_detection(date_str, time_str, node):
    so = random.randint(0, 80)
    tc = random.randint(0, 40)
    rd = random.randint(0, 60)
    total = so + tc + rd

    pct_so = round((so / total) * 100, 2) if total else 0.0
    pct_tc = round((tc / total) * 100, 2) if total else 0.0
    pct_rd = round((rd / total) * 100, 2) if total else 0.0

    temp  = round(random.uniform(26.0, 34.0), 2)
    humid = round(random.uniform(55.0, 85.0), 2)

    # Simulated EST_SO from linear regression
    n_peaks   = random.randint(100, 8000)
    avg_amp   = round(random.uniform(0.02, 0.12), 6)
    est_total = 8.874848 + (-0.000061 * n_peaks) + (141.215010 * avg_amp)
    est_so    = max(0, round(est_total * (pct_so / 100)))

    return (date_str, time_str, node["id"], temp, humid, node["area"],
            so, tc, rd, pct_so, pct_tc, pct_rd, est_so)


def seed():
    print("Initializing database...")
    result = init_db()
    print(result)

    conn = get_connection()

    # Clear existing dummy data
    conn.execute("DELETE FROM detections")
    conn.execute("DELETE FROM daily_summary")
    conn.execute("DELETE FROM weekly_summary")
    conn.commit()
    print("Cleared existing data.")

    # Generate detections
    records = []
    base_date = datetime.now() - timedelta(days=DAYS)

    for day in range(DAYS):
        current_date = base_date + timedelta(days=day)
        date_str = current_date.strftime("%Y-%m-%d")

        for node in NODES:
            for rec in range(RECORDS_PER_DAY):
                # Spread detections across the day hourly
                hour = 6 + (rec * 3)
                time_str = f"{hour:02d}:{random.randint(0,59):02d}:00"
                records.append(random_detection(date_str, time_str, node))

    conn.executemany("""
        INSERT INTO detections
            (date, time, sensor_number, temp, humid, area,
             num_detect_so, num_detect_tc, num_detect_rd,
             pct_so, pct_tc, pct_rd, est_so)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, records)
    conn.commit()
    print(f"Inserted {len(records)} detection records.")

    # Generate daily summaries
    daily = []
    for day in range(DAYS):
        current_date = base_date + timedelta(days=day)
        date_str = current_date.strftime("%Y-%m-%d")
        for node in NODES:
            rows = conn.execute("""
                SELECT SUM(num_detect_so), SUM(num_detect_tc), SUM(num_detect_rd),
                       AVG(temp), AVG(humid)
                FROM detections
                WHERE date = ? AND sensor_number = ?
            """, (date_str, node["id"])).fetchone()

            total_so, total_tc, total_rd = rows[0] or 0, rows[1] or 0, rows[2] or 0
            ave_temp  = round(rows[3] or 0, 2)
            ave_humid = round(rows[4] or 0, 2)
            total = total_so + total_tc + total_rd

            daily.append((
                date_str, node["area"],
                total_so, total_tc, total_rd,
                ave_temp, ave_humid,
                round((total_so / total) * 100, 2) if total else 0,
                round((total_tc / total) * 100, 2) if total else 0,
                round((total_rd / total) * 100, 2) if total else 0,
            ))

    conn.executemany("""
        INSERT OR REPLACE INTO daily_summary
            (date, area, total_daily_so, total_daily_tc, total_daily_rd,
             ave_daily_temp, ave_daily_humid, pct_so, pct_tc, pct_rd)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, daily)
    conn.commit()
    print(f"Inserted {len(daily)} daily summary records.")

    # Generate weekly summaries (group by YYYY-WXX)
    weekly_map = {}
    for day in range(DAYS):
        current_date = base_date + timedelta(days=day)
        month_key = current_date.strftime("%Y-%m")
        for node in NODES:
            key = (month_key, node["area"])
            if key not in weekly_map:
                weekly_map[key] = {"so": 0, "tc": 0, "rd": 0, "temps": [], "humids": []}
            rows = conn.execute("""
                SELECT SUM(num_detect_so), SUM(num_detect_tc), SUM(num_detect_rd),
                       AVG(temp), AVG(humid)
                FROM detections
                WHERE date = ? AND sensor_number = ?
            """, (current_date.strftime("%Y-%m-%d"), node["id"])).fetchone()
            weekly_map[key]["so"]     += rows[0] or 0
            weekly_map[key]["tc"]     += rows[1] or 0
            weekly_map[key]["rd"]     += rows[2] or 0
            if rows[3]: weekly_map[key]["temps"].append(rows[3])
            if rows[4]: weekly_map[key]["humids"].append(rows[4])

    weekly = []
    for (month, area), v in weekly_map.items():
        total = v["so"] + v["tc"] + v["rd"]
        ave_temp  = round(sum(v["temps"])  / len(v["temps"]),  2) if v["temps"]  else 0.0
        ave_humid = round(sum(v["humids"]) / len(v["humids"]), 2) if v["humids"] else 0.0
        weekly.append((
            month, area,
            v["so"], v["tc"], v["rd"],
            round((v["so"] / total) * 100, 2) if total else 0,
            round((v["tc"] / total) * 100, 2) if total else 0,
            round((v["rd"] / total) * 100, 2) if total else 0,
            ave_temp, ave_humid,
        ))

    conn.executemany("""
        INSERT OR REPLACE INTO weekly_summary
            (month, area, total_weekly_so, total_weekly_tc, total_weekly_rd,
             pct_so, pct_tc, pct_rd, ave_weekly_temp, ave_weekly_humid)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, weekly)
    conn.commit()
    print(f"Inserted {len(weekly)} weekly summary records.")

    conn.close()
    print("\nDone! DB seeded successfully. Run the Flask app and open /dashboard.")


if __name__ == "__main__":
    seed()
