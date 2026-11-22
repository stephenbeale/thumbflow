# yt-thumbnail

Local, free replacement for the "export still → remove.bg → Canva" routine.

1. **Grab a frame** from your local video file at a timestamp (ffmpeg, full quality — better than a YT Studio still).
2. **Remove the background** with [rembg](https://github.com/danielgatis/rembg) — runs on your PC, no API key, no credits.
3. **Copy the transparent PNG to the clipboard**, select it in Explorer, and open Canva — just press **Ctrl+V** in your design.

## Usage

```powershell
C:\Users\sjbeale\source\repos\yt-thumbnail\thumb.ps1 "D:\Videos\my-video.mp4" -t 01:23
```

| Option | Meaning |
|---|---|
| `-t ...` | What to grab. Repeat for several candidates; the first goes on the clipboard. Omit to be prompted. See **Exact frames** below. |
| `-m birefnet-portrait` | Model. Default `isnet-general-use`; `birefnet-portrait` is usually best for people (~1 GB download); `u2net_human_seg` is a lighter people model. |
| `--alpha-matting` | Softer, cleaner hair/edges (slower). |
| `--canva-url <url>` | Open your thumbnail template's edit link instead of the Uploads page. |
| `-o <folder>` | Output folder (default `%USERPROFILE%\Pictures\Thumbnails\<date>_<video>`). |
| `--no-canva` | Just make the files. |

Output per grab: `frame_<frameNo>.png` (original) and `cutout_<frameNo>.png` (transparent).

## Exact frames

Every `-t` is resolved to one exact frame (the frame rate is read from the file, so 30 and 29.97 both work):

| You type | Means |
|---|---|
| `00:01:23:15` | Editor timecode `HH:MM:SS:FF` — copy it straight from Premiere/DaVinci/CapCut. Frame 15 of second 83. |
| `00:01:23;15` | Drop-frame timecode (29.97 projects whose timecode shows a `;`). |
| `2505f` | Frame number (0 = first frame). |
| `83` / `01:23` / `01:23.5` | A time — the first frame at or after it. |

The script prints the frame it took, e.g. `frame 2505 (00:01:23:15 @ 30.000fps)`, so you can step `2504f` / `2506f` if the shot is slightly blurred.
Phone footage is often variable frame rate; the script warns when it is, as frame numbers can then drift by a frame or two.

`test_frames.py` checks grabs pixel-for-pixel against ffmpeg's decode-and-count `select=eq(n,N)` at 30 and 29.97 fps.

## Notes

- First run of each model downloads it to `%USERPROFILE%\.rembg\models`.
- `truststore` is included because AVG's HTTPS scanning breaks Python's bundled certificates (model download fails with `CERTIFICATE_VERIFY_FAILED`).
