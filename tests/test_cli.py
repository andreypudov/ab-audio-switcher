import unittest
from unittest.mock import patch

import numpy as np

from ab_switcher import __version__, build_parser
from switcher.audio_compare import (
    _build_looped_chunk,
    _get_playback_chunk,
    _seek_playback_position,
    _shift_track,
    _validate_tracks,
)
from switcher.audio_loader import _check_ffmpeg_available


class ParserTests(unittest.TestCase):
    def test_parser_accepts_multiple_files(self):
        parser = build_parser()
        args = parser.parse_args(["a.mp3", "b.flac", "c.wav"])

        self.assertEqual(args.files, ["a.mp3", "b.flac", "c.wav"])

    def test_version_flag_is_available(self):
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["--version"])

    def test_parser_reports_version(self):
        self.assertTrue(__version__)


class AudioChunkTests(unittest.TestCase):
    def test_looped_chunk_wraps_at_minimum_length(self):
        track = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], dtype=np.float32)

        chunk = _build_looped_chunk(track, position=2, frames=4, loop_length=3)

        expected = np.array(
            [[5.0, 6.0], [1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], dtype=np.float32
        )
        np.testing.assert_array_equal(chunk, expected)

    def test_switching_tracks_uses_shared_playback_position(self):
        track_a = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], dtype=np.float32)
        track_b = np.array([[10.0, 20.0], [30.0, 40.0], [50.0, 60.0]], dtype=np.float32)

        chunk, next_position = _get_playback_chunk(
            [track_a, track_b],
            current_track=1,
            playback_position=2,
            frames=2,
            loop_length=3,
        )

        expected = np.array([[50.0, 60.0], [10.0, 20.0]], dtype=np.float32)
        np.testing.assert_array_equal(chunk, expected)
        self.assertEqual(next_position, 1)


class PlaybackControlTests(unittest.TestCase):
    def test_seek_playback_position_moves_by_five_seconds(self):
        next_position = _seek_playback_position(
            playback_position=10,
            samplerate=10,
            seconds=5,
            loop_length=100,
            direction=1,
        )

        self.assertEqual(next_position, 60)

    def test_seek_playback_position_wraps_at_loop_boundary(self):
        next_position = _seek_playback_position(
            playback_position=95,
            samplerate=10,
            seconds=5,
            loop_length=100,
            direction=1,
        )

        self.assertEqual(next_position, 45)

    def test_shift_track_wraps_through_playlist(self):
        self.assertEqual(_shift_track(0, 1, 2), 1)
        self.assertEqual(_shift_track(1, 1, 2), 0)
        self.assertEqual(_shift_track(0, -1, 2), 1)


class TrackValidationTests(unittest.TestCase):
    def test_validate_tracks_raises_on_empty_tracks(self):
        with self.assertRaises(ValueError) as ctx:
            _validate_tracks([], [])
        self.assertIn("No tracks loaded", str(ctx.exception))

    def test_validate_tracks_raises_on_channel_mismatch(self):
        track_a = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
        track_b = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=np.float32)

        with self.assertRaises(ValueError) as ctx:
            _validate_tracks([track_a, track_b], ["a.wav", "b.wav"])
        self.assertIn("Channel mismatch", str(ctx.exception))

    def test_validate_tracks_raises_on_empty_track(self):
        track_a = np.array([[1.0, 2.0]], dtype=np.float32)
        track_b = np.array([], dtype=np.float32).reshape(0, 2)

        with self.assertRaises(ValueError) as ctx:
            _validate_tracks([track_a, track_b], ["a.wav", "b.wav"])
        self.assertIn("No audio samples", str(ctx.exception))

    def test_validate_tracks_succeeds_with_matching_properties(self):
        track_a = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
        track_b = np.array([[5.0, 6.0], [7.0, 8.0]], dtype=np.float32)

        # Should not raise
        _validate_tracks([track_a, track_b], ["a.wav", "b.wav"])


class FFmpegDependencyTests(unittest.TestCase):
    @patch("shutil.which")
    def test_check_ffmpeg_available_raises_when_not_found(self, mock_which):
        mock_which.return_value = None
        with self.assertRaises(RuntimeError) as ctx:
            _check_ffmpeg_available()
        self.assertIn("FFmpeg is not installed", str(ctx.exception))

    @patch("shutil.which")
    def test_check_ffmpeg_available_succeeds_when_found(self, mock_which):
        mock_which.return_value = "/usr/bin/ffmpeg"
        # Should not raise
        _check_ffmpeg_available()


if __name__ == "__main__":
    unittest.main()
