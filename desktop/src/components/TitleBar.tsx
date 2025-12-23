import { useAppStore } from '../stores/appStore';
import { getPlatformAPI } from '../lib/platform';

export default function TitleBar() {
  const { versionInfo, totalCredits } = useAppStore();

  const handleMinimize = async () => {
    const api = await getPlatformAPI();
    api.window.minimize();
  };
  const handleMaximize = async () => {
    const api = await getPlatformAPI();
    api.window.maximize();
  };
  const handleClose = async () => {
    const api = await getPlatformAPI();
    api.window.close();
  };

  return (
    <div className="h-10 bg-surface-900 border-b border-surface-800 flex items-center justify-between px-4 drag-region select-none">
      <div className="flex items-center gap-3 no-drag">
        <div className="w-6 h-6 rounded-lg bg-primary-600 flex items-center justify-center">
          <span className="text-xs font-bold text-white">2T</span>
        </div>
        <span className="text-sm font-medium text-surface-200">2TTS</span>
        {versionInfo && (
          <span className="text-xs text-surface-500">v{versionInfo.uiVersion}</span>
        )}
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 no-drag">
          <div className="flex items-center gap-1.5 px-2 py-1 bg-surface-800 rounded-lg">
            <svg
              className="w-4 h-4 text-primary-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span className="text-sm font-medium text-surface-200">
              {totalCredits.toLocaleString()}
            </span>
          </div>
        </div>

        <div className="flex items-center no-drag">
          <button
            onClick={handleMinimize}
            className="w-10 h-10 flex items-center justify-center text-surface-400 hover:text-surface-100 hover:bg-surface-800 transition-colors"
            aria-label="Minimize"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M5 10h10" stroke="currentColor" strokeWidth="2" />
            </svg>
          </button>
          <button
            onClick={handleMaximize}
            className="w-10 h-10 flex items-center justify-center text-surface-400 hover:text-surface-100 hover:bg-surface-800 transition-colors"
            aria-label="Maximize"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 14 14">
              <rect
                x="1"
                y="1"
                width="12"
                height="12"
                rx="1"
                stroke="currentColor"
                strokeWidth="2"
              />
            </svg>
          </button>
          <button
            onClick={handleClose}
            className="w-10 h-10 flex items-center justify-center text-surface-400 hover:text-white hover:bg-red-600 transition-colors"
            aria-label="Close"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 16 16">
              <path
                d="M4 4l8 8M12 4l-8 8"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
