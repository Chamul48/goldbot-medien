# Speichert einen Claude-API-Key lokal (Benutzer-Umgebungsvariable) - nur nach erfolgreicher Prüfung.
$Host.UI.RawUI.WindowTitle = "Goldbot - Claude API-Key einrichten"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Write-Host "Goldbot - Claude API-Key einrichten" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Öffne https://console.anthropic.com/settings/keys"
Write-Host "2. Unter 'Billing' Guthaben aufladen (z. B. 5 USD)"
Write-Host "3. 'Create Key' klicken und den Key kopieren (beginnt mit sk-ant-api)"
Write-Host "   Achtung: Die Konsole zeigt den Key nur EINMAL an."
Write-Host ""
Start-Process "https://console.anthropic.com/settings/keys"
$sec = Read-Host "Key hier einfügen (Rechtsklick) und Enter drücken" -AsSecureString
$key = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)).Trim()
if (-not $key.StartsWith("sk-ant-")) {
    Write-Host "Das sieht nicht wie ein Claude-Key aus (muss mit sk-ant- beginnen). Nichts gespeichert." -ForegroundColor Red
    Read-Host "Enter zum Schließen"; exit 1
}
Write-Host "Prüfe den Key ..."
$env:ANTHROPIC_API_KEY = $key
& (Join-Path $root ".venv\Scripts\python.exe") -c "import anthropic; anthropic.Anthropic().models.retrieve('claude-opus-5-5'); print('OK')"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Key wurde abgelehnt oder kein Guthaben. Nichts gespeichert." -ForegroundColor Red
    Read-Host "Enter zum Schließen"; exit 1
}
[Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", $key, "User")
Write-Host "Gespeichert. Goldbot nutzt ab jetzt Claude." -ForegroundColor Green
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*goldbot*dauer*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Get-CimInstance Win32_Process -Filter "Name='cmd.exe'" | Where-Object { $_.CommandLine -like '*goldbot-starten*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
if (Get-ScheduledTask -TaskName "Goldbot" -ErrorAction SilentlyContinue) { Start-ScheduledTask -TaskName "Goldbot" }
else { Start-Process -FilePath (Join-Path $root "windows\goldbot-starten.bat") -WorkingDirectory $root }
Read-Host "Goldbot neu gestartet. Enter zum Schließen"
