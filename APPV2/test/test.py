"""
ePADDY Flask App — Unit Tests
Run with: python test.py
"""

import os
import sys
import json
import io
import unittest
from unittest.mock import patch

# ── Path setup (same as app.py) ───────────────────────────────────────────────
sys.path.append(os.path.join(os.path.dirname(__file__), "../Database"))
sys.path.append(os.path.join(os.path.dirname(__file__), "../python"))

# Mock classify BEFORE importing app so it doesn't load the real model
MOCK_RESULTS = [
    {
        "file_name":     "test.wav",
        "num_detect_so": 10,
        "num_detect_tc": 5,
        "num_detect_rd": 2,
        "pct_so":        58.82,
        "pct_tc":        29.41,
        "pct_rd":        11.76,
    }
]

with patch("classifier.classify", return_value=MOCK_RESULTS):
    from app import app, RESULTS_PATH, clear_upload_cache, clear_session_cache


class TestRoutes(unittest.TestCase):
    """Test all GET page routes return 200"""

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_index_route(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        print("GET /           → 200 OK")

    def test_predict_route(self):
        res = self.client.get("/predict")
        self.assertEqual(res.status_code, 200)
        print("GET /predict     → 200 OK")

    def test_results_route_no_cache(self):
        """Results page with no JSON file — should still return 200"""
        clear_upload_cache()
        res = self.client.get("/results")
        self.assertEqual(res.status_code, 200)
        print("GET /results     → 200 OK (no cache)")


class TestPredictUploads(unittest.TestCase):
    """Test POST /predict-uploads"""

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_no_file_uploaded(self):
        res = self.client.post("/predict-uploads", data={})
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data)
        self.assertIn("error", data)
        print("No file          → 400 error")

    def test_invalid_file_type(self):
        """Upload a .txt file — should be rejected"""
        fake_file = (io.BytesIO(b"not a wav file"), "test.txt")
        res = self.client.post(
            "/predict-uploads",
            data={"file": fake_file},
            content_type="multipart/form-data"
        )
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data)
        self.assertIn("error", data)
        print(".txt file        → 400 rejected")

    def test_invalid_mp3_file(self):
        """Upload a .mp3 file — should be rejected"""
        fake_file = (io.BytesIO(b"fake mp3 data"), "audio.mp3")
        res = self.client.post(
            "/predict-uploads",
            data={"file": fake_file},
            content_type="multipart/form-data"
        )
        self.assertEqual(res.status_code, 400)
        print(".mp3 file        → 400 rejected")

    @patch("app.classify", return_value=MOCK_RESULTS)
    def test_valid_wav_upload(self, mock_classify):
        with open("/Users/perillaian/Desktop/Training/R_Dominica/2_05082025_171447-tenRdominica.wav", "rb") as f:
            real_wav = (io.BytesIO(f.read()), "yourfile.wav")
        res = self.client.post(
            "/predict-uploads",
            data={"file": real_wav},
            content_type="multipart/form-data"
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["status"], "ok")
        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["file_name"], "test.wav")
        print("Valid .wav       → 200 OK with results")

    def test_mixed_file_types(self):
        """Upload mix of .wav and invalid files — should reject whole batch"""
        with open("/Users/perillaian/Desktop/Training/R_Dominica/2_05082025_171447-tenRdominica.wav", "rb") as f:
            wav_data = f.read()

        real_files = [
            (io.BytesIO(wav_data),          "valid.wav"),
            (io.BytesIO(b"fake mp3 data"),  "audio.mp3"),
            (io.BytesIO(b"not a wav"),      "script.txt"),
        ]
        res = self.client.post(
            "/predict-uploads",
            data={"file": real_files},
            content_type="multipart/form-data"
        )
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data)
        self.assertIn("error", data)
        print("Mixed files      → 400 rejected")

    @patch("app.classify", side_effect=Exception("Model crashed"))
    def test_classify_error_handling(self, mock_classify):
        """Simulate classifier crash — should return 500 and clear cache"""
        fake_wav = (io.BytesIO(b"RIFF....WAVEfmt "), "test.wav")
        res = self.client.post(
            "/predict-uploads",
            data={"file": fake_wav},
            content_type="multipart/form-data"
        )
        self.assertEqual(res.status_code, 500)
        data = json.loads(res.data)
        self.assertIn("error", data)
        self.assertIn("Prediction failed", data["error"])

        # Verify session cache was cleared
        from app import SPEC_PATH, GRAPHS_PATH
        for folder in [SPEC_PATH, GRAPHS_PATH]:
            files = os.listdir(folder) if os.path.exists(folder) else []
            self.assertEqual(len(files), 0)

        print("Classifier crash → 500 error + cache cleared")

    @patch("app.classify", return_value=MOCK_RESULTS)
    def test_results_saved_to_json(self, mock_classify):
        """Check upload_predictions.json is written after prediction"""
        fake_wav = (io.BytesIO(b"RIFF....WAVEfmt "), "test.wav")
        self.client.post(
            "/predict-uploads",
            data={"file": fake_wav},
            content_type="multipart/form-data"
        )
        json_file = os.path.join(RESULTS_PATH, "upload_predictions.json")
        self.assertTrue(os.path.exists(json_file))
        with open(json_file) as f:
            saved = json.load(f)
        self.assertIsInstance(saved, list)
        print("JSON saved       → upload_predictions.json written")


class TestHelpers(unittest.TestCase):
    """Test helper functions"""

    def test_clear_upload_cache(self):
        """Create cache file then clear it"""
        os.makedirs(RESULTS_PATH, exist_ok=True)
        cache = os.path.join(RESULTS_PATH, "upload_predictions.json")
        with open(cache, "w") as f:
            json.dump([], f)
        self.assertTrue(os.path.exists(cache))
        clear_upload_cache()
        self.assertFalse(os.path.exists(cache))
        print("clear_upload_cache → JSON deleted")

    def test_clear_session_cache(self):
        """Create dummy files in spec_images and graphs then clear"""
        from app import SPEC_PATH, GRAPHS_PATH
        os.makedirs(SPEC_PATH, exist_ok=True)
        os.makedirs(GRAPHS_PATH, exist_ok=True)

        dummy_spec = os.path.join(SPEC_PATH, "dummy.png")
        dummy_graph = os.path.join(GRAPHS_PATH, "dummy.png")
        open(dummy_spec, "w").close()
        open(dummy_graph, "w").close()

        clear_session_cache()

        self.assertFalse(os.path.exists(dummy_spec))
        self.assertFalse(os.path.exists(dummy_graph))
        print("clear_session_cache → spec_images + graphs cleared")


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  ePADDY Flask App — Running Tests")
    print("=" * 50 + "\n")
    unittest.main(verbosity=0)
