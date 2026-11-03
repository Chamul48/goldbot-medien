@echo off
chcp 65001 >nul
title Goldbot - Dauerbetrieb (Fenster schließen = beenden)
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
echo Goldbot startet. Neue Aufträge: reports\auftraege\  -  Berichte: reports\
echo.
".venv\Scripts\python.exe" -m goldbot dauer
if errorlevel 2 if not errorlevel 3 (
  echo.
  echo Goldbot läuft bereits in einem anderen Fenster. Dieses Fenster schließt sich.
  timeout /t 8 >nul
  exit /b
)
pause
