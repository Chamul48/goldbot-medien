# Legt Goldbot in den Windows-Autostart (startet nach jeder Anmeldung) und
# erstellt die Desktop-Verknuepfungen.
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ws = New-Object -ComObject WScript.Shell
$desk = [Environment]::GetFolderPath('Desktop')
$startup = [Environment]::GetFolderPath('Startup')
$bat = Join-Path $root "windows\goldbot-starten.bat"

function New-Link($path, $target, $arguments = "", $icon = "") {
    $l = $ws.CreateShortcut($path); $l.TargetPath = $target; $l.Arguments = $arguments
    $l.WorkingDirectory = $root; if ($icon) { $l.IconLocation = $icon }; $l.Save()
}
New-Link (Join-Path $startup "Goldbot.lnk") $bat "" "$env:SystemRoot\System32\shell32.dll,13"
New-Link (Join-Path $desk "Goldbot.lnk") $bat "" "$env:SystemRoot\System32\shell32.dll,13"
New-Link (Join-Path $desk "Goldbot Auftraege.lnk") (Join-Path $root "reports\auftraege")
New-Link (Join-Path $desk "Goldbot Berichte.lnk") (Join-Path $root "reports")
New-Link (Join-Path $desk "Goldbot aktualisieren.lnk") "powershell.exe" "-NoProfile -ExecutionPolicy Bypass -File `"$root\windows\aktualisieren.ps1`"" "$env:SystemRoot\System32\shell32.dll,238"
New-Link (Join-Path $desk "Goldbot KI-Key einrichten.lnk") "powershell.exe" "-NoProfile -ExecutionPolicy Bypass -File `"$root\windows\api-key-setzen.ps1`"" "$env:SystemRoot\System32\shell32.dll,47"
New-Item -ItemType Directory -Force (Join-Path $root "reports\auftraege") | Out-Null
Write-Host "Autostart und Desktop-Verknuepfungen eingerichtet."
