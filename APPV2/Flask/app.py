import os
import sys
import re
import json
import shutil
import atexit
import configparser
from flask import Flask, render_template, request, jsonify, redirect, url_for

# Allow imports from Database/
sys.path.append(os.path.join(os.path.dirname(__file__), "../Database"))
from init_database import init_db, get_connection

sys.path.append(os.path.join(os.path.dirname(__file__), "../python"))
try:
    from classifier import classify
    CLASSIFIER_AVAILABLE = True
except ImportError as _e:
    CLASSIFIER_AVAILABLE = False
    classify = None
    print(f"[WARNING] Classifier not available (missing ML deps): {_e}")

from dashboard_service import (
    get_dashboard_data,
    get_daily_summary,
    get_weekly_summary,
    invalidate_cache,
)

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config.ini")
config = configparser.ConfigParser()
config.read(CONFIG_PATH)

MODEL_PATH      = config.get("paths", "model_path")
RECORDINGS_PATH = config.get("paths", "recordings_path")
AUDIO_OUTPUT    = config.get("paths", "audio_output")
RESULTS_PATH    = config.get("paths", "results_path")
LOG_PATH        = config.get("paths", "log_path", fallback="../logs/epaddy.log")
FLASK_HOST      = config.get("flask", "host", fallback="0.0.0.0")
FLASK_PORT      = config.getint("flask", "port", fallback=5000)
FLASK_DEBUG     = config.getboolean("flask", "debug", fallback=True)

BASE_DIR        = os.path.join(os.path.dirname(__file__), "..")
GRAPHS_PATH     = os.path.join(BASE_DIR, "static/graphs")
SPEC_PATH       = os.path.join(BASE_DIR, "static/spec_images")

# ── App ───────────────────────────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "../templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "../static"),
)

# ── Helpers ───────────────────────────────────────────────────────────────────
def sanitize(value):
    if value is None:
        return ""
    value = str(value).strip()
    value = re.sub(r"[;'\"\/\*\\]", "", value)
    return value[:255]


def clear_upload_cache():
    cache_file = os.path.join(RESULTS_PATH, "upload_predictions.json")
    if os.path.exists(cache_file):
        os.remove(cache_file)


def clear_session_cache():
    """Clear spectrogram and graph files — called on app exit or prediction error"""
    for folder in [SPEC_PATH, GRAPHS_PATH]:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                file_path = os.path.join(folder, f)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except Exception:
                    pass


def log_error(source, error):
    """Write error to logs folder"""
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a") as log:
            log.write(f"[{source}] {error}\n")
    except Exception:
        pass


# Register cleanup on app exit
atexit.register(clear_session_cache)
atexit.register(clear_upload_cache)


# ── Web Routes ────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/predict", methods=["GET"])
def upload():
    return render_template("predict.html")


@app.route("/about-us", methods=["GET"])
def about_us():
    return render_template("about-us.html")


@app.route("/results", methods=["GET"])
def results():
    result = None
    output_file = os.path.join(RESULTS_PATH, "upload_predictions.json")
    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            result = json.load(f)
    return render_template("results.html", result=result)


# ── Dashboard API Routes ──────────────────────────────────────────────────────
@app.route("/api/dashboard")
def dashboard_api():
    try:
        filters = {
            "start_date": sanitize(request.args.get("start_date", "")),
            "end_date"  : sanitize(request.args.get("end_date",   "")),
            "area"      : sanitize(request.args.get("area",       "")),
            "time_start": sanitize(request.args.get("time_start", "")),
            "time_end"  : sanitize(request.args.get("time_end",   "")),
            "insect"    : sanitize(request.args.get("insect",     "")),
        }
        return jsonify(get_dashboard_data(filters))
    except Exception as e:
        log_error("dashboard_api", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/dashboard/daily")
def dashboard_daily():
    try:
        date = sanitize(request.args.get("date", "")) or None
        return jsonify(get_daily_summary(date))
    except Exception as e:
        log_error("dashboard_daily", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/dashboard/weekly")
def dashboard_weekly():
    try:
        month = sanitize(request.args.get("month", "")) or None
        return jsonify(get_weekly_summary(month))
    except Exception as e:
        log_error("dashboard_weekly", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/cache/invalidate", methods=["POST"])
def cache_invalidate():
    """Called by cron job or after new data is saved to force a refresh."""
    invalidate_cache()
    return jsonify({"status": "cache cleared"})


# ── Prediction Routes ─────────────────────────────────────────────────────────
@app.route("/predict-uploads", methods=["POST"])
def predict():
    if not CLASSIFIER_AVAILABLE:
        return jsonify({"error": "Classifier not available on this server (ML dependencies not installed)."}), 503
    try:
        files = request.files.getlist("file")

        if not files or all(f.filename == "" for f in files):
            return jsonify({"error": "No files uploaded"}), 400

        for f in files:
            if not f.filename.lower().endswith(".wav"):
                return jsonify({"error": f"Invalid file type: {f.filename}. Only .wav files are supported."}), 400

        os.makedirs(RECORDINGS_PATH, exist_ok=True)
        os.makedirs(AUDIO_OUTPUT, exist_ok=True)
        os.makedirs(RESULTS_PATH, exist_ok=True)
        os.makedirs(SPEC_PATH, exist_ok=True)
        os.makedirs(GRAPHS_PATH, exist_ok=True)

        for f in files:
            save_path = os.path.join(RECORDINGS_PATH, f.filename)
            f.save(save_path)

        prediction_results = classify(RECORDINGS_PATH, AUDIO_OUTPUT, MODEL_PATH)

        if not isinstance(prediction_results, list):
            raise ValueError(f"Classifier error: {prediction_results}")

        for f in os.listdir(RECORDINGS_PATH):
            if f.lower().endswith(".wav"):
                os.remove(os.path.join(RECORDINGS_PATH, f))

        output_file = os.path.join(RESULTS_PATH, "upload_predictions.json")
        with open(output_file, "w") as f:
            json.dump(prediction_results, f, indent=2)

        return jsonify({"status": "ok", "results": prediction_results})

    except Exception as e:
        log_error("predict-uploads", e)
        clear_session_cache()
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500


# ── RPI Pipeline Routes ───────────────────────────────────────────────────────
@app.route("/receive_results", methods=["POST"])
def receive_results():
    try:
        data = request.get_json(silent=True)
        if not data or "results" not in data:
            raise ValueError("Invalid payload")
        # New data from RPi — bust the dashboard cache
        invalidate_cache()
        return jsonify({"status": "ok"})
    except Exception as e:
        log_error("receive_results", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs(RESULTS_PATH, exist_ok=True)
    os.makedirs(SPEC_PATH, exist_ok=True)
    os.makedirs(GRAPHS_PATH, exist_ok=True)
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
