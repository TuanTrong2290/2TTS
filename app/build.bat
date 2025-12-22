@echo off
REM 2TTS Build Script for Windows
REM Usage: build.bat [release VERSION]
REM   build.bat              - Build app only (for development)
REM   build.bat release 1.0.1 - Full release build with version 1.0.1

echo ============================================
echo 2TTS Build Script
echo ============================================
echo.

REM Check if this is a release build
set "RELEASE_BUILD=0"
set "RELEASE_VERSION="
if "%~1"=="release" (
    set "RELEASE_BUILD=1"
    set "RELEASE_VERSION=%~2"
)

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    exit /b 1
)

REM Check if PyInstaller is installed
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Check if required icon exists
if not exist "resources\icon.ico" (
    echo Warning: resources\icon.ico not found
    echo Please add an icon file before building
    echo.
)

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies
    exit /b 1
)

REM For release builds, use the Python script
if "%RELEASE_BUILD%"=="1" (
    echo.
    if "%RELEASE_VERSION%"=="" (
        echo Error: Version required for release build
        echo Usage: build.bat release VERSION
        echo Example: build.bat release 1.0.1
        pause
        exit /b 1
    )
    echo Running full release build v%RELEASE_VERSION%...
    python scripts\build_release.py %RELEASE_VERSION%
    if errorlevel 1 (
        echo Error: Release build failed
        exit /b 1
    )
    pause
    exit /b 0
)

REM Clean previous build
echo Cleaning previous build...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM Build with PyInstaller
echo Building executable...
pyinstaller 2tts.spec --clean

if errorlevel 1 (
    echo Error: Build failed
    exit /b 1
)

echo.
echo ============================================
echo Build completed successfully!
echo Output: dist\2TTS\
echo ============================================
echo.
echo To create a release with installer, run:
echo   build.bat release
echo.

pause
