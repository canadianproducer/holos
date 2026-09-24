@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Holos - fix commit history and publish release
rem 1) Remove "Co-Authored-By" lines from all commit messages (so GitHub shows only one contributor)
rem 2) Force-push the corrected history
rem 3) Upload the installer to GitHub Releases
where git >nul 2>&1 || ( echo git not found & pause & exit /b 1 )
rem commit pending local changes first (filter-branch needs a clean working tree)
git add -A
git diff --cached --quiet || git commit -m "Fix release upload script" || goto :fail
set FILTER_BRANCH_SQUELCH_WARNING=1
git filter-branch -f --msg-filter "sed -e '/^Co-Authored-By:/d'" -- main || goto :fail
git push --force origin main || goto :fail
if exist ".git\refs\original" rmdir /s /q ".git\refs\original"
echo.
echo History fixed. Now uploading the release...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0upload-release.ps1" || goto :fail
echo.
echo ============================================================
echo  DONE: https://github.com/canadianproducer/holos/releases
echo ============================================================
pause
exit /b 0
:fail
echo.
echo FAILED. Just tell Claude "error" - the log is in .build\upload.log
pause
exit /b 1
