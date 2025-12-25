import { ProcessingStats } from '../lib/ipc/types';
import { useTranslation } from '../lib/i18n';

interface ProcessingControlsProps {
  isProcessing: boolean;
  isPaused: boolean;
  stats: ProcessingStats;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  disabled?: boolean;
}

export default function ProcessingControls({
  isProcessing,
  isPaused,
  stats,
  onStart,
  onPause,
  onResume,
  onStop,
  disabled = false,
}: ProcessingControlsProps) {
  const { t } = useTranslation();
  const progress = stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0;
  
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const estimatedRemaining = () => {
    if (stats.completed === 0 || stats.elapsed_seconds === 0) return '-';
    const avgPerItem = stats.elapsed_seconds / stats.completed;
    const remaining = avgPerItem * stats.pending;
    return formatTime(remaining);
  };

  return (
    <div className="space-y-4">
      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-surface-400">
            {isProcessing ? (isPaused ? t('common.pause') : t('tts.processing')) : t('status.ready')}
          </span>
          <span className="text-surface-300 font-medium">
            {stats.completed} / {stats.total}
          </span>
        </div>
        <div className="h-2 bg-surface-800 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${
              stats.failed > 0 
                ? 'bg-gradient-to-r from-primary-500 to-red-500' 
                : 'bg-primary-500'
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Stats */}
      {isProcessing && (
        <div className="grid grid-cols-4 gap-4 text-center">
          <div>
            <div className="text-lg font-semibold text-green-400">{stats.completed}</div>
            <div className="text-xs text-surface-500">{t('tts.completed')}</div>
          </div>
          <div>
            <div className="text-lg font-semibold text-yellow-400">{stats.processing}</div>
            <div className="text-xs text-surface-500">{t('status.processing')}</div>
          </div>
          <div>
            <div className="text-lg font-semibold text-red-400">{stats.failed}</div>
            <div className="text-xs text-surface-500">{t('tts.failed')}</div>
          </div>
          <div>
            <div className="text-lg font-semibold text-surface-300">{estimatedRemaining()}</div>
            <div className="text-xs text-surface-500">ETA</div>
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="flex items-center gap-3">
        {!isProcessing ? (
          <button
            onClick={onStart}
            disabled={disabled || stats.pending === 0}
            className="flex-1 btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {t('common.start')}
          </button>
        ) : (
          <>
            {isPaused ? (
              <button
                onClick={onResume}
                className="flex-1 btn-primary"
              >
                <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                </svg>
                {t('common.resume')}
              </button>
            ) : (
              <button
                onClick={onPause}
                className="flex-1 px-4 py-2 bg-yellow-500/20 text-yellow-400 rounded-lg hover:bg-yellow-500/30 transition-colors font-medium"
              >
                <svg className="w-5 h-5 mr-2 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {t('common.pause')}
              </button>
            )}
            <button
              onClick={onStop}
              className="px-4 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-colors font-medium"
            >
              <svg className="w-5 h-5 mr-2 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
              </svg>
              {t('common.stop')}
            </button>
          </>
        )}
      </div>

      {/* Character count */}
      <div className="text-xs text-surface-500 text-center">
        {stats.characters_processed.toLocaleString()} characters processed
        {stats.elapsed_seconds > 0 && ` in ${formatTime(stats.elapsed_seconds)}`}
      </div>
    </div>
  );
}
