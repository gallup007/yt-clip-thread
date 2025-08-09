#!/usr/bin/env bash
set -euo pipefail

# Show versions (module form avoids PATH issues on GitHub runners)
python --version
ffmpeg -version | head -n1
python -m yt_dlp --version || true

# Make a tiny local source (no network)
rm -rf ci-clips ci-source.mp4 ci.yaml
ffmpeg -y -f lavfi -i color=size=640x360:rate=30:color=black \
       -f lavfi -i sine=frequency=1000:sample_rate=44100 \
       -t 12 -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p \
       -c:a aac ci-source.mp4

# Config for two short clips
cat > ci.yaml <<'YML'
url: "https://example.com/not-used-with-input"
output_dir: "ci-clips"
segments:
  - tweet: 1
    label: "first"
    start: "00:00:02"
    end:   "00:00:05"
  - tweet: 2
    label: "second"
    start: "00:00:06"
    end:   "00:00:10"
YML

# Run the tool and assert outputs
python clipper.py --input ci-source.mp4 --fast -c ci.yaml
test -f ci-clips/01_first_00-00-02_00-00-05.mp4
test -f ci-clips/02_second_00-00-06_00-00-10.mp4
echo "Self-test passed."
