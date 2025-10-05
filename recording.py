import os
import AppV4
import sounddevice as sd
import wave

SAMPLE_RATE = 44000  # Standard audio sample rate
DURATION = 15  # Record for 10 seconds
DEVICE = 1  # Use default mic
CHANNELS = 1  # Mono audio

def record_and_save(filename="mic_recording.wav", duration=DURATION, sample_rate=SAMPLE_RATE, channels=CHANNELS, device=None):
    """Records audio from the microphone and saves it as a WAV file."""
    filepath = os.path.join(AppV4.app.config['UPLOAD_FOLDER'], filename)

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