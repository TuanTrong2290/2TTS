import { useState, useCallback, useEffect, useRef } from 'react';
import { TextLine, LineStatus, Voice } from '../lib/ipc/types';
import { useTranslation } from '../lib/i18n';

interface LineTableProps {
  lines: TextLine[];
  voices: Voice[];
  selectedIds: Set<string>;
  onSelectionChange: (ids: Set<string>) => void;
  onTextEdit: (id: string, text: string) => void;
  onVoiceChange: (id: string, voiceId: string, voiceName: string) => void;
  onDelete: (ids: string[]) => void;
  onRetry: (ids: string[]) => void;
  onPlayAudio: (id: string) => void;
  onReorder?: (fromIndex: number, toIndex: number) => void;
}

const STATUS_CONFIG: Record<LineStatus, { labelKey: string; color: string; icon: string }> = {
  pending: { labelKey: 'status.pending', color: 'text-surface-400', icon: '○' },
  processing: { labelKey: 'status.processing', color: 'text-yellow-400', icon: '◐' },
  done: { labelKey: 'status.done', color: 'text-green-400', icon: '✓' },
  error: { labelKey: 'status.error', color: 'text-red-400', icon: '✗' },
};

export default function LineTable({
  lines,
  voices,
  selectedIds,
  onSelectionChange,
  onTextEdit,
  onVoiceChange,
  onDelete,
  onRetry,
  onPlayAudio,
  onReorder,
}: LineTableProps) {
  const { t } = useTranslation();
  const [editingLine, setEditingLine] = useState<TextLine | null>(null);
  const [editText, setEditText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

  const handleSelectAll = useCallback((checked: boolean) => {
    if (checked) {
      onSelectionChange(new Set(lines.map(l => l.id)));
    } else {
      onSelectionChange(new Set());
    }
  }, [lines, onSelectionChange]);

  const handleSelectRow = useCallback((id: string, checked: boolean) => {
    const newSelection = new Set(selectedIds);
    if (checked) {
      newSelection.add(id);
    } else {
      newSelection.delete(id);
    }
    onSelectionChange(newSelection);
  }, [selectedIds, onSelectionChange]);

  const handleDoubleClick = useCallback((line: TextLine) => {
    setEditingLine(line);
    setEditText(line.text);
  }, []);

  const handleEditSubmit = useCallback(() => {
    if (editingLine && editText.trim()) {
      onTextEdit(editingLine.id, editText.trim());
    }
    setEditingLine(null);
    setEditText('');
  }, [editingLine, editText, onTextEdit]);

  const handleEditCancel = useCallback(() => {
    setEditingLine(null);
    setEditText('');
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      e.preventDefault();
      handleEditSubmit();
    } else if (e.key === 'Escape') {
      handleEditCancel();
    }
  }, [handleEditSubmit, handleEditCancel]);

  // Focus textarea when edit panel opens
  useEffect(() => {
    if (editingLine && textareaRef.current) {
      textareaRef.current.focus();
      textareaRef.current.setSelectionRange(editText.length, editText.length);
    }
  }, [editingLine]);

  const handleContextMenu = useCallback((e: React.MouseEvent, line: TextLine) => {
    e.preventDefault();
    // Select the row if not already selected
    if (!selectedIds.has(line.id)) {
      onSelectionChange(new Set([line.id]));
    }
  }, [selectedIds, onSelectionChange]);

  // Drag and drop handlers
  const handleDragStart = useCallback((e: React.DragEvent, index: number) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', index.toString());
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, index: number) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverIndex(index);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragOverIndex(null);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent, toIndex: number) => {
    e.preventDefault();
    const fromIndex = draggedIndex;
    setDraggedIndex(null);
    setDragOverIndex(null);
    if (fromIndex !== null && fromIndex !== toIndex && onReorder) {
      onReorder(fromIndex, toIndex);
    }
  }, [draggedIndex, onReorder]);

  const handleDragEnd = useCallback(() => {
    setDraggedIndex(null);
    setDragOverIndex(null);
  }, []);

  const formatDuration = (seconds: number | null) => {
    if (seconds === null) return '-';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const allSelected = lines.length > 0 && selectedIds.size === lines.length;
  const someSelected = selectedIds.size > 0 && selectedIds.size < lines.length;

  if (lines.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="text-5xl mb-4">📄</div>
        <h3 className="text-lg font-medium text-surface-300 mb-2">{t('tts.no_lines')}</h3>
        <p className="text-sm text-surface-500 max-w-md">
          {t('tts.import_files')}
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-surface-800">
      {/* Header */}
      <div className={`grid gap-2 px-3 py-2 bg-surface-850 border-b border-surface-800 text-xs font-medium text-surface-400 uppercase tracking-wider ${onReorder ? 'grid-cols-[24px_40px_50px_1fr_180px_100px_80px_60px]' : 'grid-cols-[40px_50px_1fr_180px_100px_80px_60px]'}`}>
        {onReorder && <div></div>}
        <div className="flex items-center justify-center">
          <input
            type="checkbox"
            checked={allSelected}
            ref={(el) => el && (el.indeterminate = someSelected)}
            onChange={(e) => handleSelectAll(e.target.checked)}
            className="w-4 h-4 rounded border-surface-600 bg-surface-800 text-primary-500 focus:ring-primary-500"
          />
        </div>
        <div>{t('table.index')}</div>
        <div>{t('table.text')}</div>
        <div>{t('table.voice')}</div>
        <div>{t('table.status')}</div>
        <div>{t('table.duration')}</div>
        <div></div>
      </div>

      {/* Body */}
      <div className="max-h-[500px] overflow-y-auto">
        {lines.map((line, arrayIndex) => {
          const status = STATUS_CONFIG[line.status];
          const isSelected = selectedIds.has(line.id);

          return (
            <div
              key={line.id}
              onDragOver={(e) => { if (onReorder) handleDragOver(e, arrayIndex); }}
              onDragLeave={onReorder ? handleDragLeave : undefined}
              onDrop={(e) => { if (onReorder) handleDrop(e, arrayIndex); }}
              onContextMenu={(e) => handleContextMenu(e, line)}
              className={`
                grid gap-2 px-3 py-2
                border-b border-surface-800/50 text-sm
                transition-colors duration-100
                ${onReorder ? 'grid-cols-[24px_40px_50px_1fr_180px_100px_80px_60px]' : 'grid-cols-[40px_50px_1fr_180px_100px_80px_60px]'}
                ${isSelected ? 'bg-primary-500/10' : 'hover:bg-surface-800/50'}
                ${line.status === 'error' ? 'bg-red-500/5' : ''}
                ${draggedIndex === arrayIndex ? 'opacity-50' : ''}
                ${dragOverIndex === arrayIndex ? 'border-t-2 border-t-primary-500' : ''}
              `}
            >
              {/* Drag Handle */}
              {onReorder && (
                <div 
                  draggable
                  onDragStart={(e) => handleDragStart(e, arrayIndex)}
                  onDragEnd={handleDragEnd}
                  className="flex items-center justify-center cursor-grab active:cursor-grabbing text-surface-600 hover:text-surface-400"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8h16M4 16h16" />
                  </svg>
                </div>
              )}

              {/* Checkbox */}
              <div className="flex items-center justify-center">
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={(e) => handleSelectRow(line.id, e.target.checked)}
                  className="w-4 h-4 rounded border-surface-600 bg-surface-800 text-primary-500 focus:ring-primary-500"
                />
              </div>

              {/* Index */}
              <div className="flex items-center text-surface-500 font-mono text-xs">
                {line.index + 1}
              </div>

              {/* Text */}
              <div 
                className={`flex items-center min-w-0 cursor-text rounded px-1 -mx-1 transition-colors ${
                  editingLine?.id === line.id ? 'bg-primary-500/20 ring-1 ring-primary-500/50' : 'hover:bg-surface-700/50'
                }`}
                onDoubleClick={() => handleDoubleClick(line)}
                title="Double-click to edit"
              >
                <span 
                  className="truncate" 
                  title={line.text}
                >
                  {line.text}
                </span>
              </div>

              {/* Voice */}
              <div className="flex items-center">
                <select
                  value={line.voice_id || ''}
                  onChange={(e) => {
                    const voice = voices.find(v => v.voice_id === e.target.value);
                    if (voice) {
                      onVoiceChange(line.id, voice.voice_id, voice.name);
                    }
                  }}
                  className="w-full px-2 py-1 bg-surface-800 border border-surface-700 rounded text-xs truncate focus:outline-none focus:border-primary-500"
                >
                  <option value="">Select voice...</option>
                  {voices.map((voice) => (
                    <option key={voice.voice_id} value={voice.voice_id}>
                      {voice.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Status */}
              <div className="flex items-center gap-1.5">
                <span className={`${status.color} ${line.status === 'processing' ? 'animate-pulse' : ''}`}>
                  {status.icon}
                </span>
                <span className={`text-xs ${status.color}`}>
                  {t(status.labelKey)}
                </span>
              </div>

              {/* Duration */}
              <div className="flex items-center text-surface-500 text-xs font-mono">
                {formatDuration(line.audio_duration)}
              </div>

              {/* Actions */}
              <div className="flex items-center gap-1">
                {line.status === 'done' && line.output_path && (
                  <button
                    onClick={() => onPlayAudio(line.id)}
                    className="p-1 text-surface-400 hover:text-primary-400 transition-colors"
                    title="Play audio"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                    </svg>
                  </button>
                )}
                {line.status === 'error' && (
                  <button
                    onClick={() => onRetry([line.id])}
                    className="p-1 text-surface-400 hover:text-yellow-400 transition-colors"
                    title="Retry"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      {selectedIds.size > 0 && (
        <div className="flex items-center justify-between px-3 py-2 bg-surface-850 border-t border-surface-800">
          <span className="text-sm text-surface-400">
            {selectedIds.size} / {lines.length} {t('table.selected')}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onRetry(Array.from(selectedIds))}
              className="px-3 py-1 text-xs bg-yellow-500/20 text-yellow-400 rounded hover:bg-yellow-500/30 transition-colors"
            >
              {t('table.retry_selected')}
            </button>
            <button
              onClick={() => onDelete(Array.from(selectedIds))}
              className="px-3 py-1 text-xs bg-red-500/20 text-red-400 rounded hover:bg-red-500/30 transition-colors"
            >
              {t('table.delete_selected')}
            </button>
          </div>
        </div>
      )}

      {/* Side Edit Panel */}
      {editingLine && (
        <div className="fixed inset-0 z-50 flex justify-end">
          {/* Backdrop */}
          <div 
            className="absolute inset-0 bg-black/40"
            onClick={handleEditCancel}
          />
          
          {/* Panel */}
          <div className="relative w-full max-w-md bg-surface-900 border-l border-surface-700 shadow-2xl flex flex-col animate-in slide-in-from-right duration-200">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-surface-700 bg-surface-800/50">
              <div className="flex items-center gap-3">
                <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary-500/20 text-primary-400 font-mono text-sm font-medium">
                  {editingLine.index + 1}
                </div>
                <div>
                  <h3 className="text-sm font-medium text-surface-100">Edit Line</h3>
                  <p className="text-xs text-surface-500">Line #{editingLine.index + 1}</p>
                </div>
              </div>
              <button
                onClick={handleEditCancel}
                className="p-1.5 text-surface-400 hover:text-surface-200 hover:bg-surface-700 rounded-lg transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 p-4 overflow-y-auto">
              <div className="space-y-3">
                <label className="block text-sm font-medium text-surface-300">
                  Text Content
                </label>
                <textarea
                  ref={textareaRef}
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="w-full h-48 px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm text-surface-100 resize-none focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500/50"
                  placeholder="Enter text..."
                />
                <div className="flex items-center justify-between text-xs text-surface-500">
                  <span>{editText.length} characters</span>
                  <span className="text-surface-600">Ctrl+Enter to save, Esc to cancel</span>
                </div>
              </div>

              {/* Original text reference */}
              {editText !== editingLine.text && (
                <div className="mt-4 p-3 bg-surface-800/50 rounded-lg border border-surface-700">
                  <div className="text-xs text-surface-500 mb-1">Original text:</div>
                  <div className="text-xs text-surface-400 line-clamp-3">{editingLine.text}</div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-surface-700 bg-surface-800/50">
              <button
                onClick={handleEditCancel}
                className="px-4 py-2 text-sm font-medium text-surface-300 hover:text-surface-100 hover:bg-surface-700 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleEditSubmit}
                disabled={!editText.trim() || editText === editingLine.text}
                className="px-4 py-2 text-sm font-medium text-white bg-primary-500 hover:bg-primary-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
