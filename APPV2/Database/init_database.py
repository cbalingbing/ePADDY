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
                area           TEXT NOT NULL,
                num_detect_so  INTEGER DEFAULT 0,
                num_detect_tc  INTEGER DEFAULT 0,
                num_detect_rd  INTEGER DEFAULT 0,
                pct_so         REAL DEFAULT 0.0,
                pct_tc         REAL DEFAULT 0.0,
                pct_rd         REAL DEFAULT 0.0
            );

            CREATE TABLE IF NOT EXISTS daily_summary (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                date            TEXT NOT NULL,
                area            TEXT NOT NULL,
                total_daily_so  INTEGER DEFAULT 0,
                total_daily_tc  INTEGER DEFAULT 0,
                total_daily_rd  INTEGER DEFAULT 0,
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
                UNIQUE(month, area)
            );

            CREATE TABLE IF NOT EXISTS sensor_readings (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                date             TEXT NOT NULL,
                time             TEXT NOT NULL,
                node_name        TEXT NOT NULL,
                area             TEXT NOT NULL,
                temp             REAL DEFAULT 0.0,
                humid            REAL DEFAULT 0.0,
                UNIQUE(date, time, node_name)
            );
        """)
        conn.commit()
        conn.close()
        return "DB initialized successfully"
    except Exception as e:
        return f"DB initialization failed: {e}"


if __name__ == "__main__":
    initialized_DB = init_db()
    print(initialized_DB)
