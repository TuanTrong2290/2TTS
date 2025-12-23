import { useState, useCallback } from 'react';
import { TextLine, LineStatus, Voice } from '../lib/ipc/types';

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
}

const STATUS_CONFIG: Record<LineStatus, { label: string; color: string; icon: string }> = {
  pending: { label: 'Pending', color: 'text-surface-400', icon: '○' },
  processing: { label: 'Processing', color: 'text-yellow-400', icon: '◐' },
  done: { label: 'Done', color: 'text-green-400', icon: '✓' },
  error: { label: 'Error', color: 'text-red-400', icon: '✗' },
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
}: LineTableProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');

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
    setEditingId(line.id);
    setEditText(line.text);
  }, []);

  const handleEditSubmit = useCallback(() => {
    if (editingId && editText.trim()) {
      onTextEdit(editingId, editText.trim());
    }
    setEditingId(null);
    setEditText('');
  }, [editingId, editText, onTextEdit]);

  const handleEditCancel = useCallback(() => {
    setEditingId(null);
    setEditText('');
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleEditSubmit();
    } else if (e.key === 'Escape') {
      handleEditCancel();
    }
  }, [handleEditSubmit, handleEditCancel]);

  const handleContextMenu = useCallback((e: React.MouseEvent, line: TextLine) => {
    e.preventDefault();
    // Select the row if not already selected
    if (!selectedIds.has(line.id)) {
      onSelectionChange(new Set([line.id]));
    }
  }, [selectedIds, onSelectionChange]);

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
        <h3 className="text-lg font-medium text-surface-300 mb-2">No lines yet</h3>
        <p className="text-sm text-surface-500 max-w-md">
          Import files using drag & drop or the import button to get started.
          Supported formats: SRT, TXT, DOCX
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-surface-800">
      {/* Header */}
      <div className="grid grid-cols-[40px_50px_1fr_180px_100px_80px_60px] gap-2 px-3 py-2 bg-surface-850 border-b border-surface-800 text-xs font-medium text-surface-400 uppercase tracking-wider">
        <div className="flex items-center justify-center">
          <input
            type="checkbox"
            checked={allSelected}
            ref={(el) => el && (el.indeterminate = someSelected)}
            onChange={(e) => handleSelectAll(e.target.checked)}
            className="w-4 h-4 rounded border-surface-600 bg-surface-800 text-primary-500 focus:ring-primary-500"
          />
        </div>
        <div>#</div>
        <div>Text</div>
        <div>Voice</div>
        <div>Status</div>
        <div>Duration</div>
        <div></div>
      </div>

      {/* Body */}
      <div className="max-h-[500px] overflow-y-auto">
        {lines.map((line) => {
          const status = STATUS_CONFIG[line.status];
          const isSelected = selectedIds.has(line.id);
          const isEditing = editingId === line.id;

          return (
            <div
              key={line.id}
              onContextMenu={(e) => handleContextMenu(e, line)}
              className={`
                grid grid-cols-[40px_50px_1fr_180px_100px_80px_60px] gap-2 px-3 py-2
                border-b border-surface-800/50 text-sm
                transition-colors duration-100
                ${isSelected ? 'bg-primary-500/10' : 'hover:bg-surface-800/50'}
                ${line.status === 'error' ? 'bg-red-500/5' : ''}
              `}
            >
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
                className="flex items-center min-w-0"
                onDoubleClick={() => handleDoubleClick(line)}
              >
                {isEditing ? (
                  <textarea
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    onBlur={handleEditSubmit}
                    onKeyDown={handleKeyDown}
                    autoFocus
                    className="w-full px-2 py-1 bg-surface-800 border border-primary-500 rounded text-sm resize-none focus:outline-none"
                    rows={2}
                  />
                ) : (
                  <span 
                    className="truncate cursor-text hover:text-surface-200" 
                    title={line.text}
                  >
                    {line.text}
                  </span>
                )}
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
                  {status.label}
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
            {selectedIds.size} of {lines.length} selected
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onRetry(Array.from(selectedIds))}
              className="px-3 py-1 text-xs bg-yellow-500/20 text-yellow-400 rounded hover:bg-yellow-500/30 transition-colors"
            >
              Retry Selected
            </button>
            <button
              onClick={() => onDelete(Array.from(selectedIds))}
              className="px-3 py-1 text-xs bg-red-500/20 text-red-400 rounded hover:bg-red-500/30 transition-colors"
            >
              Delete Selected
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
