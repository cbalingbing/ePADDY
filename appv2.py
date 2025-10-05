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
from keras.models import load_model
from keras.activations import softmax
import json
import sounddevice as sd
import wave
import soundfile as sf
from scipy.signal import butter, lfilter
from pydub import AudioSegment, effects
import glob

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['GRAPH_FOLDER'] = 'static/graphs/'
model = load_model('my_model.h5')

SAMPLE_RATE = 44100  # Standard audio sample rate
DURATION = 10  # Record for 10 seconds
DEVICE = 1  # Use default mic
CHANNELS = 1  # Mono audio

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['GRAPH_FOLDER'], exist_ok=True)

lowpass_cutoff_freq = 2500  # Low-pass cutoff frequency in Hz; Highcut
highpass_cutoff_freq = 93.75  # High-pass cutoff frequency in Hz; Lowcut
filter_order = 4  # Filter order

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

# Preprocess the wav files
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
    """
    Normalize waveform to range [-1, 1].
    """
    max_val = np.max(np.abs(waveform))
    if max_val > 0:
        return waveform / max_val
    else:
        return waveform

def preprocess_audio(file_path, output_folder):
    start_time = 3 * 60 * 1000  # 3 minutes
    end_time = -1 * 60 * 1000  # -1 minute (from the end)
    
    # Load the WAV file using pydub
    audio = AudioSegment.from_file(file_path, format="wav")
    
    # Trim the audio
    trimmed_audio = audio[start_time:end_time]
    
    # Normalize the audio to 0 dB
    normalized_audio = effects.normalize(trimmed_audio)
    
    # Export to a temporary file before applying SciPy filtering
    temp_filepath = os.path.join(output_folder, "temp_" + os.path.basename(file_path))
    normalized_audio.export(temp_filepath, format="wav")
    
    # Load the sound file with SciPy for filtering
    sound_data, samplerate = sf.read(temp_filepath)
    
    # Normalize waveform for consistency
    normalized_sound_data = normalize_waveform(sound_data)
    
    # Apply band-pass filtering
    filtered_sound = apply_butterworth_filter(normalized_sound_data, lowpass_cutoff_freq, highpass_cutoff_freq, filter_order, samplerate)
    
    # Save the final processed file
    processed_filepath = os.path.join(output_folder, "processed_" + os.path.basename(file_path))
    sf.write(processed_filepath, filtered_sound, samplerate)
    
    # Remove temporary file
    os.remove(temp_filepath)
    
    # Slice the processed file into 10-second segments
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

# extract MFCC features from the wav file
def extract_features(file_path):
    # Load the sound file with a lower sample rate
    sound_data, samplerate = sf.read(file_path)
    
    # Resample the audio to a lower sample rate if necessary
    target_samplerate = 8000  # Lower sample rate to reduce memory usage
    if samplerate != target_samplerate:
        sound_data = librosa.resample(sound_data, orig_sr=samplerate, target_sr=target_samplerate)
        samplerate = target_samplerate

    # Normalize the waveform 
    normalized_sound_data = normalize_waveform(sound_data)

    # Apply the Band-pass Butterworth filter to the normalized sound
    filtered_sound_bandpass = apply_butterworth_filter(normalized_sound_data, lowpass_cutoff_freq, highpass_cutoff_freq, filter_order, samplerate)

    # Compute the mel spectrogram with a smaller FFT window
    spectrogram = librosa.feature.melspectrogram(y=filtered_sound_bandpass, sr=samplerate, n_fft=512, hop_length=256, n_mels=128)
    spectrogram = librosa.power_to_db(spectrogram, ref=np.max)
    
    # Ensure the spectrogram has a fixed length
    spectrogram = librosa.util.fix_length(spectrogram, size=128, axis=1)
    
    # Match the model input (128, 128, 1)
    spectrogram = np.expand_dims(spectrogram, axis=-1)
    spectrogram = np.expand_dims(spectrogram, axis=0)
    
    return spectrogram

# function to handle model inference
def predict_species(file_path):
    # Check the duration of the audio file
    audio = AudioSegment.from_file(file_path, format="wav")
    duration_minutes = len(audio) / (60 * 1000)
    
    if duration_minutes >= 10:
        # Preprocess the audio if it is 10 minutes or longer
        slice_filepaths = preprocess_audio(file_path, app.config['UPLOAD_FOLDER'])
    else:
        slice_filepaths = [file_path]
    
    predictions = []
    for i, slice_filepath in enumerate(slice_filepaths):
        features = extract_features(slice_filepath)
        prediction = model.predict(features)

        # Apply softmax to the output
        prediction = softmax(prediction)

        r_dominica, t_castaneum, s_oryzae, no_insects = prediction[0].numpy()  # Convert to NumPy array

        # Determine the predicted species
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
            'r_dominica': round(r_dominica * 100, 1),
            's_oryzae': round(s_oryzae * 100, 1),
            't_castaneum': round(t_castaneum * 100, 1),
            'no_insects': round(no_insects * 100, 1),
            'predicted_species': predicted_species,
            'slice_filepath': slice_filepath,
            'slice_number': i + 1  # Add slice number to the prediction
        })
    
    return predictions

# generate bar graph for predictions
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

# generate spectrogram
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

            # Predict the species for each slice
            predictions = predict_species(filepath)

            for prediction in predictions:
                # Generate graphs
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
    results = request.form.getlist('results')[0]  # Get results passed from the form
    results = json.loads(results)  # Load results as JSON

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
        # Step 1: Record audio from the browser's microphone
        duration = int(request.form.get('duration', DURATION))  # Get duration from form or use default
        device = int(request.form.get('device', DEVICE))  # Get device from form or use default

        # Record and save the audio
        record_and_save(filename=filename, duration=duration, sample_rate=SAMPLE_RATE, channels=CHANNELS, device=device)

        # Redirect to GET method to process recorded audio
        return redirect(url_for('retrieve_data'))

    # Step 2: Load the recorded file and predict (this should run on GET)
    if os.path.exists(filepath):
        predictions = predict_species(filepath)

        for prediction in predictions:
            # Step 3: Generate Graphs
            slice_filename = f"slice_{prediction['slice_number']}_{filename}"
            graph_url = generate_graph(prediction, slice_filename)
            spectrogram_url = generate_spectrogram(prediction['slice_filepath'], slice_filename)

            results.append({
                'filename': slice_filename,
                'result': prediction,
                'graph_url': graph_url,
                'spectrogram_url': spectrogram_url
            })
        print(results)

    return render_template('result.html', results=results)


@app.route('/classify', methods=['POST'])
def classify():
    # Define the path to the audio folder
    audio_folder = os.path.join(os.getcwd(), 'retrieve_audio')
    
    # Get all WAV files in the folder
    wav_files = glob.glob(os.path.join(audio_folder, '*.wav'))
    
    if not wav_files:
        return {'error': 'No WAV files found in the specified folder'}, 400
    
    # Get the most recent WAV file
    latest_wav = max(wav_files, key=os.path.getctime)
    
    results = []
    
    # Check the duration and process the file
    audio = AudioSegment.from_file(latest_wav, format="wav")
    duration_minutes = len(audio) / (60 * 1000)
    
    if duration_minutes >= 10:
        # Process long audio file
        slice_filepaths = preprocess_audio(latest_wav, app.config['UPLOAD_FOLDER'])
        
        for i, slice_filepath in enumerate(slice_filepaths):
            # Get predictions for each slice
            features = extract_features(slice_filepath)
            prediction = model.predict(features)
            
            # Apply softmax to the output
            prediction = softmax(prediction)
            r_dominica, t_castaneum, s_oryzae, no_insects = prediction[0].numpy()
            
            # Determine predicted species
            predicted_species = ''
            if no_insects > max(r_dominica, t_castaneum, s_oryzae):
                predicted_species = 'No_insects'
            elif r_dominica > max(t_castaneum, s_oryzae, no_insects):
                predicted_species = 'R_dominica'
            elif t_castaneum > max(r_dominica, s_oryzae, no_insects):
                predicted_species = 'T_castaneum'
            else:
                predicted_species = 'S_oryzae'
            
            # Generate graphs for this slice
            slice_filename = f"slice_{i+1}_{os.path.basename(latest_wav)}"
            prediction_dict = {
                'r_dominica': round(r_dominica * 100, 1),
                's_oryzae': round(s_oryzae * 100, 1),
                't_castaneum': round(t_castaneum * 100, 1),
                'no_insects': round(no_insects * 100, 1),
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
        # Process short audio file
        features = extract_features(latest_wav)
        prediction = model.predict(features)
        
        # Apply softmax to the output
        prediction = softmax(prediction)
        r_dominica, t_castaneum, s_oryzae, no_insects = prediction[0].numpy()
        
        # Determine predicted species
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
        
        # Generate graphs
        filename = os.path.basename(latest_wav)
        graph_url = generate_graph(prediction_dict, filename)
    
        
        results.append({
            'filename': filename,
            'result': prediction_dict,
            'graph_url': graph_url,
            'spectrogram_url': spectrogram_url
        })
    
    return render_template('result.html', results=results)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
