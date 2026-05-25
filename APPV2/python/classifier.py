#!/usr/bin/env python3
"""
Classifier module for ePADDY - Easy to import for SMS or other uses
"""

import os
from preprocessing import process_audio_file
from inference import YOLOClassifier


def classify(input_folder, output_folder, model_path):
    """
    Process all audio files and return classification results as a list of dicts

    Args:
        input_folder: Folder containing audio files
        output_folder: Folder to save spectrograms (will be cleaned after)
        model_path: Path to YOLO model (.pt file)

    Returns:
        List of dicts with classification results per file
    """

    try:
        wav_files = [os.path.join(input_folder, f)
                     for f in os.listdir(input_folder)
                     if f.lower().endswith('.wav')]

        if not wav_files:
            return []

        # Reference: process only the latest file
        # latest_wav = max(wav_files, key=os.path.getctime)

        classifier = YOLOClassifier(model_path)
        prediction_results = []

        for wav_file in wav_files:
            spectrograms, max_peaks = process_audio_file(wav_file, output_folder)
            summary = classifier.predict_batch(output_folder, file_extension='.png')

            # Map class counts to schema fields
            counts = summary.get('class_counts', {})
            total = summary.get('total_images', 1) or 1

            so = counts.get('S_Oryzae', 0)
            tc = counts.get('T_Castaneum', 0)
            rd = counts.get('R_Dominica', 0)

            prediction_results.append({
                "file_name":     os.path.basename(wav_file),
                "num_detect_so": so,
                "num_detect_tc": tc,
                "num_detect_rd": rd,
                "pct_so":        round(so / total * 100, 2),
                "pct_tc":        round(tc / total * 100, 2),
                "pct_rd":        round(rd / total * 100, 2),
            })

            # Clean spectrograms between files
            for filename in os.listdir(output_folder):
                file_path = os.path.join(output_folder, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)

        return prediction_results

    except Exception as e:
        raise


if __name__ == "__main__":
    # input_folder =  r"C:\Users\i.perilla\Desktop\ePaddy\test - Copy"
    # output_folder = r"C:\Users\i.perilla\Desktop\ePaddy\output_folder"
    # model_path = r"C:\Users\i.perilla\Desktop\ePaddy\Models\Epaddy_YOLOv2nano.pt"

    input_folder = '/path/to/wav/files'
    output_folder = '/tmp/epaddy_output'
    model_path = '/path/to/model.pt'

    result = classify(input_folder, output_folder, model_path)
    print(result)
