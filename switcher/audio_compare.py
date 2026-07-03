import os

import numpy as np
import sounddevice as sd
from pynput import keyboard

from .audio_loader import load_audio_ffmpeg


def build_looped_chunk(track, position, frames, loop_length):
    if loop_length <= 0:
        return np.zeros((frames, track.shape[1]), dtype=np.float32)

    indices = (position + np.arange(frames, dtype=np.intp)) % loop_length
    return track[indices]


def get_playback_chunk(tracks, current_track, playback_position, frames, loop_length):
    chunk = build_looped_chunk(
        tracks[current_track],
        playback_position,
        frames,
        loop_length,
    )
    next_position = (playback_position + frames) % loop_length
    return chunk, next_position


def compare_audio_files(files, samplerate=44100, channels=2):
    if not files:
        raise ValueError("At least one audio file is required")

    print("Loading audio…")
    tracks = []
    for path in files:
        print(f"Loading {path}")
        tracks.append(load_audio_ffmpeg(path, samplerate=samplerate, channels=channels))

    print(f"Loaded {len(tracks)} tracks")

    track_names = [os.path.basename(path) for path in files]
    current_track = 0
    playback_position = 0
    loop_length = min(len(track) for track in tracks)
    stop_requested = False

    def callback(outdata, frames, time, status):
        nonlocal current_track, playback_position, stop_requested

        if status:
            print(status, file=os.sys.stderr)

        chunk, playback_position = get_playback_chunk(
            tracks,
            current_track,
            playback_position,
            frames,
            loop_length,
        )

        outdata[:] = chunk

    def on_press(key):
        nonlocal current_track, stop_requested

        if key == keyboard.Key.space:
            current_track = (current_track + 1) % len(tracks)
            print(f"Now playing: {track_names[current_track]}")
            return

        if key == keyboard.Key.esc:
            print("Exiting on Escape")
            stop_requested = True
            listener.stop()
            return False

    listener = keyboard.Listener(on_press=on_press)

    print(f"Now playing: {track_names[current_track]}")
    print("Press SPACE to switch tracks, ESC to exit")

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
    finally:
        listener.stop()

    return 0
