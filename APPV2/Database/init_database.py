import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "../sqlite/epaddy.db")


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    try:
        conn = get_connection()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS detections (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                date           TEXT NOT NULL,
                time           TEXT NOT NULL,
                sensor_number  TEXT NOT NULL,
                temp           REAL DEFAULT 0.0,
                humid          REAL DEFAULT 0.0,
                area           TEXT NOT NULL,
                num_detect_so  INTEGER DEFAULT 0,
                num_detect_tc  INTEGER DEFAULT 0,
                num_detect_rd  INTEGER DEFAULT 0,
                pct_so         REAL DEFAULT 0.0,
                pct_tc         REAL DEFAULT 0.0,
                pct_rd         REAL DEFAULT 0.0,
                est_so         INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS daily_summary (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                date            TEXT NOT NULL,
                area            TEXT NOT NULL,
                total_daily_so  INTEGER DEFAULT 0,
                total_daily_tc  INTEGER DEFAULT 0,
                total_daily_rd  INTEGER DEFAULT 0,
                ave_daily_temp   REAL DEFAULT 0.0,
                ave_daily_humid  REAL DEFAULT 0.0,
                pct_so          REAL DEFAULT 0.0,
                pct_tc          REAL DEFAULT 0.0,
                pct_rd          REAL DEFAULT 0.0,
                UNIQUE(date, area)
            );

            CREATE TABLE IF NOT EXISTS weekly_summary (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                month            TEXT NOT NULL,
                area             TEXT NOT NULL,
                total_weekly_so  INTEGER DEFAULT 0,
                total_weekly_tc  INTEGER DEFAULT 0,
                total_weekly_rd  INTEGER DEFAULT 0,
                pct_so           REAL DEFAULT 0.0,
                pct_tc           REAL DEFAULT 0.0,
                pct_rd           REAL DEFAULT 0.0,
                ave_weekly_temp   REAL DEFAULT 0.0,
                ave_weekly_humid  REAL DEFAULT 0.0,
                UNIQUE(month, area)
            );

        """)
        conn.commit()
        conn.close()
        return "DB initialized successfully"
    except Exception as e:
        return f"DB initialization failed: {e}"


def save_detection(date: str, time: str, sensor_number: str, area: str,
                   num_so: int, num_tc: int, num_rd: int,
                   temp=None, humid=None, est_so: int = 0):
    """
    Insert one detection record.

    Counts and percentages are computed here so callers just pass raw counts.
    temp/humid are optional — pass None when no sensor CSV match was found.
    est_so is the linear regression estimate of S_Oryzae insects scaled by PD_SO.
    """
    total = num_so + num_tc + num_rd
    pct_so = round((num_so / total) * 100, 2) if total else 0.0
    pct_tc = round((num_tc / total) * 100, 2) if total else 0.0
    pct_rd = round((num_rd / total) * 100, 2) if total else 0.0

    try:
        conn = get_connection()
        conn.execute(
            """
            INSERT INTO detections
                (date, time, sensor_number, temp, humid, area,
                 num_detect_so, num_detect_tc, num_detect_rd,
                 pct_so, pct_tc, pct_rd, est_so)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (date, time, sensor_number, temp, humid, area,
             num_so, num_tc, num_rd,
             pct_so, pct_tc, pct_rd, est_so)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] save_detection failed: {e}")
        return False


if __name__ == "__main__":
    initialized_DB = init_db()
    print(initialized_DB)
