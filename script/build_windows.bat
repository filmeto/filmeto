@echo off
REM ============================================================================
REM Filmeto - Windows Build Script
REM Produces: dist\Filmeto.exe
REM ============================================================================

setlocal EnableDelayedExpansion

set APP_NAME=Filmeto
set APP_VERSION=%FILMETO_VERSION:~0,10%
if "%APP_VERSION%"=="" set APP_VERSION=0.1.0
set MAIN_ENTRY=main.py

cd /d "%~dp0\.."
set PROJECT_ROOT=%CD%
set DIST_DIR=%PROJECT_ROOT%\dist
set BUILD_DIR=%PROJECT_ROOT%\build

echo ========================================
echo   Building Filmeto for Windows
echo ========================================

REM --- Ensure virtual environment ---
if "%VIRTUAL_ENV%"=="" (
    set VENV_PATH=%PROJECT_ROOT%\.venv
    if not exist "%VENV_PATH%" (
        echo Creating virtual environment ...
        python -m venv "%VENV_PATH%"
    )
    echo Activating virtual environment ...
    call "%VENV_PATH%\Scripts\activate.bat"
) else (
    echo Using active virtual environment: %VIRTUAL_ENV%
)

REM --- Install dependencies ---
echo Installing build dependencies ...
pip install --upgrade pip
pip install pyinstaller
pip install -r "%PROJECT_ROOT%\requirements.txt"

REM --- Cleanup previous build ---
echo Cleaning previous build artifacts ...
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"

REM --- PyInstaller command ---
echo Running PyInstaller ...

set PYI_CMD=pyinstaller %MAIN_ENTRY%
set PYI_CMD=!PYI_CMD! --name %APP_NAME%
set PYI_CMD=!PYI_CMD! --onedir
set PYI_CMD=!PYI_CMD! --windowed
set PYI_CMD=!PYI_CMD! --noconfirm
set PYI_CMD=!PYI_CMD! --clean
set PYI_CMD=!PYI_CMD! --distpath "%DIST_DIR%"
set PYI_CMD=!PYI_CMD! --workpath "%BUILD_DIR%"

REM Icon
if exist "%PROJECT_ROOT%\textures\filmeto.ico" (
    set PYI_CMD=!PYI_CMD! --icon "%PROJECT_ROOT%\textures\filmeto.ico"
) else (
    echo [WARN] No .ico icon found, using default PySide6 icon
)

REM Data folders
for %%F in (agent app i18n server style textures utils) do (
    if exist "%PROJECT_ROOT%\%%F" (
        set PYI_CMD=!PYI_CMD! --add-data "%%F;%%F"
    )
)

%PYI_CMD%

echo.
echo ========================================
echo   Build complete: %DIST_DIR%\%APP_NAME%
echo ========================================
