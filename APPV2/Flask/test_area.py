"""
test_area.py — tests for the Area-name dashboard filter routes
==============================================================
Verifies that the dashboard API filters detections by the friendly
`area_name` (with coordinate fallback for legacy rows that have no name),
and that responses expose BOTH area_name (popup label) and area (coords)
so the map can pin and label correctly.

Runs against a throwaway SQLite DB — it does NOT touch your real epaddy.db.

Run:
    python test_area.py
"""

import os
import sys
import json
import tempfile
import unittest
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "../Database"))
sys.path.insert(0, os.path.join(HERE, "../python"))

# ── Point the DB at a throwaway file BEFORE anything connects ──────────────────
import init_database
_TMP_DB = os.path.join(tempfile.mkdtemp(), "test_area.db")
init_database.DB_PATH = _TMP_DB
from init_database import init_db, get_connection

# app.py handles a missing classifier gracefully (CLASSIFIER_AVAILABLE=False),
# so importing it here is safe even without the ML deps installed.
from app import app
import dashboard_service

TODAY = datetime.now().strftime("%Y-%m-%d")
NOW   = datetime.now().strftime("%H:%M:%S")

WAREHOUSE_A   = "120.9842,14.5995"
WAREHOUSE_B   = "121.0244,14.5547"
LEGACY_COORDS = "100.0000,10.0000"


def seed():
    """Reset the throwaway DB with a known set of detections."""
    init_db()
    conn = get_connection()
    conn.execute("DELETE FROM detections")
    rows = [
        # date, time, sensor, temp, humid, area(coords), area_name, so, tc, rd, pso, ptc, prd, est
        (TODAY, NOW, "1", 30.0, 70.0, WAREHOUSE_A,   "Warehouse-A", 10, 2, 1, 76.9, 15.4,  7.7, 5),
        (TODAY, NOW, "1", 30.0, 70.0, WAREHOUSE_A,   "Warehouse-A",  4, 0, 0, 100.0, 0.0,  0.0, 2),
        (TODAY, NOW, "2", 29.0, 72.0, WAREHOUSE_B,   "Warehouse-B",  0, 5, 0,   0.0, 100.0, 0.0, 0),
        # legacy row: no friendly name (area_name = NULL)
        (TODAY, NOW, "3", 28.0, 65.0, LEGACY_COORDS, None,           3, 3, 3,  33.3, 33.3, 33.3, 1),
    ]
    conn.executemany("""
        INSERT INTO detections
            (date, time, sensor_number, temp, humid, area, area_name,
             num_detect_so, num_detect_tc, num_detect_rd,
             pct_so, pct_tc, pct_rd, est_so)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    conn.close()


class TestAreaFilter(unittest.TestCase):

    def setUp(self):
        seed()
        dashboard_service.invalidate_cache()   # don't serve stale cached results
        app.config["TESTING"] = True
        self.client = app.test_client()

    def _get(self, url):
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200, url)
        return json.loads(res.data)

    # ── dropdown list: friendly names, coordinate fallback for legacy rows ─────
    def test_areas_dropdown_uses_friendly_names(self):
        data = self._get("/api/dashboard/latest")
        areas = data["areas"]
        self.assertIn("Warehouse-A", areas)
        self.assertIn("Warehouse-B", areas)
        self.assertIn(LEGACY_COORDS, areas)     # legacy row falls back to coords
        self.assertNotIn(WAREHOUSE_A, areas)    # coords hidden when a name exists
        print("areas dropdown:", areas)

    # ── filter by friendly name on each route ─────────────────────────────────
    def test_latest_filter_by_area_name(self):
        data = self._get("/api/dashboard/latest?area=Warehouse-A")
        self.assertTrue(data["recent"])
        for r in data["recent"]:
            self.assertEqual(r["area_name"], "Warehouse-A")
        print("latest?area=Warehouse-A rows:", len(data["recent"]))

    def test_dashboard_filter_by_area_name(self):
        data = self._get("/api/dashboard?area=Warehouse-B")
        self.assertTrue(data["recent"])
        for r in data["recent"]:
            self.assertEqual(r["area_name"], "Warehouse-B")
            self.assertEqual(r["area"], WAREHOUSE_B)

    def test_insect_filter_by_area_name(self):
        data = self._get("/api/dashboard/insect?period=latest&insect=so&area=Warehouse-A")
        self.assertTrue(data["recent"])
        for r in data["recent"]:
            self.assertEqual(r["area_name"], "Warehouse-A")
            self.assertGreater(r["num_detect_so"], 0)

    # ── legacy rows (no name) still filterable by their coordinates ────────────
    def test_legacy_filter_by_coordinates(self):
        data = self._get(f"/api/dashboard?area={LEGACY_COORDS}")
        self.assertTrue(data["recent"])
        for r in data["recent"]:
            self.assertEqual(r["area"], LEGACY_COORDS)

    # ── map locations expose name + coordinates ───────────────────────────────
    def test_locations_have_name_and_coords(self):
        data = self._get("/api/dashboard/latest")
        self.assertTrue(data["locations"])
        for loc in data["locations"]:
            self.assertIn("area", loc)        # coordinates → map pin
            self.assertIn("area_name", loc)   # friendly name → popup
        match = [l for l in data["locations"] if l["area"] == WAREHOUSE_A]
        self.assertTrue(match and match[0]["area_name"] == "Warehouse-A")

    # ── an unknown name returns nothing ───────────────────────────────────────
    def test_unknown_area_returns_empty(self):
        data = self._get("/api/dashboard?area=Nonexistent")
        self.assertEqual(data["recent"], [])


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  ePADDY — Area Filter Route Tests")
    print("  DB:", _TMP_DB)
    print("=" * 50 + "\n")
    unittest.main(verbosity=2)
