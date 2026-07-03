#!/usr/bin/env sh

set -eu

# check parameters
if [ $# -ne 3 ]; then
    echo "Usage: $0 <source-file> <destination-file> <bitrate>" >&2
    exit 1
fi

SOURCE="$1"
DESTINATION="$2"
BITRATE="$3"

# check source file exists
if [ ! -f "$SOURCE" ]; then
    echo "Error: source file '$SOURCE' not found." >&2
    exit 1
fi

# convert source to destination with requested bitrate
echo "Converting '$SOURCE' to '$DESTINATION' at bitrate $BITRATE..."
if ! ffmpeg -y -loglevel error -i "$SOURCE" -b:a "$BITRATE" "$DESTINATION" >/dev/null; then
    echo "Error: failed to create destination file '$DESTINATION'." >&2
    exit 1
fi

echo "Done. Generated $DESTINATION."
