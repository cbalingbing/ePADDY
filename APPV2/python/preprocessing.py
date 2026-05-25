"""
Audio preprocessing module for ePADDY
Handles loading, resampling, and processing of audio files
"""

import os
import numpy as np
import librosa
import soundfile as sf
import cv2
from config import AudioConfig
from spectrogram import generate_epaddy_spectrogram
from segmentation import split_audio_segments
import numpy as np
from burst_peaks import detect_burst_peaks

def process_audio_file(
    file_path: str,
    output_dir: str,
    segment_duration: float = AudioConfig.SEGMENT_DURATION,
    samplerate: int = AudioConfig.SR
) -> list:
    """
    Complete ePADDY preprocessing pipeline:
    Load → Resample (if needed) → Segment → Generate Spectrograms → Save
    
    Args:
        file_path: path to audio file
        output_dir: directory to save spectrograms
        segment_duration: duration of each segment in seconds (default: 10s)
    
    Returns:
        List of saved spectrogram file paths
    """
    
    print(f"\n{'=' * 80}")
    print(f"Processing: {os.path.basename(file_path)}")
    print(f"{'=' * 80}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Load audio file
    audio, original_sr = sf.read(file_path)
    
    # Convert stereo to mono if needed
    if len(audio.shape) > 1:
        audio = np.mean(audio, axis=1)
        print(f"   Converted stereo to mono")
    
    # Resample to 44100 Hz if needed
    if original_sr != AudioConfig.SR:
        print(f"   Resampling from {original_sr} Hz to {AudioConfig.SR} Hz")
        audio = librosa.resample(audio, orig_sr=original_sr, target_sr=AudioConfig.SR)

    # Split into segments
    print(f"   Splitting audio into {segment_duration}s segments...")
    segments = split_audio_segments(audio, AudioConfig.SR, segment_duration)

    max_peaks = None
    # Count burst_peaks
    for segment, idx in segments:
        count_peaks = detect_burst_peaks(segment, sr=samplerate, threshold=0.25, peak_distance=50)
        num_peaks = len(count_peaks)
        if max_peaks is None:  # handle first iteration
            max_peaks = num_peaks
        elif num_peaks > max_peaks:  # compare integers
            max_peaks = num_peaks



    # Generate spectrograms
    saved_files = []
    base_filename = os.path.splitext(os.path.basename(file_path))[0]

    for segment, idx in segments:
        print(f"   Processing segment {idx}...", end=" ")
        
        # Generate spectrogram using ePADDY parameters
        spec_image = generate_epaddy_spectrogram(
            audio_data=segment,
            samplerate=AudioConfig.SR,
            target_size=AudioConfig.TARGET_SIZE,
        )
        
        # Save spectrogram
        output_path = os.path.join(output_dir, f"{base_filename}_seg{idx:03d}.png")
        cv2.imwrite(output_path, spec_image)
        saved_files.append(output_path)
        print(f"✓ Saved to {os.path.basename(output_path)}")
    
    print(f"   Total spectrograms generated: {len(saved_files)}")
    
    return saved_files,max_peaks


if __name__ == "__main__":
    # input_path =  r"C:\Users\i.perilla\Desktop\ePaddy\test - Copy\1_17022026_190002-iSound.wav"
    # output_path = r"C:\Users\i.perilla\Desktop\ePaddy\output_folder"
    # preprocessed_audio_files = process_audio_file(
    #     file_path = input_path,
    #     output_dir =  output_path,
    #     segment_duration = 10.0,
    #     samplerate = 44100
    # )
    print("Audio preprocessing module loaded successfully")
