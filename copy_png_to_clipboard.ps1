param([Parameter(Mandatory)][string]$Path)
# Puts a PNG on the clipboard twice: as raw "PNG" data (keeps transparency;
# browsers/Canva read this) and as a normal bitmap (fallback for other apps).
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms, System.Drawing

$bytes = [System.IO.File]::ReadAllBytes((Resolve-Path $Path))
$pngStream = New-Object System.IO.MemoryStream(, $bytes)
$bitmap = [System.Drawing.Image]::FromStream((New-Object System.IO.MemoryStream(, $bytes)))

$data = New-Object System.Windows.Forms.DataObject
$data.SetData('PNG', $false, $pngStream)
$data.SetImage($bitmap)
[System.Windows.Forms.Clipboard]::SetDataObject($data, $true)
