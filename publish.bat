@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Holos - publish to GitHub

rem Sends the source code to https://github.com/canadianproducer/holos
rem First run may open a browser window to sign in to GitHub (Git Credential Manager).

where git >nul 2>&1 || ( echo git not found. Install Git for Windows. & pause & exit /b 1 )

if not exist ".git" (
    git init -b main || goto :fail
    git remote add origin https://github.com/canadianproducer/holos.git || goto :fail
)
git config user.name "Canadian Producer"
git config user.email "canadianproducer@users.noreply.github.com"
git config core.autocrlf false

git add -A || goto :fail
git diff --cached --quiet && ( echo Nothing new to publish. & goto :push )
git commit -F .build\commit_msg.txt || goto :fail

:push
git push -u origin main || goto :fail
echo.
echo ============================================================
echo  DONE: https://github.com/canadianproducer/holos
echo ============================================================
if not defined NOPAUSE pause
exit /b 0

:fail
echo.
echo PUBLISH FAILED. Copy the text above and send it to Claude.
if not defined NOPAUSE pause
exit /b 1
