import { useEffect, useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import TTSPage from './pages/TTSPage';
import SettingsPage from './pages/SettingsPage';
import TranscribePage from './pages/TranscribePage';
import { useAppStore } from './stores/appStore';
import { ipcClient } from './lib/ipc';
import { getPlatformAPI } from './lib/platform';
import { updateManager, UpdateState } from './lib/updater';
import SplashScreen from './components/SplashScreen';
import ErrorScreen from './components/ErrorScreen';
import UpdateDialog from './components/UpdateDialog';

interface DebugInfo {
  isDev: boolean;
  isPackaged: boolean;
  resourcesPath: string;
  appPath: string;
  userDataPath: string;
  backendError: string | null;
  backendRunning: boolean;
}

function App() {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [debugInfo, setDebugInfo] = useState<DebugInfo | null>(null);
  const [updateState, setUpdateState] = useState<UpdateState>(updateManager.getState());
  const { setBackendReady, setVersionInfo } = useAppStore();

  // Subscribe to update manager
  useEffect(() => {
    return updateManager.subscribe(setUpdateState);
  }, []);

  useEffect(() => {
    let unsubDebug: (() => void) | undefined;

    // Listen for debug info from main process
    getPlatformAPI().then((api) => {
      unsubDebug = api.onDebugInfo((info: DebugInfo) => {
        console.log('[Debug Info]', info);
        setDebugInfo(info);
      });
    }).catch(console.error);

    return () => {
      unsubDebug?.();
    };
  }, []);

  useEffect(() => {
    async function initializeApp() {
      console.log('[App] Starting initialization...');
      try {
        console.log('[App] Calling handshake...');
        const handshake = await ipcClient.handshake();
        console.log('[App] Handshake response:', handshake);
        if (!handshake.compatible) {
          setError(
            `Version mismatch: UI v${handshake.ui_version} is not compatible with Backend v${handshake.backend_version}. Minimum required UI version: ${handshake.min_ui_version}. Please reinstall the application.`
          );
          return;
        }
        setVersionInfo({
          uiVersion: handshake.ui_version,
          backendVersion: handshake.backend_version,
          protocolVersion: handshake.protocol_version,
        });
        setBackendReady(true);
        setIsLoading(false);
        console.log('[App] Initialization complete');
        
        // Check for updates silently after startup
        setTimeout(() => {
          updateManager.checkForUpdates(true).catch(console.error);
        }, 3000);
      } catch (err) {
        console.error('[App] Initialization error:', err);
        const message = err instanceof Error ? err.message : 'Failed to connect to backend';
        setError(message);
      }
    }

    initializeApp();
  }, [setBackendReady, setVersionInfo]);

  if (error) {
    return (
      <ErrorScreen 
        message={error} 
        onRetry={() => window.location.reload()} 
        debugInfo={debugInfo}
      />
    );
  }

  if (isLoading) {
    return <SplashScreen debugInfo={debugInfo} />;
  }

  return (
    <>
      <Layout>
        <Routes>
          <Route path="/" element={<TTSPage />} />
          <Route path="/transcribe" element={<TranscribePage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </Layout>

      {/* Update Dialog */}
      <UpdateDialog
        isOpen={updateState.available}
        updateInfo={updateState.updateInfo}
        onClose={() => updateManager.dismiss()}
        onUpdate={() => updateManager.downloadAndInstall()}
        isDownloading={updateState.downloading}
        downloadProgress={updateState.progress}
      />
    </>
  );
}

export default App;
