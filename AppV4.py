from flask import Flask, render_template, request, redirect, url_for, make_response
import os
import tensorflow as tf
import json
import serial
import classify
import recording
import visualization
import sys
import glob
from pydub import AudioSegment, effects
import warnings

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] =  os.path.join(BASE_DIR, 'uploads')
app.config['GRAPH_FOLDER'] = 'static/graphs/'


os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['GRAPH_FOLDER'], exist_ok=True)

warnings.filterwarnings("ignore")



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
            predictions = classify.predict_species(filepath)
            for prediction in predictions:
                slice_filename = f"slice_{prediction['slice_number']}_{file.filename}"
                graph_url = visualization.generate_graph(prediction, slice_filename)
                spectrogram_url = visualization.generate_spectrogram(prediction['slice_filepath'], slice_filename)
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
            f"{item['result']['RD']}%",
            f"{item['result']['SO']}%",
            f"{item['result']['TC']}%",
            f"{item['result']['NoInsect']}%"
        ])
    output = '\n'.join(','.join(row) for row in csv_output)
    response = make_response(output)
    response.headers['Content-Disposition'] = 'attachment; filename=predictions.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response

@app.route('/record', methods=['POST', 'GET'])
def record():
    results = []
    filename = "mic_recording.wav"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if request.method == "POST":
        duration = int(request.form.get('duration', recording.DURATION))
        device = int(request.form.get('device', recording.DEVICE))
        recording.record_and_save(filename=filename, duration=duration, sample_rate=recording.SAMPLE_RATE, channels=recording.CHANNELS, device=device)
        return redirect(url_for('record'))
    if os.path.exists(filepath):
        predictions = classify.predict_species(filepath)
        for prediction in predictions:
            slice_filename = f"slice_{prediction['slice_number']}_{filename}"
            graph_url = visualization.generate_graph(prediction, slice_filename)
            spectrogram_url = visualization.generate_spectrogram(prediction['slice_filepath'], slice_filename)
            results.append({
                'filename': slice_filename,
                'result': prediction,
                'graph_url': graph_url,
                'spectrogram_url': spectrogram_url
            })

    return render_template('result.html', results=results)

@app.route('/classify', methods=['POST'])
def realtime_sensor():
    audio_folder = os.path.join(os.getcwd(), 'retrieve_audio')
    wav_files = glob.glob(os.path.join(audio_folder, '*.wav'))
    if not wav_files:
        return {'error': 'No WAV files found in the specified folder'}, 400
    latest_wav = max(wav_files, key=os.path.getctime)
    filename = os.path.splitext(os.path.basename(latest_wav))[0]
    results = []
    audio = AudioSegment.from_file(latest_wav, format="wav")
    duration_minutes = len(audio) / (60 * 1000)
    if duration_minutes >= 10:
        predictions = classify.predict_species(latest_wav)
        for prediction in predictions:
            slice_filename = f"slice_{prediction['slice_number']}_{filename}"
            graph_url = visualization.generate_graph(prediction, slice_filename)
            spectrogram_url = visualization.generate_spectrogram(prediction['slice_filepath'], slice_filename)
            results.append({
                'filename': slice_filename,
                'result': prediction,
                'graph_url': graph_url,
                'spectrogram_url': spectrogram_url
            })

    #     slice_filepaths = preprocess_audio(latest_wav, app.config['UPLOAD_FOLDER'])
    #     for i, slice_filepath in enumerate(slice_filepaths):
    #         features = extract_features(slice_filepath)
    #         prediction = tflite_predict(features)
    #         prediction = softmax(prediction)
    #         r_dominica, t_castaneum, s_oryzae, no_insects = prediction[0]
    #         predicted_species = ''
    #         if no_insects > max(r_dominica, t_castaneum, s_oryzae):
    #             predicted_species = 'No_insects'
    #         elif r_dominica > max(t_castaneum, s_oryzae, no_insects):
    #             predicted_species = 'R_dominica'
    #         elif t_castaneum > max(r_dominica, s_oryzae, no_insects):
    #             predicted_species = 'T_castaneum'
    #         else:
    #             predicted_species = 'S_oryzae'
    #         slice_filename = f"slice_{i+1}_{os.path.basename(latest_wav)}"
    #         prediction_dict = {
    #             'r_dominica': round(float(r_dominica) * 100, 1),
    #             's_oryzae': round(float(s_oryzae) * 100, 1),
    #             't_castaneum': round(float(t_castaneum) * 100, 1),
    #             'no_insects': round(float(no_insects) * 100, 1),
    #             'predicted_species': predicted_species,
    #             'slice_filepath': slice_filepath,
    #             'slice_number': i + 1
    #         }
    #         graph_url = generate_graph(prediction_dict, slice_filename)
    #         spectrogram_url = generate_spectrogram(slice_filepath, slice_filename)
    #         results.append({
    #             'filename': slice_filename,
    #             'result': prediction_dict,
    #             'graph_url': graph_url,
    #             'spectrogram_url': spectrogram_url
    #         })
    # else:
    #     features = extract_features(latest_wav)
    #     prediction = tflite_predict(features)
    #     prediction = softmax(prediction)
    #     r_dominica, t_castaneum, s_oryzae, no_insects = prediction[0]
    #     predicted_species = ''
    #     if no_insects > max(r_dominica, t_castaneum, s_oryzae):
    #         predicted_species = 'No_insects'
    #     elif r_dominica > max(t_castaneum, s_oryzae, no_insects):
    #         predicted_species = 'R_dominica'
    #     elif t_castaneum > max(r_dominica, s_oryzae, no_insects):
    #         predicted_species = 'T_castaneum'
    #     else:
    #         predicted_species = 'S_oryzae'
    #     prediction_dict = {
    #         'r_dominica': round(r_dominica * 100, 1),
    #         's_oryzae': round(s_oryzae * 100, 1),
    #         't_castaneum': round(t_castaneum * 100, 1),
    #         'no_insects': round(no_insects * 100, 1),
    #         'predicted_species': predicted_species,
    #         'slice_filepath': latest_wav,
    #         'slice_number': 1
    #     }
    #     filename = os.path.basename(latest_wav)
    #     graph_url = generate_graph(prediction_dict, filename)
    #     spectrogram_url = generate_spectrogram(latest_wav, filename)
    #     results.append({
    #         'filename': filename,
    #         'result': prediction_dict,
    #         'graph_url': graph_url,
    #         'spectrogram_url': spectrogram_url
    #     })


    return render_template('result.html', results=results)

if __name__ == '__main__':

    # Ensure the virtual environment's Scripts directory is in PATH (Windows)
    if sys.platform.startswith('win'):
        venv_scripts = os.path.join(os.path.dirname(__file__), '.venv', 'Scripts')
        if os.path.exists(venv_scripts) and venv_scripts not in os.environ.get('PATH', ''):
            os.environ['PATH'] = venv_scripts + os.pathsep + os.environ.get('PATH', '')
    app.run(host="0.0.0.0", port=5000)
