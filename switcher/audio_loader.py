import subprocess

import numpy as np


def load_audio_ffmpeg(path, samplerate=44100, channels=2):
    """Decode an audio file to float32 PCM using FFmpeg."""
    cmd = [
        "ffmpeg",
        "-v",
        "error",
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

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    raw, err = proc.communicate()

    if proc.returncode != 0:
        message = err.decode("utf-8", errors="replace").strip() or "ffmpeg failed"
        raise RuntimeError(f"Unable to decode {path}: {message}")

    if not raw:
        raise ValueError(f"No audio data decoded from {path}")

    audio = np.frombuffer(raw, dtype=np.float32)
    audio = audio.reshape(-1, channels)
    return audio
