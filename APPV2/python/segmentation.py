"""
segmentation.py — ePADDY Audio Segmentation
============================================
Splits a full audio waveform into fixed-length windows
centred on detected burst peaks.

Usage:
    from segmentation import split_audio_segments
"""

import numpy as np

from config import AudioConfig
from peak_detection import detect_burst_peaks


def split_audio_segments(audio_data: np.ndarray,
                         samplerate: int,
                         segment_duration: float = AudioConfig.SEGMENT_DURATION,
                         threshold_factor: float = AudioConfig.THRESHOLD_FACTOR,
                         peak_distance: int      = AudioConfig.PEAK_DISTANCE,
                         trim_start: float       = AudioConfig.TRIM_START,
                         trim_end: float         = AudioConfig.TRIM_END) -> list:
    """
    Split audio into fixed-length windows centred on detected burst peaks.
    Overlapping peaks are deduplicated — each peak only creates one segment.

    Args:
        audio_data       : full audio waveform (mono)
        samplerate       : sample rate (Hz)
        segment_duration : window size in seconds  (default: 10 s)
        threshold_factor : peak detection sensitivity
        peak_distance    : minimum samples between peaks
        trim_start       : seconds to skip at recording start (default: 180 s)
        trim_end         : seconds to skip at recording end   (default: 60 s)

    Returns:
        List of (segment_array, index, peak_time_seconds) tuples
        Returns empty list if no peaks found or audio too short
    """
    half_window    = int((segment_duration / 2) * samplerate)
    segment_length = int(segment_duration * samplerate)

    # Trim edges
    start_sample = int(trim_start * samplerate)
    end_sample   = len(audio_data) - int(trim_end * samplerate)

    if start_sample >= end_sample:
        print(' Audio too short after trimming — no segments created.')
        return [], {}   # always return (segments, amp_stats) so callers can unpack

    trimmed = audio_data[start_sample:end_sample]
    print(f'  Trimmed: skipping first {trim_start}s and last {trim_end}s')
    print(f'  Processing {len(trimmed) / samplerate:.1f}s of audio')

    # Detect peaks on trimmed audio
    peaks, amp_stats = detect_burst_peaks(trimmed, samplerate,
                                          threshold_factor=threshold_factor,
                                          peak_distance=peak_distance)

    if len(peaks) == 0:
        print(' No burst peaks detected — no segments created.')
        return [], amp_stats

    print(f'  Detected {len(peaks)} peaks — building segments...')

    segments    = []
    used_ranges = []

    for peak_idx in peaks:
        start = max(0, peak_idx - half_window)
        end   = min(len(trimmed), start + segment_length)
        start = max(0, end - segment_length)

        # Skip peaks already covered by a previous segment window
        if any(s <= peak_idx <= e for s, e in used_ranges):
            continue

        segment = trimmed[start:end]

        # Pad short segments (end of file)
        if len(segment) < segment_length:
            padding = segment_length - len(segment)
            segment = np.pad(segment, (0, padding), mode='constant')

        # Peak time relative to the ORIGINAL (untrimmed) audio
        peak_time = (peak_idx + start_sample) / samplerate
        print(f'  Segment {len(segments):03d}: peak @ {peak_time:.2f}s  '
              f'[{(start + start_sample) / samplerate:.2f}s – '
              f'{(end + start_sample) / samplerate:.2f}s]')

        segments.append((segment, len(segments), peak_time))
        used_ranges.append((start, end))

    print(f'  Total segments: {len(segments)}')
    return segments, amp_stats
