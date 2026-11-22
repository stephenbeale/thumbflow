"""Checks that frame grabs are exact and that timestamp parsing is right.

Run:  .venv\\Scripts\\python.exe test_frames.py
Builds short test videos (30 and 29.97 fps) where every frame differs, then
compares each grabbed frame pixel-for-pixel with ffmpeg's select=eq(n,N), which
decodes from the start and counts frames - the ground truth.
"""
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageChops

sys.path.insert(0, str(Path(__file__).parent))
from make_thumbnail import extract_frame, frame_label, probe_fps, resolve_frame  # noqa: E402

failures = 0


def check(name, got, want):
    global failures
    ok = got == want
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {name}: got {got}, want {want}")


def reference_frame(video, n, dest):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
                    "-vf", f"select=eq(n\\,{n})", "-fps_mode", "passthrough",
                    "-frames:v", "1", str(dest)], check=True)


def same_image(a, b):
    with Image.open(a) as x, Image.open(b) as y:
        return ImageChops.difference(x.convert("RGB"), y.convert("RGB")).getbbox() is None


# --- parsing (no video needed) ---
f30, f2997 = Fraction(30), Fraction(30000, 1001)
check("frame number", resolve_frame("2490f", f30), 2490)
check("seconds", resolve_frame("83", f30), 2490)
check("mm:ss", resolve_frame("01:23", f30), 2490)
check("time between frames rounds up", resolve_frame("0.01", f30), 1)
check("timecode 30fps", resolve_frame("00:01:23:15", f30), 2505)
check("timecode NDF 29.97", resolve_frame("00:01:00:00", f2997), 1800)
check("timecode DF 29.97 after 1 min", resolve_frame("00:01:00;02", f2997), 1800)
check("timecode DF 29.97 at 10 min", resolve_frame("00:10:00;00", f2997), 17982)
check("label", frame_label(2505, f30), "00:01:23:15")

# --- exact grabs against ground truth ---
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    for rate in ("30", "30000/1001"):
        video = tmp / f"v_{rate.replace('/', '_')}.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                        "-i", f"testsrc2=size=640x360:rate={rate}:duration=12",
                        "-c:v", "libx264", "-g", "60", str(video)], check=True)
        fps = probe_fps(video)
        for n in (0, 1, 29, 30, 31, 59, 60, 61, 299, 300, 301, 355):
            got, want = tmp / f"got_{n}.png", tmp / f"want_{n}.png"
            extract_frame(video, n, fps, got)
            reference_frame(video, n, want)
            check(f"{rate}fps frame {n} matches", same_image(got, want), True)
        # neighbouring frames really differ, so a match above means something
        reference_frame(video, 31, tmp / "n31.png")
        check(f"{rate}fps frames 30/31 differ", same_image(tmp / "want_30.png", tmp / "n31.png"), False)

print(f"\n{'ALL PASSED' if not failures else f'{failures} FAILED'}")
sys.exit(1 if failures else 0)
