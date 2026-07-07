import os

import numpy as np
import sounddevice as sd
from pynput import keyboard

from .audio_loader import load_audio_ffmpeg


def _build_looped_chunk(
    track: np.ndarray, position: int, frames: int, loop_length: int
) -> np.ndarray:
    """Build a chunk of audio with looping support.

    Args:
        track: Audio track array of shape (num_samples, channels)
        position: Current playback position in samples
        frames: Number of frames to retrieve
        loop_length: Length of loop in samples

    Returns:
        Audio chunk of shape (frames, channels)
    """
    if loop_length <= 0:
        return np.zeros((frames, track.shape[1]), dtype=np.float32)

    indices = (position + np.arange(frames, dtype=np.intp)) % loop_length
    return track[indices]


def _get_playback_chunk(
    tracks: list[np.ndarray],
    current_track: int,
    playback_position: int,
    frames: int,
    loop_length: int,
) -> tuple[np.ndarray, int]:
    """Get the next playback chunk for the current track.

    Args:
        tracks: List of audio track arrays
        current_track: Index of the currently playing track
        playback_position: Current position in samples
        frames: Number of frames to retrieve
        loop_length: Length of loop in samples

    Returns:
        Tuple of (audio_chunk, next_position)
    """
    chunk = _build_looped_chunk(
        tracks[current_track],
        playback_position,
        frames,
        loop_length,
    )
    next_position = (playback_position + frames) % loop_length
    return chunk, next_position


def _validate_tracks(tracks: list[np.ndarray], files: list[str]) -> None:
    """Validate that all tracks have compatible properties.

    Args:
        tracks: List of audio track arrays
        files: List of file paths corresponding to tracks

    Raises:
        ValueError: If tracks have incompatible properties
    """
    if not tracks:
        raise ValueError("No tracks loaded")

    if len(tracks) != len(files):
        raise ValueError("Mismatch between loaded tracks and file list")

    first_channels = tracks[0].shape[1]
    first_samples = tracks[0].shape[0]

    for i, (track, path) in enumerate(zip(tracks, files)):
        if track.ndim != 2:
            raise ValueError(
                f"{path}: Expected 2D array (samples, channels), got {track.ndim}D"
            )

        if track.shape[1] != first_channels:
            raise ValueError(
                f"Channel mismatch in {path}: "
                f"Expected {first_channels} channels, got {track.shape[1]}"
            )

        if track.shape[0] == 0:
            raise ValueError(f"{path}: No audio samples found")

        if track.shape[0] < first_samples / 100:
            print(
                f"Warning: {path} is significantly shorter than {os.path.basename(files[0])}. "
                "It will loop frequently during playback."
            )


def compare_audio_files(
    files: list[str], samplerate: int = 44100, channels: int = 2
) -> int:
    """Compare multiple audio files interactively with instant A/B switching.

    Args:
        files: List of audio file paths to compare
        samplerate: Target sample rate in Hz
        channels: Number of audio channels

    Returns:
        Exit code (0 for success)
    """
    if not files:
        raise ValueError("At least one audio file is required")

    # Validate file list
    invalid_files = [f for f in files if not os.path.exists(f)]
    if invalid_files:
        raise FileNotFoundError(f"Files not found: {', '.join(invalid_files)}")

    print("Loading audio…")
    tracks = []
    for path in files:
        try:
            print(f"Loading {os.path.basename(path)}", end="", flush=True)
            track = load_audio_ffmpeg(path, samplerate=samplerate, channels=channels)
            tracks.append(track)
            duration = track.shape[0] / samplerate
            print(f" ✓ ({duration:.2f}s)")
        except FileNotFoundError as e:
            print(" ✗")
            raise FileNotFoundError(f"Cannot read {path}: {e}") from e
        except RuntimeError as e:
            print(" ✗")
            raise RuntimeError(f"Failed to decode {path}: {e}") from e
        except ValueError as e:
            print(" ✗")
            raise ValueError(f"Invalid audio data in {path}: {e}") from e

    # Validate all tracks are compatible
    _validate_tracks(tracks, files)

    print(f"\nSuccessfully loaded {len(tracks)} track(s)")

    track_names = [os.path.basename(path) for path in files]
    current_track = 0
    playback_position = 0
    loop_length = min(len(track) for track in tracks)
    stop_requested = False

    def callback(outdata, frames, time, status):
        nonlocal current_track, playback_position, stop_requested

        if status:
            print(f"Audio warning: {status}", file=os.sys.stderr)

        chunk, playback_position = _get_playback_chunk(
            tracks,
            current_track,
            playback_position,
            frames,
            loop_length,
        )

        outdata[:] = chunk

    def on_press(key):
        nonlocal current_track, stop_requested

        try:
            if key == keyboard.Key.space:
                current_track = (current_track + 1) % len(tracks)
                print(f"Now playing: {track_names[current_track]}")
                return

            if key == keyboard.Key.esc:
                print("Exiting on Escape")
                stop_requested = True
                listener.stop()
                return False
        except AttributeError:
            # Handle special key cases where attribute lookup may fail
            pass

    listener = keyboard.Listener(on_press=on_press)

    print(f"Now playing: {track_names[current_track]}")
    print("Press SPACE to switch tracks, ESC to exit\n")

    try:
        with sd.OutputStream(
            samplerate=samplerate,
            channels=channels,
            callback=callback,
            dtype="float32",
        ):
            listener.start()
            listener.join()
    except KeyboardInterrupt:
        print("Exiting on Ctrl-C")
    except Exception as e:
        print(f"Playback error: {e}", file=os.sys.stderr)
        return 1
    finally:
        listener.stop()

    return 0
