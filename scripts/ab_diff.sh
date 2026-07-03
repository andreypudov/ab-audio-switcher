#!/usr/bin/env sh

set -eu

# check parameters
if [ $# -ne 3 ]; then
    echo "Usage: $0 <source-audio-file-1> <source-audio-file-2> <destination-spectrogram-file>" >&2
    exit 1
fi

SOURCE1="$1"
SOURCE2="$2"
DESTINATION="$3"
SPECTROGRAM_SIZE="3840x2160"

# check source files exist
for source in "$SOURCE1" "$SOURCE2"; do
    if [ ! -f "$source" ]; then
        echo "Error: source file '$source' not found." >&2
        exit 1
    fi
done

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ab-compare.XXXXXX")"
TMP_SPEC1="$TMP_DIR/source-a.png"
TMP_SPEC2="$TMP_DIR/source-b.png"
cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT HUP INT TERM

# generate separate high-resolution spectrograms and combine them as a difference image
echo "Generating spectrogram from '$(basename "$SOURCE1")'..."
if ! ffmpeg -y -loglevel error -i "$SOURCE1" -frames:v 1 -lavfi "showspectrumpic=s=$SPECTROGRAM_SIZE:color=rainbow" "$TMP_SPEC1" >/dev/null; then
    echo "Error: failed to create spectrogram from '$(basename "$SOURCE1")'." >&2
    exit 1
fi

echo "Generating spectrogram from '$(basename "$SOURCE2")'..."
if ! ffmpeg -y -loglevel error -i "$SOURCE2" -frames:v 1 -lavfi "showspectrumpic=s=$SPECTROGRAM_SIZE:color=rainbow" "$TMP_SPEC2" >/dev/null; then
    echo "Error: failed to create spectrogram from '$(basename "$SOURCE2")'." >&2
    exit 1
fi

echo "Generating difference spectrogram '$DESTINATION' from '$(basename "$SOURCE1")' and '$(basename "$SOURCE2")'..."
if ! ffmpeg -y -loglevel error -i "$TMP_SPEC1" -i "$TMP_SPEC2" -filter_complex "[0:v][1:v]blend=all_mode=difference" -frames:v 1 "$DESTINATION" >/dev/null; then
    echo "Error: failed to create spectrogram '$DESTINATION'." >&2
    exit 1
fi

echo "Done. Generated $DESTINATION."

