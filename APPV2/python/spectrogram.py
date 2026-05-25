"""
Spectrogram generation module for ePADDY
Generates mel-spectrograms following paper specifications
"""

import numpy as np
import librosa
import cv2
import matplotlib.pyplot as plt
from typing import Tuple
from config import AudioConfig


def generate_epaddy_spectrogram(
    audio_data: np.ndarray,
    samplerate: int = AudioConfig.SR,
    target_size: Tuple[int, int] = AudioConfig.TARGET_SIZE,
) -> np.ndarray:
    """
    Generate mel-spectrogram following ePADDY paper specifications (Table 2)
    
    Preprocessing steps:
    1. Amplitude to Decibel Conversion: Logarithmic transformation for wide dynamic range
    2. Normalization: Scale to [0, 1] range for standardized input
    3. Resizing: Bicubic interpolation to 640×640 pixels
    4. Color Mapping: Apply viridis colormap for enhanced visualization
    5. Final Output: 8-bit RGB format (0-255)
    
    Args:
        audio_data: numpy array of audio samples (mono)
        samplerate: sample rate in Hz (must be 44100 for ePADDY)
        target_size: (width, height) for YOLO, default (640, 640)
    
    Returns:
        RGB image array of shape (640, 640, 3) with uint8 values (0-255)
    """
    
    # Verify sample rate matches expected configuration
    if samplerate != AudioConfig.SR:
        print(f"⚠️  Warning: Sample rate is {samplerate} Hz, expected {AudioConfig.SR} Hz")
        print(f"   Audio will be resampled to {AudioConfig.SR} Hz")
        audio_data = librosa.resample(audio_data, orig_sr=samplerate, target_sr=AudioConfig.SR)
        samplerate = AudioConfig.SR
    
    # Convert stereo to mono if needed
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)
    
    # Generate mel spectrogram with Table 2 parameters
    mel_spec = librosa.feature.melspectrogram(
        y=audio_data,
        sr=samplerate,
        n_fft=AudioConfig.NFFT,           # 4096 FFT points
        hop_length=AudioConfig.HOP_LENGTH, # ~661 samples (0.015s * 44100Hz)
        win_length=AudioConfig.WIN_LENGTH, # 4096 samples window
        window=AudioConfig.WIN_FUNCTION,   # Hann window
        n_mels=AudioConfig.MELS,           # 512 mel bands
        fmin=AudioConfig.FREQUENCY_MIN,    # 50 Hz minimum
        fmax=AudioConfig.FREQUENCY_MAX     # 16,000 Hz maximum
    )
    
    # Step 1: Amplitude to Decibel Conversion
    mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
    
    # Step 2: Normalization to [0, 1] range
    mel_min = mel_spec_db.min()
    mel_max = mel_spec_db.max()
    mel_spec_normalized = (mel_spec_db - mel_min) / (mel_max - mel_min)
    
    # Flip vertically (low frequencies at bottom, as in standard spectrograms)
    mel_spec_normalized = np.flipud(mel_spec_normalized)
    
    # Step 3: Resizing to 640×640 pixels using bicubic interpolation
    mel_spec_resized = cv2.resize(
        mel_spec_normalized,
        target_size,
        interpolation=cv2.INTER_CUBIC  # Bicubic interpolation
    )
    
    # Step 4: Color Mapping using viridis colormap
    viridis = plt.get_cmap('viridis')
    mel_spec_colored = viridis(mel_spec_resized)
    
    # Step 5: Final Output - Convert to 8-bit format (0-255)
    # Take only RGB channels (drop alpha channel if present)
    mel_spec_rgb = (mel_spec_colored[:, :, :3] * 255).astype(np.uint8)
    
    # Convert RGB to BGR for OpenCV compatibility
    mel_spec_bgr = cv2.cvtColor(mel_spec_rgb, cv2.COLOR_RGB2BGR)
    
    return mel_spec_bgr


if __name__ == "__main__":
    # Test with sample audio
    print("Spectrogram generation module loaded successfully")
