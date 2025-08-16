# yt-clip-thread

[![CI](https://github.com/gallup007/yt-clip-thread/actions/workflows/ci.yml/badge.svg)](https://github.com/gallup007/yt-clip-thread/actions)

Config-driven (or config-free!) CLI to turn a single YouTube video into a numbered thread of clips.

**Highlights**
- Paste **your YouTube URL** + **time ranges** and get clips — **no YAML required**
- Optional **labels** for filenames
- Optional **ranges file** (simple text, one range per line)
- Classic **YAML mode** for reproducible runs & PR review
- **Fast** keyframe cuts or **precise** re-encoded cuts
- Keeps projects separate with `--output-dir`

---

## Prereqs

- Python **3.9+**
- `ffmpeg` and `yt-dlp` on your PATH  
  macOS:
  ```bash
  brew install ffmpeg yt-dlp
