"""
Audio processing configuration parameters for ePADDY
Based on Table 2 specifications
"""

class AudioConfig:
    """ePADDY audio processing parameters."""

    # ── Sample Rate ──────────────────────────────────────────
    SR               = 8000          # Sample rate (Hz)

    # ── FFT Parameters ───────────────────────────────────────
    NFFT             = 1024          # FFT points
    WIN_LENGTH       = 1024          # Window length (samples)
    WIN_FUNCTION     = 'hann'        # Window function
    HOP_LENGTH       = 256           # Hop length (samples)

    # ── Mel Spectrogram ──────────────────────────────────────
    MELS             = 64            # Number of Mel bands
    FREQUENCY_MIN    = 50.0          # Min frequency (Hz)
    FREQUENCY_MAX    = 4000.0        # Max frequency (Hz)

    # ── Output ───────────────────────────────────────────────
    TARGET_SIZE      = (640, 640)    # YOLO input size (W x H)

    # ── Segmentation ─────────────────────────────────────────
    SEGMENT_DURATION = 10.0          # Segment window (seconds)
    TRIM_START       = 180.0         # Skip first N seconds (3 min)
    TRIM_END         = 60.0          # Skip last N seconds  (1 min)

    # ── Peak Detection ───────────────────────────────────────
    THRESHOLD_FACTOR = 0.25          # RMS multiplier — lower = more sensitive
    PEAK_DISTANCE    = 50            # Minimum samples between peaks
    BANDPASS_LOW     = 200.0         # Bandpass lower bound (Hz)
    BANDPASS_HIGH    = 3800.0        # Bandpass upper bound (Hz)

def print_config():
    """Print current audio configuration"""
    print("Audio Processing Configuration (Table 2):")
    print("=" * 60)
    print(f"Sample Rate (SR): {AudioConfig.SR:,} Hz")
    print(f"Number of FFT Points (NFFT): {AudioConfig.NFFT}")
    print(f"Window Length (WIN_LENGTH): {AudioConfig.WIN_LENGTH} samples")
    print(f"Window Function (WIN_FUNCTION): {AudioConfig.WIN_FUNCTION}")
    print(f"Time Resolution (TIME_RESOLUTION): {AudioConfig.TIME_RESOLUTION} s")
    print(f"Hop Length (calculated): {AudioConfig.HOP_LENGTH} samples")
    print(f"Number of Mel Bands (MELS): {AudioConfig.MELS}")
    print(f"Minimum Frequency (FREQUENCY_MIN): {AudioConfig.FREQUENCY_MIN} Hz")
    print(f"Maximum Frequency (FREQUENCY_MAX): {AudioConfig.FREQUENCY_MAX:,} Hz")
    print(f"Target Image Size: {AudioConfig.TARGET_SIZE[0]} × {AudioConfig.TARGET_SIZE[1]} pixels")
    print(f"Segment Duration: {AudioConfig.SEGMENT_DURATION} seconds")


if __name__ == "__main__":
    print_config()
