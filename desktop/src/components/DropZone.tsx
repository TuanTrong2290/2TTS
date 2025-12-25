import { useState, useCallback, useEffect, useRef } from 'react';
import { listen } from '@tauri-apps/api/event';
import { getPlatformAPI } from '../lib/platform';
import { useTranslation } from '../lib/i18n';

interface DropZoneProps {
  onFilesDropped: (files: string[]) => void;
  compact?: boolean;
}

export default function DropZone({ onFilesDropped, compact = false }: DropZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const { t } = useTranslation();
  const onFilesDroppedRef = useRef(onFilesDropped);
  
  // Keep ref updated
  useEffect(() => {
    onFilesDroppedRef.current = onFilesDropped;
  }, [onFilesDropped]);

  // Listen for Tauri drag-drop events
  useEffect(() => {
    const unlisten = listen<string[]>('files-dropped', (event) => {
      if (event.payload && event.payload.length > 0) {
        onFilesDroppedRef.current(event.payload);
      }
    });

    return () => {
      unlisten.then((fn) => fn());
    };
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    // File paths are handled by Tauri's files-dropped event
  }, []);

  const handleBrowse = async () => {
    try {
      const api = await getPlatformAPI();
      const files = await api.dialog.openFile({
        title: 'Import Files',
        filters: [
          { name: 'Supported Files', extensions: ['srt', 'txt', 'docx'] },
          { name: 'SRT Files', extensions: ['srt'] },
          { name: 'Text Files', extensions: ['txt'] },
          { name: 'Word Documents', extensions: ['docx'] },
        ],
      });
      if (files && files.length > 0) {
        onFilesDropped(files);
      }
    } catch (err) {
      console.error('Failed to open file dialog:', err);
    }
  };

  if (compact) {
    return (
      <div
        onClick={handleBrowse}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          flex items-center justify-center gap-2 px-4 py-2 
          border-2 border-dashed rounded-lg cursor-pointer
          transition-all duration-200
          ${isDragging 
            ? 'border-primary-500 bg-primary-500/10' 
            : 'border-surface-700 hover:border-surface-600 hover:bg-surface-800/50'
          }
        `}
      >
        <svg className="w-4 h-4 text-surface-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
        <span className="text-sm text-surface-400">{t('tts.drop_files')}</span>
      </div>
    );
  }

  return (
    <div
      onClick={handleBrowse}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`
        flex flex-col items-center justify-center gap-4 p-8
        border-2 border-dashed rounded-xl cursor-pointer
        transition-all duration-200 min-h-[180px]
        ${isDragging 
          ? 'border-primary-500 bg-primary-500/10 scale-[1.02]' 
          : 'border-surface-700 hover:border-surface-600 hover:bg-surface-800/50'
        }
      `}
    >
      <div className="text-5xl">📂</div>
      <div className="text-center">
        <p className="text-lg font-medium text-surface-200">
          {t('tts.drop_files')}
        </p>
        <p className="text-sm text-surface-500 mt-1">
          {t('tts.supported_formats')}
        </p>
      </div>
      <div className="flex items-center gap-2 text-xs text-surface-600">
        <kbd className="px-2 py-1 bg-surface-800 rounded">Ctrl+I</kbd>
        <span>to import</span>
      </div>
    </div>
  );
}
