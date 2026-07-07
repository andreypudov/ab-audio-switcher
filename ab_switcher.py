import argparse
import sys

from switcher.audio_compare import compare_audio_files

__version__ = "0.2.0"


def build_parser():
    parser = argparse.ArgumentParser(
        description="Compare multiple audio files interactively with instant A/B switching.",
        epilog="Examples:\n"
        "  %(prog)s track_a.mp3 track_b.flac\n"
        "  %(prog)s a.wav b.wav c.flac",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "files",
        nargs="+",
        metavar="FILE",
        help="Audio files to compare (e.g., track_a.mp3 track_b.flac)",
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

    try:
        return compare_audio_files(args.files)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
