import { useState, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { getPlatformAPI } from '../lib/platform';
import { ipcClient, TranscriptionResult } from '../lib/ipc';
import { useTranslation } from '../lib/i18n';
import { useAppStore } from '../stores/appStore';

export default function TranscribePage() {
  const { t } = useTranslation();
  const { setTotalCredits } = useAppStore();
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<TranscriptionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // Options
  const [language, setLanguage] = useState<string>('');
  const [enableDiarization, setEnableDiarization] = useState(false);
  const [numSpeakers, setNumSpeakers] = useState<number | undefined>(undefined);

  const handleSelectFile = useCallback(async () => {
    try {
      const api = await getPlatformAPI();
      const files = await api.dialog.openFile({
        title: 'Select Audio/Video File',
        filters: [
          {
            name: 'Media',
            extensions: ['mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac', 'wma', 'mp4', 'mkv', 'avi', 'mov', 'webm'],
          },
        ],
      });
      if (files && files.length > 0) {
        setSelectedFile(files[0]);
        setResult(null);
        setError(null);
      }
    } catch (err) {
      console.error('Failed to open file dialog:', err);
    }
  }, []);

  const handleTranscribe = useCallback(async () => {
    if (!selectedFile) return;
    setIsProcessing(true);
    setProgress(0);
    setResult(null);
    setError(null);

    try {
      const result = await ipcClient.startTranscription({
        file_path: selectedFile,
        language: language || undefined,
        diarize: enableDiarization,
        num_speakers: enableDiarization ? numSpeakers : undefined,
      });
      setResult(result);
      
      // Refresh credits after transcription
      const credits = await ipcClient.getCredits();
      setTotalCredits(credits);
    } catch (err) {
      console.error('Transcription failed:', err);
      setError(err instanceof Error ? err.message : 'Transcription failed');
    } finally {
      setIsProcessing(false);
      setProgress(100);
    }
  }, [selectedFile, language, enableDiarization, numSpeakers, setTotalCredits]);

  const handleExport = useCallback(async (format: 'txt' | 'srt' | 'json') => {
    if (!result) return;

    try {
      const api = await getPlatformAPI();
      const fileName = selectedFile?.replace(/\.[^/.]+$/, '') || 'transcription';
      const savePath = await api.dialog.saveFile({
        title: `Export as ${format.toUpperCase()}`,
        defaultPath: `${fileName}.${format}`,
        filters: [{ name: format.toUpperCase(), extensions: [format] }],
      });

      if (!savePath) return;

      let content = '';
      if (format === 'txt') {
        content = result.text;
      } else if (format === 'srt') {
        content = result.segments.map((seg, i) => {
          const start = formatTime(seg.start);
          const end = formatTime(seg.end);
          const speaker = seg.speaker_id ? `[${seg.speaker_id}] ` : '';
          return `${i + 1}\n${start} --> ${end}\n${speaker}${seg.text}\n`;
        }).join('\n');
      } else if (format === 'json') {
        content = JSON.stringify(result, null, 2);
      }

      // Write file via invoke
      await invoke('write_text_file', { path: savePath, contents: content });
      
    } catch (err) {
      console.error('Export failed:', err);
      setError('Failed to export file');
    }
  }, [result, selectedFile]);

  const handleCopyToTTS = useCallback(() => {
    if (!result) return;
    // Copy text to clipboard or navigate to TTS with text
    navigator.clipboard.writeText(result.text);
  }, [result]);

  const formatTime = (seconds: number): string => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 1000);
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')},${ms.toString().padStart(3, '0')}`;
  };

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="h-full flex flex-col gap-4 p-4 overflow-hidden">
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-xl font-semibold text-surface-100">{t('transcribe.title')}</h1>
          <p className="text-sm text-surface-500">{t('transcribe.drop_media')}</p>
        </div>
      </div>

      {/* File Selection */}
      <div className="card shrink-0 space-y-4">
        <div>
          <label className="block text-sm font-medium text-surface-300 mb-2">
            Audio/Video File
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={selectedFile || ''}
              readOnly
              placeholder="Select a media file..."
              className="flex-1 px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm"
            />
            <button onClick={handleSelectFile} className="btn-secondary">
              Browse
            </button>
          </div>
          <p className="text-xs text-surface-500 mt-1">
            Supported: MP3, WAV, M4A, FLAC, OGG, AAC, MP4, MKV, AVI, MOV, WebM
          </p>
        </div>

        {/* Options */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-surface-300 mb-2">
              {t('transcribe.language')}
            </label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm"
            >
              <option value="">{t('transcribe.auto_detect')}</option>
              <option value="en">English</option>
              <option value="vi">Vietnamese</option>
              <option value="zh">Chinese</option>
              <option value="ja">Japanese</option>
              <option value="ko">Korean</option>
              <option value="fr">French</option>
              <option value="de">German</option>
              <option value="es">Spanish</option>
              <option value="pt">Portuguese</option>
              <option value="ru">Russian</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-300 mb-2">
              {t('transcribe.identify_speakers')}
            </label>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={enableDiarization}
                  onChange={(e) => setEnableDiarization(e.target.checked)}
                  className="w-4 h-4 rounded border-surface-600 bg-surface-800"
                />
                <span className="text-sm text-surface-300">{t('common.enable')}</span>
              </label>
              {enableDiarization && (
                <input
                  type="number"
                  min={2}
                  max={10}
                  value={numSpeakers || ''}
                  onChange={(e) => setNumSpeakers(e.target.value ? parseInt(e.target.value) : undefined)}
                  placeholder={t('transcribe.num_speakers')}
                  className="w-24 px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm"
                />
              )}
            </div>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            onClick={handleTranscribe}
            disabled={!selectedFile || isProcessing}
            className="btn-primary"
          >
            {isProcessing ? (
              <>
                <svg className="w-4 h-4 mr-2 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                {t('tts.processing')}
              </>
            ) : (
              t('transcribe.start')
            )}
          </button>
        </div>

        {isProcessing && (
          <div className="w-full bg-surface-700 rounded-full h-2">
            <div
              className="bg-primary-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="flex-1 min-h-0 card flex flex-col">
          <div className="flex items-center justify-between mb-4 shrink-0">
            <div>
              <h2 className="text-lg font-medium text-surface-200">Result</h2>
              <p className="text-xs text-surface-500">
                Language: {result.language} | Segments: {result.segments.length}
                {result.speakers.length > 0 && ` | Speakers: ${result.speakers.length}`}
              </p>
            </div>
            <div className="flex gap-2">
              <button onClick={() => handleExport('txt')} className="btn-ghost text-sm">
                Export TXT
              </button>
              <button onClick={() => handleExport('srt')} className="btn-ghost text-sm">
                Export SRT
              </button>
              <button onClick={() => handleExport('json')} className="btn-ghost text-sm">
                Export JSON
              </button>
              <button onClick={handleCopyToTTS} className="btn-secondary text-sm">
                Copy to TTS
              </button>
            </div>
          </div>

          {/* Segments */}
          <div className="flex-1 min-h-0 overflow-y-auto space-y-2">
            {result.segments.length > 0 ? (
              result.segments.map((seg, i) => (
                <div
                  key={i}
                  className="p-3 bg-surface-800/50 rounded-lg border border-surface-700 hover:border-surface-600 transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-primary-400 font-mono">
                        {formatDuration(seg.start)} - {formatDuration(seg.end)}
                      </span>
                      {seg.speaker_id && (
                        <span className="text-xs px-2 py-0.5 bg-surface-700 rounded text-surface-300">
                          {seg.speaker_id}
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => navigator.clipboard.writeText(seg.text)}
                      className="text-surface-500 hover:text-surface-300"
                      title="Copy"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                    </button>
                  </div>
                  <p className="text-sm text-surface-200">{seg.text}</p>
                </div>
              ))
            ) : (
              <div className="p-4 bg-surface-800 rounded-lg">
                <p className="text-surface-300 whitespace-pre-wrap">{result.text}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
