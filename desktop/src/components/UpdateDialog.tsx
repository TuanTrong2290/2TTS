

interface UpdateInfo {
  version: string;
  currentVersion: string;
  releaseNotes?: string;
  releaseDate?: string;
}

interface UpdateDialogProps {
  isOpen: boolean;
  updateInfo: UpdateInfo | null;
  onClose: () => void;
  onUpdate: () => void;
  isDownloading: boolean;
  downloadProgress: number; // 0-100
}

export default function UpdateDialog({
  isOpen,
  updateInfo,
  onClose,
  onUpdate,
  isDownloading,
  downloadProgress,
}: UpdateDialogProps) {
  if (!isOpen || !updateInfo) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={!isDownloading ? onClose : undefined}
      />
      
      {/* Dialog */}
      <div className="relative w-full max-w-md mx-4 bg-surface-900 rounded-xl border border-surface-700 shadow-2xl overflow-hidden">
        {/* Header with gradient */}
        <div className="relative px-6 pt-6 pb-4 bg-gradient-to-br from-primary-500/20 to-transparent">
          <div className="flex items-start gap-4">
            {/* Update icon */}
            <div className="p-3 bg-primary-500/20 rounded-xl">
              <svg className="w-8 h-8 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
            </div>
            
            <div className="flex-1">
              <h2 className="text-lg font-semibold text-surface-100">Update Available</h2>
              <p className="text-sm text-surface-400 mt-1">
                A new version of 2TTS is ready to install
              </p>
            </div>

            {/* Close button */}
            {!isDownloading && (
              <button
                onClick={onClose}
                className="p-1 text-surface-500 hover:text-surface-300 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* Version info */}
        <div className="px-6 py-4 border-b border-surface-800">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="text-center">
                <div className="text-xs text-surface-500 uppercase tracking-wide">Current</div>
                <div className="text-sm font-mono text-surface-400 mt-1">v{updateInfo.currentVersion}</div>
              </div>
              
              <svg className="w-5 h-5 text-surface-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
              
              <div className="text-center">
                <div className="text-xs text-primary-400 uppercase tracking-wide">New</div>
                <div className="text-sm font-mono text-primary-400 font-medium mt-1">v{updateInfo.version}</div>
              </div>
            </div>

            {updateInfo.releaseDate && (
              <div className="text-xs text-surface-500">
                {new Date(updateInfo.releaseDate).toLocaleDateString()}
              </div>
            )}
          </div>
        </div>

        {/* Release notes */}
        {updateInfo.releaseNotes && (
          <div className="px-6 py-4 border-b border-surface-800">
            <h3 className="text-xs font-medium text-surface-400 uppercase tracking-wide mb-2">
              What's New
            </h3>
            <div className="max-h-32 overflow-y-auto text-sm text-surface-300 space-y-1 pr-2 scrollbar-thin">
              {updateInfo.releaseNotes.split('\n').map((line, i) => (
                <p key={i} className={line.startsWith('-') || line.startsWith('*') ? 'pl-2' : ''}>
                  {line}
                </p>
              ))}
            </div>
          </div>
        )}

        {/* Download progress */}
        {isDownloading && (
          <div className="px-6 py-4 border-b border-surface-800">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-surface-400">Downloading update...</span>
              <span className="text-sm font-mono text-primary-400">{downloadProgress}%</span>
            </div>
            <div className="h-2 bg-surface-800 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-primary-500 to-primary-400 rounded-full transition-all duration-300"
                style={{ width: `${downloadProgress}%` }}
              />
            </div>
            <p className="text-xs text-surface-500 mt-2">
              Please wait, the app will restart automatically after installation.
            </p>
          </div>
        )}

        {/* Actions */}
        <div className="px-6 py-4 flex items-center justify-end gap-3 bg-surface-900/50">
          {!isDownloading ? (
            <>
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm text-surface-400 hover:text-surface-200 transition-colors"
              >
                Remind Me Later
              </button>
              <button
                onClick={onUpdate}
                className="px-5 py-2 text-sm font-medium text-white bg-primary-500 hover:bg-primary-600 rounded-lg transition-colors flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Update Now
              </button>
            </>
          ) : (
            <button
              disabled
              className="px-5 py-2 text-sm font-medium text-surface-400 bg-surface-800 rounded-lg cursor-not-allowed flex items-center gap-2"
            >
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Installing...
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
