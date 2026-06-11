#!/usr/bin/env python3
"""
classifier.py — ePADDY insect detector (YOLO object-detection)
==============================================================
PURE PREDICTION. Runs the YOLO DETECTION model over the spectrograms of
EVERY .wav file in the input folder and returns the results. It does NOT
write to the database and does NOT send anything — email_sender.py owns
those side-effects (DB write + temp/humid lookup + email).

    classify(input_folder, output_folder, model_path) -> list[dict]

Each dict (one per processed .wav):
    file_name      str    the .wav filename
    num_detect_so  int    total S_Oryzae bounding boxes (all segments)
    num_detect_tc  int    total T_Castaneum boxes
    num_detect_rd  int    total R_Dominica boxes
    pct_so/tc/rd   float   % of all boxes that were each class
    max_peaks      int     number of burst-peak segments
    avg_amplitude  float   mean |amplitude| (drives est_so)
    est_so         int     regression estimate of S_Oryzae insects,
                           scaled by the % of segments S_Oryzae dominated
"""

import os
import re
from datetime import datetime
from preprocessing import process_audio_file
from inference import YOLOClassifier

ALL_KNOWN_CLASSES = ['R_Dominica', 'S_Oryzae', 'T_Castaneum']

# Recording timestamp embedded in the filename: {node}_{DDMMYYYY_HHMMSS}-iSound.wav
_TS_RE = re.compile(r'_(\d{8}_\d{6})-iSound\.wav$', re.IGNORECASE)


def _recording_time(path):
    """Sort key for 'latest' selection: the REAL datetime parsed from the
    filename (DDMMYYYY_HHMMSS), not file ctime. Files copied onto the device
    (e.g. via a shared drive) get a fresh ctime that doesn't reflect when they
    were recorded, so ctime would wrongly pick a stale recording. Falls back to
    ctime only when the name doesn't match the expected pattern."""
    m = _TS_RE.search(os.path.basename(path))
    if m:
        try:
            return datetime.strptime(m.group(1), "%d%m%Y_%H%M%S").timestamp()
        except ValueError:
            pass
    return os.path.getctime(path)


def _analyze_wav(wav_file, output_folder, detector):
    """Process one .wav and return its prediction dict."""
    spectrograms, max_peaks, avg_amplitude = process_audio_file(wav_file, output_folder)

    base = {
        "file_name"    : os.path.basename(wav_file),
        "num_detect_so": 0, "num_detect_tc": 0, "num_detect_rd": 0,
        "pct_so": 0.0, "pct_tc": 0.0, "pct_rd": 0.0,
        "max_peaks"    : max_peaks or 0,
        "avg_amplitude": round(avg_amplitude or 0.0, 6),
        "est_so"       : 0,
    }
    if not spectrograms:
        return base   # no segments → nothing to detect

    det_summary    = detector.predict_batch(output_folder, conf=0.80, file_extension='.png')
    total_segments = det_summary['total_images']
    per_image      = det_summary['results']

    # TD_xx = total boxes for that class across all segments
    # dominant_count = segments where that class had the most boxes
    total_boxes_per_class    = {c: 0 for c in ALL_KNOWN_CLASSES}
    dominant_count_per_class = {c: 0 for c in ALL_KNOWN_CLASSES}
    for r in per_image:
        for cls, cnt in r['class_counts'].items():
            if cls in total_boxes_per_class:
                total_boxes_per_class[cls] += cnt
        if r['top_class'] in dominant_count_per_class:
            dominant_count_per_class[r['top_class']] += 1

    td_so = total_boxes_per_class['S_Oryzae']
    td_tc = total_boxes_per_class['T_Castaneum']
    td_rd = total_boxes_per_class['R_Dominica']
    total_boxes = td_so + td_tc + td_rd

    def pct(n):
        return round(n / total_boxes * 100, 2) if total_boxes else 0.0

    # % of segments where S_Oryzae was dominant (drives the est_so scaling)
    pd_so = (dominant_count_per_class['S_Oryzae'] / total_segments * 100) if total_segments else 0.0

    # est_so — linear regression estimate scaled by S_Oryzae dominance %
    estimated_total = 8.874848 + (-0.000061 * max_peaks) + (141.215010 * avg_amplitude)
    est_so = max(0, round(estimated_total * (pd_so / 100)))

    base.update({
        "num_detect_so": td_so, "num_detect_tc": td_tc, "num_detect_rd": td_rd,
        "pct_so": pct(td_so), "pct_tc": pct(td_tc), "pct_rd": pct(td_rd),
        "est_so": est_so,
    })
    return base


def classify(input_folder, output_folder, model_path, latest_only=False):
    """
    Run YOLO detection over the .wav files in input_folder.

    latest_only=False : process every .wav (default — used by the web upload).
    latest_only=True  : process only the newest recording, chosen by the
                        timestamp in the filename (not file ctime), so a stale
                        file copied in via a shared drive can't win. Used by the
                        cron email_sender.

    Returns a list of per-file prediction dicts (empty list if no .wav files).
    Pure prediction — no DB writes, no email.
    """
    wav_files = [
        os.path.join(input_folder, f)
        for f in os.listdir(input_folder)
        if f.lower().endswith('.wav')
    ]
    if not wav_files:
        return []

    if latest_only:
        wav_files = [max(wav_files, key=_recording_time)]

    os.makedirs(output_folder, exist_ok=True)
    detector = YOLOClassifier(model_path)
    results  = []

    for wav_file in sorted(wav_files):
        try:
            results.append(_analyze_wav(wav_file, output_folder, detector))
        except Exception as e:
            print(f"[classifier] Failed on {os.path.basename(wav_file)}: {e}")
        finally:
            # Clean spectrogram PNGs between files
            for fn in os.listdir(output_folder):
                fp = os.path.join(output_folder, fn)
                if os.path.isfile(fp):
                    try:
                        os.remove(fp)
                    except OSError:
                        pass

    return results


if __name__ == "__main__":
    import sys, json
    inp = sys.argv[1] if len(sys.argv) > 1 else '/path/to/wavs'
    out = sys.argv[2] if len(sys.argv) > 2 else '/tmp/epaddy_output'
    mdl = sys.argv[3] if len(sys.argv) > 3 else '/path/to/YOLOBBOX.pt'
    print(json.dumps(classify(inp, out, mdl), indent=2))
