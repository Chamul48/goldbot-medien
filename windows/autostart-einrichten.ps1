# Richtet Goldbot als geplante Aufgabe ein (startet nach jeder Anmeldung, unabhängig
# von dem Programm, das sie gestartet hat) und
# erstellt die Desktop-Verknüpfungen.
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ws = New-Object -ComObject WScript.Shell
$desk = [Environment]::GetFolderPath('Desktop')
$startup = [Environment]::GetFolderPath('Startup')
$bat = Join-Path $root "windows\goldbot-starten.bat"

function New-Link($path, $target, $arguments = "", $icon = "") {
    $l = $ws.CreateShortcut($path); $l.TargetPath = $target; $l.Arguments = $arguments
    $l.WorkingDirectory = $root; if ($icon) { $l.IconLocation = $icon }; $l.Save()
}
# Autostart als geplante Aufgabe: läuft unabhängig vom aufrufenden Programm und
# zeigt das Fenster normal am Desktop. Fallback: Verknüpfung im Autostart-Ordner.
$taskOk = $false
try {
    $action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$bat`"" -WorkingDirectory $root
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew `
        -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    Register-ScheduledTask -TaskName "Goldbot" -Action $action -Trigger $trigger -Principal $principal `
        -Settings $settings -Description "Goldbot Dauerbetrieb" -Force -ErrorAction Stop | Out-Null
    $taskOk = $true
    Remove-Item (Join-Path $startup "Goldbot.lnk") -ErrorAction SilentlyContinue  # sonst doppelter Start
    Write-Host "Geplante Aufgabe 'Goldbot' eingerichtet."
} catch {
    Write-Host "Geplante Aufgabe nicht möglich ($($_.Exception.Message)) - nutze Autostart-Ordner." -ForegroundColor Yellow
    New-Link (Join-Path $startup "Goldbot.lnk") $bat "" "$env:SystemRoot\System32\shell32.dll,13"
}
New-Link (Join-Path $desk "Goldbot.lnk") $bat "" "$env:SystemRoot\System32\shell32.dll,13"
New-Link (Join-Path $desk "Goldbot Aufträge.lnk") (Join-Path $root "reports\auftraege")
New-Link (Join-Path $desk "Goldbot Berichte.lnk") (Join-Path $root "reports")
New-Link (Join-Path $desk "Goldbot aktualisieren.lnk") "powershell.exe" "-NoProfile -ExecutionPolicy Bypass -File `"$root\windows\aktualisieren.ps1`"" "$env:SystemRoot\System32\shell32.dll,238"
New-Link (Join-Path $desk "Goldbot KI-Key einrichten.lnk") "powershell.exe" "-NoProfile -ExecutionPolicy Bypass -File `"$root\windows\api-key-setzen.ps1`"" "$env:SystemRoot\System32\shell32.dll,47"
New-Link (Join-Path $desk "Goldbot Fiverr-Hilfe.lnk") (Join-Path $root ".venv\Scripts\pythonw.exe") "-m goldbot einfuegen" "$env:SystemRoot\System32\shell32.dll,134"
New-Link (Join-Path $desk "Goldbot Muster-Videos.lnk") (Join-Path $root "reports\muster")
Remove-Item (Join-Path $desk "Goldbot Auftraege.lnk") -ErrorAction SilentlyContinue  # alter Name ohne Umlaut
New-Item -ItemType Directory -Force (Join-Path $root "reports\auftraege"), (Join-Path $root "reports\muster") | Out-Null
Write-Host "Autostart und Desktop-Verknüpfungen eingerichtet."
