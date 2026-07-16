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


def probe_audio_ffmpeg(path: str) -> tuple[int, int]:
    """Probe audio stream metadata using FFprobe.

    Args:
        path: Path to the audio file

    Returns:
        Tuple of (samplerate, channels)

    Raises:
        FileNotFoundError: If the file does not exist
        RuntimeError: If FFprobe is unavailable or probing fails
        ValueError: If metadata is missing or invalid
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Audio file not found: {path}")

    if shutil.which("ffprobe") is None:
        raise RuntimeError(
            "FFprobe is not installed or not found in PATH. "
            "Please install FFmpeg (which includes FFprobe)."
        )

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=sample_rate,channels",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
    ]

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except FileNotFoundError as e:
        raise RuntimeError("FFprobe executable not found") from e

    if proc.returncode != 0:
        error_msg = proc.stderr.strip() or "FFprobe failed with unknown error"
        raise RuntimeError(f"Unable to probe {path}: {error_msg}")

    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if len(lines) < 2:
        raise ValueError(f"Could not read samplerate/channels from {path}")

    try:
        samplerate = int(lines[0])
        channels = int(lines[1])
    except ValueError as e:
        raise ValueError(f"Invalid FFprobe metadata for {path}: {lines}") from e

    if samplerate <= 0 or channels <= 0:
        raise ValueError(
            f"Invalid audio metadata for {path}: samplerate={samplerate}, channels={channels}"
        )

    return samplerate, channels


def load_audio_ffmpeg(
    path: str, samplerate: int | None = None, channels: int | None = None
) -> np.ndarray:
    """Decode an audio file to float32 PCM using FFmpeg.

    Args:
        path: Path to the audio file
        samplerate: Target sample rate in Hz. If None, keep source rate.
        channels: Number of audio channels. If None, keep source channels.

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

    _, probe_channels = probe_audio_ffmpeg(path)
    target_channels = channels if channels is not None else probe_channels

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
        "-",
    ]

    if channels is not None:
        cmd.extend(["-ac", str(channels)])

    if samplerate is not None:
        cmd.extend(["-ar", str(samplerate)])

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
        audio = audio.reshape(-1, target_channels)
        return audio
    except ValueError as e:
        raise ValueError(f"Failed to process audio data from {path}: {str(e)}") from e
