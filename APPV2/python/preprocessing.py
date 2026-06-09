"""
preprocessing.py — ePADDY Main Preprocessing Entry Point
=========================================================
This is the file imported by classifier.py.

Exposes:
    process_audio_file(file_path, output_dir)
        → (spectrograms, max_peaks)

Mirrors the behaviour of classifier.py:
    - Receives the LATEST .wav file path from classifier.py
    - Processes only that one file
    - Returns spectrograms + peak count for the classifier

All heavy logic lives in the individual modules:
    config.py          — AudioConfig parameters
    filters.py         — bandpass_filter, normalize_waveform
    peak_detection.py  — detect_burst_peaks
    segmentation.py    — split_audio_segments
    spectrogram.py     — generate_epaddy_spectrogram

Usage (from classifier.py):
    from preprocessing import process_audio_file
    spectrograms, max_peaks = process_audio_file(latest_wav, output_dir)
"""

import os
from typing import List, Tuple

import numpy as np
import soundfile as sf
import librosa
import cv2
import matplotlib.pyplot as plt

from config      import AudioConfig
from segmentation import split_audio_segments
from spectrogram  import generate_epaddy_spectrogram


def process_audio_file(file_path: str,
                       output_dir: str,
                       segment_duration: float = AudioConfig.SEGMENT_DURATION,
                       visualize: bool          = False
                       ) -> Tuple[List[np.ndarray], int]:
    """
    Full ePADDY preprocessing pipeline for a SINGLE audio file.
    Called by classifier.py with the latest .wav recording.

    Pipeline:
        Load WAV → Mono → Resample (8 kHz) → Trim edges
        → Detect burst peaks → Segment → Mel spectrogram → Save PNG

    Args:
        file_path        : path to the latest .wav file
                           (classifier.py finds this via os.path.getctime)
        output_dir       : folder to save spectrogram PNGs
                           (cleaned up by classifier.py after inference)
        segment_duration : segment window in seconds  (default: 10 s)
        visualize        : display first 3 spectrograms  (default: False)

    Returns:
        (spectrograms, max_peaks)
            spectrograms : list of BGR image arrays  (one per segment)
            max_peaks    : number of peaks / segments generated
    """
    print(f"\n{'='*70}")
    print(f"  Processing: {os.path.basename(file_path)}")
    print(f"{'='*70}")

    os.makedirs(output_dir, exist_ok=True)

    # ── Load audio ───────────────────────────────────────────
    audio, original_sr = sf.read(file_path)

    # Stereo → mono
    if len(audio.shape) > 1:
        audio = np.mean(audio, axis=1)
        print('  Converted stereo → mono')

    # Resample if needed
    if original_sr != AudioConfig.SR:
        print(f'  Resampling {original_sr} Hz → {AudioConfig.SR} Hz...')
        audio = librosa.resample(audio,
                                 orig_sr=original_sr,
                                 target_sr=AudioConfig.SR)

    print(f'  Duration : {len(audio) / AudioConfig.SR:.1f}s  |  SR: {AudioConfig.SR} Hz')

    # ── Segment around burst peaks ───────────────────────────
    segments, amp_stats = split_audio_segments(audio, AudioConfig.SR, segment_duration)
    avg_amplitude = amp_stats.get('avg_amplitude', 0.0)

    if not segments:
        print('  No segments generated — file skipped.')
        return [], 0, avg_amplitude

    max_peaks     = len(segments)
    spectrograms  = []
    base_filename = os.path.splitext(os.path.basename(file_path))[0]

    # ── Generate and save spectrograms ───────────────────────
    for segment, idx, peak_time in segments:
        print(f'  Spectrogram {idx:03d}  (peak @ {peak_time:.2f}s)...', end=' ')

        spec     = generate_epaddy_spectrogram(segment,
                                               AudioConfig.SR,
                                               AudioConfig.TARGET_SIZE)
        out_path = os.path.join(output_dir, f'{base_filename}_seg{idx:03d}.png')
        cv2.imwrite(out_path, spec)
        spectrograms.append(spec)
        print(f'✓  {os.path.basename(out_path)}')

    # ── Optional inline visualization ────────────────────────
    if visualize and spectrograms:
        n     = min(3, len(spectrograms))
        fig, axes = plt.subplots(1, n, figsize=(6 * n, 5))
        if n == 1:
            axes = [axes]
        for i, (seg, idx, pt) in enumerate(segments[:n]):
            rgb = cv2.cvtColor(spectrograms[i], cv2.COLOR_BGR2RGB)
            axes[i].imshow(rgb)
            axes[i].set_title(f'Seg {idx:03d}  |  Peak @ {pt:.2f}s\n640×640 px')
            axes[i].axis('off')
        plt.suptitle(os.path.basename(file_path), fontsize=11)
        plt.tight_layout()
        plt.show()

    print(f'\n  {len(spectrograms)} spectrograms saved → {output_dir}')
    print(f'  Avg amplitude : {avg_amplitude:.6f}')
    return spectrograms, max_peaks, avg_amplitude
