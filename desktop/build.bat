@echo off
setlocal enabledelayedexpansion

if "%1"=="" (
    echo Usage: build.bat release ^<version^>
    echo Example: build.bat release 1.0.9
    exit /b 1
)

if "%1"=="release" (
    if "%2"=="" (
        echo Error: Version number required
        echo Usage: build.bat release ^<version^>
        exit /b 1
    )
    
    set VERSION=%2
    echo.
    echo ========================================
    echo  Building 2TTS Desktop v!VERSION! (Tauri)
    echo ========================================
    echo.
    
    REM Update version in package.json
    echo [1/7] Updating package.json version to !VERSION!...
    powershell -Command "(Get-Content package.json) -replace '\"version\": \"[^\"]+\"', '\"version\": \"!VERSION!\"' | Set-Content package.json"
    if errorlevel 1 (
        echo Error: Failed to update package.json
        exit /b 1
    )
    
    REM Update version in tauri.conf.json
    echo [2/7] Updating tauri.conf.json version to !VERSION!...
    powershell -Command "(Get-Content src-tauri\tauri.conf.json) -replace '\"version\": \"[^\"]+\"', '\"version\": \"!VERSION!\"' | Set-Content src-tauri\tauri.conf.json"
    if errorlevel 1 (
        echo Error: Failed to update tauri.conf.json
        exit /b 1
    )
    
    REM Update version in Cargo.toml
    echo [3/7] Updating Cargo.toml version to !VERSION!...
    powershell -Command "(Get-Content src-tauri\Cargo.toml) -replace 'version = \"[^\"]+\"', 'version = \"!VERSION!\"' | Set-Content src-tauri\Cargo.toml"
    if errorlevel 1 (
        echo Error: Failed to update Cargo.toml
        exit /b 1
    )
    
    REM Build Python backend
    echo [4/7] Building Python backend...
    pushd ..\backend
    python -m PyInstaller --onefile --name backend --paths="../app" --hidden-import=core --hidden-import=core.config --hidden-import=core.models --hidden-import=services --hidden-import=services.elevenlabs --hidden-import=services.file_import --hidden-import=services.audio --hidden-import=ipc --hidden-import=ipc.server --hidden-import=ipc.handlers --hidden-import=ipc.types --hidden-import=requests --hidden-import=pysrt --hidden-import=docx --hidden-import=langdetect --hidden-import=pydub --exclude-module=PyQt6 --exclude-module=PyQt5 --exclude-module=tkinter --exclude-module=matplotlib --exclude-module=numpy --exclude-module=PIL --exclude-module=supabase --console main.py
    if errorlevel 1 (
        popd
        echo Error: Failed to build Python backend
        exit /b 1
    )
    popd
    
    if not exist "..\backend\dist\backend.exe" (
        echo Error: backend.exe not found
        exit /b 1
    )
    
    REM Copy sidecar
    echo [5/7] Copying backend sidecar...
    call npm run tauri:sidecar
    if errorlevel 1 (
        echo Error: Failed to copy sidecar
        exit /b 1
    )
    
    REM Build Tauri app
    echo [6/7] Building Tauri app...
    call npx tauri build
    if errorlevel 1 (
        echo Error: Tauri build failed
        exit /b 1
    )
    
    REM Get installer path
    set "INSTALLER=src-tauri\target\release\bundle\nsis\2TTS_!VERSION!_x64-setup.exe"
    if not exist "!INSTALLER!" (
        echo Error: Installer not found at !INSTALLER!
        exit /b 1
    )
    
    REM Calculate SHA256
    echo [7/7] Calculating SHA256...
    for /f "skip=1 delims=" %%a in ('certutil -hashfile "!INSTALLER!" SHA256 ^| findstr /v "CertUtil"') do (
        set "SHA256=%%a"
        goto :got_hash
    )
    :got_hash
    set "SHA256=!SHA256: =!"
    echo SHA256: !SHA256!
    
    echo.
    echo ========================================
    echo  Build v!VERSION! completed!
    echo ========================================
    echo  Installer: !INSTALLER!
    echo  SHA256: !SHA256!
    echo ========================================
    
    exit /b 0
)

echo Unknown command: %1
echo Usage: build.bat release ^<version^>
exit /b 1
