# Goldbot aktualisieren: lädt die neueste Version von GitHub und behält
# deine config.yaml, deine Berichte und die Python-Umgebung.
param([string]$Branch = "main")
$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "Goldbot aktualisieren"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
# Eigener Ordner pro Lauf: ein abgebrochener Lauf darf den nächsten nicht blockieren
$tmp = Join-Path $env:TEMP ("goldbot-update-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
Get-ChildItem $env:TEMP -Directory -Filter "goldbot-update*" -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddHours(-1) } |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

function Stop-Goldbot {
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -like '*goldbot*dauer*' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Get-CimInstance Win32_Process -Filter "Name='cmd.exe'" |
        Where-Object { $_.CommandLine -like '*goldbot-starten*' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}

function Get-Source($name) {
    $folder = Join-Path $tmp ($name -replace '[/\\]', '_')
    $zip = "$folder.zip"
    Invoke-WebRequest -UseBasicParsing "https://codeload.github.com/chamul48/goldbot-medien/zip/refs/heads/$name" -OutFile $zip
    Expand-Archive $zip -DestinationPath $folder -Force
    $dir = Get-ChildItem $folder -Directory | Select-Object -First 1
    if ($dir -and (Test-Path (Join-Path $dir.FullName "goldbot\leads.py"))) { return $dir.FullName }
    return $null
}

try {
    New-Item -ItemType Directory -Force $tmp | Out-Null

    Write-Host "Lade neueste Version ($Branch) ..."
    $src = $null
    try { $src = Get-Source $Branch } catch { }
    if (-not $src) {
        Write-Host "Auf '$Branch' noch nicht vorhanden - nehme den Entwicklungs-Branch."
        $src = Get-Source "claude/automated-profile-sales-bot-8lab1g"
    }
    if (-not $src) { throw "Download fehlgeschlagen oder unvollständig." }

    # Vergleich VOR dem Kopieren: wurde config.yaml selbst geändert?
    $userCfg = Join-Path $root "config.yaml"
    $oldExample = Join-Path $root "config.example.yaml"
    $cfgUntouched = (Test-Path $userCfg) -and (Test-Path $oldExample) -and `
        ((Get-FileHash $userCfg).Hash -eq (Get-FileHash $oldExample).Hash)

    Write-Host "Stoppe Goldbot ..."
    Stop-Goldbot
    Start-Sleep 1

    foreach ($item in "goldbot", "docs", "tests", "windows") {
        $from = Join-Path $src $item
        if (Test-Path $from) {
            # Inhalt kopieren (nicht den Ordner in den Ordner)
            New-Item -ItemType Directory -Force (Join-Path $root $item) | Out-Null
            Copy-Item (Join-Path $from "*") (Join-Path $root $item) -Recurse -Force
        }
    }
    foreach ($file in "requirements.txt", "config.example.yaml", "README.md") {
        $from = Join-Path $src $file
        if (Test-Path $from) { Copy-Item $from (Join-Path $root $file) -Force }
    }
    if ($cfgUntouched -or -not (Test-Path $userCfg)) {
        Copy-Item $oldExample $userCfg -Force
        Write-Host "config.yaml aktualisiert."
    } else {
        Write-Host "config.yaml hast du geändert - bleibt wie sie ist. Neue Optionen stehen in config.example.yaml." -ForegroundColor Yellow
    }

    Write-Host "Prüfe Python-Pakete ..."
    & (Join-Path $root ".venv\Scripts\python.exe") -m pip install -q --disable-pip-version-check -r (Join-Path $root "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "pip install ist fehlgeschlagen." }

    Write-Host "Starte Goldbot ..."
    # Über die geplante Aufgabe starten, falls vorhanden: dann läuft Goldbot unabhängig
    # von diesem Fenster weiter.
    if (Get-ScheduledTask -TaskName "Goldbot" -ErrorAction SilentlyContinue) {
        Start-ScheduledTask -TaskName "Goldbot"
    } else {
        Start-Process -FilePath (Join-Path $root "windows\goldbot-starten.bat") -WorkingDirectory $root
    }
    Write-Host "Fertig." -ForegroundColor Green
    Start-Sleep 3
} catch {
    Write-Host ""
    Write-Host "Update fehlgeschlagen: $_" -ForegroundColor Red
    Write-Host "Goldbot wurde nicht verändert oder läuft mit der alten Version weiter."
    if ([Environment]::UserInteractive -and -not [Console]::IsInputRedirected) { Read-Host "Enter zum Schließen" }
    exit 1
} finally {
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
}
