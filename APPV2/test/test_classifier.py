#!/usr/bin/env python3
"""
test_classifier.py — test ONLY the classifier output
====================================================
No email, no DB, no SMTP. Reads paths from ../config.ini, runs classify(),
then prints and sanity-checks the result.

Run:
    python test_classifier.py
"""
import os
import sys
import json
import configparser

HERE  = os.path.dirname(os.path.abspath(__file__))
APPV2 = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(APPV2, "python"))
from classifier import classify

cfg = configparser.ConfigParser()
cfg.read(os.path.join(APPV2, "config.ini"))
MODEL_PATH   = cfg.get("paths", "model_path")
AUDIO_INPUT  = cfg.get("paths", "audio_input")
AUDIO_OUTPUT = cfg.get("paths", "audio_output")

print(f"model_path  : {MODEL_PATH}")
print(f"audio_input : {AUDIO_INPUT}")
print(f"audio_output: {AUDIO_OUTPUT}")
print("Running classifier...\n")

results = classify(AUDIO_INPUT, AUDIO_OUTPUT, MODEL_PATH)

print(f"Returned {len(results)} result(s):\n")
print(json.dumps(results, indent=2))

# sanity check: list of dicts with the expected keys (detection pipeline)
expected = {"file_name", "num_detect_so", "num_detect_tc", "num_detect_rd",
            "pct_so", "pct_tc", "pct_rd", "max_peaks", "avg_amplitude", "est_so"}
ok = isinstance(results, list)
for r in results:
    if not expected.issubset(r):
        ok = False
        print(f"\n[!] Missing keys in: {r}")
print("\nOutput shape:", "OK" if ok else "WRONG")
