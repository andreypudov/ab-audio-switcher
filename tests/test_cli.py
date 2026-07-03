import unittest

import numpy as np

from ab_switcher import __version__, build_parser
from switcher.audio_compare import build_looped_chunk, get_playback_chunk


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

    def test_looped_chunk_wraps_at_minimum_length(self):
        track = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], dtype=np.float32)

        chunk = build_looped_chunk(track, position=2, frames=4, loop_length=3)

        expected = np.array(
            [[5.0, 6.0], [1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], dtype=np.float32
        )
        np.testing.assert_array_equal(chunk, expected)

    def test_switching_tracks_uses_shared_playback_position(self):
        track_a = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], dtype=np.float32)
        track_b = np.array([[10.0, 20.0], [30.0, 40.0], [50.0, 60.0]], dtype=np.float32)

        chunk, next_position = get_playback_chunk(
            [track_a, track_b],
            current_track=1,
            playback_position=2,
            frames=2,
            loop_length=3,
        )

        expected = np.array([[50.0, 60.0], [10.0, 20.0]], dtype=np.float32)
        np.testing.assert_array_equal(chunk, expected)
        self.assertEqual(next_position, 1)


if __name__ == "__main__":
    unittest.main()
