from flask import Flask, render_template, request, redirect, url_for, make_response
import os
from datetime import datetime
import numpy as np
import librosa
import matplotlib
import csv
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import librosa.display
import json
import sounddevice as sd
import wave
import soundfile as sf
from scipy.signal import butter, lfilter
from pydub import AudioSegment, effects
import glob
import serial
import time

# --- TFLite imports and model loading ---
import tensorflow as tf

TFLITE_MODEL_PATH = r"C:\Users\HP\Desktop\EPaddy Updated\my_model.tflite"

interpreter = tf.lite.Interpreter(model_path=TFLITE_MODEL_PATH)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

#for sending message using GSM module
serial_port = '/dev/ttyAMA0'
baud_rate = 9600 #change this to the proper baud_rate
phone_number = "+6"    # <-- replace with the actual recipient number


# === OPEN SERIAL ===
ser = serial.Serial(serial_port, baud_rate, timeout=2)
time.sleep(2)


def tflite_predict(features):
    features = features.astype(np.float32)
    interpreter.set_tensor(input_details[0]['index'], features)
    interpreter.invoke()
    output_data = interpreter.get_tensor(output_details[0]['index'])
    return output_data

def softmax(x):
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum(axis=-1, keepdims=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['GRAPH_FOLDER'] = 'static/graphs/'

SAMPLE_RATE = 44100  # Standard audio sample rate
DURATION = 10  # Record for 10 seconds
DEVICE = 1  # Use default mic
CHANNELS = 1  # Mono audio

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['GRAPH_FOLDER'], exist_ok=True)

lowpass_cutoff_freq = 2500  # Low-pass cutoff frequency in Hz; Highcut
highpass_cutoff_freq = 93.75  # High-pass cutoff frequency in Hz; Lowcut
filter_order = 4  # Filter order

def send_command(command, delay=1):
    """Helper to send command and print the response"""
    print(f">>> {command}")
    ser.write((command + '\r').encode())
    time.sleep(delay)
    response = ser.read_all().decode(errors='ignore')
    print(response)
    return response

def record_and_save(filename="mic_recording.wav", duration=DURATION, sample_rate=SAMPLE_RATE, channels=CHANNELS, device=None):
    """Records audio from the microphone and saves it as a WAV file."""
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    print(f"Recording for {duration} seconds...")
    audio_data = sd.rec(int(sample_rate * duration), samplerate=sample_rate, channels=channels, dtype='int16', device=device)
    sd.wait()
    print("Recording complete.")

    with wave.open(filepath, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit audio
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data.tobytes())

    print(f"Audio saved as {filepath}")
    return filepath  # Return file path for processing

def butter_bandpass(lowcut, highcut, fs, order=4):
    nyquist_freq = 0.5 * fs
    low = min(lowcut, highcut) / nyquist_freq
    high = max(lowcut, highcut) / nyquist_freq
    b, a = butter(order, [low, high], btype='band', analog=False)
    return b, a

def apply_butterworth_filter(data, lowcut, highcut, order, fs):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = lfilter(b, a, data)
    return y

def normalize_waveform(waveform):
    max_val = np.max(np.abs(waveform))
    if max_val > 0:
        return waveform / max_val
    else:
        return waveform

def preprocess_audio(file_path, output_folder):
    start_time = 3 * 60 * 1000  # 3 minutes
    end_time = -1 * 60 * 1000  # -1 minute (from the end)
    audio = AudioSegment.from_file(file_path, format="wav")
    trimmed_audio = audio[start_time:end_time]
    normalized_audio = effects.normalize(trimmed_audio)
    temp_filepath = os.path.join(output_folder, "temp_" + os.path.basename(file_path))
    normalized_audio.export(temp_filepath, format="wav")
    sound_data, samplerate = sf.read(temp_filepath)
    normalized_sound_data = normalize_waveform(sound_data)
    filtered_sound = apply_butterworth_filter(normalized_sound_data, lowpass_cutoff_freq, highpass_cutoff_freq, filter_order, samplerate)
    processed_filepath = os.path.join(output_folder, "processed_" + os.path.basename(file_path))
    sf.write(processed_filepath, filtered_sound, samplerate)
    os.remove(temp_filepath)
    processed_audio = AudioSegment.from_file(processed_filepath, format="wav")
    slice_duration = 10 * 1000  # 10 seconds in milliseconds
    slice_filepaths = []
    for i in range(10):
        start_slice = i * slice_duration
        end_slice = start_slice + slice_duration
        slice_audio = processed_audio[start_slice:end_slice]
        slice_output_path = os.path.join(output_folder, f"slice_{i+1}_" + os.path.basename(file_path))
        slice_audio.export(slice_output_path, format="wav")
        slice_filepaths.append(slice_output_path)
    return slice_filepaths

def extract_features(file_path):
    sound_data, samplerate = sf.read(file_path)
    target_samplerate = 8000  # Lower sample rate to reduce memory usage
    if samplerate != target_samplerate:
        sound_data = librosa.resample(sound_data, orig_sr=samplerate, target_sr=target_samplerate)
        samplerate = target_samplerate
    normalized_sound_data = normalize_waveform(sound_data)
    filtered_sound_bandpass = apply_butterworth_filter(normalized_sound_data, lowpass_cutoff_freq, highpass_cutoff_freq, filter_order, samplerate)
    spectrogram = librosa.feature.melspectrogram(y=filtered_sound_bandpass, sr=samplerate, n_fft=512, hop_length=256, n_mels=128)
    spectrogram = librosa.power_to_db(spectrogram, ref=np.max)
    spectrogram = librosa.util.fix_length(spectrogram, size=128, axis=1)
    spectrogram = np.expand_dims(spectrogram, axis=-1)
    spectrogram = np.expand_dims(spectrogram, axis=0)
    return spectrogram

def predict_species(file_path):
    audio = AudioSegment.from_file(file_path, format="wav")
    duration_minutes = len(audio) / (60 * 1000)
    if duration_minutes >= 10:
        slice_filepaths = preprocess_audio(file_path, app.config['UPLOAD_FOLDER'])
    else:
        slice_filepaths = [file_path]
    predictions = []
    for i, slice_filepath in enumerate(slice_filepaths):
        features = extract_features(slice_filepath)
        prediction = tflite_predict(features)
        prediction = softmax(prediction)
        r_dominica, t_castaneum, s_oryzae, no_insects = prediction[0]
        predicted_species = ''
        if no_insects > max(r_dominica, t_castaneum, s_oryzae):
            predicted_species = 'No_insects'
        elif r_dominica > max(t_castaneum, s_oryzae, no_insects):
            predicted_species = 'R_dominica'
        elif t_castaneum > max(r_dominica, s_oryzae, no_insects):
            predicted_species = 'T_castaneum'
        else:
            predicted_species = 'S_oryzae'
        predictions.append({
            'r_dominica': round(float(r_dominica) * 100, 1),
            's_oryzae': round(float(s_oryzae) * 100, 1),
            't_castaneum': round(float(t_castaneum) * 100, 1),
            'no_insects': round(float(no_insects) * 100, 1),
            'predicted_species': predicted_species,
            'slice_filepath': slice_filepath,
            'slice_number': i + 1
        })
    return predictions

def generate_graph(prediction, filename):
    species = ['$\it{R\_dominica}$', '$\it{S\_oryzae}$', '$\it{T\_castaneum}$', 'No_insects']
    values = [prediction['no_insects'], prediction['s_oryzae'], prediction['t_castaneum'], prediction['r_dominica']]
    plt.figure(figsize=(5, 4))
    plt.bar(species, values, color=['#1F78B4', '#1F78B4', '#1F78B4', '#1F78B4'])
    plt.ylabel('Prediction (%)')
    plt.title(f'Prediction for {filename}')
    graph_path = f"{filename}_bar.png"
    plt.savefig(os.path.join(app.config['GRAPH_FOLDER'], graph_path))
    plt.close()
    return graph_path

def generate_spectrogram(file_path, filename):
    audio, sr = librosa.load(file_path, sr=None)
    plt.figure(figsize=(5, 4))
    S = librosa.feature.melspectrogram(y=audio, sr=sr, n_mels=128, fmax=8000)
    S_dB = librosa.power_to_db(S, ref=np.max)
    librosa.display.specshow(S_dB, sr=sr, fmax=8000, cmap='magma')
    plt.colorbar(format='%+2.0f dB')
    plt.title(f'Spectrogram for {filename}')
    spectrogram_path = f"{filename}_spectrogram.png"
    plt.savefig(os.path.join(app.config['GRAPH_FOLDER'], spectrogram_path))
    plt.close()
    return spectrogram_path


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload')
def upload():
    return render_template('upload.html')

@app.route('/predict', methods=['POST'])
def predict():
    if 'files' not in request.files:
        return 'No files uploaded', 400
    files = request.files.getlist('files')
    if not files:
        return 'No selected files', 400
    results = []
    for file in files:
        if file and file.filename.endswith('.wav'):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            predictions = predict_species(filepath)
            for prediction in predictions:
                slice_filename = f"slice_{prediction['slice_number']}_{file.filename}"
                graph_url = generate_graph(prediction, slice_filename)
                spectrogram_url = generate_spectrogram(prediction['slice_filepath'], slice_filename)
                results.append({
                    'filename': slice_filename,
                    'result': prediction,
                    'graph_url': graph_url,
                    'spectrogram_url': spectrogram_url
                })
    return render_template('result.html', results=results)

@app.route('/generate_csv', methods=['POST'])
def generate_csv():
    results = request.form.getlist('results')[0]
    results = json.loads(results)
    csv_output = [["File Name", "R_dominica", "S_oryzae", "T_castaneum", "No Insect"]]
    for item in results:
        csv_output.append([
            item['filename'],
            f"{item['result']['no_insects']}%",
            f"{item['result']['s_oryzae']}%",
            f"{item['result']['t_castaneum']}%",
            f"{item['result']['r_dominica']}%"
        ])
    output = '\n'.join(','.join(row) for row in csv_output)
    response = make_response(output)
    response.headers['Content-Disposition'] = 'attachment; filename=predictions.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response

@app.route('/retrieve_data', methods=['POST', 'GET'])
def retrieve_data():
    results = []
    filename = "mic_recording2.wav"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if request.method == "POST":
        duration = int(request.form.get('duration', DURATION))
        device = int(request.form.get('device', DEVICE))
        record_and_save(filename=filename, duration=duration, sample_rate=SAMPLE_RATE, channels=CHANNELS, device=device)
        return redirect(url_for('retrieve_data'))
    if os.path.exists(filepath):
        predictions = predict_species(filepath)
        for prediction in predictions:
            slice_filename = f"slice_{prediction['slice_number']}_{filename}"
            graph_url = generate_graph(prediction, slice_filename)
            spectrogram_url = generate_spectrogram(prediction['slice_filepath'], slice_filename)
            results.append({
                'filename': slice_filename,
                'result': prediction,
                'graph_url': graph_url,
                'spectrogram_url': spectrogram_url
            })

    return render_template('result.html', results=results)

@app.route('/classify', methods=['POST'])
def classify():
    audio_folder = os.path.join(os.getcwd(), 'retrieve_audio')
    wav_files = glob.glob(os.path.join(audio_folder, '*.wav'))
    if not wav_files:
        return {'error': 'No WAV files found in the specified folder'}, 400
    latest_wav = max(wav_files, key=os.path.getctime)
    results = []
    audio = AudioSegment.from_file(latest_wav, format="wav")
    duration_minutes = len(audio) / (60 * 1000)
    if duration_minutes >= 10:
        slice_filepaths = preprocess_audio(latest_wav, app.config['UPLOAD_FOLDER'])
        for i, slice_filepath in enumerate(slice_filepaths):
            features = extract_features(slice_filepath)
            prediction = tflite_predict(features)
            prediction = softmax(prediction)
            r_dominica, t_castaneum, s_oryzae, no_insects = prediction[0]
            predicted_species = ''
            if no_insects > max(r_dominica, t_castaneum, s_oryzae):
                predicted_species = 'No_insects'
            elif r_dominica > max(t_castaneum, s_oryzae, no_insects):
                predicted_species = 'R_dominica'
            elif t_castaneum > max(r_dominica, s_oryzae, no_insects):
                predicted_species = 'T_castaneum'
            else:
                predicted_species = 'S_oryzae'
            slice_filename = f"slice_{i+1}_{os.path.basename(latest_wav)}"
            prediction_dict = {
                'r_dominica': round(float(r_dominica) * 100, 1),
                's_oryzae': round(float(s_oryzae) * 100, 1),
                't_castaneum': round(float(t_castaneum) * 100, 1),
                'no_insects': round(float(no_insects) * 100, 1),
                'predicted_species': predicted_species,
                'slice_filepath': slice_filepath,
                'slice_number': i + 1
            }
            graph_url = generate_graph(prediction_dict, slice_filename)
            spectrogram_url = generate_spectrogram(slice_filepath, slice_filename)
            results.append({
                'filename': slice_filename,
                'result': prediction_dict,
                'graph_url': graph_url,
                'spectrogram_url': spectrogram_url
            })
    else:
        features = extract_features(latest_wav)
        prediction = tflite_predict(features)
        prediction = softmax(prediction)
        r_dominica, t_castaneum, s_oryzae, no_insects = prediction[0]
        predicted_species = ''
        if no_insects > max(r_dominica, t_castaneum, s_oryzae):
            predicted_species = 'No_insects'
        elif r_dominica > max(t_castaneum, s_oryzae, no_insects):
            predicted_species = 'R_dominica'
        elif t_castaneum > max(r_dominica, s_oryzae, no_insects):
            predicted_species = 'T_castaneum'
        else:
            predicted_species = 'S_oryzae'
        prediction_dict = {
            'r_dominica': round(r_dominica * 100, 1),
            's_oryzae': round(s_oryzae * 100, 1),
            't_castaneum': round(t_castaneum * 100, 1),
            'no_insects': round(no_insects * 100, 1),
            'predicted_species': predicted_species,
            'slice_filepath': latest_wav,
            'slice_number': 1
        }
        filename = os.path.basename(latest_wav)
        graph_url = generate_graph(prediction_dict, filename)
        spectrogram_url = generate_spectrogram(latest_wav, filename)
        results.append({
            'filename': filename,
            'result': prediction_dict,
            'graph_url': graph_url,
            'spectrogram_url': spectrogram_url
        })

    all_results = [item['result']['predicted_species'] for item in results]
    print(all_results)
    tc = 0
    so = 0
    rd = 0
    ni = 0

    for result in all_results:

        if result == 't_castaneum':
            tc += 1
        elif result =='s_oryzae':
            so +=1
        elif result == 'r_dominica':
            rd+=1
        elif result== 'no_insects':
            ni +=1

    #find the most evident type of insect in the wav file

    counts = {
        't_castaneum': tc,
        'S_oryzae': so,
        'r_dominica': rd,
        'no_insects': ni
    }
    max_label = max(counts, key=counts.get)
    max_value = counts[max_label]

    message_text =f"The highest count is +{max_value} from {max_label}"
    #Send text msg

    send_command('AT')
    # 2. Set text mode
    send_command('AT+CMGF=1')

    # 3. Send SMS command
    send_command(f'AT+CMGS="{phone_number}"')
    time.sleep(1)  # wait a bit

    # 4. Send message text + Ctrl+Z
    ser.write(message_text.encode())
    ser.write(b"\x1A")  # Ctrl+Z
    ser.close()

    return render_template('result.html', results=results)

if __name__ == '__main__':
    import sys
    import os
    # Ensure the virtual environment's Scripts directory is in PATH (Windows)
    if sys.platform.startswith('win'):
        venv_scripts = os.path.join(os.path.dirname(__file__), '.venv', 'Scripts')
        if os.path.exists(venv_scripts) and venv_scripts not in os.environ.get('PATH', ''):
            os.environ['PATH'] = venv_scripts + os.pathsep + os.environ.get('PATH', '')
    app.run(host="0.0.0.0", port=5000)
