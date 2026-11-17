@echo off
chcp 65001 >nul
cd /d "%~dp0"
if "%~1"=="" (
  echo Ziehe ein Foto von dir auf diese Datei, dann entsteht dein Fiverr-Profilbild.
  pause
  exit /b 2
)
if not exist ".venv\Scripts\python.exe" (
  echo Einmalige Einrichtung, dauert ein paar Minuten ...
  py -3 -m venv .venv || python -m venv .venv
  ".venv\Scripts\python.exe" -m pip install -q "rembg[cpu]" "opencv-python-headless<5"
)
".venv\Scripts\python.exe" profilbild.py "%~1"
if not errorlevel 1 start "" "%~dpn1_fiverr_vorschau.png"
pause
