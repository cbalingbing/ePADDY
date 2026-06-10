"""
test_latest_only.py — verify classify()'s latest-only selection
===============================================================
Creates MULTIPLE .wav files in a temp folder and checks that:
    classify(..., latest_only=True)  → processes ONLY the newest file
    classify(...)                    → processes ALL files (default)

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
print("looking for classifier in:", target)     # <-- debug line, remove later
sys.path.insert(0, target)

import classifier   # import the MODULE (tests use classifier.classify / patch classifier.*)

class TestLatestOnly(unittest.TestCase):

    def setUp(self):
        self.recordings = tempfile.mkdtemp()
        self.output     = tempfile.mkdtemp()

        # Create 3 .wav files with strictly increasing creation times
        self.names = []
        for i in range(3):
            path = os.path.join(self.recordings, f"node_{i}.wav")
            with open(path, "wb") as f:
                f.write(b"RIFFfakewav")
            self.names.append(os.path.basename(path))
            time.sleep(0.05)        # ensure distinct ctimes
        self.latest_name = self.names[-1]   # node_2.wav is newest

    # process_audio_file mocked → no segments → classifier uses its zero-result
    # path, so no real model/inference is needed.
    @patch("classifier.YOLOClassifier")
    @patch("classifier.process_audio_file", return_value=([], 0, 0.0))
    def test_latest_only_processes_one(self, mock_proc, mock_yolo):
        results = classifier.classify(self.recordings, self.output,
                                      "fake_model.pt", latest_only=True)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["file_name"], self.latest_name)
        print(f"latest_only=True  → processed only {results[0]['file_name']}")

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
