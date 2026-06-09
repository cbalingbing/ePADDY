"""
filters.py — ePADDY Audio Filters & Normalization
==================================================
Provides bandpass filtering and waveform normalization
used before peak detection.

Usage:
    from filters import bandpass_filter, normalize_waveform
"""

import numpy as np
from scipy.signal import butter, filtfilt

from config import AudioConfig


def bandpass_filter(waveform: np.ndarray,
                    sr: int,
                    lowcut: float  = AudioConfig.BANDPASS_LOW,
                    highcut: float = AudioConfig.BANDPASS_HIGH,
                    order: int     = 4) -> np.ndarray:
    """
    Butterworth bandpass filter — isolates insect/pest frequency range.
    Removes low-frequency rumble (below lowcut) and noise (above highcut).

    Args:
        waveform : input audio signal
        sr       : sample rate (Hz)
        lowcut   : lower bound (Hz) — removes low-frequency rumble
        highcut  : upper bound (Hz) — removes high-frequency noise
        order    : filter steepness  (default: 4)

    Returns:
        Filtered waveform, same length as input
    """
    nyquist = sr / 2.0
    low     = lowcut  / nyquist
    high    = min(highcut / nyquist, 0.99)   # clamp strictly below Nyquist
    b, a    = butter(order, [low, high], btype='band')
    return filtfilt(b, a, waveform)


def normalize_waveform(waveform: np.ndarray) -> np.ndarray:
    """
    Normalize waveform to [-1, 1].
    Ensures peak detection is volume-independent.

    Args:
        waveform : input audio signal

    Returns:
        Normalized waveform, or original if silent (all zeros)
    """
    max_val = np.max(np.abs(waveform))
    if max_val == 0:
        return waveform
    return waveform / max_val
