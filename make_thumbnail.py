"""YouTube thumbnail prep: grab a frame from a local video, cut out the
background for free (rembg, runs locally), copy the transparent PNG to the
clipboard and open Canva so you can just press Ctrl+V.

Usage:
    python make_thumbnail.py VIDEO --time 01:23 [--time 02:10 ...]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import webbrowser
from datetime import datetime
from fractions import Fraction
from pathlib import Path

try:  # use the Windows certificate store (AVG's HTTPS scanning breaks Python's bundled certs)
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = Path.home() / "Pictures" / "Thumbnails"
DEFAULT_CANVA_URL = "https://www.canva.com/folder/uploads"
DEFAULT_MODEL = "isnet-general-use"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video", type=Path, help="Local video file (mp4, mov, mkv...)")
    p.add_argument("-t", "--time", action="append", dest="times",
                   help="What to grab: time (83, 01:23, 00:01:23.5), editor timecode "
                        "(00:01:23:15, ';' before frames = drop-frame) or frame number (2490f). "
                        "Repeat for several candidates.")
    p.add_argument("-o", "--out", type=Path, default=DEFAULT_OUT, help=f"Output folder (default {DEFAULT_OUT})")
    p.add_argument("-m", "--model", default=DEFAULT_MODEL,
                   help="rembg model: isnet-general-use (default), u2net, u2net_human_seg, "
                        "birefnet-portrait (best for people, large download), birefnet-general")
    p.add_argument("--alpha-matting", action="store_true", help="Softer, cleaner edges (slower)")
    p.add_argument("--canva-url", default=DEFAULT_CANVA_URL,
                   help="Page to open, e.g. your thumbnail template's edit link")
    p.add_argument("--no-canva", action="store_true", help="Don't copy to clipboard or open Canva")
    return p.parse_args(argv)


def probe_fps(video: Path) -> Fraction:
    """Frame rate of the first video stream, e.g. 30/1 or 30000/1001 (29.97)."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate,avg_frame_rate", "-of", "json", str(video)],
        capture_output=True, text=True, check=True).stdout
    stream = json.loads(out)["streams"][0]
    r, avg = Fraction(stream["r_frame_rate"]), Fraction(stream.get("avg_frame_rate") or "0/1")
    if avg and abs(float(r - avg)) > 0.01:
        print(f"  ! variable frame rate (nominal {float(r):.3f}, average {float(avg):.3f}) - "
              "typical of phone footage; frame numbers may be off by a frame or two")
    return r


def _seconds(text: str) -> float:
    """'83', '01:23', '00:01:23.5' -> seconds."""
    total = 0.0
    for part in text.split(":"):
        total = total * 60 + float(part)
    return total


def timecode_to_frame(tc: str, fps: Fraction) -> int:
    """'HH:MM:SS:FF' (non-drop) or 'HH:MM:SS;FF' (29.97/59.94 drop-frame) -> frame index."""
    drop = ";" in tc
    h, m, s, f = (int(x) for x in re.split(r"[:;]", tc))
    nominal = round(fps)  # timecode counts 30 frames/sec even at 29.97
    if f >= nominal:
        sys.exit(f"Timecode {tc}: frame field {f} must be below {nominal}")
    frame = ((h * 60 + m) * 60 + s) * nominal + f
    if drop:  # skip 2 (or 4 at 59.94) frame numbers every minute except every 10th
        dropped = round(nominal / 15)
        minutes = h * 60 + m
        frame -= dropped * (minutes - minutes // 10)
    return frame


def resolve_frame(spec: str, fps: Fraction) -> int:
    """Turn a -t value into an exact frame index (0 = first frame).

    '2490f'          -> frame 2490
    '00:01:23:15'    -> editor timecode (HH:MM:SS:FF); ';' before FF = drop-frame
    '83', '01:23.5'  -> time; the first frame at or after it
    """
    spec = spec.strip()
    if re.fullmatch(r"\d+f", spec, re.IGNORECASE):
        return int(spec[:-1])
    if re.fullmatch(r"\d+:\d+:\d+[:;]\d+", spec):
        return timecode_to_frame(spec, fps)
    if re.fullmatch(r"[\d:.]+", spec):
        return math.ceil(round(_seconds(spec) * fps, 6))
    sys.exit(f"Don't understand timestamp '{spec}' (use 83, 01:23, 00:01:23:15 or 2490f)")


def frame_label(frame: int, fps: Fraction) -> str:
    """Frame index -> 'HH:MM:SS:FF' (non-drop, nominal rate) for display."""
    nominal = round(fps)
    secs, ff = divmod(frame, nominal)
    return f"{secs // 3600:02d}:{secs // 60 % 60:02d}:{secs % 60:02d}:{ff:02d}"


def extract_frame(video: Path, frame: int, fps: Fraction, dest: Path) -> None:
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found on PATH")
    # Frame N starts at N/fps. ffmpeg's accurate seek outputs the first frame whose
    # time is >= -ss, so aiming half a frame early lands exactly on frame N and is
    # immune to rounding in the container's timestamps.
    seek = max(0.0, float((frame - Fraction(1, 2)) / fps))
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-ss", f"{seek:.6f}", "-i", str(video), "-frames:v", "1", "-update", "1", str(dest)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not dest.exists():
        sys.exit(f"ffmpeg failed to grab frame {frame}: "
                 f"{result.stderr.strip() or 'no output (past the end of the video?)'}")


def remove_background(src: Path, dest: Path, session, alpha_matting: bool) -> None:
    from PIL import Image
    from rembg import remove

    with Image.open(src) as img:
        cut = remove(img, session=session, alpha_matting=alpha_matting)
    cut.save(dest)


def copy_to_clipboard(png: Path) -> bool:
    helper = HERE / "copy_png_to_clipboard.ps1"
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-STA", "-File", str(helper), str(png)],
        capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ! clipboard copy failed: {result.stderr.strip()}")
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    video: Path = args.video.expanduser().resolve()
    if not video.is_file():
        sys.exit(f"Video not found: {video}")

    times = args.times or [input("Time, timecode or frame to grab (e.g. 01:23, 00:01:23:15, 2490f): ").strip()]
    times = [t for t in times if t]
    if not times:
        sys.exit("No timestamp given")

    out_dir: Path = args.out / f"{datetime.now():%Y-%m-%d}_{video.stem}"
    out_dir.mkdir(parents=True, exist_ok=True)

    fps = probe_fps(video)
    frames = [(ts, resolve_frame(ts, fps)) for ts in times]

    from rembg import new_session
    print(f"Loading background-removal model '{args.model}' (first run downloads it)...")
    session = new_session(args.model)

    cutouts: list[Path] = []
    for ts, n in frames:
        frame = out_dir / f"frame_{n:06d}.png"
        cutout = out_dir / f"cutout_{n:06d}.png"
        print(f"[{ts}] frame {n} ({frame_label(n, fps)} @ {float(fps):.3f}fps) -> {frame}")
        extract_frame(video, n, fps, frame)
        print(f"[{ts}] removing background -> {cutout}")
        remove_background(frame, cutout, session, args.alpha_matting)
        cutouts.append(cutout)

    print(f"\nDone. Files in {out_dir}")
    if args.no_canva:
        return 0

    # Clipboard holds one image: the first cut-out. Others are in the folder.
    if copy_to_clipboard(cutouts[0]):
        print(f"Copied {cutouts[0].name} to the clipboard - press Ctrl+V in Canva.")
    subprocess.run(["explorer", f"/select,{cutouts[0]}"])  # drag-and-drop fallback
    webbrowser.open(args.canva_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
