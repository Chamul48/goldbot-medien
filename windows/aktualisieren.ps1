# Goldbot aktualisieren: lädt die neueste Version von GitHub und behält
# deine config.yaml, deine Berichte und die Python-Umgebung.
param([string]$Branch = "main")
$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "Goldbot aktualisieren"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$tmp = Join-Path $env:TEMP "goldbot-update"
Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory $tmp | Out-Null

function Get-Branch($name) {
    $zip = Join-Path $tmp "src.zip"
    $url = "https://codeload.github.com/chamul48/goldbot-medien/zip/refs/heads/$name"
    Invoke-WebRequest -UseBasicParsing $url -OutFile $zip
    Expand-Archive $zip -DestinationPath (Join-Path $tmp $name.Replace('/', '_')) -Force
    $dir = Get-ChildItem (Join-Path $tmp $name.Replace('/', '_')) -Directory | Select-Object -First 1
    if (Test-Path (Join-Path $dir.FullName "goldbot\leads.py")) { return $dir.FullName }
    return $null
}

Write-Host "Lade neueste Version ($Branch) ..."
$src = $null
try { $src = Get-Branch $Branch } catch { }
if (-not $src) {
    Write-Host "Auf '$Branch' noch nicht vorhanden - nehme den Entwicklungs-Branch."
    $src = Get-Branch "claude/automated-profile-sales-bot-8lab1g"
}

$userCfg = Join-Path $root "config.yaml"
$oldExample = Join-Path $root "config.example.yaml"
$cfgUntouched = (Test-Path $userCfg) -and (Test-Path $oldExample) -and `
    ((Get-FileHash $userCfg).Hash -eq (Get-FileHash $oldExample).Hash)

foreach ($item in "goldbot", "docs", "tests", "windows", "requirements.txt", "config.example.yaml", "README.md") {
    $from = Join-Path $src $item
    if (Test-Path $from) { Copy-Item $from $root -Recurse -Force }
}
if ($cfgUntouched -or -not (Test-Path $userCfg)) {
    Copy-Item $oldExample $userCfg -Force
    Write-Host "config.yaml aktualisiert."
} else {
    Write-Host "config.yaml hast du geaendert - bleibt wie sie ist. Neue Optionen siehst du in config.example.yaml." -ForegroundColor Yellow
}

Write-Host "Pruefe Python-Pakete ..."
& (Join-Path $root ".venv\Scripts\python.exe") -m pip install -q -r (Join-Path $root "requirements.txt")
Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Starte Goldbot neu ..."
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*goldbot*dauer*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Get-Process cmd -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like 'Goldbot*' } | Stop-Process -Force
Start-Process -FilePath (Join-Path $root "windows\goldbot-starten.bat") -WorkingDirectory $root
Write-Host "Fertig." -ForegroundColor Green
Start-Sleep 3
