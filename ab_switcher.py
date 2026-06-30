import subprocess
import numpy as np
import sounddevice as sd
from pynput import keyboard


# ------------------------------------------------------------
# FFmpeg-based decoder (no pydub, no audioop)
# ------------------------------------------------------------
def load_audio_ffmpeg(path, samplerate=44100, channels=2):
    """
    Decode audio file to float32 PCM using FFmpeg.
    Returns a numpy array shaped (samples, channels).
    """
    cmd = [
        "ffmpeg",
        "-i",
        path,
        "-f",
        "f32le",
        "-acodec",
        "pcm_f32le",
        "-ac",
        str(channels),
        "-ar",
        str(samplerate),
        "-",
    ]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    raw = proc.stdout.read()
    audio = np.frombuffer(raw, dtype=np.float32)

    if channels > 1:
        audio = audio.reshape(-1, channels)
    else:
        audio = audio.reshape(-1, 1)

    return audio


# ------------------------------------------------------------
# Load audio files
# ------------------------------------------------------------
print("Loading audio…")
track_a = load_audio_ffmpeg("A.wav")
track_b = load_audio_ffmpeg("B.wav")

print("Track A samples:", track_a.shape)
print("Track B samples:", track_b.shape)

# ------------------------------------------------------------
# Playback state
# ------------------------------------------------------------
current = "A"
index = 0
samplerate = 44100
channels = 2


# ------------------------------------------------------------
# Audio callback
# ------------------------------------------------------------
def callback(outdata, frames, time, status):
    global index, current

    src = track_a if current == "A" else track_b
    end = index + frames
    chunk = src[index:end]

    # Loop if end reached
    if len(chunk) < frames:
        pad = np.zeros((frames - len(chunk), channels), dtype=np.float32)
        chunk = np.vstack((chunk, pad))
        index = 0
    else:
        index = end

    outdata[:] = chunk


# ------------------------------------------------------------
# Hotkey listener
# ------------------------------------------------------------
def on_press(key):
    global current
    if key == keyboard.Key.space:
        current = "B" if current == "A" else "A"
        print("Switched to", current)


listener = keyboard.Listener(on_press=on_press)
listener.start()

# ------------------------------------------------------------
# Start playback
# ------------------------------------------------------------
print("Playing… press SPACE to switch between A and B")
with sd.OutputStream(
    samplerate=samplerate, channels=channels, callback=callback, dtype="float32"
):
    listener.join()
