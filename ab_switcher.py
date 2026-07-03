import argparse

from switcher.audio_compare import compare_audio_files

__version__ = "0.2.0"


def build_parser():
    parser = argparse.ArgumentParser(
        description="Compare multiple audio files interactively."
    )
    parser.add_argument(
        "files",
        nargs="+",
        metavar="FILE",
        help="Audio files to compare (for example: track_a.mp3 track_b.flac)",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return compare_audio_files(args.files)


if __name__ == "__main__":
    raise SystemExit(main())
