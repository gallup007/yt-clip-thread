#!/usr/bin/env python3
import argparse, subprocess, sys, yaml, pathlib, re, os, shlex

def to_hms(s: str) -> str:
    s = s.strip()
    parts = [int(p) for p in s.split(":")]
    if len(parts) == 2:
        h, m, sec = 0, parts[0], parts[1]
    elif len(parts) == 3:
        h, m, sec = parts
    else:
        raise ValueError(f"Bad timecode: {s} (use MM:SS or HH:MM:SS)")
    return f"{h:02d}:{m:02d}:{sec:02d}"

def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9\-]+", "-", str(s).lower()).strip("-")

def run(cmd):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)

def ensure_video(url: str, outdir: pathlib.Path) -> pathlib.Path:
    outdir.mkdir(parents=True, exist_ok=True)
    tmpl = str(outdir / "source.%(ext)s")

    cmd = [
        "yt-dlp", url,
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        "--merge-output-format", "mp4",
        "-o", tmpl
    ]

    # Optional extras via environment
    extra = os.environ.get("YT_DLP_OPTS", "")
    if extra:
        cmd += shlex.split(extra)

    cookies = os.environ.get("YT_DLP_COOKIES") or os.environ.get("YT_COOKIES_FILE")
    if cookies:
        cmd += ["--cookies", cookies]

    run(cmd)

    mp4s = sorted(outdir.glob("source*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not mp4s:
        raise FileNotFoundError("No MP4 found after download.")
    return mp4s[0]


def clip(input_path: pathlib.Path, start: str, end: str, out_path: pathlib.Path, accurate: bool):
    start_hms, end_hms = to_hms(start), to_hms(end)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if accurate:
        cmd = [
            "ffmpeg","-y","-ss",start_hms,"-to",end_hms,"-i",str(input_path),
            "-c:v","libx264","-preset","veryfast","-crf","18",
            "-c:a","aac","-movflags","+faststart",str(out_path)
        ]
    else:
        cmd = ["ffmpeg","-y","-ss",start_hms,"-to",end_hms,"-i",str(input_path),"-c","copy",str(out_path)]
    run(cmd)

def parse_ranges(ranges_str: str):
    pieces = [r.strip() for r in ranges_str.split(";") if r.strip()]
    ranges = []
    for r in pieces:
        if "-" not in r:
            raise SystemExit(f"Bad range: {r} (expected START-END)")
        s, e = [x.strip() for x in r.split("-", 1)]
        ranges.append((s, e))
    return ranges

def parse_labels(labels_str: str, n: int):
    labels = [slug(x.strip()) for x in labels_str.split(";")] if labels_str else []
    # Pad or trim to match count
    out = []
    for i in range(n):
        out.append(labels[i] if i < len(labels) and labels[i] else f"clip-{i+1}")
    return out

def load_ranges_file(path: pathlib.Path):
    """
    Each non-empty, non-# line:
      START-END [optional label words...]
    Example:
      00:01:23-00:02:10 intro-hook
      05:32-06:20 killer-stat
    """
    lines = path.read_text().splitlines()
    items = []
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        # Split on whitespace once after START-END
        m = re.match(r"^(\S+)\s*-\s*(\S+)(?:\s+(.+))?$", ln)
        if not m:
            raise SystemExit(f"Bad line in {path}: {ln}\nExpected: START-END [label]")
        start, end, label = m.group(1), m.group(2), m.group(3) or None
        items.append((start, end, label))
    return items

def main():
    ap = argparse.ArgumentParser(description="Clip tweet-length segments from one YouTube video.")
    ap.add_argument("-c","--config", default="segments.yaml", help="YAML config (ignored if --url/--ranges or --ranges-file are given)")
    ap.add_argument("--url", help="YouTube URL (no-YAML mode)")
    ap.add_argument("--ranges", help='Semicolon-separated ranges: "MM:SS-MM:SS;MM:SS-MM:SS;..."')
    ap.add_argument("--labels", help='Semicolon-separated labels matching --ranges (optional)')
    ap.add_argument("--ranges-file", help='Path to text file: each line "START-END [label]"')
    ap.add_argument("--output-dir", help="Directory for output + source.mp4 (defaults to 'clips' or YAML's output_dir)")
    ap.add_argument("--input", help="Path to a pre-downloaded video (skip yt-dlp)")
    ap.add_argument("--fast", action="store_true", help="Use stream copy (faster, keyframe-bound)")
    args = ap.parse_args()

    # Build config from CLI one-liner
    if args.url and (args.ranges or args.ranges_file):
        segments = []
        if args.ranges_file:
            items = load_ranges_file(pathlib.Path(args.ranges_file))
            for i, (s, e, lbl) in enumerate(items, 1):
                segments.append({"tweet": i, "label": slug(lbl or f"clip-{i}"), "start": to_hms(s), "end": to_hms(e)})
        else:
            pairs = parse_ranges(args.ranges)
            labels = parse_labels(args.labels, len(pairs))
            for i, ((s, e), lbl) in enumerate(zip(pairs, labels), 1):
                segments.append({"tweet": i, "label": lbl, "start": to_hms(s), "end": to_hms(e)})

        cfg = {"url": args.url, "output_dir": args.output_dir or "clips", "segments": segments}

    else:
        # YAML mode
        with open(args.config, "r") as f:
            cfg = yaml.safe_load(f)

    url = cfg["url"]
    outdir = pathlib.Path(args.output_dir or cfg.get("output_dir","clips"))
    segments = cfg["segments"]
    input_path = pathlib.Path(args.input) if args.input else ensure_video(url, outdir)

    for seg in segments:
        t = int(seg["tweet"])
        label = slug(seg.get("label", f"clip-{t}"))
        start, end = seg["start"], seg["end"]
        out_name = f"{t:02d}_{label}_{start.replace(':','-')}_{end.replace(':','-')}.mp4"
        clip(input_path, start, end, outdir / out_name, accurate=not args.fast)

    print("Done →", outdir.resolve())

if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
