@echo off
chcp 65001 >nul
title Goldbot - Dauerbetrieb (Fenster schließen = beenden)
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
echo Goldbot startet. Neue Aufträge: reports\auftraege\  -  Berichte: reports\  -  Protokoll: reports\goldbot.log
echo.
:start
".venv\Scripts\python.exe" -m goldbot dauer
set rc=%errorlevel%
if "%rc%"=="2" (
  echo.
  echo Goldbot läuft bereits in einem anderen Fenster. Dieses Fenster schließt sich.
  timeout /t 8 >nul
  exit /b
)
if "%rc%"=="0" exit /b
echo.
echo Goldbot wurde unerwartet beendet (Code %rc%). Neustart in 60 Sekunden ...
echo Fenster schließen, um Goldbot ganz zu beenden.
timeout /t 60 >nul
goto start
