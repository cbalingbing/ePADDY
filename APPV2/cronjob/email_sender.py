#!/usr/bin/env python3
"""
email_sender.py — ePADDY cronjob (detection pipeline)
=====================================================
Cron entry point. Uses the (pure-prediction) classifier to detect insects in
ALL .wav files, then OWNS the side-effects:
    - looks up temp/humid for each recording (sensor CSV)
    - writes one detections row per .wav (save_detection)
    - logs a CSV row per .wav
    - emails a summary

Run by cron with an absolute python path:
    /path/to/.venv/bin/python /path/to/APPV2/cronjob/email_sender.py
All paths are resolved absolutely, so the cron working directory doesn't matter.
"""

import os
import sys
import csv
import uuid
import smtplib
import configparser
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

HERE  = os.path.dirname(os.path.abspath(__file__))   # .../APPV2/cronjob
APPV2 = os.path.dirname(HERE)                         # .../APPV2

# Pure-prediction classifier + sensor lookup (detection pipeline)
sys.path.insert(0, os.path.join(APPV2, "python"))
from classifier import classify
from sensor_lookup import parse_audio_filename, get_sensor_reading

# DB write (this script owns it — the classifier does not touch the DB)
sys.path.insert(0, os.path.join(APPV2, "Database"))
from init_database import init_db, save_detection

# ── Config ────────────────────────────────────────────────────────────────────
cfg = configparser.ConfigParser()
cfg.read(os.path.join(APPV2, "config.ini"))

MODEL_PATH   = cfg.get("paths", "model_path")
AUDIO_INPUT  = cfg.get("paths", "audio_input")
AUDIO_OUTPUT = cfg.get("paths", "audio_output")
NODE_NAME    = cfg.get("node",  "node_name", fallback="unknown")

# Temp/humidity sensor CSV written by the RPi node (optional)
TH_READINGS  = cfg.get("sensor", "readings_csv", fallback="")

# Requires [email] and [Area] sections in config.ini:
#   [email]
#   app_pass = /path/to/credentials.txt   ; line1 = sender gmail, line2 = app password
#   emails   = a@x.com, b@y.com
#   csv_path = ../results/predictions.csv  ; optional
#   [Area]
#   placeholder_name = Warehouse-A         ; friendly name  -> DB area_name
#   coordinates      = 120.9842,14.5995    ; "lon,lat"      -> DB area / map pin
CRED_PATH   = cfg.get("email", "app_pass")
EMAILS      = [e.strip() for e in cfg.get("email", "emails").split(",") if e.strip()]
CSV_PATH    = cfg.get("email", "csv_path",
                      fallback=os.path.join(APPV2, "results", "predictions.csv"))
AREA_NAME   = cfg.get("Area", "placeholder_name", fallback="Unknown")
AREA_COORDS = cfg.get("Area", "coordinates", fallback="")

with open(CRED_PATH) as f:
    _lines = f.readlines()
    SENDER_EMAIL = _lines[0].strip()
    APP_PASS     = _lines[1].strip()

CSV_HEADER = ["Date", "Time", "Sensor", "Area_Name", "Coordinates",
              "Num_SO", "Num_TC", "Num_RD", "Pct_SO", "Pct_TC", "Pct_RD",
              "Max_Peaks", "Est_SO", "Temp", "Humid"]


def clear_folder(path):
    """Delete all files in a folder (used to clear leftover spectrograms)."""
    if not os.path.isdir(path):
        return
    for fn in os.listdir(path):
        fp = os.path.join(path, fn)
        if os.path.isfile(fp):
            try:
                os.remove(fp)
            except OSError:
                pass


def log_to_csv(rows):
    """Append one row per processed file to the CSV log (writes header once)."""
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    file_exists = os.path.isfile(CSV_PATH)
    with open(CSV_PATH, "a", newline="") as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(CSV_HEADER)
        w.writerows(rows)


def build_email_body(results, now):
    lines = ["ePADDY Detection Report", f"Generated: {now}", ""]
    if not results:
        lines.append("No audio files found / no detections.")
        return "\n".join(lines)
    for r in results:
        lines += [
            f"File: {r['file_name']}",
            f"  S_Oryzae    : {r['num_detect_so']} ({r['pct_so']}%)",
            f"  T_Castaneum : {r['num_detect_tc']} ({r['pct_tc']}%)",
            f"  R_Dominica  : {r['num_detect_rd']} ({r['pct_rd']}%)",
            f"  Est. S_Oryzae insects : {r['est_so']}",
            "",
        ]
    return "\n".join(lines)


def send_email(body):
    s = smtplib.SMTP("smtp.gmail.com", 587)
    s.starttls()
    s.login(SENDER_EMAIL, APP_PASS)          # log in once, then loop recipients
    for addr in EMAILS:
        msg = MIMEMultipart()
        msg["From"]       = SENDER_EMAIL
        msg["To"]         = addr
        msg["Subject"]    = "[ePADDY] Detection Results"
        msg["Message-ID"] = f"<{uuid.uuid4()}@gmail.com>"
        msg.attach(MIMEText(body, "plain"))
        s.sendmail(SENDER_EMAIL, addr, msg.as_string())
        print(f"Email sent to {addr}")
    s.quit()


def main():
    now = datetime.now()
    try:
        clear_folder(AUDIO_OUTPUT)                   # pre-clean: drop leftovers from a crashed run
        init_db()                                   # ensure tables exist (+ migrations)
        # Cron processes only the LATEST recording (latest_only=True)
        results = classify(AUDIO_INPUT, AUDIO_OUTPUT, MODEL_PATH, latest_only=True)

        rows = []
        for r in results:
            wav_path = os.path.join(AUDIO_INPUT, r["file_name"])

            # Date / time / sensor from the filename; fall back to now + node name
            parsed = parse_audio_filename(wav_path)
            if parsed:
                sensor_number, _, date_str, time_str = parsed
            else:
                sensor_number = NODE_NAME
                date_str = now.strftime("%Y-%m-%d")
                time_str = now.strftime("%H:%M:%S")

            # Temp/humid lookup (the sender owns this, not the classifier)
            temp, humid = (None, None)
            if TH_READINGS:
                temp, humid = get_sensor_reading(wav_path, TH_READINGS)

            save_detection(
                date=date_str, time=time_str, sensor_number=sensor_number,
                area=AREA_COORDS, area_name=AREA_NAME,
                num_so=r["num_detect_so"], num_tc=r["num_detect_tc"],
                num_rd=r["num_detect_rd"], temp=temp, humid=humid,
                est_so=r["est_so"],
            )
            rows.append([date_str, time_str, sensor_number, AREA_NAME, AREA_COORDS,
                         r["num_detect_so"], r["num_detect_tc"], r["num_detect_rd"],
                         r["pct_so"], r["pct_tc"], r["pct_rd"],
                         r["max_peaks"], r["est_so"], temp, humid])

        if rows:
            log_to_csv(rows)

        send_email(build_email_body(results, now))
        print(f"[{now}] Done. {len(results)} file(s) processed.")
    except Exception as e:
        print(f"[{now}] Error: {e}")
    finally:
        clear_folder(AUDIO_OUTPUT)                   # post-clean: leave no spectrograms behind


if __name__ == "__main__":
    main()
