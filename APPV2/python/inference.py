"""
YOLO inference module for ePADDY
Performs classification on generated spectrograms
"""

import os
from ultralytics import YOLO


class YOLOClassifier:
    """YOLO model wrapper for audio classification via spectrograms"""
    
    def __init__(self, model_path: str):
        """
        Initialize YOLO model
        
        Args:
            model_path: path to trained YOLO model (.pt file)
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        print(f"Loading YOLO model from: {model_path}")
        self.model = YOLO(model_path)
        self.class_names = self.model.names
        print(f"Model loaded successfully")
        print(f"Classes: {self.class_names}")
        print(f"Total classes: {len(self.class_names)}")
    
    def predict_single(self, image_path: str, verbose: bool = True):
        """
        Run prediction on a single image
        
        Args:
            image_path: path to spectrogram image
            verbose: whether to print results
        
        Returns:
            Dictionary with prediction results
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Run inference
        results = self.model(image_path, verbose=False)
        result = results[0]
        
        # Extract classification results
        top_class_id = result.probs.top1
        top_class_name = self.class_names[top_class_id]
        confidence = result.probs.top1conf.item()
        
        # Get top 3 predictions
        top3_ids = result.probs.top5[:3]
        top3_confs = result.probs.top5conf[:3]
        
        top3_predictions = []
        for class_id, conf in zip(top3_ids, top3_confs):
            top3_predictions.append({
                'class_id': int(class_id),
                'class_name': self.class_names[int(class_id)],
                'confidence': float(conf)
            })
        
        prediction_result = {
            'filename': os.path.basename(image_path),
            'top_class': top_class_name,
            'top_class_id': int(top_class_id),
            'confidence': float(confidence),
            'top3_predictions': top3_predictions
        }
        
        if verbose:
            print(f"  {os.path.basename(image_path)} → {top_class_name} ({confidence:.1%})")
        
        return prediction_result
    
    def predict_batch(self, image_folder: str, file_extension: str = '.png'):
        """
        Run predictions on all images in a folder
        
        Args:
            image_folder: folder containing spectrogram images
            file_extension: image file extension to process
        
        Returns:
            Dictionary with summary statistics and results:
            {
                'total_images': int,
                'class_counts': dict,
                'results': list  # detailed predictions for each image
            }
        """
        # Find all image files
        image_files = [f for f in os.listdir(image_folder)
                      if f.lower().endswith(file_extension)]
        
        if not image_files:
            print(f"⚠️  No {file_extension} files found in {image_folder}")
            return [], {}
        
        print(f"\nProcessing {len(image_files)} images...\n")
        
        all_results = []
        class_counts = {}
        
        # Process each image
        for i, filename in enumerate(image_files, 1):
            file_path = os.path.join(image_folder, filename)
            
            print(f"[{i}/{len(image_files)}] ", end="")
            result = self.predict_single(file_path, verbose=True)
            all_results.append(result)
            
            # Count classifications
            top_class = result['top_class']
            class_counts[top_class] = class_counts.get(top_class, 0) + 1
        
        # Print detailed results
        print("\n" + "=" * 50)
        print("Detailed Results:")
        print("=" * 50)
        for result in all_results:
            print(f"\n{result['filename']}:")
            print(f"  Prediction: {result['top_class']} ({result['confidence']:.1%})")
            print(f"  Top 3:")
            for i, pred in enumerate(result['top3_predictions'], 1):
                print(f"    {i}. {pred['class_name']}: {pred['confidence']:.1%}")
        
        # Print summary
        print("\n" + "=" * 50)
        print("Summary:")
        print("=" * 50)
        total = len(image_files)
        for class_name, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total) * 100
            print(f"  {class_name}: {count}/{total} ({percentage:.1f}%)")
        print("=" * 50 + "\n")
        
        summary = {
            'total_images': total,
            'class_counts': class_counts,
            'results': all_results  # Still include in summary for JSON export
        }
        
        return summary


if __name__ == "__main__":
    print("YOLO inference module loaded successfully")
