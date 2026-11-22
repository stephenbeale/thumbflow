# Wrapper: runs make_thumbnail.py with the repo's own virtualenv.
#   .\thumb.ps1 "D:\Videos\my-video.mp4" -t 01:23
#   .\thumb.ps1 "D:\Videos\my-video.mp4" -t 01:23 -t 04:10 -m birefnet-portrait
$py = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
    Write-Host 'First run: creating virtualenv and installing rembg...'
    python -m venv (Join-Path $PSScriptRoot '.venv')
    & $py -m pip install -q -r (Join-Path $PSScriptRoot 'requirements.txt')
}
& $py (Join-Path $PSScriptRoot 'make_thumbnail.py') @args
exit $LASTEXITCODE
