@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title Голос — збірка

rem ============================================================
rem  One-click build of Holos.exe
rem    build.bat      - auto: GPU if NVIDIA present, else CPU
rem    build.bat cpu  - for any PC (~1.5 GB)
rem    build.bat gpu  - NVIDIA acceleration (~4.5 GB)
rem    build.bat release - CPU build + installer for GitHub Releases
rem  Needs only internet (and git, for one dependency).
rem ============================================================

rem close running Holos.exe, otherwise dist folder is locked
taskkill /IM Holos.exe /F >nul 2>&1

set "VARIANT=%~1"
set "RELEASE="
if /i "%VARIANT%"=="release" ( set "VARIANT=cpu" & set "RELEASE=1" )
if "%VARIANT%"=="" (
    where nvidia-smi >nul 2>&1 && (set "VARIANT=gpu") || (set "VARIANT=cpu")
)
if /i "%VARIANT%"=="gpu" (set "TORCH_INDEX=https://download.pytorch.org/whl/cu128") else (set "TORCH_INDEX=https://download.pytorch.org/whl/cpu")
echo.
echo === Варіант збірки: %VARIANT% ===

set "B=%~dp0.build"
set "UV_PYTHON_INSTALL_DIR=%B%\python"
set "UV_CACHE_DIR=%B%\uv-cache"
if not exist "%B%" mkdir "%B%"

rem --- 1. uv (Python manager, single exe) ---
set "UV=%B%\uv.exe"
if not exist "%UV%" if exist "%B%\bin\uv.exe" set "UV=%B%\bin\uv.exe"
if not exist "%UV%" (
    echo [1/5] Завантажую uv...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$env:UV_INSTALL_DIR='%B%'; $env:UV_NO_MODIFY_PATH='1'; irm https://astral.sh/uv/install.ps1 | iex"
    if exist "%B%\bin\uv.exe" set "UV=%B%\bin\uv.exe"
)
if not exist "%UV%" ( echo ПОМИЛКА: uv не встановився & goto :fail )

rem --- 2. Python 3.11 venv (uv-managed Python always has tkinter) ---
echo [2/5] Python 3.11...
rem separate env per variant: CPU and CUDA torch cannot share one
if not exist "%B%\env-%VARIANT%\Scripts\python.exe" (
    "%UV%" venv "%B%\env-%VARIANT%" --python 3.11 --python-preference only-managed || goto :fail
)
set "PY=%B%\env-%VARIANT%\Scripts\python.exe"
"%PY%" -c "import tkinter" || ( echo ПОМИЛКА: у Python немає tkinter & goto :fail )

rem --- 3. PyTorch (CPU or CUDA) ---
echo [3/5] PyTorch (%VARIANT%) — може зайняти кілька хвилин...
"%UV%" pip install --python "%PY%" torch==2.8.0 torchaudio==2.8.0 --index-url %TORCH_INDEX% || goto :fail

rem --- 4. Other libraries ---
echo [4/5] Бібліотеки...
"%UV%" pip install --python "%PY%" -r requirements.txt pyinstaller || goto :fail

rem --- 5. Build exe ---
echo [5/5] Збираю Holos.exe...
set "DISTDIR=dist"
if defined RELEASE set "DISTDIR=dist-release"
"%PY%" -m PyInstaller --noconfirm --clean --distpath "%DISTDIR%" holos.spec || goto :fail

echo.
echo ============================================================
echo  ГОТОВО:  %DISTDIR%\Holos\Holos.exe
echo  Швидка перевірка без інтерфейсу:  dist\Holos\Holos.exe --selftest
echo ============================================================

rem --- Installer (if Inno Setup 6 is installed; "build.bat release" installs it via winget) ---
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" if defined RELEASE (
    echo Installing Inno Setup 6 via winget...
    winget install --id JRSoftware.InnoSetup -e --silent --accept-package-agreements --accept-source-agreements
    if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
)
if exist "%ISCC%" (
    echo Створюю інсталятор...
    "%ISCC%" /Q /DVariant=%VARIANT% /DDistDir=%DISTDIR%\Holos installer.iss && echo  Інсталятор готовий: тека dist\
) else (
    echo  (Щоб отримати Holos-Setup.exe: встановіть Inno Setup 6 і запустіть build.bat ще раз)
)
echo.
pause
exit /b 0

:fail
echo.
echo ЗБІРКА НЕ ВДАЛАСЯ. Скопіюйте текст вище й надішліть Claude.
pause
exit /b 1
