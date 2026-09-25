@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Holos - push to GitHub

rem Pushes branch main and release tags to https://github.com/canadianproducer/holos
rem Changes are made on branches and merged into main first (see CONTRIBUTING.md),
rem so this script never creates commits itself.
rem First run may open a browser window to sign in to GitHub (Git Credential Manager).

where git >nul 2>&1 || ( echo git not found. Install Git for Windows. & goto :fail )
git config user.name "Canadian Producer"
git config user.email "canadianproducer@users.noreply.github.com"
git config core.autocrlf false

for /f "delims=" %%i in ('git status --porcelain') do goto :dirty

git push origin main --follow-tags || goto :fail
echo.
echo ============================================================
echo  DONE: https://github.com/canadianproducer/holos
echo ============================================================
if not defined NOPAUSE pause
exit /b 0

:dirty
echo There are uncommitted changes:
git status --short
echo Commit them on a branch and merge into main first (see CONTRIBUTING.md).

:fail
echo.
echo PUBLISH FAILED. Copy the text above and send it to Claude.
if not defined NOPAUSE pause
exit /b 1
