@echo off
chcp 65001 >nul
rem Upload dist\Holos-Setup-<version>.exe to GitHub Releases
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0upload-release.ps1"
pause
