"""
Audio segmentation module for ePADDY
Splits audio files into fixed-duration segments
"""

import numpy as np
from config import AudioConfig


def split_audio_segments(
    audio_data: np.ndarray,
    samplerate: int,
    segment_duration: float = AudioConfig.SEGMENT_DURATION
) -> list:
    """
    Split audio into fixed-duration segments (10 seconds for ePADDY)
    
    Args:
        audio_data: numpy array of audio samples
        samplerate: sample rate in Hz
        segment_duration: duration of each segment in seconds (default: 10s)
    
    Returns:
        List of tuples: [(segment_audio, segment_index), ...]
    """
    segment_length = int(segment_duration * samplerate)
    num_segments = int(np.ceil(len(audio_data) / segment_length))
    segments = []
    
    for i in range(num_segments):
        start = i * segment_length
        end = min((i + 1) * segment_length, len(audio_data))
        segment = audio_data[start:end]
        
        # Pad last segment if it's shorter than segment_duration
        if len(segment) < segment_length:
            padding = segment_length - len(segment)
            segment = np.pad(segment, (0, padding), mode='constant')
            print(f"  Segment {i}: Padded {padding} samples to reach {segment_duration}s")
        
        segments.append((segment, i))
    
    return segments


if __name__ == "__main__":
    # Test segmentation
    print("Audio segmentation module loaded successfully")
