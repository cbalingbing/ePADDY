import librosa
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

# Function to detect signal bursts (sharp peaks)
def detect_burst_peaks(waveform, sr, threshold=0.25, peak_distance=50):
    """
    Detects signal bursts based on sharp peaks above the threshold.
    :param waveform: The input waveform
    :param sr: Sampling rate of the signal
    :param threshold: Amplitude threshold for peak detection
    :param peak_distance: Minimum distance between consecutive peaks
    :return: Indices of detected bursts (peaks)
    """
    abs_waveform = np.abs(waveform)  # Take absolute of the waveform to consider both positive and negative peaks
    peaks, properties = find_peaks(abs_waveform, height=threshold, distance=peak_distance)
    burst_amplitudes = abs_waveform[peaks]  # Amplitude of the detected peaks

    # Calculate min, average, and max amplitude
    min_amp = np.min(waveform)
    avg_amp = np.mean(abs_waveform)
    max_amp = np.max(waveform)

    # Print statistics
    # print(f"Min Amplitude: {min_amp}")
    # print(f"Average Amplitude: {avg_amp}")
    # print(f"Max Amplitude: {max_amp}")
   #print(f"Number of bursts detected: {len(peaks)}")

    return peaks