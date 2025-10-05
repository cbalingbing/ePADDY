import matplotlib.pyplot as plt
import librosa.display
import os
import AppV4
import numpy as np

def generate_graph(prediction, filename):
    species = ['$\it{R\_dominica}$', '$\it{S\_oryzae}$', '$\it{T\_castaneum}$', 'No_insects']
    values = [prediction['RD'], prediction['SO'], prediction['TC'], prediction['NoInsects']]
    plt.figure(figsize=(5, 4))
    plt.bar(species, values, color=['#1F78B4', '#1F78B4', '#1F78B4', '#1F78B4'])
    plt.ylabel('Prediction (%)')
    plt.title(f'Prediction for {filename}')
    graph_path = f"{filename}_bar.png"
    plt.savefig(os.path.join(AppV4.app.config['GRAPH_FOLDER'], graph_path))
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
    plt.savefig(os.path.join(AppV4.app.config['GRAPH_FOLDER'], spectrogram_path))
    plt.close()
    return spectrogram_path