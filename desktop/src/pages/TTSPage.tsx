import { useState, useEffect, useCallback, useRef } from 'react';
import { useAppStore } from '../stores/appStore';
import { ipcClient } from '../lib/ipc';
import { getPlatformAPI } from '../lib/platform';
import DropZone from '../components/DropZone';
import LineTable from '../components/LineTable';
import ProcessingControls from '../components/ProcessingControls';
import VoiceSettings from '../components/VoiceSettings';

export default function TTSPage() {
  console.log('[TTSPage] Rendering...');
  
  const {
    voices,
    setVoices,
    lines,
    addLines,
    updateLine,
    updateLineStatus,
    deleteLines,
    clearLines,
    selectedLineIds,
    setSelectedLineIds,
    setLineVoice,
    setAllLinesVoice,
    defaultVoiceId,
    defaultVoiceName,
    setDefaultVoice,
    outputFolder,
    setOutputFolder,
    totalCredits,
    setTotalCredits,
    isProcessing,
    setProcessing,
    isPaused,
    setPaused,
    processingStats,
    updateProcessingStats,
    resetProcessingStats,
  } = useAppStore();
  
  console.log('[TTSPage] State:', { voicesCount: voices.length, linesCount: lines.length, outputFolder });

  const [isLoadingVoices, setIsLoadingVoices] = useState(false);
  const [, setIsImporting] = useState(false);
  const [voiceSettings, setVoiceSettings] = useState({
    stability: 0.5,
    similarityBoost: 0.75,
    style: 0,
    speed: 1.0,
    useSpeakerBoost: true,
    modelId: 'eleven_v3',
  });
  const processingRef = useRef(false);

  useEffect(() => {
    loadVoices();
    loadConfig();

    const unsubCredits = ipcClient.onCreditsUpdate(({ total }) => setTotalCredits(total));

    return () => {
      unsubCredits();
    };
  }, []);

  async function loadVoices() {
    setIsLoadingVoices(true);
    try {
      const voiceList = await ipcClient.getVoices();
      setVoices(voiceList);
    } catch (err) {
      console.error('Failed to load voices:', err);
    } finally {
      setIsLoadingVoices(false);
    }
  }

  async function loadConfig() {
    try {
      const config = await ipcClient.getConfig();
      setOutputFolder(config.default_output_folder);
    } catch (err) {
      console.error('Failed to load config:', err);
    }
  }

  const handleRefreshVoices = async () => {
    setIsLoadingVoices(true);
    try {
      const voiceList = await ipcClient.refreshVoices();
      setVoices(voiceList);
    } catch (err) {
      console.error('Failed to refresh voices:', err);
    } finally {
      setIsLoadingVoices(false);
    }
  };

  const handleFilesDropped = useCallback(async (files: string[]) => {
    setIsImporting(true);
    try {
      const result = await ipcClient.importFiles(files, {
        auto_split: true,
        max_chars: 5000,
      });
      
      if (result.errors.length > 0) {
        console.error('Import errors:', result.errors);
      }
      
      if (result.lines.length > 0) {
        // Convert to the format expected by addLines
        const texts = result.lines.map(l => l.text);
        const sourceFile = result.lines[0]?.source_file || undefined;
        addLines(texts, sourceFile);
      }
    } catch (err) {
      console.error('Failed to import files:', err);
    } finally {
      setIsImporting(false);
    }
  }, [addLines]);

  const handleSelectFolder = async () => {
    try {
      const api = await getPlatformAPI();
      const folder = await api.dialog.openDirectory('Select Output Folder');
      if (folder) {
        setOutputFolder(folder);
      }
    } catch (err) {
      console.error('Failed to open folder dialog:', err);
    }
  };

  const handleVoiceChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const voiceId = e.target.value;
    const voice = voices.find((v) => v.voice_id === voiceId);
    if (voice) {
      setDefaultVoice(voice.voice_id, voice.name);
      // Apply to all lines without a voice
      lines.forEach((line) => {
        if (!line.voice_id) {
          setLineVoice(line.id, voice.voice_id, voice.name);
        }
      });
    }
  };

  const handleApplyVoiceToAll = () => {
    if (defaultVoiceId && defaultVoiceName) {
      setAllLinesVoice(defaultVoiceId, defaultVoiceName);
    }
  };

  const handleStartProcessing = async () => {
    if (lines.length === 0 || !outputFolder) return;

    setProcessing(true);
    processingRef.current = true;
    resetProcessingStats();

    const pendingLines = lines.filter((l) => l.status === 'pending');
    let completed = 0;
    let failed = 0;
    const startTime = Date.now();

    for (const line of pendingLines) {
      if (!processingRef.current) break; // Check if stopped

      if (!line.voice_id) {
        updateLineStatus(line.id, 'error', 'No voice selected');
        failed++;
        continue;
      }

      updateLineStatus(line.id, 'processing');
      updateProcessingStats({ processing: 1 });

      try {
        const outputPath = `${outputFolder}\\${String(line.index + 1).padStart(4, '0')}_${Date.now()}.mp3`;
        const result = await ipcClient.startTTSJob({
          text: line.text,
          voice_id: line.voice_id,
          output_path: outputPath,
          model_id: voiceSettings.modelId,
          voice_settings: {
            stability: voiceSettings.stability,
            similarity_boost: voiceSettings.similarityBoost,
            style: voiceSettings.style,
            use_speaker_boost: voiceSettings.useSpeakerBoost,
          },
        });

        updateLine(line.id, {
          status: 'done',
          output_path: result.output_path,
          audio_duration: result.duration_ms / 1000,
        });
        completed++;
      } catch (err) {
        updateLineStatus(line.id, 'error', err instanceof Error ? err.message : 'Unknown error');
        failed++;
      }

      const elapsed = (Date.now() - startTime) / 1000;
      updateProcessingStats({
        completed,
        failed,
        pending: pendingLines.length - completed - failed,
        processing: 0,
        elapsed_seconds: elapsed,
        characters_processed: lines
          .filter((l) => l.status === 'done')
          .reduce((sum, l) => sum + l.text.length, 0),
      });
    }

    setProcessing(false);
    processingRef.current = false;
  };

  const handlePauseProcessing = () => {
    setPaused(true);
  };

  const handleResumeProcessing = () => {
    setPaused(false);
  };

  const handleStopProcessing = () => {
    processingRef.current = false;
    setProcessing(false);
    setPaused(false);
  };

  const handlePlayAudio = async (id: string) => {
    const line = lines.find((l) => l.id === id);
    if (line?.output_path) {
      try {
        // Open file with default player using shell
        const { open } = await import('@tauri-apps/plugin-shell');
        await open(line.output_path);
      } catch (err) {
        console.error('Failed to open file:', err);
      }
    }
  };

  const handleRetry = (ids: string[]) => {
    ids.forEach((id) => {
      updateLineStatus(id, 'pending');
    });
  };

  const handleJoinMP3 = async () => {
    const completedLines = lines.filter((l) => l.status === 'done' && l.output_path);
    if (completedLines.length === 0) return;

    const outputPath = `${outputFolder}\\joined_${Date.now()}.mp3`;
    const inputFiles = completedLines.map((l) => l.output_path!);

    try {
      const result = await ipcClient.concatenateAudio(inputFiles, outputPath, {
        silence_gap: 0.3,
      });
      if (result.success) {
        alert(`MP3 joined successfully: ${result.output_path}`);
      }
    } catch (err) {
      alert(`Failed to join MP3: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  const handleGenerateSRT = async () => {
    const completedLines = lines.filter((l) => l.status === 'done' && l.audio_duration);
    if (completedLines.length === 0) return;

    const outputPath = `${outputFolder}\\subtitles_${Date.now()}.srt`;
    const srtLines = completedLines.map((l) => ({
      index: l.index,
      text: l.text,
      audio_duration: l.audio_duration,
    }));

    try {
      const result = await ipcClient.generateSRT(srtLines, outputPath, {
        gap: 0.1,
      });
      if (result.success) {
        alert(`SRT generated successfully: ${result.output_path}`);
      }
    } catch (err) {
      alert(`Failed to generate SRT: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  const handleClearAll = () => {
    if (confirm('Are you sure you want to clear all lines?')) {
      clearLines();
    }
  };

  const totalCharacters = lines.reduce((sum, l) => sum + l.text.length, 0);
  const pendingCount = lines.filter((l) => l.status === 'pending').length;
  const completedCount = lines.filter((l) => l.status === 'done').length;

  return (
    <div className="h-full flex flex-col gap-4 p-4 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-xl font-semibold text-surface-100">Text to Speech</h1>
          <p className="text-sm text-surface-500">
            {lines.length} lines | {totalCharacters.toLocaleString()} characters
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-sm text-surface-400">
            Credits: <span className="text-primary-400 font-medium">{totalCredits.toLocaleString()}</span>
          </div>
        </div>
      </div>

      {/* Controls bar */}
      <div className="flex items-center gap-4 shrink-0">
        {/* Voice selector */}
        <div className="flex items-center gap-2">
          <label className="text-sm text-surface-400">Voice:</label>
          <select
            value={defaultVoiceId || ''}
            onChange={handleVoiceChange}
            disabled={isLoadingVoices}
            className="w-64 px-3 py-1.5 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-primary-500"
          >
            <option value="">Select default voice...</option>
            {voices.map((voice) => (
              <option key={voice.voice_id} value={voice.voice_id}>
                {voice.name} ({voice.category})
              </option>
            ))}
          </select>
          <button
            onClick={handleRefreshVoices}
            disabled={isLoadingVoices}
            className="p-1.5 text-surface-400 hover:text-surface-200 transition-colors"
            title="Refresh voices"
          >
            <svg className={`w-4 h-4 ${isLoadingVoices ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
          {lines.length > 0 && (
            <button
              onClick={handleApplyVoiceToAll}
              disabled={!defaultVoiceId}
              className="px-2 py-1 text-xs bg-surface-800 text-surface-400 rounded hover:bg-surface-700 disabled:opacity-50"
            >
              Apply to all
            </button>
          )}
        </div>

        {/* Output folder */}
        <div className="flex items-center gap-2 flex-1">
          <label className="text-sm text-surface-400">Output:</label>
          <input
            type="text"
            value={outputFolder}
            onChange={(e) => setOutputFolder(e.target.value)}
            className="flex-1 px-3 py-1.5 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-primary-500"
            placeholder="Select output folder..."
          />
          <button
            onClick={handleSelectFolder}
            className="p-1.5 text-surface-400 hover:text-surface-200 transition-colors"
            title="Browse"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
          </button>
        </div>
      </div>

      {/* Drop zone (compact when lines exist) */}
      <div className="shrink-0">
        <DropZone onFilesDropped={handleFilesDropped} compact={lines.length > 0} />
      </div>

      {/* Lines table */}
      <div className="flex-1 min-h-0 overflow-auto">
        <LineTable
          lines={lines}
          voices={voices}
          selectedIds={selectedLineIds}
          onSelectionChange={setSelectedLineIds}
          onTextEdit={(id, text) => updateLine(id, { text })}
          onVoiceChange={setLineVoice}
          onDelete={deleteLines}
          onRetry={handleRetry}
          onPlayAudio={handlePlayAudio}
        />
      </div>

      {/* Voice settings */}
      {lines.length > 0 && (
        <div className="shrink-0">
          <VoiceSettings
            stability={voiceSettings.stability}
            similarityBoost={voiceSettings.similarityBoost}
            style={voiceSettings.style}
            speed={voiceSettings.speed}
            useSpeakerBoost={voiceSettings.useSpeakerBoost}
            modelId={voiceSettings.modelId}
            onChange={setVoiceSettings}
          />
        </div>
      )}

      {/* Processing controls */}
      {lines.length > 0 && (
        <div className="shrink-0 p-4 bg-surface-900 rounded-lg border border-surface-800 space-y-4">
          <ProcessingControls
            isProcessing={isProcessing}
            isPaused={isPaused}
            stats={{
              ...processingStats,
              total: lines.length,
              pending: pendingCount,
            }}
            onStart={handleStartProcessing}
            onPause={handlePauseProcessing}
            onResume={handleResumeProcessing}
            onStop={handleStopProcessing}
            disabled={!outputFolder || !defaultVoiceId || pendingCount === 0}
          />

          {/* Post-processing buttons */}
          <div className="flex items-center justify-between pt-4 border-t border-surface-800">
            <div className="flex items-center gap-2">
              <button
                onClick={handleJoinMP3}
                disabled={completedCount < 2}
                className="px-3 py-1.5 text-sm bg-surface-800 text-surface-300 rounded-lg hover:bg-surface-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <svg className="w-4 h-4 inline mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                Join MP3 ({completedCount})
              </button>
              <button
                onClick={handleGenerateSRT}
                disabled={completedCount === 0}
                className="px-3 py-1.5 text-sm bg-surface-800 text-surface-300 rounded-lg hover:bg-surface-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <svg className="w-4 h-4 inline mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Generate SRT
              </button>
            </div>
            <button
              onClick={handleClearAll}
              disabled={isProcessing}
              className="px-3 py-1.5 text-sm text-red-400 hover:bg-red-500/10 rounded-lg disabled:opacity-50 transition-colors"
            >
              Clear All
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
