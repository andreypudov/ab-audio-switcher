#!/usr/bin/env sh

set -eu

# check parameters
if [ $# -ne 2 ]; then
    echo "Usage: $0 <source-file> <destination-spectrogram-file>" >&2
    exit 1
fi

SOURCE="$1"
DESTINATION="$2"

# check source file exists
if [ ! -f "$SOURCE" ]; then
    echo "Error: source file '$SOURCE' not found." >&2
    exit 1
fi

# generate a high-resolution spectrogram with ffmpeg
echo "Generating spectrogram '$DESTINATION' from '$SOURCE'..."
if ! ffmpeg -y -loglevel error -i "$SOURCE" -frames:v 1 -lavfi "showspectrumpic=s=3840x2160:color=rainbow" "$DESTINATION" >/dev/null; then
    echo "Error: failed to create spectrogram '$DESTINATION'." >&2
    exit 1
fi

echo "Done. Generated $DESTINATION."
