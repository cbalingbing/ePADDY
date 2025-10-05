

import os
import librosa
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

# Function to save plots
def save_plot_as_png(fig, filename):
    directory = r'C:\Users\HP\Desktop\EPaddy Updated\results_peaks'
    if not os.path.exists(directory):
        os.makedirs(directory)
    filepath = os.path.join(directory, filename)
    fig.savefig(filepath, dpi=300, bbox_inches='tight')

# Function to detect signal bursts (sharp peaks)
def detect_burst_peaks(waveform, sr, threshold, peak_distance):  #threshold and peak distance values can be varied/adjusted
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
    print(f"Min Amplitude: {min_amp}")
    print(f"Average Amplitude: {avg_amp}")
    print(f"Max Amplitude: {max_amp}")
    print(f"Number of bursts detected: {len(peaks)}")

    return peaks

# Function to plot the waveform with burst peaks highlighted
def plot_waveform_with_bursts(ax, waveform, burst_peaks, sr, peak_window=5, color='red'):
    time = np.linspace(0, len(waveform) / sr, len(waveform))  # Time axis

    # Plot the waveform in grey first
    ax.plot(time, waveform, color='0.90', label='Waveform')

    # Highlight the bursts by coloring a window around each peak
    for peak in burst_peaks:
        start = max(0, peak - peak_window)  # Ensure we don't go below index 0
        end = min(len(waveform), peak + peak_window)  # Ensure we don't exceed the length of the waveform
        ax.plot(time[start:end], waveform[start:end], color=color)

    ax.set_ylabel('Amplitude', fontsize=12)
    ax.set_xlabel('Time (seconds)', fontsize=12)
    ax.tick_params(axis='x', labelsize=12)
    ax.tick_params(axis='y', labelsize=12)
    ax.set_ylim(-0.2, 0.2)

# Import the wav files
DATASET_PATH = "C:/Users/HP/Desktop/EPaddy Updated/retrieve_audio/"
#LGB1_8k, _ = librosa.load(DATASET_PATH + 'RD20.wav', sr=8000)
LGB2_8k, _ = librosa.load(DATASET_PATH + 'TC20.wav', sr=8000)
#LGB3_8k, _ = librosa.load(DATASET_PATH + 'RD30.wav', sr=8000)

# Waveforms and titles for plotting
waveforms = [LGB2_8K]
titles = ['10 heads R. dominica', '20 heads R. dominica', '30 heads R. dominica']
#colors = ['red', 'blue', 'green']

# Create subplots for three species
fig, ax = plt.subplots(1, 3, figsize=(8, 8), sharey=True)
for i, waveform in enumerate(waveforms):
    ax[i].set_title(f'{titles[i]} Waveform (SR = 8kHz)', fontsize=12)
    
    # Detect burst peaks
    burst_peaks = detect_burst_peaks(waveform, sr=8000, threshold=0.03, peak_distance=30)  #threshold and peak distance values can be varied/adjusted
    
    # Plot waveform with bursts highlighted
    plot_waveform_with_bursts(ax[i], waveform, burst_peaks, sr=8000, peak_window=10, color='red')
    
    # Display the burst count
    ax[i].text(0.5, 0.9, f'Bursts: {len(burst_peaks)}', horizontalalignment='center', verticalalignment='center', 
               transform=ax[i].transAxes, fontsize=10, color='red')

# Save the plot
save_plot_as_png(fig, 'waveform_burst_RD123a.png')

# Show the plot
plt.tight_layout()
plt.show()
