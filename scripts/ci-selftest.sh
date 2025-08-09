#!/usr/bin/env bash
set -euo pipefail
python --version
ffmpeg -version | head -n1
yt-dlp --version

rm -rf ci-clips ci-source.mp4 ci.yaml
ffmpeg -y -f lavfi -i color=size=640x360:rate=30:color=black \
       -f lavfi -i sine=frequency=1000:sample_rate=44100 \
       -t 12 -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p \
       -c:a aac ci-source.mp4

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

python clipper.py --input ci-source.mp4 --fast -c ci.yaml
test -f ci-clips/01_first_00-00-02_00-00-05.mp4
test -f ci-clips/02_second_00-00-06_00-00-10.mp4
echo "Self-test passed."
