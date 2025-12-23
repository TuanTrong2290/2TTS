@echo off
echo Building 2TTS Desktop Application...
echo.

cd /d "%~dp0\.."

echo Step 1: Installing npm dependencies...
call npm install
if errorlevel 1 goto error

echo.
echo Step 2: Building Python sidecar...
python scripts\build-sidecar.py
if errorlevel 1 goto error

echo.
echo Step 3: Building Tauri application...
call npm run tauri build
if errorlevel 1 goto error

echo.
echo Build completed successfully!
echo Output: src-tauri\target\release\bundle\
goto end

:error
echo.
echo Build failed with error code %errorlevel%
exit /b %errorlevel%

:end
