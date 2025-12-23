# 2TTS Release Script
param(
    [Parameter(Mandatory=$true)]
    [string]$Version,
    
    [string]$Notes = "Bug fixes and improvements"
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = "$RootDir\..\backend"

Write-Host "=== 2TTS Release Script ===" -ForegroundColor Cyan
Write-Host "Version: $Version" -ForegroundColor Yellow
Write-Host "Notes: $Notes" -ForegroundColor Yellow
Write-Host ""

# Helper function to write UTF8 without BOM
function Write-Utf8NoBom {
    param([string]$Path, [string]$Content)
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

# Step 1: Update version in all files
Write-Host "[1/8] Updating version numbers..." -ForegroundColor Green

# tauri.conf.json - use regex to preserve formatting
$tauriPath = "$RootDir\src-tauri\tauri.conf.json"
$tauriContent = [System.IO.File]::ReadAllText($tauriPath)
$tauriContent = $tauriContent -replace '"version":\s*"[^"]*"', "`"version`": `"$Version`""
Write-Utf8NoBom $tauriPath $tauriContent

# Cargo.toml - only update package version (first occurrence)
$cargoPath = "$RootDir\src-tauri\Cargo.toml"
$cargoContent = [System.IO.File]::ReadAllText($cargoPath)
$cargoContent = $cargoContent -replace '(?m)^(version\s*=\s*")[^"]*(")', "`${1}$Version`${2}"
Write-Utf8NoBom $cargoPath $cargoContent

# package.json - use regex to preserve formatting
$pkgPath = "$RootDir\package.json"
$pkgContent = [System.IO.File]::ReadAllText($pkgPath)
$pkgContent = $pkgContent -replace '"version":\s*"[^"]*"', "`"version`": `"$Version`""
Write-Utf8NoBom $pkgPath $pkgContent

# backend/ipc/handlers.py - update BACKEND_VERSION
$handlersPath = "$BackendDir\ipc\handlers.py"
if (Test-Path $handlersPath) {
    $handlersContent = [System.IO.File]::ReadAllText($handlersPath)
    $handlersContent = $handlersContent -replace 'BACKEND_VERSION\s*=\s*"[^"]*"', "BACKEND_VERSION = `"$Version`""
    Write-Utf8NoBom $handlersPath $handlersContent
}

# src/lib/ipc/client.ts - update UI_VERSION
$clientPath = "$RootDir\src\lib\ipc\client.ts"
if (Test-Path $clientPath) {
    $clientContent = [System.IO.File]::ReadAllText($clientPath)
    $clientContent = $clientContent -replace "const UI_VERSION\s*=\s*'[^']*'", "const UI_VERSION = '$Version'"
    Write-Utf8NoBom $clientPath $clientContent
}

Write-Host "Version updated to $Version" -ForegroundColor Gray

# Step 2: Build backend
Write-Host "[2/8] Building backend..." -ForegroundColor Green
Push-Location $BackendDir
pyinstaller backend.spec --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Backend build failed" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location
Write-Host "Backend built" -ForegroundColor Gray

# Step 3: Copy sidecar
Write-Host "[3/8] Copying sidecar..." -ForegroundColor Green
Push-Location $RootDir
node scripts/copy-sidecar.js
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Sidecar copy failed" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location
Write-Host "Sidecar copied" -ForegroundColor Gray

# Step 4: Load signing key
Write-Host "[4/8] Loading signing key..." -ForegroundColor Green
$keyPath = "$RootDir\tauri-signing-key.key"
if (-not (Test-Path $keyPath)) {
    Write-Host "ERROR: Signing key not found at $keyPath" -ForegroundColor Red
    exit 1
}
$env:TAURI_SIGNING_PRIVATE_KEY = [System.IO.File]::ReadAllText($keyPath)
$env:TAURI_SIGNING_PRIVATE_KEY_PASSWORD = "2tts2025"
Write-Host "Signing key loaded" -ForegroundColor Gray

# Step 5: Build Tauri app
Write-Host "[5/8] Building Tauri application..." -ForegroundColor Green
Push-Location $RootDir
npm run tauri build
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Tauri build failed" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location
Write-Host "Tauri build completed" -ForegroundColor Gray

# Step 6: Create latest.json
Write-Host "[6/8] Creating latest.json..." -ForegroundColor Green
$bundleDir = "$RootDir\src-tauri\target\release\bundle\nsis"
$exeName = "2TTS_${Version}_x64-setup.exe"
$sigFile = "$bundleDir\$exeName.sig"

if (-not (Test-Path $sigFile)) {
    Write-Host "ERROR: Signature file not found at $sigFile" -ForegroundColor Red
    exit 1
}

$signature = [System.IO.File]::ReadAllText($sigFile).Trim()
$pubDate = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

$latestJson = @"
{
  "version": "$Version",
  "notes": "$Notes",
  "pub_date": "$pubDate",
  "platforms": {
    "windows-x86_64": {
      "signature": "$signature",
      "url": "https://github.com/TuanTrong2290/2TTS/releases/download/v$Version/$exeName"
    }
  }
}
"@

Write-Utf8NoBom "$bundleDir\latest.json" $latestJson
Write-Host "latest.json created" -ForegroundColor Gray

# Step 7: Create GitHub release
Write-Host "[7/8] Creating GitHub release..." -ForegroundColor Green
Push-Location $RootDir\..

$exePath = "$bundleDir\$exeName"
$latestPath = "$bundleDir\latest.json"

# Check if release exists (suppress errors temporarily)
$ErrorActionPreference = "SilentlyContinue"
gh release view "v$Version" 2>$null | Out-Null
$releaseExists = $LASTEXITCODE -eq 0
$ErrorActionPreference = "Stop"

if ($releaseExists) {
    Write-Host "Release v$Version exists, updating assets..." -ForegroundColor Yellow
    gh release upload "v$Version" $exePath $latestPath --clobber
} else {
    Write-Host "Creating new release v$Version..." -ForegroundColor Yellow
    gh release create "v$Version" --title "2TTS v$Version" --notes $Notes $exePath $latestPath
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to create/update release" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

# Step 8: Done
Write-Host "[8/8] Release complete!" -ForegroundColor Green
Write-Host ""
Write-Host "=== Release Summary ===" -ForegroundColor Cyan
Write-Host "Version: $Version" -ForegroundColor White
Write-Host "URL: https://github.com/TuanTrong2290/2TTS/releases/tag/v$Version" -ForegroundColor White
Write-Host ""
Write-Host "Users will receive auto-update prompts!" -ForegroundColor Green
