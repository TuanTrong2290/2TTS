interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  kind?: 'warning' | 'danger' | 'info';
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  kind = 'warning',
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!isOpen) return null;

  const kindStyles = {
    warning: {
      iconBg: 'bg-amber-500/20',
      iconColor: 'text-amber-400',
      gradientFrom: 'from-amber-500/20',
      buttonBg: 'bg-amber-500 hover:bg-amber-600',
    },
    danger: {
      iconBg: 'bg-red-500/20',
      iconColor: 'text-red-400',
      gradientFrom: 'from-red-500/20',
      buttonBg: 'bg-red-500 hover:bg-red-600',
    },
    info: {
      iconBg: 'bg-blue-500/20',
      iconColor: 'text-blue-400',
      gradientFrom: 'from-blue-500/20',
      buttonBg: 'bg-blue-500 hover:bg-blue-600',
    },
  };

  const styles = kindStyles[kind];

  const icons = {
    warning: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
    danger: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
      </svg>
    ),
    info: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onCancel}
      />

      {/* Dialog */}
      <div className="relative w-full max-w-md mx-4 bg-surface-900 rounded-xl border border-surface-700 shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header with gradient */}
        <div className={`relative px-6 pt-6 pb-4 bg-gradient-to-br ${styles.gradientFrom} to-transparent`}>
          <div className="flex items-start gap-4">
            {/* Icon */}
            <div className={`p-3 ${styles.iconBg} rounded-xl`}>
              <div className={styles.iconColor}>
                {icons[kind]}
              </div>
            </div>

            <div className="flex-1">
              <h2 className="text-lg font-semibold text-surface-100">{title}</h2>
              <p className="text-sm text-surface-400 mt-1">{message}</p>
            </div>

            {/* Close button */}
            <button
              onClick={onCancel}
              className="p-1 text-surface-500 hover:text-surface-300 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Actions */}
        <div className="px-6 py-4 flex items-center justify-end gap-3 bg-surface-900/50 border-t border-surface-800">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-surface-300 hover:text-surface-100 hover:bg-surface-800 rounded-lg transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className={`px-5 py-2 text-sm font-medium text-white ${styles.buttonBg} rounded-lg transition-colors flex items-center gap-2`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
