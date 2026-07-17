import os

import numpy as np
import sounddevice as sd
from pynput import keyboard

from .audio_device import build_output_stream_kwargs
from .audio_loader import load_audio_ffmpeg, probe_audio_ffmpeg
from .playback_status import PlaybackStatusDisplay
from .terminal_utils import clear_and_print, disable_echo, restore_terminal, flush_input


SEEK_SECONDS = 3


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


def _seek_playback_position(
    playback_position: int,
    samplerate: int,
    seconds: int,
    loop_length: int,
    direction: int,
) -> int:
    """Seek playback position forward or backward by a fixed number of seconds.

    Args:
        playback_position: Current playback position in samples
        samplerate: Sample rate in Hz
        seconds: Number of seconds to seek
        loop_length: Length of loop in samples
        direction: 1 for forward seek, -1 for backward seek

    Returns:
        New playback position in samples, wrapped to the current loop length
    """
    if loop_length <= 0:
        return 0

    seek_samples = int(seconds * samplerate)
    return (playback_position + (direction * seek_samples)) % loop_length


def _shift_track(current_track: int, delta: int, track_count: int) -> int:
    """Move between tracks with wraparound.

    Args:
        current_track: Current track index
        delta: Relative step to apply (-1 for previous, 1 for next)
        track_count: Number of loaded tracks

    Returns:
        New track index, wrapped to the playlist length
    """
    if track_count <= 0:
        return 0

    return (current_track + delta) % track_count


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
    files: list[str], samplerate: int | None = None, channels: int | None = None
) -> int:
    """Compare multiple audio files interactively with instant A/B switching.

    Args:
        files: List of audio file paths to compare
        samplerate: Target sample rate in Hz. If None, use source rate.
        channels: Number of audio channels. If None, use source channels.

    Returns:
        Exit code (0 for success)
    """
    if not files:
        raise ValueError("At least one audio file is required")

    # Validate file list
    invalid_files = [f for f in files if not os.path.exists(f)]
    if invalid_files:
        raise FileNotFoundError(f"Files not found: {', '.join(invalid_files)}")

    stream_samplerate = samplerate
    stream_channels = channels
    if stream_samplerate is None or stream_channels is None:
        first_samplerate, first_channels = probe_audio_ffmpeg(files[0])
        stream_samplerate = (
            first_samplerate if stream_samplerate is None else stream_samplerate
        )
        stream_channels = first_channels if stream_channels is None else stream_channels

        # If native mode is requested (samplerate/channels are None), require all
        # tracks to match to avoid hidden resampling/remixing.
        for path in files[1:]:
            file_samplerate, file_channels = probe_audio_ffmpeg(path)
            if samplerate is None and file_samplerate != stream_samplerate:
                raise ValueError(
                    "Bit-perfect playback requires matching sample rates across all files. "
                    f"Expected {stream_samplerate} Hz, got {file_samplerate} Hz in {path}."
                )
            if channels is None and file_channels != stream_channels:
                raise ValueError(
                    "Bit-perfect playback requires matching channel counts across all files. "
                    f"Expected {stream_channels} channels, got {file_channels} in {path}."
                )

    print("Loading audio...")
    tracks = []
    for path in files:
        try:
            print(f"Loading {os.path.basename(path)}", end="", flush=True)
            track = load_audio_ffmpeg(
                path,
                samplerate=stream_samplerate,
                channels=stream_channels,
            )
            tracks.append(track)
            duration = track.shape[0] / stream_samplerate
            print(f" [OK] ({duration:.2f}s)", flush=True)
        except FileNotFoundError as e:
            print(" [ERR]", flush=True)
            raise FileNotFoundError(f"Cannot read {path}: {e}") from e
        except RuntimeError as e:
            print(" [ERR]", flush=True)
            raise RuntimeError(f"Failed to decode {path}: {e}") from e
        except ValueError as e:
            print(" [ERR]", flush=True)
            raise ValueError(f"Invalid audio data in {path}: {e}") from e

    # Validate all tracks are compatible
    _validate_tracks(tracks, files)

    print(f"\nSuccessfully loaded {len(tracks)} track(s)")
    stream_kwargs, output_mode_message = build_output_stream_kwargs(
        samplerate=stream_samplerate,
        channels=stream_channels,
    )
    if output_mode_message:
        print(output_mode_message, flush=True)

    track_names = [os.path.basename(path) for path in files]
    current_track = 0
    playback_position = 0
    loop_length = min(len(track) for track in tracks)
    status_display = PlaybackStatusDisplay(
        samplerate=stream_samplerate,
        get_playback_position=lambda: playback_position,
        get_track_name=lambda: track_names[current_track],
    )
    is_exiting = False

    def callback(outdata, frames, time, status):
        nonlocal current_track, playback_position

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
        nonlocal current_track, playback_position, is_exiting

        try:
            if is_exiting:
                return

            if key == keyboard.Key.space or key == keyboard.Key.up:
                current_track = _shift_track(current_track, 1, len(tracks))
                status_display.render()
                return

            if key == keyboard.Key.down:
                current_track = _shift_track(current_track, -1, len(tracks))
                status_display.render()
                return

            if key == keyboard.Key.left:
                playback_position = _seek_playback_position(
                    playback_position,
                    stream_samplerate,
                    seconds=SEEK_SECONDS,
                    loop_length=loop_length,
                    direction=-1,
                )
                status_display.render()
                return

            if key == keyboard.Key.right:
                playback_position = _seek_playback_position(
                    playback_position,
                    stream_samplerate,
                    seconds=SEEK_SECONDS,
                    loop_length=loop_length,
                    direction=1,
                )
                status_display.render()
                return

            if key == keyboard.Key.esc:
                is_exiting = True
                status_display.stop()
                clear_and_print("Quitting...", newline=True)
                listener.stop()
                return False
        except AttributeError:
            # Handle special key cases where attribute lookup may fail
            pass

    # Create the listener without suppression. Suppression requires
    # accessibility permissions on macOS and can make the listener fail to
    # start; instead disable local terminal echo below to avoid the ESC byte
    # being displayed in the shell.
    listener = keyboard.Listener(on_press=on_press, suppress=False)

    # Print the instructions once, then show a status line that will be updated in-place
    print(
        "Press SPACE or ↑ to switch to the next track, ↓ to switch to the previous track, "
        f"←/→ to seek {SEEK_SECONDS} seconds, ESC to exit",
        flush=True,
    )
    print("", flush=True)
    status_display.render()

    # Terminal state helpers for suppressing local echo of pressed keys
    orig_term_attrs = None
    terminal_fd = None

    try:
        # Before starting the listener, disable local terminal echo so
        # characters like ESC aren't echoed by the shell when the user
        # presses keys. This avoids writing escape bytes like `^[` to the
        # terminal even if the global listener can't suppress events.
        # Try to disable local terminal echo; returns (fd, orig_attrs) or (None, None)
        terminal_fd, orig_term_attrs = disable_echo()

        with sd.OutputStream(
            callback=callback,
            **stream_kwargs,
        ):
            listener.start()
            status_display.start()
            # Emit a newline immediately after starting the listener so any
            # external messages (e.g. macOS accessibility warnings) appear on
            # their own line instead of being appended to the status line.
            try:
                print("", flush=True)
            except Exception:
                pass
            listener.join()
    except KeyboardInterrupt:
        is_exiting = True
        status_display.stop()
        clear_and_print("Quitting...", newline=True)
    except Exception as e:
        print(f"Playback error: {e}", file=os.sys.stderr)
        return 1
    finally:
        status_display.stop()

        try:
            listener.stop()
        except Exception:
            pass

        # Restore terminal attributes if they were changed
        try:
            restore_terminal(terminal_fd, orig_term_attrs)
        except Exception:
            pass

        # Flush any pending input (for example the ESC byte) so the shell
        # doesn't display leftover control characters after this program exits.
        try:
            flush_input()
        except Exception:
            pass

    return 0
