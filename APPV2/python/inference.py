"""
YOLO inference module for ePADDY
Performs DETECTION (bounding box) on generated spectrograms.

Key difference from the old classify model:
  - Old: result.probs  → single top-1 label per image  (classify)
  - New: result.boxes  → N bounding boxes per image     (detect)

Each spectrogram segment may contain MULTIPLE insects.
predict_batch() reports the dominant class per segment
(the class with the highest box count in that image).
"""

import os
from ultralytics import YOLO


class YOLOClassifier:
    """YOLO detection wrapper for ePADDY spectrogram inference."""

    def __init__(self, model_path: str):
        """
        Load a YOLO detection model (.pt).

        Args:
            model_path: path to trained YOLO detect model
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")

        print(f"Loading YOLO detection model from: {model_path}")
        self.model = YOLO(model_path)
        self.class_names = self.model.names
        print(f"Model loaded successfully")
        print(f"Classes: {self.class_names}")
        print(f"Total classes: {len(self.class_names)}")

    # ------------------------------------------------------------------
    # Single-image prediction
    # ------------------------------------------------------------------
    def predict_single(self, image_path: str, conf: float = 0.5, verbose: bool = True):
        """
        Run BBOX detection on one spectrogram image.

        Args:
            image_path : path to a spectrogram PNG
            verbose    : print per-image summary

        Returns:
            dict:
                filename        – basename of the image
                total_boxes     – total detections in this image
                class_counts    – {class_name: box_count}
                top_class       – class with the most boxes  (None if 0 detections)
                top_class_count – box count of the top class (0 if no detections)
                boxes           – list of raw box dicts (class, confidence, xyxy)
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        results = self.model(image_path,conf=conf, verbose=False)
        result  = results[0]

        class_counts = {}
        boxes_detail = []

        for box in result.boxes:
            class_id   = int(box.cls)
            class_name = self.class_names[class_id]
            confidence = float(box.conf)
            xyxy       = box.xyxy[0].tolist()           # [x1, y1, x2, y2]

            class_counts[class_name] = class_counts.get(class_name, 0) + 1
            boxes_detail.append({
                'class_id'  : class_id,
                'class_name': class_name,
                'confidence': confidence,
                'xyxy'      : xyxy,
            })

        # Dominant class = most boxes in this image
        if class_counts:
            top_class       = max(class_counts, key=class_counts.get)
            top_class_count = class_counts[top_class]
        else:
            top_class       = None
            top_class_count = 0

        prediction_result = {
            'filename'       : os.path.basename(image_path),
            'total_boxes'    : len(boxes_detail),
            'class_counts'   : class_counts,
            'top_class'      : top_class,
            'top_class_count': top_class_count,
            'boxes'          : boxes_detail,
        }

        if verbose:
            if top_class:
                print(
                    f"  {os.path.basename(image_path)} → "
                    f"Top: {top_class} ({top_class_count} box(es)) | "
                    f"Total detections: {len(boxes_detail)}"
                )
            else:
                print(f"  {os.path.basename(image_path)} → No detections")

        return prediction_result

    # ------------------------------------------------------------------
    # Batch prediction
    # ------------------------------------------------------------------
    def predict_batch(self, image_folder: str,conf: float = 0.5, file_extension: str = '.png'):
        """
        Run BBOX detection on all spectrograms in a folder.

        For each image:
            - counts boxes per class
            - records which class had the MOST boxes (dominant class)

        Summary counts how many images each class "won" (was dominant in).

        Args:
            image_folder   : folder of spectrogram PNGs
            file_extension : image suffix to scan for

        Returns:
            dict:
                total_images  – number of spectrograms processed
                class_counts  – {class_name: images_where_dominant}
                total_boxes   – grand total of all bbox detections
                results       – list of per-image dicts from predict_single()
        """
        image_files = sorted([
            f for f in os.listdir(image_folder)
            if f.lower().endswith(file_extension)
        ])

        if not image_files:
            print(f"⚠️  No {file_extension} files found in {image_folder}")
            return {'total_images': 0, 'class_counts': {}, 'total_boxes': 0, 'results': []}

        print(f"\nProcessing {len(image_files)} spectrogram(s) with BBOX detection...\n")

        all_results  = []
        class_counts = {}   # images where each class was dominant
        grand_total_boxes = 0

        for i, filename in enumerate(image_files, 1):
            file_path = os.path.join(image_folder, filename)
            print(f"[{i}/{len(image_files)}] ", end="")

            result = self.predict_single(file_path,conf=conf, verbose=True)
            all_results.append(result)
            grand_total_boxes += result['total_boxes']

            # Tally dominant class across images
            if result['top_class']:
                tc = result['top_class']
                class_counts[tc] = class_counts.get(tc, 0) + 1

        # ── Detailed per-image report ──────────────────────────────────
        print("\n" + "=" * 55)
        print("Detailed Detection Results (per spectrogram segment):")
        print("=" * 55)
        for r in all_results:
            print(f"\n  {r['filename']}:")
            if r['total_boxes'] == 0:
                print("    No insects detected.")
            else:
                print(f"    Total boxes : {r['total_boxes']}")
                print(f"    Dominant    : {r['top_class']} ({r['top_class_count']} box(es))")
                print(f"    All classes : ", end="")
                print(", ".join(
                    f"{cls}: {cnt}" for cls, cnt in
                    sorted(r['class_counts'].items(), key=lambda x: x[1], reverse=True)
                ))

        # ── Batch summary ──────────────────────────────────────────────
        total = len(image_files)
        print("\n" + "=" * 55)
        print("Batch Summary:")
        print("=" * 55)
        print(f"  Segments processed : {total}")
        print(f"  Total bbox detections : {grand_total_boxes}")
        print(f"  Segments with no detections : {sum(1 for r in all_results if r['total_boxes'] == 0)}")
        print("\n  Dominant class per segment:")
        for class_name, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total) * 100
            print(f"    {class_name}: dominant in {count}/{total} segment(s) ({pct:.1f}%)")
        print("=" * 55 + "\n")

        summary = {
            'total_images': total,
            'class_counts': class_counts,       # used by classifier.py for % report
            'total_boxes' : grand_total_boxes,
            'results'     : all_results,
        }

        return summary


if __name__ == "__main__":
    print("ePADDY YOLO detection inference module loaded successfully")
