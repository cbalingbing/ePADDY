#!/usr/bin/env python3
"""
Example usage script for ePADDY audio classification
Demonstrates how to use the modular components
"""

import os
from preprocessing import process_audio_file
from inference import YOLOClassifier


def example_process_latest_file():
    """
    Example: Process the latest audio file in a folder
    Similar to the original notebook's latest_wav approach
    """
    
    # Configuration
    input_folder = '/path/to/audio/files'  # CHANGE THIS
    output_folder = '/path/to/spectrograms'  # CHANGE THIS
    model_path = '/path/to/model.pt'  # CHANGE THIS
    
    # Find latest .wav file
    wav_files = [
        os.path.join(input_folder, f) 
        for f in os.listdir(input_folder) 
        if f.lower().endswith('.wav')
    ]
    
    if not wav_files:
        print("No .wav files found!")
        return
    
    # Get the latest file based on creation time (like the notebook)
    latest_wav = max(wav_files, key=os.path.getctime)
    
    print(f"Latest audio file: {os.path.basename(latest_wav)}")
    print(f"Created: {os.path.getctime(latest_wav)}")
    
    # Step 1: Process audio and generate spectrograms
    print("\n--- Processing Audio ---")
    spectrogram_files = process_audio_file(
        file_path=latest_wav,
        output_dir=output_folder,
        segment_duration=10.0
    )
    
    # Step 2: Run YOLO predictions
    print("\n--- Running YOLO Predictions ---")
    classifier = YOLOClassifier(model_path)
    results, summary = classifier.predict_batch(output_folder, file_extension='.png')
    
    # Step 3: Display results
    print("\n--- Final Results ---")
    print(f"Audio file: {os.path.basename(latest_wav)}")
    print(f"Total spectrograms: {summary['total_images']}")
    print(f"Class distribution:")
    for class_name, count in summary['class_counts'].items():
        percentage = (count / summary['total_images']) * 100
        print(f"  {class_name}: {count} ({percentage:.1f}%)")


def example_custom_processing():
    """
    Example: Custom processing with individual modules
    """
    import numpy as np
    import soundfile as sf
    from segmentation import split_audio_segments
    from spectrogram import generate_epaddy_spectrogram
    import cv2
    
    # Load your audio file
    audio_path = '/path/to/your/audio.wav'
    audio_data, samplerate = sf.read(audio_path)
    
    # Convert stereo to mono if needed
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)
    
    # Split into segments
    segments = split_audio_segments(audio_data, samplerate, segment_duration=10.0)
    
    # Generate spectrograms for each segment
    for segment_audio, idx in segments:
        spec_image = generate_epaddy_spectrogram(segment_audio, samplerate)
        
        # Save spectrogram
        output_path = f'spectrogram_seg{idx:03d}.png'
        cv2.imwrite(output_path, spec_image)
        print(f"Saved: {output_path}")


def example_batch_prediction():
    """
    Example: Run predictions on existing spectrograms
    """
    spectrogram_folder = '/path/to/spectrograms'
    model_path = '/path/to/model.pt'
    
    # Initialize classifier
    classifier = YOLOClassifier(model_path)
    
    # Get model info
    print(f"Model classes: {classifier.class_names}")
    print(f"Total classes: {len(classifier.class_names)}")
    
    # Run batch prediction
    results, summary = classifier.predict_batch(
        image_folder=spectrogram_folder,
        file_extension='.png'
    )
    
    # Access individual results
    for result in results:
        print(f"\nFile: {result['filename']}")
        print(f"Prediction: {result['top_class']} ({result['confidence']:.2%})")
        print("Top 3 predictions:")
        for pred in result['top3_predictions']:
            print(f"  {pred['class_name']}: {pred['confidence']:.2%}")


if __name__ == "__main__":
    print("ePADDY Example Usage")
    print("=" * 60)
    print("\nUncomment the example you want to run:\n")
    
    # Uncomment one of these to run an example:
    
    # Example 1: Process latest file (recommended)
    # example_process_latest_file()
    
    # Example 2: Custom processing with individual modules
    # example_custom_processing()
    
    # Example 3: Batch prediction on existing spectrograms
    # example_batch_prediction()
    
    print("\nPlease edit the paths in the script and uncomment an example to run.")
