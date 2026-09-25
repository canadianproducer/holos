@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Holos - release
rem Publishes a release: checks, then pushes main and tag vX.Y.Z to GitHub.
rem GitHub Actions (.github/workflows/release.yml) then builds the installer on a clean
rem machine, tests it and creates the release with SHA256SUMS.txt.
rem Before running: release branch merged into main and tag vX.Y.Z created (see CONTRIBUTING.md).
set NOPAUSE=1

for /f tokens^=2^ delims^=^" %%v in ('findstr /b /c:"VERSION = " app\common.py') do set "VER=%%v"
if not defined VER ( echo Cannot read VERSION from app\common.py & goto :fail )
findstr /b /l /c:"## [%VER%]" CHANGELOG.md >nul || ( echo CHANGELOG.md has no section [%VER%] & goto :fail )
git rev-parse -q --verify "refs/tags/v%VER%" >nul || ( echo Tag v%VER% not found. Create it after merging the release branch. & goto :fail )
git merge-base --is-ancestor "v%VER%" main || ( echo Tag v%VER% is not on main. & goto :fail )
echo === Releasing Holos %VER% ===

call "%~dp0publish.bat" || goto :fail
echo.
echo ============================================================
echo  Tag v%VER% pushed. GitHub is building the installer now (~20-30 min):
echo  https://github.com/canadianproducer/holos/actions
echo  The release will appear here when the build and tests pass:
echo  https://github.com/canadianproducer/holos/releases
echo ============================================================
pause
exit /b 0
:fail
echo.
echo RELEASE FAILED. Copy the text above and send it to Claude.
pause
exit /b 1
