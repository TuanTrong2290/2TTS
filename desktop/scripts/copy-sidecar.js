/**
 * Copy backend sidecar for Tauri build
 * Tauri requires sidecars to be named with target triple
 */
const fs = require('fs');
const path = require('path');

const sourceBackend = path.join(__dirname, '../../backend/dist/backend.exe');
const tauriDir = path.join(__dirname, '../src-tauri');

// Windows x64 target triple
const targetTriple = 'x86_64-pc-windows-msvc';
const targetBackend = path.join(tauriDir, `backend-${targetTriple}.exe`);

// Check if source exists
if (!fs.existsSync(sourceBackend)) {
  console.error(`Error: Backend not found at ${sourceBackend}`);
  console.log('Please build the backend first: cd ../backend && pyinstaller backend.spec');
  process.exit(1);
}

// Copy backend to src-tauri root
console.log(`Copying ${sourceBackend} -> ${targetBackend}`);
fs.copyFileSync(sourceBackend, targetBackend);

// Also copy to target/debug for dev mode
const debugDir = path.join(tauriDir, 'target/debug');
if (fs.existsSync(debugDir)) {
  const debugBackend = path.join(debugDir, `backend-${targetTriple}.exe`);
  console.log(`Copying to debug: ${debugBackend}`);
  fs.copyFileSync(sourceBackend, debugBackend);
}

console.log('Sidecar copied successfully!');
