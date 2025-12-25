interface UpToDateDialogProps {
  isOpen: boolean;
  currentVersion: string | null;
  onClose: () => void;
}

export default function UpToDateDialog({ isOpen, currentVersion, onClose }: UpToDateDialogProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      
      <div className="relative w-full max-w-sm mx-4 bg-surface-900 rounded-xl border border-surface-700 shadow-2xl overflow-hidden">
        <div className="relative px-6 pt-6 pb-4 bg-gradient-to-br from-green-500/20 to-transparent">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-green-500/20 rounded-xl">
              <svg className="w-8 h-8 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            
            <div className="flex-1">
              <h2 className="text-lg font-semibold text-surface-100">You're Up to Date</h2>
              <p className="text-sm text-surface-400 mt-1">
                2TTS is running the latest version
              </p>
            </div>

            <button
              onClick={onClose}
              className="p-1 text-surface-500 hover:text-surface-300 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div className="px-6 py-4 border-b border-surface-800">
          <div className="flex items-center justify-center gap-2">
            <div className="text-center">
              <div className="text-xs text-surface-500 uppercase tracking-wide">Current Version</div>
              <div className="text-lg font-mono text-green-400 font-medium mt-1">v{currentVersion || 'Unknown'}</div>
            </div>
          </div>
        </div>

        <div className="px-6 py-4 flex items-center justify-center bg-surface-900/50">
          <button
            onClick={onClose}
            className="px-5 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg transition-colors"
          >
            OK
          </button>
        </div>
      </div>
    </div>
  );
}
