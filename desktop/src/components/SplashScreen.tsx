interface DebugInfo {
  isDev: boolean;
  isPackaged: boolean;
  resourcesPath: string;
  appPath: string;
  userDataPath: string;
  backendError: string | null;
  backendRunning: boolean;
}

interface SplashScreenProps {
  debugInfo?: DebugInfo | null;
}

export default function SplashScreen({ debugInfo }: SplashScreenProps) {
  return (
    <div className="h-screen flex flex-col items-center justify-center bg-surface-950">
      <div className="flex flex-col items-center gap-6 animate-fade-in">
        <div className="w-20 h-20 rounded-2xl bg-primary-600 flex items-center justify-center shadow-lg shadow-primary-600/20">
          <span className="text-3xl font-bold text-white">2T</span>
        </div>
        <div className="flex flex-col items-center gap-2">
          <h1 className="text-2xl font-semibold text-surface-100">2TTS</h1>
          <p className="text-sm text-surface-500">Connecting to backend...</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-primary-500 animate-pulse" />
          <div className="w-2 h-2 rounded-full bg-primary-500 animate-pulse [animation-delay:150ms]" />
          <div className="w-2 h-2 rounded-full bg-primary-500 animate-pulse [animation-delay:300ms]" />
        </div>

        {/* Debug Info Panel */}
        {debugInfo && (
          <div className="mt-8 p-4 bg-surface-900 rounded-lg border border-surface-800 text-left max-w-lg">
            <h2 className="text-xs font-semibold text-surface-400 mb-2">Debug Info</h2>
            <div className="text-xs text-surface-500 space-y-1 font-mono">
              <p><span className="text-surface-400">isPackaged:</span> {String(debugInfo.isPackaged)}</p>
              <p><span className="text-surface-400">backendRunning:</span> {String(debugInfo.backendRunning)}</p>
              <p className="truncate"><span className="text-surface-400">resourcesPath:</span> {debugInfo.resourcesPath}</p>
              {debugInfo.backendError && (
                <p className="text-red-400 break-all"><span className="text-surface-400">error:</span> {debugInfo.backendError}</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
