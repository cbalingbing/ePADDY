import os
import numpy as np
import soundfile as sf
import librosa
import matplotlib.pyplot as plt
from sklearn.metrics import (
    confusion_matrix, classification_report,
    precision_recall_curve, average_precision_score,
    precision_recall_fscore_support, roc_curve, auc
)
import tensorflow as tf
from scipy.signal import butter, filtfilt

# ==============================
# Preprocessing Functions
# ==============================

def split_audio(data, samplerate, segment_duration=10):
    segment_length = segment_duration * samplerate
    num_segments = int(np.ceil(len(data) / segment_length))
    segments = []
    for i in range(num_segments):
        start = int(i * segment_length)
        end = int(min((i + 1) * segment_length, len(data)))
        segment = data[start:end]
        segments.append((segment, i))
    return segments

def butter_bandpass(lowcut, highcut, fs, order=4):
    nyquist_freq = 0.5 * fs
    low = min(lowcut, highcut) / nyquist_freq
    high = max(lowcut, highcut) / nyquist_freq
    b, a = butter(order, [low, high], btype='band')
    return b, a

def apply_butterworth_filter(data, lowcut, highcut, fs, order=4):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    return filtfilt(b, a, data)

def normalize_waveform(data):
    return data / np.max(np.abs(data))

def preprocess_audio(file_path, output_folder,
                     trim_start=3*60, trim_end=-60,
                     lowcut=93.75, highcut=2500,
                     filter_order=4, segment_duration=10):

    os.makedirs(output_folder, exist_ok=True)
    data, samplerate = sf.read(file_path)

    # Trim start (3 min) and end (1 min)
    if os.path.basename(file_path) != "mic_recording.wav":
        start_sample = int(trim_start * samplerate)
        end_sample = len(data) + int(trim_end * samplerate) if trim_end < 0 else int(trim_end * samplerate)
        if start_sample >= end_sample:
            print(f"[WARNING] Trimming produced empty audio for {file_path}")
            return None, []
        data = data[start_sample:end_sample]

    normalized_data = normalize_waveform(data)
    filtered_data = apply_butterworth_filter(normalized_data, lowcut, highcut, samplerate, filter_order)

    processed_filepath = os.path.join(output_folder, "processed_" + os.path.basename(file_path))
    sf.write(processed_filepath, filtered_data, samplerate)

    segments = split_audio(filtered_data, samplerate, segment_duration)
    segment_files = []
    for segment, idx in segments:
        segment_filename = os.path.join(output_folder, f"processed_segment{idx+1}_" + os.path.basename(file_path))
        sf.write(segment_filename, segment, samplerate)
        segment_files.append(segment_filename)

    return processed_filepath, segment_files

# ==============================
# Evaluation Script for TFLite
# ==============================

CLASSES = ['NoInsects', 'RD', 'SO', 'TC']
tflite_model_path = r"C:\Users\HP\Desktop\EPaddy Updated\modelv2.tflite"  # <-- your TFLite model
test_dir = r"C:\Users\HP\Desktop\EPaddy Updated\test"
output_dir = "processed_test"
results_dir = "evaluation_results"
os.makedirs(output_dir, exist_ok=True)
os.makedirs(results_dir, exist_ok=True)

# Load TFLite model
interpreter = tf.lite.Interpreter(model_path=tflite_model_path)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

y_true, y_pred, y_score = [], [], []

test_files = []
for root, _, files in os.walk(test_dir):
    for f in files:
        if f.endswith(".wav"):
            test_files.append(os.path.join(root, f))

for file in test_files:
    true_class = os.path.basename(os.path.dirname(file))
    if true_class not in CLASSES:
        continue

    processed, segments = preprocess_audio(file, output_dir)
    if not segments:
        continue

    for seg in segments:
        y, sr = librosa.load(seg, sr=None)
        mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)
        mel_db = librosa.power_to_db(mel, ref=np.max)

        if mel_db.shape[1] < 128:
            pad_width = 128 - mel_db.shape[1]
            mel_db = np.pad(mel_db, ((0,0),(0,pad_width)), mode='constant')
        else:
            mel_db = mel_db[:, :128]

        mel_db = mel_db[np.newaxis, ..., np.newaxis].astype(np.float32)

        # TFLite Inference
        interpreter.set_tensor(input_details[0]['index'], mel_db)
        interpreter.invoke()
        preds = interpreter.get_tensor(output_details[0]['index'])[0]

        pred_class = np.argmax(preds)
        y_true.append(CLASSES.index(true_class))
        y_pred.append(pred_class)
        y_score.append(preds)

y_score = np.array(y_score)

# ==============================
# Metrics
# ==============================
cm = confusion_matrix(y_true, y_pred, labels=range(len(CLASSES)))
report = classification_report(y_true, y_pred, labels=range(len(CLASSES)), target_names=CLASSES, zero_division=0)
prec, rec, f1, _ = precision_recall_fscore_support(y_true, y_pred, labels=range(len(CLASSES)))

# ==============================
# Save All Graphs Function
# ==============================
def save_all_graphs(cm, prec, rec, f1, y_true, y_score, results_dir="evaluation_results"):
    # Confusion Matrix
    plt.figure(figsize=(6,6))
    plt.imshow(cm, cmap="Blues")
    plt.title("Confusion Matrix")
    plt.xticks(range(len(CLASSES)), CLASSES, rotation=45)
    plt.yticks(range(len(CLASSES)), CLASSES)
    plt.colorbar()
    for i in range(len(CLASSES)):
        for j in range(len(CLASSES)):
            plt.text(j, i, cm[i,j], ha="center", va="center", color="red")
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, "confusion_matrix.png"))
    plt.close()

    # Precision-Recall Curves
    aps = []
    plt.figure()
    for i in range(len(CLASSES)):
        y_true_bin = np.array([1 if t==i else 0 for t in y_true])
        if y_true_bin.sum() == 0:
            continue
        precision, recall, _ = precision_recall_curve(y_true_bin, y_score[:, i])
        ap = average_precision_score(y_true_bin, y_score[:, i])
        aps.append(ap)
        plt.plot(recall, precision, label=f"{CLASSES[i]} (AP={ap:.2f})")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Precision-Recall Curve")
    plt.legend()
    plt.savefig(os.path.join(results_dir, "precision_recall_curve.png"))
    plt.close()

    # ROC Curves
    plt.figure()
    for i in range(len(CLASSES)):
        y_true_bin = np.array([1 if t==i else 0 for t in y_true])
        if y_true_bin.sum() == 0:
            continue
        fpr, tpr, _ = roc_curve(y_true_bin, y_score[:, i])
        roc_auc = auc(fpr, tpr)
        plt.plot(fpr, tpr, label=f"{CLASSES[i]} (AUC={roc_auc:.2f})")
    plt.plot([0,1], [0,1], "k--")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curves")
    plt.legend()
    plt.savefig(os.path.join(results_dir, "roc_curves.png"))
    plt.close()

    # Bar chart: Precision, Recall, F1
    x = np.arange(len(CLASSES))
    width = 0.25
    plt.figure(figsize=(8,5))
    plt.bar(x - width, prec, width, label="Precision")
    plt.bar(x, rec, width, label="Recall")
    plt.bar(x + width, f1, width, label="F1-score")
    plt.xticks(x, CLASSES)
    plt.ylabel("Score")
    plt.title("Per-class Metrics")
    plt.legend()
    plt.savefig(os.path.join(results_dir, "per_class_metrics.png"))
    plt.close()

    return np.mean(aps) if aps else 0.0

# ==============================
# Run and Save Outputs
# ==============================
print("\nClassification Report:\n", report)
mAP = save_all_graphs(cm, prec, rec, f1, y_true, y_score, results_dir=results_dir)
print(f"\nMean Average Precision (mAP): {mAP:.3f}")
print(f"\n✅ All graphs and metrics saved in '{results_dir}' folder.")
