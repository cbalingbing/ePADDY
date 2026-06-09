"""
spectrogram.py — ePADDY Mel Spectrogram Generation
===================================================
Converts an audio segment into a 640×640 viridis-coloured
mel spectrogram image ready for YOLO inference.

Usage:
    from spectrogram import generate_epaddy_spectrogram
"""

import numpy as np
import librosa
import matplotlib.pyplot as plt
import cv2
from typing import Tuple

from config import AudioConfig


def generate_epaddy_spectrogram(audio_data: np.ndarray,
                                 samplerate: int         = AudioConfig.SR,
                                 target_size: Tuple[int, int] = AudioConfig.TARGET_SIZE
                                 ) -> np.ndarray:
    """
    Generate a mel-spectrogram image following ePADDY paper specs.

    Steps:
        1. Resample if needed
        2. Ensure mono
        3. Compute mel spectrogram
        4. Amplitude → dB  (log scale, wide dynamic range)
        5. Normalize to [0, 1]
        6. Flip vertically  (low frequencies at bottom)
        7. Bicubic resize to target_size
        8. Apply viridis colormap
        9. Convert to uint8 BGR  (OpenCV format)

    Args:
        audio_data  : mono audio array
        samplerate  : sample rate (Hz) — will resample if != AudioConfig.SR
        target_size : (width, height) output size — default (640, 640)

    Returns:
        BGR image array  shape (H, W, 3)  dtype uint8
    """
    # Step 1 — Resample if needed
    if samplerate != AudioConfig.SR:
        audio_data = librosa.resample(audio_data,
                                      orig_sr=samplerate,
                                      target_sr=AudioConfig.SR)
        samplerate = AudioConfig.SR

    # Step 2 — Ensure mono
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)

    # Step 3 — Mel spectrogram
    mel_spec = librosa.feature.melspectrogram(
        y=audio_data,
        sr=samplerate,
        n_fft=AudioConfig.NFFT,
        hop_length=AudioConfig.HOP_LENGTH,
        win_length=AudioConfig.WIN_LENGTH,
        window=AudioConfig.WIN_FUNCTION,
        n_mels=AudioConfig.MELS,
        fmin=AudioConfig.FREQUENCY_MIN,
        fmax=AudioConfig.FREQUENCY_MAX
    )

    # Step 4 — Amplitude to dB
    mel_db = librosa.power_to_db(mel_spec, ref=np.max)

    # Step 5 — Normalize to [0, 1]
    mel_min, mel_max = mel_db.min(), mel_db.max()
    mel_norm = (mel_db - mel_min) / (mel_max - mel_min + 1e-8)

    # Step 6 — Flip vertically (low freq at bottom)
    mel_norm = np.flipud(mel_norm)

    # Step 7 — Bicubic resize
    mel_resized = cv2.resize(mel_norm, target_size, interpolation=cv2.INTER_CUBIC)

    # Step 8 — Viridis colormap
    mel_colored = plt.get_cmap('viridis')(mel_resized)

    # Step 9 — uint8 BGR
    mel_rgb = (mel_colored[:, :, :3] * 255).astype(np.uint8)
    mel_bgr = cv2.cvtColor(mel_rgb, cv2.COLOR_RGB2BGR)

    return mel_bgr
