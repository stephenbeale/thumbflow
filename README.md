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
| `-t 01:23` | Timestamp (`83`, `01:23`, `00:01:23.5`). Repeat for several candidates; the first goes on the clipboard. Omit to be prompted. |
| `-m birefnet-portrait` | Model. Default `isnet-general-use`; `birefnet-portrait` is usually best for people (~1 GB download); `u2net_human_seg` is a lighter people model. |
| `--alpha-matting` | Softer, cleaner hair/edges (slower). |
| `--canva-url <url>` | Open your thumbnail template's edit link instead of the Uploads page. |
| `-o <folder>` | Output folder (default `%USERPROFILE%\Pictures\Thumbnails\<date>_<video>`). |
| `--no-canva` | Just make the files. |

Output per timestamp: `frame_<ts>.png` (original) and `cutout_<ts>.png` (transparent).

## Notes

- First run of each model downloads it to `%USERPROFILE%\.rembg\models`.
- `truststore` is included because AVG's HTTPS scanning breaks Python's bundled certificates (model download fails with `CERTIFICATE_VERIFY_FAILED`).
