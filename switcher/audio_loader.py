import os
import shutil
import subprocess

import numpy as np


def _check_ffmpeg_available():
    """Check if FFmpeg is available in the system PATH."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "FFmpeg is not installed or not found in PATH.\n"
            "Please install FFmpeg:\n"
            "  macOS: brew install ffmpeg\n"
            "  Linux: sudo apt-get install ffmpeg\n"
            "  Windows: choco install ffmpeg or download from https://ffmpeg.org/download.html"
        )


def load_audio_ffmpeg(
    path: str, samplerate: int = 44100, channels: int = 2
) -> np.ndarray:
    """Decode an audio file to float32 PCM using FFmpeg.

    Args:
        path: Path to the audio file
        samplerate: Target sample rate in Hz
        channels: Number of audio channels

    Returns:
        numpy array of shape (num_samples, channels) with dtype float32

    Raises:
        FileNotFoundError: If the audio file does not exist
        RuntimeError: If FFmpeg is not available or decoding fails
        ValueError: If no audio data could be decoded
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Audio file not found: {path}")

    if not os.path.isfile(path):
        raise ValueError(f"Path is not a file: {path}")

    _check_ffmpeg_available()

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

    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False
        )
        raw, err = proc.communicate()
    except FileNotFoundError:
        raise RuntimeError(
            "FFmpeg executable not found. Please install FFmpeg and ensure it's in your PATH."
        )

    if proc.returncode != 0:
        error_msg = err.decode("utf-8", errors="replace").strip()
        if not error_msg:
            error_msg = "FFmpeg failed with unknown error"
        raise RuntimeError(f"Unable to decode {path}: {error_msg}")

    if not raw:
        raise ValueError(
            f"No audio data decoded from {path}. "
            "The file may be corrupt, empty, or in an unsupported format."
        )

    try:
        audio = np.frombuffer(raw, dtype=np.float32)
        if audio.size == 0:
            raise ValueError(f"No audio samples in decoded data from {path}")
        audio = audio.reshape(-1, channels)
        return audio
    except ValueError as e:
        raise ValueError(f"Failed to process audio data from {path}: {str(e)}") from e
