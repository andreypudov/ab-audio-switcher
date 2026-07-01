#!/bin/sh

# ------------------------------------------------------------
# Check parameters
# ------------------------------------------------------------
if [ $# -ne 2 ]; then
    echo "Usage: $0 <source-file> <bitrate>"
    exit 1
fi

SRC="$1"
BITRATE="$2"

# Check source file exists
if [ ! -f "$SRC" ]; then
    echo "Error: source file '$SRC' not found."
    exit 1
fi

# ------------------------------------------------------------
# Step 1: FLAC → WAV (reference)
# ------------------------------------------------------------
echo "Creating A.wav (decoded FLAC)..."
ffmpeg -y -i "$SRC" -c:a pcm_f32le A.wav

# ------------------------------------------------------------
# Step 2: FLAC → MP3 (lossy)
# ------------------------------------------------------------
echo "Creating MP3 at bitrate $BITRATE..."
ffmpeg -y -i "$SRC" -b:a "$BITRATE" source.mp3

# ------------------------------------------------------------
# Step 3: MP3 → WAV (decoded lossy)
# ------------------------------------------------------------
echo "Creating B.wav (decoded MP3)..."
ffmpeg -y -i source.mp3 -c:a pcm_f32le B.wav

echo "Done. Generated A.wav and B.wav."
