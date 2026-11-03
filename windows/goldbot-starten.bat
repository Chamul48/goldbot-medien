@echo off
chcp 65001 >nul
title Goldbot - Dauerbetrieb (Fenster schliessen = beenden)
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
echo Goldbot startet. Neue Auftraege: reports\auftraege\  -  Berichte: reports\
echo.
".venv\Scripts\python.exe" -m goldbot dauer
pause
