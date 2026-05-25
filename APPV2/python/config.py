"""
Audio processing configuration parameters for ePADDY
Based on Table 2 specifications
"""


class AudioConfig:
    """Audio processing configuration parameters from Table 2"""
    
    # Sample Rate
    SR = 44100  # 44,100 Hz
    
    # FFT Parameters
    NFFT = 4096  # Number of FFT Points
    WIN_LENGTH = 4096  # Window Length in samples
    WIN_FUNCTION = 'hann'  # Window Function (Hann window)
    
    # Time Resolution
    TIME_RESOLUTION = 0.015  # 0.015 seconds
    
    # Calculate hop_length from time resolution
    # hop_length = time_resolution * sample_rate
    HOP_LENGTH = int(TIME_RESOLUTION * SR)  # 661 samples
    
    # Mel Spectrogram Parameters
    MELS = 512  # Number of Mel Bands
    FREQUENCY_MIN = 50.0  # Minimum Frequency in Hz
    FREQUENCY_MAX = 16000.0  # Maximum Frequency in Hz
    
    # YOLO Input Size
    TARGET_SIZE = (640, 640)  # Width × Height for YOLOv8/v11
    
    # Segment Duration
    SEGMENT_DURATION = 10.0  # 10 seconds (as mentioned in paper)


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
