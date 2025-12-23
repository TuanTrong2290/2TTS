@echo off
echo Starting 2TTS Desktop in development mode...
echo.

cd /d "%~dp0\.."

echo Installing dependencies if needed...
call npm install

echo.
echo Starting Tauri dev server...
echo (Backend will run from Python source directly)
echo.

call npm run tauri dev
