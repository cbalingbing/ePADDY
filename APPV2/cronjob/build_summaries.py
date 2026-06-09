#!/usr/bin/env python3
"""
build_summaries.py — ePADDY summary aggregator (cron job)
=========================================================
Rebuilds daily_summary and weekly_summary (keyed by MONTH) from the
detections table. Replaces the aggregation that seed_db.py used to do,
but non-destructively and from REAL data.

Idempotent: uses INSERT OR REPLACE keyed on each table's UNIQUE constraint
(daily: UNIQUE(date, area); weekly: UNIQUE(month, area)), so it is safe to
run repeatedly / on a schedule.

Run (cron):
    /path/to/.venv/bin/python /path/to/APPV2/cronjob/build_summaries.py

Dry-run (no writes — shows what WOULD be aggregated):
    python build_summaries.py --test

After writing it tries to bust the Flask dashboard cache via
POST /api/cache/invalidate. The TTL cache lives inside the Flask process,
so a separate cron process can only clear it over HTTP. If Flask isn't
reachable that's non-fatal — the cache also expires on its own (1 hour).
"""

import os
import sys
import argparse
import configparser
from urllib import request as urlrequest

HERE  = os.path.dirname(os.path.abspath(__file__))
APPV2 = os.path.dirname(HERE)

sys.path.insert(0, os.path.join(APPV2, "Database"))
from init_database import init_db, get_connection

# Shared "grand total of all three pest counts" expression used for pct math.
_TOTAL = "SUM(num_detect_so + num_detect_tc + num_detect_rd)"

# date × area → daily_summary  (area_name carried via MAX; 1:1 with coords)
DAILY_SELECT = f"""
    SELECT date, area, MAX(area_name) AS area_name,
           SUM(num_detect_so), SUM(num_detect_tc), SUM(num_detect_rd),
           ROUND(AVG(temp), 2), ROUND(AVG(humid), 2),
           ROUND(100.0 * SUM(num_detect_so) / NULLIF({_TOTAL}, 0), 2),
           ROUND(100.0 * SUM(num_detect_tc) / NULLIF({_TOTAL}, 0), 2),
           ROUND(100.0 * SUM(num_detect_rd) / NULLIF({_TOTAL}, 0), 2),
           SUM(est_so)
    FROM detections
    GROUP BY date, area
"""

# month (YYYY-MM) × area → weekly_summary  (area_name carried via MAX)
WEEKLY_SELECT = f"""
    SELECT strftime('%Y-%m', date) AS month, area, MAX(area_name) AS area_name,
           SUM(num_detect_so), SUM(num_detect_tc), SUM(num_detect_rd),
           ROUND(100.0 * SUM(num_detect_so) / NULLIF({_TOTAL}, 0), 2),
           ROUND(100.0 * SUM(num_detect_tc) / NULLIF({_TOTAL}, 0), 2),
           ROUND(100.0 * SUM(num_detect_rd) / NULLIF({_TOTAL}, 0), 2),
           ROUND(AVG(temp), 2), ROUND(AVG(humid), 2),
           SUM(est_so)
    FROM detections
    GROUP BY month, area
"""

DAILY_INSERT = """
    INSERT OR REPLACE INTO daily_summary
        (date, area, area_name, total_daily_so, total_daily_tc, total_daily_rd,
         ave_daily_temp, ave_daily_humid, pct_so, pct_tc, pct_rd, total_daily_est_so)
"""

WEEKLY_INSERT = """
    INSERT OR REPLACE INTO weekly_summary
        (month, area, area_name, total_weekly_so, total_weekly_tc, total_weekly_rd,
         pct_so, pct_tc, pct_rd, ave_weekly_temp, ave_weekly_humid, total_weekly_est_so)
"""


def dry_run():
    init_db()                                # ensure schema/migrations (adds cols only)
    conn = get_connection()
    det    = conn.execute("SELECT COUNT(*) FROM detections").fetchone()[0]
    daily  = conn.execute(DAILY_SELECT).fetchall()
    weekly = conn.execute(WEEKLY_SELECT).fetchall()
    conn.close()

    print("── DRY RUN (no writes) ─────────────────────────────")
    print(f"detections rows          : {det}")
    print(f"daily_summary  would be  : {len(daily)} rows  (date x area)")
    print(f"weekly_summary would be  : {len(weekly)} rows (month x area)")
    print("\nSample daily rows:")
    for r in daily[:5]:
        print("  ", tuple(r))
    print("\nSample weekly rows:")
    for r in weekly[:5]:
        print("  ", tuple(r))
    if det == 0:
        print("\n[!] detections table is EMPTY — nothing to aggregate yet.")


def build():
    init_db()                                # ensure tables + migrations exist
    conn = get_connection()
    conn.execute(DAILY_INSERT  + DAILY_SELECT)
    conn.execute(WEEKLY_INSERT + WEEKLY_SELECT)
    conn.commit()
    d = conn.execute("SELECT COUNT(*) FROM daily_summary").fetchone()[0]
    w = conn.execute("SELECT COUNT(*) FROM weekly_summary").fetchone()[0]
    conn.close()
    print(f"daily_summary : {d} rows")
    print(f"weekly_summary: {w} rows")
    _invalidate_cache()


def _invalidate_cache():
    """Bust the running Flask app's in-process TTL cache (best effort)."""
    cfg = configparser.ConfigParser()
    cfg.read(os.path.join(APPV2, "config.ini"))
    host = cfg.get("flask", "host", fallback="127.0.0.1")
    if host == "0.0.0.0":                     # 0.0.0.0 is a bind addr, not connectable
        host = "127.0.0.1"
    port = cfg.get("flask", "port", fallback="5000")
    url  = f"http://{host}:{port}/api/cache/invalidate"
    try:
        req = urlrequest.Request(url, method="POST")
        with urlrequest.urlopen(req, timeout=3) as resp:
            print(f"cache invalidate: {resp.status} ({url})")
    except Exception as e:
        print(f"cache invalidate skipped (Flask not reachable): {e}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="ePADDY summary aggregator")
    ap.add_argument("--test", action="store_true",
                    help="dry run: show what would be aggregated, write nothing")
    args = ap.parse_args()
    if args.test:
        dry_run()
    else:
        build()
