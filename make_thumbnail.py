"""YouTube thumbnail prep: grab a frame from a local video, cut out the
background for free (rembg, runs locally), copy the transparent PNG to the
clipboard and open Canva so you can just press Ctrl+V.

Usage:
    python make_thumbnail.py VIDEO --time 01:23 [--time 02:10 ...]
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import webbrowser
from datetime import datetime
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
                   help="Timestamp to grab, e.g. 83, 01:23 or 00:01:23.5. Repeat for several candidates.")
    p.add_argument("-o", "--out", type=Path, default=DEFAULT_OUT, help=f"Output folder (default {DEFAULT_OUT})")
    p.add_argument("-m", "--model", default=DEFAULT_MODEL,
                   help="rembg model: isnet-general-use (default), u2net, u2net_human_seg, "
                        "birefnet-portrait (best for people, large download), birefnet-general")
    p.add_argument("--alpha-matting", action="store_true", help="Softer, cleaner edges (slower)")
    p.add_argument("--canva-url", default=DEFAULT_CANVA_URL,
                   help="Page to open, e.g. your thumbnail template's edit link")
    p.add_argument("--no-canva", action="store_true", help="Don't copy to clipboard or open Canva")
    return p.parse_args(argv)


def safe_stamp(ts: str) -> str:
    return ts.replace(":", "-").replace(".", "_")


def extract_frame(video: Path, ts: str, dest: Path) -> None:
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found on PATH")
    # -ss after -i = frame-accurate seek (slower on long files, but exact)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-i", str(video), "-ss", ts, "-frames:v", "1", str(dest)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not dest.exists():
        sys.exit(f"ffmpeg failed to grab frame at {ts}: {result.stderr.strip() or 'no output (timestamp past end?)'}")


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

    times = args.times or [input("Timestamp to grab (e.g. 01:23): ").strip()]
    times = [t for t in times if t]
    if not times:
        sys.exit("No timestamp given")

    out_dir: Path = args.out / f"{datetime.now():%Y-%m-%d}_{video.stem}"
    out_dir.mkdir(parents=True, exist_ok=True)

    from rembg import new_session
    print(f"Loading background-removal model '{args.model}' (first run downloads it)...")
    session = new_session(args.model)

    cutouts: list[Path] = []
    for ts in times:
        frame = out_dir / f"frame_{safe_stamp(ts)}.png"
        cutout = out_dir / f"cutout_{safe_stamp(ts)}.png"
        print(f"[{ts}] grabbing frame -> {frame}")
        extract_frame(video, ts, frame)
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
