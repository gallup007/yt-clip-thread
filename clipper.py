#!/usr/bin/env python3
import argparse, subprocess, sys, yaml, pathlib, re

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
    run([
        "yt-dlp", url,
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        "--merge-output-format", "mp4",
        "-o", tmpl
    ])
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

def main():
    ap = argparse.ArgumentParser(description="Clip tweet-length segments from one YouTube video.")
    ap.add_argument("-c","--config", default="segments.yaml", help="YAML config (ignored if --url and --ranges are given)")
    ap.add_argument("--url", help="YouTube URL (no-YAML mode)")
    ap.add_argument("--ranges", help='Semicolon-separated ranges: "MM:SS-MM:SS;MM:SS-MM:SS;..."')
    ap.add_argument("--input", help="Path to a pre-downloaded video (skip yt-dlp)")
    ap.add_argument("--fast", action="store_true", help="Use stream copy (faster, keyframe-bound)")
    ap.add_argument("--output-dir", help="Directory for output + source.mp4 (defaults to 'clips' or YAML's output_dir)")
    args = ap.parse_args()

    if args.url and args.ranges:
        pieces = [r.strip() for r in args.ranges.split(";") if r.strip()]
        segments = []
        for i, r in enumerate(pieces, 1):
            if "-" not in r:
                raise SystemExit(f"Bad range: {r} (expected START-END)")
            s, e = [x.strip() for x in r.split("-", 1)]
            segments.append({"tweet": i, "label": f"clip-{i}", "start": to_hms(s), "end": to_hms(e)})
        cfg = {"url": args.url, "output_dir": args.output_dir or "clips", "segments": segments}
    else:
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
