interface DebugInfo {
  isDev: boolean;
  isPackaged: boolean;
  resourcesPath: string;
  appPath: string;
  userDataPath: string;
  backendError: string | null;
  backendRunning: boolean;
}

interface ErrorScreenProps {
  message: string;
  onRetry?: () => void;
  debugInfo?: DebugInfo | null;
}

export default function ErrorScreen({ message, onRetry, debugInfo }: ErrorScreenProps) {
  return (
    <div className="h-screen flex flex-col items-center justify-center bg-surface-950 p-8">
      <div className="max-w-2xl w-full flex flex-col items-center gap-6 text-center animate-fade-in">
        <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center">
          <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>
        <div className="flex flex-col gap-2">
          <h1 className="text-xl font-semibold text-surface-100">Connection Error</h1>
          <p className="text-sm text-surface-400 leading-relaxed">{message}</p>
        </div>

        {/* Debug Info Panel */}
        {debugInfo && (
          <div className="w-full mt-4 p-4 bg-surface-900 rounded-lg border border-surface-800 text-left">
            <h2 className="text-sm font-semibold text-surface-300 mb-2">Debug Information</h2>
            <div className="text-xs text-surface-500 space-y-1 font-mono">
              <p><span className="text-surface-400">isDev:</span> {String(debugInfo.isDev)}</p>
              <p><span className="text-surface-400">isPackaged:</span> {String(debugInfo.isPackaged)}</p>
              <p><span className="text-surface-400">backendRunning:</span> {String(debugInfo.backendRunning)}</p>
              <p><span className="text-surface-400">resourcesPath:</span> {debugInfo.resourcesPath}</p>
              <p><span className="text-surface-400">appPath:</span> {debugInfo.appPath}</p>
              <p><span className="text-surface-400">userDataPath:</span> {debugInfo.userDataPath}</p>
              {debugInfo.backendError && (
                <p className="text-red-400"><span className="text-surface-400">backendError:</span> {debugInfo.backendError}</p>
              )}
            </div>
          </div>
        )}

        <div className="flex gap-3">
          {onRetry && (
            <button onClick={onRetry} className="btn-primary">
              <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              Retry
            </button>
          )}
          <button
            onClick={() => window.close()}
            className="btn-secondary"
          >
            Exit
          </button>
        </div>
      </div>
    </div>
  );
}
