@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Holos - release
rem One click: check version tag -> push main + tag -> build installer -> upload to GitHub Releases
rem Before running: release branch merged into main and tag vX.Y.Z created (see CONTRIBUTING.md).
set NOPAUSE=1

for /f tokens^=2^ delims^=^" %%v in ('findstr /b /c:"VERSION = " app\common.py') do set "VER=%%v"
if not defined VER ( echo Cannot read VERSION from app\common.py & goto :fail )
findstr /c:"#define AppVersion \"%VER%\"" installer.iss >nul || ( echo installer.iss AppVersion is not %VER% & goto :fail )
git rev-parse -q --verify "refs/tags/v%VER%" >nul || ( echo Tag v%VER% not found. Create it after merging the release branch. & goto :fail )
git merge-base --is-ancestor "v%VER%" main || ( echo Tag v%VER% is not on main. & goto :fail )
echo === Releasing Holos %VER% ===

call "%~dp0publish.bat" || goto :fail
call "%~dp0build.bat" release || goto :fail
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0upload-release.ps1" || goto :fail
echo.
echo ============================================================
echo  RELEASE %VER% DONE: https://github.com/canadianproducer/holos/releases
echo ============================================================
pause
exit /b 0
:fail
echo.
echo RELEASE FAILED. Copy the text above and send it to Claude.
pause
exit /b 1
