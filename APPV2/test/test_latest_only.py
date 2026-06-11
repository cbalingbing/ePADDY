"""
test_latest_only.py — verify classify()'s latest-only selection
===============================================================
Creates MULTIPLE .wav files in a temp folder and checks that:
    classify(..., latest_only=True)  → processes ONLY the newest RECORDING
    classify(...)                    → processes ALL files (default)

"Newest" is decided by the timestamp in the filename ({node}_{DDMMYYYY_HHMMSS}-
iSound.wav), NOT by file ctime. The key test writes the files so that ctime
order is the OPPOSITE of recording-date order — proving a stale file copied in
later (newest ctime) can't win over a genuinely newer recording.

The YOLO model and audio preprocessing are mocked, so this runs without
torch/the model or real audio.

Run:  python test_latest_only.py
"""


import time
import tempfile
import unittest
from unittest.mock import patch
import os, sys
# absolute path to APPV2/python, relative to THIS file (not the cwd)
target = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, target)

import classifier   # import the MODULE (tests use classifier.classify / patch classifier.*)

class TestLatestOnly(unittest.TestCase):

    def setUp(self):
        self.recordings = tempfile.mkdtemp()
        self.output     = tempfile.mkdtemp()

        # Real recording filenames. IMPORTANT: written in an order where ctime
        # is the REVERSE of the recording date, to prove selection is by the
        # filename timestamp and not by ctime:
        #   written 1st (oldest ctime) → 11 Jun 2026  ← newest RECORDING
        #   written 2nd                → 02 Jun 2026
        #   written 3rd (newest ctime) → 18 May 2026  ← stale copy, must NOT win
        self.names = [
            "1_11062026_120003-iSound.wav",   # 2026-06-11  (latest recording)
            "1_02062026_100000-iSound.wav",   # 2026-06-02
            "1_18052026_220002-iSound.wav",   # 2026-05-18  (newest ctime, stale)
        ]
        for name in self.names:
            with open(os.path.join(self.recordings, name), "wb") as f:
                f.write(b"RIFFfakewav")
            time.sleep(0.05)        # ensure distinct, increasing ctimes
        self.latest_name = "1_11062026_120003-iSound.wav"   # by DATE, not ctime

    # process_audio_file mocked → no segments → classifier uses its zero-result
    # path, so no real model/inference is needed.
    @patch("classifier.YOLOClassifier")
    @patch("classifier.process_audio_file", return_value=([], 0, 0.0))
    def test_latest_only_picks_newest_recording_not_newest_ctime(self, mock_proc, mock_yolo):
        results = classifier.classify(self.recordings, self.output,
                                      "fake_model.pt", latest_only=True)
        self.assertEqual(len(results), 1)
        # The May-18 file has the newest ctime but the oldest date — it must lose.
        self.assertEqual(results[0]["file_name"], self.latest_name)
        print(f"latest_only=True  → processed only {results[0]['file_name']} (by date)")

    @patch("classifier.YOLOClassifier")
    @patch("classifier.process_audio_file", return_value=([], 0, 0.0))
    def test_default_processes_all(self, mock_proc, mock_yolo):
        results = classifier.classify(self.recordings, self.output,
                                      "fake_model.pt")
        self.assertEqual(len(results), 3)
        got = sorted(r["file_name"] for r in results)
        self.assertEqual(got, sorted(self.names))
        print(f"default           → processed all {len(results)} files")

    @patch("classifier.YOLOClassifier")
    @patch("classifier.process_audio_file", return_value=([], 0, 0.0))
    def test_no_wavs_returns_empty(self, mock_proc, mock_yolo):
        empty = tempfile.mkdtemp()
        self.assertEqual(classifier.classify(empty, self.output, "fake_model.pt",
                                             latest_only=True), [])


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  ePADDY — classify() latest-only tests")
    print("=" * 50 + "\n")
    unittest.main(verbosity=2)
