import os
import numpy as np
import soundfile as sf
import librosa
from scipy.signal import butter, filtfilt
import tensorflow as tf
import tempfile
from pathlib import Path
import AppV4

# ========================
# Load your TFLite model
# ========================
interpreter = tf.lite.Interpreter(model_path=r"C:\Users\HP\Desktop\EPaddy Updated\modelv3.tflite")
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Define your class labels
#subdirectories = ['RD', 'TC', 'SO', 'NoInsects']
subdirectories = ['SO', 'TC', 'RD', 'NoInsect']


# ========================
# Utility Functions
# ========================
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


def butter_bandpass(lowcut, highcut, fs, filter_order=4):
    nyquist_freq = 0.5 * fs
    low = min(lowcut, highcut) / nyquist_freq
    high = max(lowcut, highcut) / nyquist_freq
    b, a = butter(filter_order, [low, high], btype='band')
    return b, a


def apply_butterworth_filter(data, lowcut, highcut, fs, order):
    b, a = butter_bandpass(lowcut, highcut, fs, order)
    return filtfilt(b, a, data)


def normalize_waveform(data):
    return data / np.max(np.abs(data))


def preprocess_audio(file_path, output_folder,
                     trim_start=3 * 60, trim_end=-60,
                     lowcut=93.75, highcut=2500,
                     filter_order=4, segment_duration=10):
    os.makedirs(output_folder, exist_ok=True)

    # Load audio
    data, samplerate = sf.read(file_path)

    # Trim (start 3 min, remove last 1 min)
    if os.path.basename(file_path) != "mic_recording.wav":
        start_sample = int(trim_start * samplerate)
        end_sample = len(data) + int(trim_end * samplerate) if trim_end < 0 else int(trim_end * samplerate)

        if start_sample >= end_sample:
            print(f"[WARNING] Trimming produced empty audio for {file_path}")
            return None, []

        data = data[start_sample:end_sample]

    # Normalize + Filter
    normalized_data = normalize_waveform(data)
    filtered_data = apply_butterworth_filter(normalized_data, lowcut, highcut, samplerate, filter_order)

    # Save full processed file
    processed_filepath = os.path.join(output_folder, "processed_" + os.path.basename(file_path))
    sf.write(processed_filepath, filtered_data, samplerate)

    # Split into segments
    segments = split_audio(filtered_data, samplerate, segment_duration)
    segment_files = []
    for segment, idx in segments:
        segment_filename = os.path.join(output_folder, f"processed_segment{idx + 1}_" + os.path.basename(file_path))
        sf.write(segment_filename, segment, samplerate)
        segment_files.append(segment_filename)

    return processed_filepath, segment_files


def melspectrogram(file_path, n_mels=128, n_fft=2048, hop_length=512):
    y, sr = librosa.load(file_path, sr=None)
    mel_spec = librosa.feature.melspectrogram(y=y, sr=sr, n_fft=n_fft,
                                              hop_length=hop_length, n_mels=n_mels)
    mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)

    # Ensure fixed width (128 frames)
    if mel_spec_db.shape[1] < 128:
        pad_width = 128 - mel_spec_db.shape[1]
        mel_spec_db = np.pad(mel_spec_db, ((0, 0), (0, pad_width)), mode='constant')
    else:
        mel_spec_db = mel_spec_db[:, :128]

    return mel_spec_db


# ========================
# Prediction Function
# ========================
def predict_species(file_path):

        file_path = Path(file_path).resolve()

        processed_file, slice_filepaths = preprocess_audio(file_path, AppV4.app.config['UPLOAD_FOLDER'])
        predictions = []
        for i, slice_filepath in enumerate(slice_filepaths):


            audio_features = melspectrogram(slice_filepath)

                # Reshape for model (batch, height, width, channel)
            audio_features = np.expand_dims(audio_features, axis=-1).astype(np.float32)
            audio_features = np.expand_dims(audio_features, axis=0)

                # Run inference with TFLite
            interpreter.set_tensor(input_details[0]['index'], audio_features)
            interpreter.invoke()
            prediction = interpreter.get_tensor(output_details[0]['index'])[0]

                # Convert to percentages
            prediction_percent = prediction * 100.0

                # Unpack in correct order
            rd, tc, so, no_insects = prediction_percent

                # Decision logic (per segment)
            if no_insects > max(rd, tc, so):
                    predicted_species = "NoInsects"
            elif rd > max(tc, so, no_insects):
                    predicted_species = "RD"
            elif tc > max(rd, so, no_insects):
                    predicted_species = "TC"
            else:
                    predicted_species = "SO"


            predictions.append({
                    'RD': round(float(rd)),
                    'SO': round(float(so)),
                    'TC': round(float(tc)),
                    'NoInsects': round(float(no_insects)),
                    'predicted_species': predicted_species,
                    'slice_filepath': slice_filepath,
                    'slice_number': i + 1
                })
        return predictions


