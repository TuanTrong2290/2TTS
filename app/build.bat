@echo off
REM 2TTS Build Script for Windows
REM This script builds the 2TTS application into a Windows executable

echo ============================================
echo 2TTS Build Script
echo ============================================
echo.

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

REM Build installer with Inno Setup (if available)
set "ISCC_EXE="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if not "%ISCC_EXE%"=="" (
    echo.
    echo Building installer (Inno Setup)...
    if exist "dist_installer" rmdir /s /q dist_installer
    "%ISCC_EXE%" "installer\2TTS.iss"
    if errorlevel 1 (
        echo Error: Installer build failed
        exit /b 1
    )
    echo Installer output: dist_installer\
) else (
    echo.
    echo Inno Setup compiler (ISCC.exe) not found - skipping installer build.
    echo Install Inno Setup 6 to produce Setup.exe (installer\2TTS.iss)
)

pause
