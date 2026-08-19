@echo off
title AfriHealth — Stop All
echo Stopping AfriHealth Assistant...
taskkill /FI "WINDOWTITLE eq AfriHealth Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq AfriHealth Frontend*" /F >nul 2>&1
echo Done. All AfriHealth processes stopped.
pause
