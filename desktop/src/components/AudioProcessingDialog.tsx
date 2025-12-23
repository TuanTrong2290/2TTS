import { useState } from 'react';
import { ipcClient, AudioProcessingSettings } from '../lib/ipc';

interface AudioProcessingDialogProps {
  isOpen: boolean;
  onClose: () => void;
  files: Array<{ input_path: string; output_path: string }>;
  onComplete: (results: Array<{ input_path: string; success: boolean }>) => void;
}

export default function AudioProcessingDialog({
  isOpen,
  onClose,
  files,
  onComplete,
}: AudioProcessingDialogProps) {
  const [settings, setSettings] = useState<AudioProcessingSettings>({
    normalize: false,
    normalize_level: -3.0,
    fade_in: 0,
    fade_out: 0,
    silence_padding_start: 0,
    silence_padding_end: 0,
    trim_silence: false,
    trim_threshold: -40,
    speed: 1.0,
    pitch_shift: 0,
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0 });

  if (!isOpen) return null;

  const handleProcess = async () => {
    setIsProcessing(true);
    setProgress({ current: 0, total: files.length });

    try {
      const result = await ipcClient.batchProcessAudio(files, settings);
      onComplete(result.results.map(r => ({ input_path: r.input_path, success: r.success })));
      onClose();
    } catch (err) {
      console.error('Audio processing failed:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-surface-900 rounded-xl border border-surface-700 w-[500px] max-h-[80vh] overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-surface-700">
          <h2 className="text-lg font-semibold text-surface-100">Audio Post-Processing</h2>
          <button onClick={onClose} className="text-surface-400 hover:text-surface-200">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-4 space-y-4 overflow-y-auto max-h-[60vh]">
          <div className="text-sm text-surface-400 mb-4">
            Process {files.length} audio file{files.length !== 1 ? 's' : ''} with the settings below.
          </div>

          {/* Normalize */}
          <div className="space-y-2">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.normalize}
                onChange={(e) => setSettings({ ...settings, normalize: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <span className="text-sm text-surface-300">Normalize Audio</span>
            </label>
            {settings.normalize && (
              <div className="pl-7">
                <label className="text-xs text-surface-400">Target Level (dB)</label>
                <input
                  type="number"
                  value={settings.normalize_level}
                  onChange={(e) => setSettings({ ...settings, normalize_level: parseFloat(e.target.value) })}
                  className="w-24 px-2 py-1 bg-surface-800 border border-surface-700 rounded text-sm ml-2"
                />
              </div>
            )}
          </div>

          {/* Fade In/Out */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-surface-400 block mb-1">Fade In (seconds)</label>
              <input
                type="number"
                min={0}
                max={10}
                step={0.1}
                value={settings.fade_in}
                onChange={(e) => setSettings({ ...settings, fade_in: parseFloat(e.target.value) || 0 })}
                className="w-full px-2 py-1 bg-surface-800 border border-surface-700 rounded text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-surface-400 block mb-1">Fade Out (seconds)</label>
              <input
                type="number"
                min={0}
                max={10}
                step={0.1}
                value={settings.fade_out}
                onChange={(e) => setSettings({ ...settings, fade_out: parseFloat(e.target.value) || 0 })}
                className="w-full px-2 py-1 bg-surface-800 border border-surface-700 rounded text-sm"
              />
            </div>
          </div>

          {/* Silence Padding */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-surface-400 block mb-1">Silence at Start (sec)</label>
              <input
                type="number"
                min={0}
                max={10}
                step={0.1}
                value={settings.silence_padding_start}
                onChange={(e) => setSettings({ ...settings, silence_padding_start: parseFloat(e.target.value) || 0 })}
                className="w-full px-2 py-1 bg-surface-800 border border-surface-700 rounded text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-surface-400 block mb-1">Silence at End (sec)</label>
              <input
                type="number"
                min={0}
                max={10}
                step={0.1}
                value={settings.silence_padding_end}
                onChange={(e) => setSettings({ ...settings, silence_padding_end: parseFloat(e.target.value) || 0 })}
                className="w-full px-2 py-1 bg-surface-800 border border-surface-700 rounded text-sm"
              />
            </div>
          </div>

          {/* Trim Silence */}
          <div className="space-y-2">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={settings.trim_silence}
                onChange={(e) => setSettings({ ...settings, trim_silence: e.target.checked })}
                className="w-4 h-4 rounded"
              />
              <span className="text-sm text-surface-300">Trim Silence</span>
            </label>
            {settings.trim_silence && (
              <div className="pl-7">
                <label className="text-xs text-surface-400">Threshold (dB)</label>
                <input
                  type="number"
                  value={settings.trim_threshold}
                  onChange={(e) => setSettings({ ...settings, trim_threshold: parseFloat(e.target.value) })}
                  className="w-24 px-2 py-1 bg-surface-800 border border-surface-700 rounded text-sm ml-2"
                />
              </div>
            )}
          </div>

          {/* Speed & Pitch */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-surface-400 block mb-1">Speed ({settings.speed?.toFixed(2)}x)</label>
              <input
                type="range"
                min={0.5}
                max={2}
                step={0.05}
                value={settings.speed}
                onChange={(e) => setSettings({ ...settings, speed: parseFloat(e.target.value) })}
                className="w-full accent-primary-500"
              />
            </div>
            <div>
              <label className="text-xs text-surface-400 block mb-1">Pitch Shift ({settings.pitch_shift} semitones)</label>
              <input
                type="range"
                min={-12}
                max={12}
                step={1}
                value={settings.pitch_shift}
                onChange={(e) => setSettings({ ...settings, pitch_shift: parseFloat(e.target.value) })}
                className="w-full accent-primary-500"
              />
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 px-4 py-3 border-t border-surface-700">
          <button onClick={onClose} className="btn-ghost">Cancel</button>
          <button
            onClick={handleProcess}
            disabled={isProcessing || files.length === 0}
            className="btn-primary"
          >
            {isProcessing ? (
              <>
                <svg className="w-4 h-4 mr-2 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Processing {progress.current}/{progress.total}...
              </>
            ) : (
              `Process ${files.length} File${files.length !== 1 ? 's' : ''}`
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
