@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Holos - release
rem One click: publish code -> build installer -> upload to GitHub Releases
set NOPAUSE=1
call "%~dp0publish.bat" || goto :fail
call "%~dp0build.bat" release || goto :fail
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0upload-release.ps1" || goto :fail
echo.
echo ============================================================
echo  RELEASE DONE: https://github.com/canadianproducer/holos/releases
echo ============================================================
pause
exit /b 0
:fail
echo.
echo RELEASE FAILED. Copy the text above and send it to Claude.
pause
exit /b 1
