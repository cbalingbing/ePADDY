"""
dashboard_service.py — ePADDY Dashboard Data Service
=====================================================
Owns all dashboard DB queries and the TTL cache layer.
app.py just calls get_dashboard_data() and invalidate_cache().

Cache buckets:
    _query_cache  — filtered queries,      TTL = 5 min
    _daily_cache  — daily summary data,    TTL = 1 hour
    _weekly_cache — weekly summary data,   TTL = 1 hour

Cache is invalidated via invalidate_cache(), which can be called
by a cron job (POST /api/cache/invalidate) or after a new detection
is saved.
"""

import os
import sys
import json
from cachetools import TTLCache

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../Database"))
from init_database import get_connection

# ── Cache buckets ─────────────────────────────────────────────────────────────
_query_cache  = TTLCache(maxsize=200, ttl=300)   # 5 min  — filtered queries
_daily_cache  = TTLCache(maxsize=50,  ttl=3600)  # 1 hour — daily summaries
_weekly_cache = TTLCache(maxsize=20,  ttl=3600)  # 1 hour — weekly summaries


def _cache_key(params: dict) -> str:
    """Stable string key from a dict of filter params."""
    return json.dumps(params, sort_keys=True)


# ── Raw DB queries ────────────────────────────────────────────────────────────
def _run_queries(conditions: list, params: list) -> dict:
    """
    Execute all dashboard queries against the DB and return a
    serialisable dict. Not called directly — go through
    get_dashboard_data() so the cache is respected.
    """
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    # For temp/humidity we need an extra NULL guard
    th_where = (
        where + " AND temp IS NOT NULL AND humid IS NOT NULL"
        if where else
        "WHERE temp IS NOT NULL AND humid IS NOT NULL"
    )

    conn = get_connection()

    # Recent detections (top 50, newest first)
    recent = conn.execute(f"""
        SELECT date, time, sensor_number, area,
               temp, humid,
               num_detect_so, num_detect_tc, num_detect_rd,
               pct_so, pct_tc, pct_rd, est_so
        FROM detections {where}
        ORDER BY date DESC, time DESC
        LIMIT 50
    """, params).fetchall()

    # Hourly detections — for the time-series chart
    hourly = conn.execute(f"""
        SELECT date,
               substr(time, 1, 2) AS hour,
               SUM(num_detect_so) AS so,
               SUM(num_detect_tc) AS tc,
               SUM(num_detect_rd) AS rd
        FROM detections {where}
        GROUP BY date, hour
        ORDER BY date, hour
    """, params).fetchall()

    # Pest distribution totals — for the donut chart
    totals = conn.execute(f"""
        SELECT COALESCE(SUM(num_detect_so), 0) AS total_so,
               COALESCE(SUM(num_detect_tc), 0) AS total_tc,
               COALESCE(SUM(num_detect_rd), 0) AS total_rd
        FROM detections {where}
    """, params).fetchone()

    # Temp & humidity trend
    th_trend = conn.execute(f"""
        SELECT date, time, temp, humid
        FROM detections {th_where}
        ORDER BY date, time
    """, params).fetchall()

    # EST_SO trend
    est_trend = conn.execute(f"""
        SELECT date, time, est_so
        FROM detections {where}
        ORDER BY date, time
    """, params).fetchall()

    # Latest single detection — for the summary card
    latest = conn.execute(f"""
        SELECT date, time, sensor_number, area,
               num_detect_so, num_detect_tc, num_detect_rd, est_so
        FROM detections {where}
        ORDER BY date DESC, time DESC
        LIMIT 1
    """, params).fetchone()

    # Total record count — for the summary card
    total_count = conn.execute(
        f"SELECT COUNT(*) FROM detections {where}", params
    ).fetchone()[0]

    # Per-area aggregation — for the heatmap
    # area is stored as "lon,lat" — parsed by the frontend
    locations = conn.execute(f"""
        SELECT area,
               SUM(num_detect_so + num_detect_tc + num_detect_rd) AS total
        FROM detections {where}
        GROUP BY area
    """, params).fetchall()

    # Distinct areas — for the filter dropdown
    all_areas = conn.execute(
        "SELECT DISTINCT area FROM detections ORDER BY area"
    ).fetchall()

    conn.close()

    return {
        "recent"     : [dict(r) for r in recent],
        "hourly"     : [dict(r) for r in hourly],
        "totals"     : dict(totals) if totals else {},
        "th_trend"   : [dict(r) for r in th_trend],
        "est_trend"  : [dict(r) for r in est_trend],
        "latest"     : dict(latest) if latest else None,
        "total_count": total_count,
        "locations"  : [dict(r) for r in locations],
        "areas"      : [r[0] for r in all_areas],
    }


# ── Public API ────────────────────────────────────────────────────────────────
def get_dashboard_data(filters: dict) -> dict:
    """
    Return dashboard data for the given filters.
    Serves from _query_cache if the entry is still valid,
    otherwise queries the DB and stores the result.

    filters keys (all optional, empty string = no filter):
        start_date, end_date, area, time_start, time_end, insect
    """
    key = _cache_key(filters)
    if key in _query_cache:
        return _query_cache[key]

    conditions, params = [], []

    if filters.get("start_date"):
        conditions.append("date >= ?");        params.append(filters["start_date"])
    if filters.get("end_date"):
        conditions.append("date <= ?");        params.append(filters["end_date"])
    if filters.get("area"):
        conditions.append("area = ?");         params.append(filters["area"])
    if filters.get("time_start"):
        conditions.append("time >= ?");        params.append(filters["time_start"])
    if filters.get("time_end"):
        conditions.append("time <= ?");        params.append(filters["time_end"])

    insect = filters.get("insect", "")
    if insect == "so":
        conditions.append("num_detect_so > 0")
    elif insect == "tc":
        conditions.append("num_detect_tc > 0")
    elif insect == "rd":
        conditions.append("num_detect_rd > 0")

    result = _run_queries(conditions, params)
    _query_cache[key] = result
    return result


def get_daily_summary(date: str = None) -> dict:
    """
    Return daily summary data, cached for 1 hour.
    If date is None, returns all daily summaries.
    """
    key = _cache_key({"type": "daily", "date": date or ""})
    if key in _daily_cache:
        return _daily_cache[key]

    conn = get_connection()
    where  = "WHERE date = ?" if date else ""
    params = [date] if date else []

    rows = conn.execute(f"""
        SELECT date, area,
               total_daily_so, total_daily_tc, total_daily_rd,
               ave_daily_temp, ave_daily_humid,
               pct_so, pct_tc, pct_rd
        FROM daily_summary {where}
        ORDER BY date DESC
    """, params).fetchall()
    conn.close()

    result = {"daily": [dict(r) for r in rows]}
    _daily_cache[key] = result
    return result


def get_weekly_summary(month: str = None) -> dict:
    """
    Return weekly summary data, cached for 1 hour.
    If month is None, returns all weekly summaries.
    """
    key = _cache_key({"type": "weekly", "month": month or ""})
    if key in _weekly_cache:
        return _weekly_cache[key]

    conn = get_connection()
    where  = "WHERE month = ?" if month else ""
    params = [month] if month else []

    rows = conn.execute(f"""
        SELECT month, area,
               total_weekly_so, total_weekly_tc, total_weekly_rd,
               pct_so, pct_tc, pct_rd,
               ave_weekly_temp, ave_weekly_humid
        FROM weekly_summary {where}
        ORDER BY month DESC
    """, params).fetchall()
    conn.close()

    result = {"weekly": [dict(r) for r in rows]}
    _weekly_cache[key] = result
    return result


def invalidate_cache():
    """Clear all cache buckets. Call after new data is written to the DB,
    or via the /api/cache/invalidate cron endpoint."""
    _query_cache.clear()
    _daily_cache.clear()
    _weekly_cache.clear()
