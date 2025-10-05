import soundfile as sf
import numpy as np
from scipy.signal import find_peaks


def detect_burst_peaks(file_path, threshold, peak_distance):
    # Load audio (supports WAV, FLAC, OGG, etc.)
    waveform, sr = sf.read(file_path)

    # If stereo, convert to mono
    if len(waveform.shape) > 1:
        waveform = np.mean(waveform, axis=1)

    abs_waveform = np.abs(waveform)
    peaks, properties = find_peaks(abs_waveform, height=threshold, distance=peak_distance)

    print(f"Sampling Rate: {sr}")
    print(f"Number of bursts detected: {len(peaks)}")

    return peaks

detect = detect_burst_peaks(file_path=r"C:\Users\HP\Desktop\EPaddy Updated\retrieve_audio\TC20.wav", threshold=0.03, peak_distance=30)