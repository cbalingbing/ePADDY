"""
sensor_lookup.py — ePADDY temp/humidity CSV matcher

Matches a recording's node_id + timestamp (parsed from the audio filename)
against the sensor CSV written by the RPi 0 node (recordv2.py).

Audio filename format : {node_id}_{timestamp}-iSound.wav
                        e.g.  1_16022026_140002-iSound.wav
CSV row format        : DDMMYYYY_HHMMSS,node_id,filepath,temperature,humidity  (no header row)
                        e.g.  16022026_140002,1,/mnt/.../1_16022026_140002-iSound.wav,28.50,75.30
"""

import csv
import os
import re
from datetime import datetime

_FILENAME_RE = re.compile(r'^(\d+)_(\d{8}_\d{6})-iSound\.wav$', re.IGNORECASE)
_TS_FMT      = "%d%m%Y_%H%M%S"


def parse_audio_filename(audio_filepath: str):
    """
    Extract (node_id, timestamp_str, date_str, time_str) from the audio filename.
    Returns None if the filename does not match the expected pattern.
    """
    basename = os.path.basename(audio_filepath)
    m = _FILENAME_RE.match(basename)
    if not m:
        return None

    node_id = m.group(1)
    ts_str  = m.group(2)

    try:
        dt = datetime.strptime(ts_str, _TS_FMT)
    except ValueError:
        return None

    return node_id, ts_str, dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S")


def get_sensor_reading(audio_filepath: str, csv_path: str):
    """
    Look up the temp/humidity that was recorded alongside this audio file.

    Matching rule (dual-check):
      - node_id from filename == node_id column in CSV
      - timestamp string from filename appears inside the filename column in CSV

    Returns:
        (temp, humid)  on success
        (None, None)   if no match or CSV not found
    """
    parsed = parse_audio_filename(audio_filepath)
    if parsed is None:
        print(f"[sensor_lookup] Cannot parse node/timestamp from: "
              f"{os.path.basename(audio_filepath)}")
        return None, None

    node_id, ts_str, _, _ = parsed
    key = f"{node_id}_{ts_str}"

    if not os.path.exists(csv_path):
        print(f"[sensor_lookup] CSV not found: {csv_path}")
        return None, None

    matched_row = None
    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 5:
                continue
            csv_node     = row[1].strip()
            csv_filepath = row[2].strip()
            if csv_node == node_id and key in csv_filepath:
                matched_row = row

    if matched_row is None:
        print(f"[sensor_lookup] No CSV row matched '{key}' — "
              "temp/humid will be NULL in detections")
        return None, None

    try:
        temp  = float(matched_row[3])
        humid = float(matched_row[4])
    except (IndexError, ValueError) as e:
        print(f"[sensor_lookup] Could not parse temp/humid: {e}")
        return None, None

    print(f"[sensor_lookup] Matched — node={node_id}, ts={ts_str}, "
          f"temp={temp:.2f}°C, humid={humid:.2f}%")
    return temp, humid
