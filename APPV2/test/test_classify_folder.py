"""
test_classify_folder.py — full-coverage tests for classifier.classify()
=======================================================================
Exercises classify() against a temp FOLDER of many realistic .wav files,
covering selection (default vs latest_only), detection-count flow-through,
and edge cases.

Runs ANYWHERE — no numpy / torch / model needed. The two heavy modules the
classifier imports (preprocessing, inference) are STUBBED in sys.modules
BEFORE classifier is imported, so the real ML stack never loads. Individual
tests then patch classifier.process_audio_file / classifier.YOLOClassifier to
script exactly what each .wav "detects".

Run:  python test_classify_folder.py
"""

import os
import sys
import time
import types
import tempfile
import unittest
from unittest.mock import patch

# ── Stub the ML modules BEFORE importing classifier (avoids numpy/torch) ───────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))

_fake_pre = types.ModuleType("preprocessing")
_fake_pre.process_audio_file = lambda wav, out: ([], 0, 0.0)   # default: no segments
sys.modules["preprocessing"] = _fake_pre

_fake_inf = types.ModuleType("inference")
class _StubYOLO:                       # default stub — overridden per test
    def __init__(self, model_path):
        pass
    def predict_batch(self, folder, conf=0.80, file_extension=".png"):
        return {"total_images": 0, "results": []}
_fake_inf.YOLOClassifier = _StubYOLO
sys.modules["inference"] = _fake_inf

import classifier   # noqa: E402  (must come after the stubs above)


# ── Helpers ────────────────────────────────────────────────────────────────────
def make_wavs(folder, names, gap=0.02):
    """Create empty .wav files in `folder`, in list order, with increasing
    ctimes (so ctime order == list order). Returns the list of names."""
    for n in names:
        with open(os.path.join(folder, n), "wb") as f:
            f.write(b"RIFFfakewav")
        time.sleep(gap)
    return names


def fake_detector(per_image, total_images=None):
    """Build a fake YOLOClassifier class whose predict_batch returns a scripted
    detection summary (list of {class_counts, top_class} dicts)."""
    summary = {
        "total_images": total_images if total_images is not None else len(per_image),
        "results": per_image,
    }
    class _Fake:
        def __init__(self, model_path):
            pass
        def predict_batch(self, folder, conf=0.80, file_extension=".png"):
            return summary
    return _Fake


EXPECTED_KEYS = {
    "file_name", "num_detect_so", "num_detect_tc", "num_detect_rd",
    "pct_so", "pct_tc", "pct_rd", "max_peaks", "avg_amplitude", "est_so",
}

# A realistic folder of recordings. NOTE the order written here (= ctime order)
# is deliberately NOT the recording-date order, so latest_only can be proven to
# use the filename timestamp, not ctime.
FOLDER_FILES = [
    "1_05012026_080000-iSound.wav",   # 05 Jan 2026
    "1_11062026_120003-iSound.wav",   # 11 Jun 2026  ← newest recording
    "2_02062026_100000-iSound.wav",   # 02 Jun 2026
    "1_18052026_220002-iSound.wav",   # 18 May 2026  ← written LAST = newest ctime
]
NEWEST_BY_DATE = "1_11062026_120003-iSound.wav"


class TestClassifyFolder(unittest.TestCase):

    def setUp(self):
        self.rec = tempfile.mkdtemp()
        self.out = tempfile.mkdtemp()

    # ── Selection ──────────────────────────────────────────────────────────────
    @patch("classifier.YOLOClassifier", new=_StubYOLO)
    @patch("classifier.process_audio_file", return_value=([], 0, 0.0))
    def test_default_processes_all(self, _proc):
        make_wavs(self.rec, FOLDER_FILES)
        results = classifier.classify(self.rec, self.out, "fake.pt")
        self.assertEqual(len(results), len(FOLDER_FILES))
        self.assertEqual(
            sorted(r["file_name"] for r in results), sorted(FOLDER_FILES))

    @patch("classifier.YOLOClassifier", new=_StubYOLO)
    @patch("classifier.process_audio_file", return_value=([], 0, 0.0))
    def test_latest_only_picks_newest_by_date(self, _proc):
        make_wavs(self.rec, FOLDER_FILES)
        results = classifier.classify(self.rec, self.out, "fake.pt", latest_only=True)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["file_name"], NEWEST_BY_DATE)

    @patch("classifier.YOLOClassifier", new=_StubYOLO)
    @patch("classifier.process_audio_file", return_value=([], 0, 0.0))
    def test_latest_only_ignores_newest_ctime(self, _proc):
        # The 18-May file is written LAST (newest ctime) but is the OLDEST
        # recording — it must NOT be selected.
        make_wavs(self.rec, FOLDER_FILES)
        newest_ctime = max(
            (os.path.join(self.rec, n) for n in FOLDER_FILES), key=os.path.getctime)
        self.assertTrue(newest_ctime.endswith("1_18052026_220002-iSound.wav"))
        results = classifier.classify(self.rec, self.out, "fake.pt", latest_only=True)
        self.assertNotEqual(results[0]["file_name"], "1_18052026_220002-iSound.wav")

    @patch("classifier.YOLOClassifier", new=_StubYOLO)
    @patch("classifier.process_audio_file", return_value=([], 0, 0.0))
    def test_latest_only_single_file(self, _proc):
        make_wavs(self.rec, ["1_01012026_000000-iSound.wav"])
        results = classifier.classify(self.rec, self.out, "fake.pt", latest_only=True)
        self.assertEqual(len(results), 1)

    @patch("classifier.YOLOClassifier", new=_StubYOLO)
    @patch("classifier.process_audio_file", return_value=([], 0, 0.0))
    def test_non_standard_name_falls_back_to_ctime(self, _proc):
        # A file that doesn't match the {node}_{ts}-iSound.wav pattern still
        # participates via ctime fallback; written last → it's newest by ctime.
        make_wavs(self.rec, ["1_01012026_000000-iSound.wav", "weird_name.wav"])
        results = classifier.classify(self.rec, self.out, "fake.pt", latest_only=True)
        self.assertEqual(results[0]["file_name"], "weird_name.wav")

    # ── Edge cases ─────────────────────────────────────────────────────────────
    @patch("classifier.YOLOClassifier", new=_StubYOLO)
    @patch("classifier.process_audio_file", return_value=([], 0, 0.0))
    def test_empty_folder_returns_empty(self, _proc):
        self.assertEqual(classifier.classify(self.rec, self.out, "fake.pt"), [])
        self.assertEqual(
            classifier.classify(self.rec, self.out, "fake.pt", latest_only=True), [])

    @patch("classifier.YOLOClassifier", new=_StubYOLO)
    @patch("classifier.process_audio_file", return_value=([], 0, 0.0))
    def test_ignores_non_wav_files(self, _proc):
        make_wavs(self.rec, ["1_01012026_000000-iSound.wav"])
        with open(os.path.join(self.rec, "notes.txt"), "w") as f:
            f.write("ignore me")
        with open(os.path.join(self.rec, "image.png"), "wb") as f:
            f.write(b"x")
        results = classifier.classify(self.rec, self.out, "fake.pt")
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["file_name"].endswith(".wav"))

    @patch("classifier.YOLOClassifier", new=_StubYOLO)
    @patch("classifier.process_audio_file", return_value=([], 0, 0.0))
    def test_no_segments_gives_zero_result(self, _proc):
        make_wavs(self.rec, ["1_01012026_000000-iSound.wav"])
        r = classifier.classify(self.rec, self.out, "fake.pt")[0]
        self.assertEqual((r["num_detect_so"], r["num_detect_tc"], r["num_detect_rd"]), (0, 0, 0))
        self.assertEqual(r["est_so"], 0)
        self.assertTrue(EXPECTED_KEYS.issubset(r))

    @patch("classifier.process_audio_file")
    def test_failed_file_is_skipped_others_survive(self, proc):
        # First file (alphabetically) raises; the rest must still be processed.
        make_wavs(self.rec, [
            "1_01012026_000000-iSound.wav",
            "1_02012026_000000-iSound.wav",
            "1_03012026_000000-iSound.wav",
        ])
        def side_effect(wav, out):
            if wav.endswith("1_01012026_000000-iSound.wav"):
                raise RuntimeError("boom — corrupt audio")
            return ([], 0, 0.0)
        proc.side_effect = side_effect
        with patch("classifier.YOLOClassifier", new=_StubYOLO):
            results = classifier.classify(self.rec, self.out, "fake.pt")
        names = {r["file_name"] for r in results}
        self.assertEqual(len(results), 2)
        self.assertNotIn("1_01012026_000000-iSound.wav", names)

    # ── Detection-count flow-through ───────────────────────────────────────────
    @patch("classifier.process_audio_file", return_value=(["seg1", "seg2"], 1500, 0.05))
    def test_detection_counts_and_pct(self, _proc):
        make_wavs(self.rec, ["1_01012026_000000-iSound.wav"])
        per_image = [
            {"class_counts": {"S_Oryzae": 3, "T_Castaneum": 1}, "top_class": "S_Oryzae"},
            {"class_counts": {"S_Oryzae": 2},                    "top_class": "S_Oryzae"},
        ]
        with patch("classifier.YOLOClassifier", new=fake_detector(per_image)):
            r = classifier.classify(self.rec, self.out, "fake.pt")[0]
        # totals: SO=5, TC=1, RD=0  (total boxes = 6)
        self.assertEqual(r["num_detect_so"], 5)
        self.assertEqual(r["num_detect_tc"], 1)
        self.assertEqual(r["num_detect_rd"], 0)
        self.assertAlmostEqual(r["pct_so"], round(5 / 6 * 100, 2))
        self.assertAlmostEqual(r["pct_tc"], round(1 / 6 * 100, 2))
        self.assertEqual(r["max_peaks"], 1500)
        # S_Oryzae dominant in 2/2 segments → est_so scaled by 100% → > 0
        self.assertGreater(r["est_so"], 0)
        self.assertTrue(EXPECTED_KEYS.issubset(r))

    @patch("classifier.process_audio_file", return_value=(["seg1"], 9000, 0.0))
    def test_est_so_zero_when_no_so_dominance(self, _proc):
        make_wavs(self.rec, ["1_01012026_000000-iSound.wav"])
        per_image = [
            {"class_counts": {"R_Dominica": 4}, "top_class": "R_Dominica"},
        ]
        with patch("classifier.YOLOClassifier", new=fake_detector(per_image)):
            r = classifier.classify(self.rec, self.out, "fake.pt")[0]
        self.assertEqual(r["num_detect_rd"], 4)
        self.assertEqual(r["est_so"], 0)   # no S_Oryzae dominance → scaled to 0

    def test_result_shape_is_list_of_dicts(self):
        make_wavs(self.rec, FOLDER_FILES)
        with patch("classifier.process_audio_file", return_value=([], 0, 0.0)), \
             patch("classifier.YOLOClassifier", new=_StubYOLO):
            results = classifier.classify(self.rec, self.out, "fake.pt")
        self.assertIsInstance(results, list)
        for r in results:
            self.assertIsInstance(r, dict)
            self.assertTrue(EXPECTED_KEYS.issubset(r))


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  ePADDY — classify() folder coverage tests")
    print("=" * 60 + "\n")
    unittest.main(verbosity=2)
