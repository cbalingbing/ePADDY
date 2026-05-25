#!/usr/bin/env python3
"""
Main prediction script for ePADDY YOLO classification
Processes the latest audio file in the input folder and runs YOLO inference
"""

import os
import sys
import argparse
import json
from datetime import datetime
from preprocessing import process_audio_file
from inference import YOLOClassifier


def get_latest_audio_file(input_folder: str, file_extension: str = '.wav'):
    """
    Find the latest audio file in the folder based on creation time
    
    Args:
        input_folder: folder containing audio files
        file_extension: audio file extension (default: '.wav')
    
    Returns:
        Path to the latest audio file, or None if no files found
    """
    if not os.path.exists(input_folder):
        raise FileNotFoundError(f"Input folder not found: {input_folder}")
    
    # Find all audio files
    audio_files = [
        os.path.join(input_folder, f)
        for f in os.listdir(input_folder)
        if f.lower().endswith(file_extension)
    ]
    
    if not audio_files:
        return None
    
    # Get the latest file based on creation time
    latest_file = max(audio_files, key=os.path.getctime)
    
    return latest_file


def main():
    """Main prediction pipeline"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='ePADDY Audio Classification - Process latest audio file'
    )
    parser.add_argument(
        '--input-folder',
        type=str,
        required=True,
        help='Folder containing audio files'
    )
    parser.add_argument(
        '--output-folder',
        type=str,
        required=True,
        help='Folder to save spectrograms'
    )
    parser.add_argument(
        '--model-path',
        type=str,
        required=True,
        help='Path to trained YOLO model (.pt file)'
    )
    parser.add_argument(
        '--file-extension',
        type=str,
        default='.wav',
        help='Audio file extension (default: .wav)'
    )
    parser.add_argument(
        '--segment-duration',
        type=float,
        default=10.0,
        help='Segment duration in seconds (default: 10.0)'
    )
    parser.add_argument(
        '--save-results',
        type=str,
        default=None,
        help='Path to save prediction results as JSON (optional)'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("ePADDY Audio Classification - Latest File Prediction")
    print("=" * 80)
    print(f"Input folder: {args.input_folder}")
    print(f"Output folder: {args.output_folder}")
    print(f"Model path: {args.model_path}")
    print(f"File extension: {args.file_extension}")
    print(f"Segment duration: {args.segment_duration}s")
    print("=" * 80)
    
    # Step 1: Find the latest audio file
    print("\n[Step 1] Finding latest audio file...")
    latest_file = get_latest_audio_file(args.input_folder, args.file_extension)
    
    if latest_file is None:
        print(f"❌ No {args.file_extension} files found in {args.input_folder}")
        sys.exit(1)
    
    file_creation_time = datetime.fromtimestamp(os.path.getctime(latest_file))
    print(f"✓ Latest file: {os.path.basename(latest_file)}")
    print(f"  Created: {file_creation_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 2: Process audio file (generate spectrograms)
    print("\n[Step 2] Processing audio file...")
    try:
        spectrogram_files = process_audio_file(
            file_path=latest_file,
            output_dir=args.output_folder,
            segment_duration=args.segment_duration
        )
        print(f"✓ Generated {len(spectrogram_files)} spectrogram(s)")
    except Exception as e:
        print(f"❌ Error processing audio: {str(e)}")
        sys.exit(1)
    
    # Step 3: Load YOLO model
    print("\n[Step 3] Loading YOLO model...")
    try:
        classifier = YOLOClassifier(args.model_path)
        print("✓ Model loaded successfully")
    except Exception as e:
        print(f"❌ Error loading model: {str(e)}")
        sys.exit(1)
    
    # Step 4: Run predictions
    print("\n[Step 4] Running predictions...")
    try:
        results, summary = classifier.predict_batch(
            image_folder=args.output_folder,
            file_extension='.png'
        )
        print("✓ Predictions completed")
    except Exception as e:
        print(f"❌ Error during prediction: {str(e)}")
        sys.exit(1)
    
    # Step 5: Save results if requested
    if args.save_results:
        print(f"\n[Step 5] Saving results to {args.save_results}...")
        try:
            output_data = {
                'audio_file': os.path.basename(latest_file),
                'audio_file_path': latest_file,
                'creation_time': file_creation_time.isoformat(),
                'processing_time': datetime.now().isoformat(),
                'model_path': args.model_path,
                'segment_duration': args.segment_duration,
                'summary': {
                    'total_images': summary['total_images'],
                    'class_counts': summary['class_counts']
                },
                'detailed_results': results
            }
            
            os.makedirs(os.path.dirname(args.save_results) if os.path.dirname(args.save_results) else '.', exist_ok=True)
            with open(args.save_results, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            print(f"✓ Results saved to {args.save_results}")
        except Exception as e:
            print(f"⚠️  Warning: Could not save results: {str(e)}")
    
    print("\n" + "=" * 80)
    print("✓ Pipeline completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
