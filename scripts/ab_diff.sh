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

# check source files exist
for source in "$SOURCE1" "$SOURCE2"; do
    if [ ! -f "$source" ]; then
        echo "Error: source file '$source' not found." >&2
        exit 1
    fi
done

TMP_AUDIO="${TMPDIR:-/tmp}/ab-compare-$$.wav"
cleanup() {
    rm -f "$TMP_AUDIO"
}
trap cleanup EXIT HUP INT TERM

# generate a high-resolution comparison spectrogram with ffmpeg
echo "Generating comparison spectrogram '$DESTINATION' from '$SOURCE1' and '$SOURCE2'..."
if ! ffmpeg -y -loglevel error -i "$SOURCE1" -i "$SOURCE2" -filter_complex "[0:a][1:a]amerge=inputs=2" -vn -f wav "$TMP_AUDIO" >/dev/null; then
    echo "Error: failed to create comparison audio." >&2
    exit 1
fi

if ! ffmpeg -y -loglevel error -i "$TMP_AUDIO" -frames:v 1 -lavfi "showspectrumpic=s=3840x2160:color=rainbow" "$DESTINATION" >/dev/null; then
    echo "Error: failed to create spectrogram '$DESTINATION'." >&2
    exit 1
fi

echo "Done. Generated $DESTINATION."

