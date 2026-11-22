# thumbflow

Make YouTube thumbnails from your existing videos, then finish the job in Canva.
A local, free replacement for the "export still → remove.bg → Canva" routine.

1. **Grab a frame** from your local video file at an exact frame/timecode (ffmpeg, full quality — better than a YT Studio still).
2. **Remove the background** with [rembg](https://github.com/danielgatis/rembg) — runs on your PC, no API key, no credits.
3. **Copy the transparent PNG to the clipboard**, select it in Explorer, and open Canva — just press **Ctrl+V** in your design.

## Requirements

- Windows (clipboard and Explorer steps are Windows-only)
- Python 3.10+ and [ffmpeg](https://ffmpeg.org/) (with `ffprobe`) on your PATH

The first run of `thumb.ps1` creates a `.venv` and installs `requirements.txt` automatically.

## Usage

```powershell
.\thumb.ps1 "D:\Videos\my-video.mp4" -t 00:01:23:15
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

## Your Canva template

Copy `thumbflow.config.example.json` to `thumbflow.config.json` (git-ignored — design links act as keys, so keep them out of the repo) and set `canva_url`.

- **Best: a Template link.** In Canva open your thumbnail design → **Share → More → Template link** → copy. Opening it creates a *fresh copy* every time, so your template stays untouched.
- An `.../edit` link also works, but opens the original — the script reminds you to do **File → Make a copy** before pasting.

`--canva-url <url>` overrides the config for one run.

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

## Tests

```powershell
.\.venv\Scripts\python.exe test_frames.py
```

Checks frame grabs pixel-for-pixel against ffmpeg's decode-and-count `select=eq(n,N)` at 30 and 29.97 fps, plus timecode parsing.

## Notes

- First run of each model downloads it to `%USERPROFILE%\.rembg\models`.
- `truststore` makes Python use the Windows certificate store, so the model download works behind antivirus HTTPS scanning (which otherwise fails with `CERTIFICATE_VERIFY_FAILED`).
