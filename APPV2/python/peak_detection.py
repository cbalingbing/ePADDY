"""
peak_detection.py — ePADDY Burst Peak Detection
================================================
Detects insect burst events in an audio waveform using
RMS envelope analysis after bandpass filtering.

Usage:
    from peak_detection import detect_burst_peaks
"""

import numpy as np
import librosa
from scipy.signal import find_peaks

from config import AudioConfig
from filters import bandpass_filter, normalize_waveform


def detect_burst_peaks(waveform: np.ndarray,
                       sr: int,
                       threshold_factor: float = AudioConfig.THRESHOLD_FACTOR,
                       peak_distance: int      = AudioConfig.PEAK_DISTANCE,
                       lowcut: float           = AudioConfig.BANDPASS_LOW,
                       highcut: float          = AudioConfig.BANDPASS_HIGH
                       ) -> np.ndarray:
    """
    Detect signal bursts in audio after bandpass filtering.

    Pipeline:
        1. Bandpass filter  → isolate insect frequency range
        2. Normalize        → volume-independent threshold
        3. RMS envelope     → smooth out single-sample spikes
        4. Adaptive thresh  → scale to signal energy level
        5. find_peaks       → locate burst events

    Args:
        waveform         : input audio signal
        sr               : sample rate (Hz)
        threshold_factor : RMS multiplier — lower = more sensitive
                           (default: 0.25)
        peak_distance    : minimum samples between consecutive peaks
        lowcut           : bandpass lower bound (Hz)
        highcut          : bandpass upper bound (Hz)

    Returns:
        1-D array of peak indices in original waveform sample space
    """
    # Step 1 — Bandpass filter
    filtered = bandpass_filter(waveform, sr, lowcut=lowcut, highcut=highcut)

    # Step 2 — Normalize to [-1, 1]
    filtered = normalize_waveform(filtered)

    # Step 3 — RMS envelope (10 ms frames)
    frame_length = max(2, int(sr * 0.01))
    hop          = max(1, frame_length // 2)
    rms_envelope = librosa.feature.rms(
        y=filtered,
        frame_length=frame_length,
        hop_length=hop
    )[0]

    # Step 4 — Adaptive threshold based on signal RMS energy
    rms       = np.sqrt(np.mean(filtered ** 2))
    threshold = rms * threshold_factor

    # Step 5 — Peak detection on smoothed envelope
    peaks, _ = find_peaks(rms_envelope, height=threshold, distance=peak_distance)

    # Amplitude stats on the normalized waveform
    abs_waveform = np.abs(filtered)
    stats = {
        'min_amplitude': float(np.min(filtered)),
        'avg_amplitude': float(np.mean(abs_waveform)),
        'max_amplitude': float(np.max(filtered)),
    }

    # Map envelope frame indices → waveform sample indices
    return peaks * hop, stats
