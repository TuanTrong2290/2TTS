import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useAppStore } from '../stores/appStore';
import { ipcClient, AudioProcessingSettings } from '../lib/ipc';
import { getPlatformAPI } from '../lib/platform';
import DropZone from '../components/DropZone';
import LineTable from '../components/LineTable';
import ProcessingControls from '../components/ProcessingControls';
import VoiceSettings from '../components/VoiceSettings';
import VoiceLibraryDialog from '../components/VoiceLibraryDialog';
import ConfirmDialog from '../components/ConfirmDialog';
import { detectLanguage, DetectedLanguage } from '../lib/languageDetect';
import { useTranslation } from '../lib/i18n';

// Processing mode options
type ProcessingMode = 'sequential' | 'parallel';

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
    setTotalCredits,
    isProcessing,
    setProcessing,
    isPaused,
    setPaused,
    processingStats,
    updateProcessingStats,
    resetProcessingStats,
    favoriteVoiceIds,
    toggleFavoriteVoice,
    voicePresets,
    addVoicePreset,
    removeVoicePreset,
    reorderLines,
    exportHistory,
    addExportEntry,
    clearExportHistory,
    hasRecoveryData,
    saveRecoveryData,
    clearRecoveryData,
    restoreFromRecovery,
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
    pauseSettings: {
      enabled: false,
      shortPauseDuration: 300,
      longPauseDuration: 700,
    },
  });
  const processingRef = useRef(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [showLogs, setShowLogs] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const [showVoiceLibrary, setShowVoiceLibrary] = useState(false);
  const [, setIsRefreshingCredits] = useState(false);
  const [debugMode, setDebugMode] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [showRecoveryDialog, setShowRecoveryDialog] = useState(false);
  const [showExportHistory, setShowExportHistory] = useState(false);
  const [, setCurrentSessionFolder] = useState<string>('');
  const { t } = useTranslation();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [lastDebugData, setLastDebugData] = useState<Record<string, any> | null>(null);
  
  // New feature states
  const [processingMode, setProcessingMode] = useState<ProcessingMode>('parallel');
  const [threadCount, setThreadCount] = useState(3);
  const [showPostProcessDialog, setShowPostProcessDialog] = useState(false);
  const [postProcessSettings, setPostProcessSettings] = useState<AudioProcessingSettings>({
    normalize: false,
    normalize_level: -3,
    fade_in: 0,
    fade_out: 0,
    trim_silence: false,
    trim_threshold: -40,
    speed: 1.0,
  });
  const [isPostProcessing, setIsPostProcessing] = useState(false);
  const [projectName, setProjectName] = useState('Untitled');

  const addLog = useCallback((msg: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prev => [...prev.slice(-50), `[${timestamp}] ${msg}`]);
    setTimeout(() => logsEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
  }, []);

  useEffect(() => {
    loadVoices();
    loadConfig();
    loadCredits();

    const unsubCredits = ipcClient.onCreditsUpdate(({ total }) => setTotalCredits(total));

    // Check for recovery data on mount
    if (hasRecoveryData) {
      setShowRecoveryDialog(true);
    }

    return () => {
      unsubCredits();
    };
  }, []);

  // Auto-save recovery data when lines change
  useEffect(() => {
    if (lines.length > 0) {
      saveRecoveryData();
    }
  }, [lines, outputFolder, defaultVoiceId]);

  // Auto-save every 30 seconds if there are lines
  useEffect(() => {
    const interval = setInterval(() => {
      if (lines.length > 0) {
        saveRecoveryData();
      }
    }, 30000);
    return () => clearInterval(interval);
  }, [lines.length]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in inputs
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLSelectElement) {
        return;
      }

      // Ctrl+S: Save project
      if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        handleSaveProject();
      }
      // Ctrl+O: Open project
      else if (e.ctrlKey && e.key === 'o') {
        e.preventDefault();
        handleLoadProject();
      }
      // F5 or Ctrl+Enter: Start processing
      else if ((e.key === 'F5' || (e.ctrlKey && e.key === 'Enter')) && !isProcessing && lines.length > 0 && outputFolder && defaultVoiceId) {
        e.preventDefault();
        handleStartProcessing();
      }
      // Escape: Stop processing
      else if (e.key === 'Escape' && isProcessing) {
        e.preventDefault();
        handleStopProcessing();
      }
      // Space: Pause/Resume (only during processing)
      else if (e.key === ' ' && isProcessing) {
        e.preventDefault();
        if (isPaused) {
          handleResumeProcessing();
        } else {
          handlePauseProcessing();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isProcessing, isPaused, lines.length, outputFolder, defaultVoiceId]);

  async function loadCredits() {
    setIsRefreshingCredits(true);
    try {
      const credits = await ipcClient.getCredits();
      setTotalCredits(credits);
    } catch (err) {
      console.error('Failed to load credits:', err);
    } finally {
      setIsRefreshingCredits(false);
    }
  }

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
        
        // Auto-apply voice patterns to new lines
        try {
          const lineData = result.lines.map(l => ({ id: l.id, text: l.text }));
          const matches = await ipcClient.batchMatchVoices(lineData);
          let matchCount = 0;
          matches.forEach((match) => {
            if (match.matched && match.voice_id && match.voice_name) {
              setLineVoice(match.id, match.voice_id, match.voice_name);
              matchCount++;
            }
          });
          if (matchCount > 0) {
            addLog(`Auto-assigned voices to ${matchCount} lines using patterns`);
          }
        } catch (err) {
          console.error('Failed to auto-match voices:', err);
        }
      }
    } catch (err) {
      console.error('Failed to import files:', err);
    } finally {
      setIsImporting(false);
    }
  }, [addLines, setLineVoice, addLog]);

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

  const handleOpenOutputFolder = async () => {
    if (!outputFolder) return;
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('open_path', { path: outputFolder });
    } catch (err) {
      console.error('Failed to open output folder:', err);
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

  // Pre-process text with pause markers if enabled
  const preprocessText = async (text: string): Promise<string> => {
    if (!voiceSettings.pauseSettings.enabled) return text;
    try {
      const result = await ipcClient.processPauses(text, {
        pause_enabled: true,
        short_pause_duration: voiceSettings.pauseSettings.shortPauseDuration,
        long_pause_duration: voiceSettings.pauseSettings.longPauseDuration,
      });
      return result.processed;
    } catch {
      return text;
    }
  };

  const handleStartProcessing = async () => {
    const pendingCount = lines.filter((l) => l.status === 'pending').length;
    addLog(`Start clicked - Mode: ${processingMode}, Threads: ${threadCount}, Lines: ${lines.length}, Pending: ${pendingCount}`);

    if (lines.length === 0 || !outputFolder) {
      addLog('ERROR: Aborted - no lines or output folder');
      return;
    }

    setProcessing(true);
    processingRef.current = true;
    resetProcessingStats();

    const pendingLines = lines.filter((l) => l.status === 'pending');
    addLog(`Processing ${pendingLines.length} pending lines...`);
    
    // Create session folder with format h_m_s_dd_mm_yy
    const now = new Date();
    const sessionFolderName = `${now.getHours()}_${now.getMinutes()}_${now.getSeconds()}_${String(now.getDate()).padStart(2, '0')}_${String(now.getMonth() + 1).padStart(2, '0')}_${String(now.getFullYear()).slice(-2)}`;
    const sessionPath = `${outputFolder}\\${sessionFolderName}`;
    setCurrentSessionFolder(sessionFolderName);
    addLog(`Session folder: ${sessionFolderName}`);
    
    const startTime = Date.now();

    // PARALLEL MODE - Use batch TTS
    if (processingMode === 'parallel') {
      addLog(`Using parallel processing with ${threadCount} threads`);
      
      // Mark all as processing
      pendingLines.forEach(line => updateLineStatus(line.id, 'processing'));
      
      // Prepare batch data with preprocessed text
      const batchLines = await Promise.all(pendingLines.map(async (line) => {
        const processedText = await preprocessText(line.text);
        return {
          id: line.id,
          text: processedText,
          voice_id: line.voice_id || defaultVoiceId || '',
          output_path: `${sessionPath}\\${String(line.index + 1).padStart(4, '0')}.mp3`,
        };
      }));
      
      // Filter out lines without voice
      const validLines = batchLines.filter(l => l.voice_id);
      const invalidCount = batchLines.length - validLines.length;
      
      if (invalidCount > 0) {
        addLog(`Skipping ${invalidCount} lines without voice assignment`);
        pendingLines.filter(l => !l.voice_id).forEach(l => {
          updateLineStatus(l.id, 'error', 'No voice selected');
        });
      }
      
      if (validLines.length > 0) {
        try {
          const result = await ipcClient.startBatchTTS({
            lines: validLines,
            thread_count: threadCount,
            settings: {
              stability: voiceSettings.stability,
              similarity_boost: voiceSettings.similarityBoost,
              style: voiceSettings.style,
              use_speaker_boost: voiceSettings.useSpeakerBoost,
              speed: voiceSettings.speed,
            },
          });
          
          // Process results
          let completed = 0;
          let failed = invalidCount;
          
          result.results.forEach((r) => {
            const line = pendingLines.find(l => l.id === r.id);
            if (r.success && r.output_path) {
              updateLine(r.id, {
                status: 'done',
                output_path: r.output_path,
                audio_duration: (r.duration_ms || 0) / 1000,
              });
              completed++;
              
              if (line) {
                addExportEntry({
                  outputPath: r.output_path,
                  lineIndex: line.index,
                  lineText: line.text.substring(0, 100),
                  voiceName: line.voice_name || 'Unknown',
                  durationMs: r.duration_ms || 0,
                  sessionFolder: sessionFolderName,
                });
              }
            } else {
              updateLineStatus(r.id, 'error', r.error || 'Unknown error');
              failed++;
            }
          });
          
          addLog(`BATCH DONE - Completed: ${completed}, Failed: ${failed}`);
          
          const elapsed = (Date.now() - startTime) / 1000;
          updateProcessingStats({
            completed,
            failed,
            pending: 0,
            processing: 0,
            elapsed_seconds: elapsed,
            characters_processed: lines.filter(l => l.status === 'done').reduce((sum, l) => sum + l.text.length, 0),
          });
        } catch (err) {
          const errMsg = err instanceof Error ? err.message : 'Batch processing failed';
          addLog(`BATCH ERROR: ${errMsg}`);
          pendingLines.forEach(l => updateLineStatus(l.id, 'error', errMsg));
        }
      }
      
      loadCredits();
    } 
    // SEQUENTIAL MODE - Process one by one
    else {
      let completed = 0;
      let failed = 0;

      for (const line of pendingLines) {
        if (!processingRef.current) {
          addLog('Stopped by user');
          break;
        }

        // Wait while paused
        while (isPaused && processingRef.current) {
          await new Promise(resolve => setTimeout(resolve, 100));
        }

        if (!line.voice_id) {
          addLog(`Line ${line.index + 1}: ERROR - No voice selected`);
          updateLineStatus(line.id, 'error', 'No voice selected');
          failed++;
          continue;
        }

        addLog(`Line ${line.index + 1}: Processing "${line.text.substring(0, 30)}..."`);
        updateLineStatus(line.id, 'processing');
        updateProcessingStats({ processing: 1 });

        try {
          const outputPath = `${sessionPath}\\${String(line.index + 1).padStart(4, '0')}.mp3`;
          
          // Preprocess text for pauses
          const processedText = await preprocessText(line.text);
          
          const result = await ipcClient.startTTSJob({
            text: processedText,
            voice_id: line.voice_id,
            output_path: outputPath,
            model_id: voiceSettings.modelId,
            voice_settings: {
              stability: voiceSettings.stability,
              similarity_boost: voiceSettings.similarityBoost,
              style: voiceSettings.style,
              use_speaker_boost: voiceSettings.useSpeakerBoost,
              speed: voiceSettings.speed,
            },
            debug: debugMode,
          });

          if (result.debug) {
            setLastDebugData(result.debug);
          }

          addLog(`Line ${line.index + 1}: SUCCESS - ${result.duration_ms}ms`);
          updateLine(line.id, {
            status: 'done',
            output_path: result.output_path,
            audio_duration: result.duration_ms / 1000,
          });
          completed++;
          
          addExportEntry({
            outputPath: result.output_path,
            lineIndex: line.index,
            lineText: line.text.substring(0, 100),
            voiceName: line.voice_name || 'Unknown',
            durationMs: result.duration_ms,
            sessionFolder: sessionFolderName,
          });
          
          loadCredits();
        } catch (err) {
          const errMsg = err instanceof Error ? err.message : 'Unknown error';
          addLog(`Line ${line.index + 1}: ERROR - ${errMsg}`);
          updateLineStatus(line.id, 'error', errMsg);
          failed++;
        }

        const elapsed = (Date.now() - startTime) / 1000;
        updateProcessingStats({
          completed,
          failed,
          pending: pendingLines.length - completed - failed,
          processing: 0,
          elapsed_seconds: elapsed,
          characters_processed: lines.filter(l => l.status === 'done').reduce((sum, l) => sum + l.text.length, 0),
        });
      }

      addLog(`DONE - Completed: ${completed}, Failed: ${failed}, Total: ${pendingLines.length}`);
    }

    setProcessing(false);
    processingRef.current = false;

    // System notification when batch completes
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('2TTS - Processing Complete', {
        body: `Processing finished`,
        icon: '/icon.png',
      });
    } else if ('Notification' in window && Notification.permission !== 'denied') {
      Notification.requestPermission().then((permission) => {
        if (permission === 'granted') {
          new Notification('2TTS - Processing Complete', {
            body: `Processing finished`,
            icon: '/icon.png',
          });
        }
      });
    }
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
        const { invoke } = await import('@tauri-apps/api/core');
        await invoke('open_path', { path: line.output_path });
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
    setShowClearConfirm(true);
  };

  const handleConfirmClear = () => {
    clearLines();
    clearRecoveryData();
    setShowClearConfirm(false);
  };

  // Project Save/Load handlers
  const handleSaveProject = async () => {
    try {
      const api = await getPlatformAPI();
      const filePath = await api.dialog.saveFile({
        title: 'Save Project',
        defaultPath: `${projectName}.2tts`,
        filters: [{ name: '2TTS Project', extensions: ['2tts', 'json'] }],
      });
      
      if (filePath) {
        const projectData = {
          version: '1.0',
          name: projectName,
          outputFolder,
          defaultVoiceId,
          defaultVoiceName,
          voiceSettings,
          lines: lines.map(l => ({
            id: l.id,
            index: l.index,
            text: l.text,
            voice_id: l.voice_id,
            voice_name: l.voice_name,
            status: l.status,
          })),
        };
        
        await ipcClient.saveProject(filePath, projectData);
        addLog(`Project saved: ${filePath}`);
        setProjectName(filePath.split('\\').pop()?.replace('.2tts', '') || projectName);
      }
    } catch (err) {
      console.error('Failed to save project:', err);
      addLog(`ERROR: Failed to save project - ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  const handleLoadProject = async () => {
    try {
      const api = await getPlatformAPI();
      const filePaths = await api.dialog.openFile({
        title: 'Open Project',
        filters: [{ name: '2TTS Project', extensions: ['2tts', 'json'] }],
      });
      
      if (filePaths && filePaths.length > 0) {
        const result = await ipcClient.loadProject(filePaths[0]);
        if (result.success && result.project) {
          const proj = result.project as {
            name?: string;
            outputFolder?: string;
            defaultVoiceId?: string;
            defaultVoiceName?: string;
            voiceSettings?: typeof voiceSettings;
            lines?: Array<{ id: string; index: number; text: string; voice_id: string; voice_name: string; status: string }>;
          };
          
          if (proj.outputFolder) setOutputFolder(proj.outputFolder);
          if (proj.defaultVoiceId && proj.defaultVoiceName) {
            setDefaultVoice(proj.defaultVoiceId, proj.defaultVoiceName);
          }
          if (proj.voiceSettings) setVoiceSettings(proj.voiceSettings);
          if (proj.name) setProjectName(proj.name);
          
          // Restore lines
          if (proj.lines && proj.lines.length > 0) {
            clearLines();
            const texts = proj.lines.map(l => l.text);
            addLines(texts);
            // Restore voice assignments
            proj.lines.forEach(l => {
              if (l.voice_id && l.voice_name) {
                setLineVoice(l.id, l.voice_id, l.voice_name);
              }
            });
          }
          
          addLog(`Project loaded: ${filePaths[0]}`);
        }
      }
    } catch (err) {
      console.error('Failed to load project:', err);
      addLog(`ERROR: Failed to load project - ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  // Audio post-processing handler
  const handlePostProcess = async () => {
    const completedLines = lines.filter(l => l.status === 'done' && l.output_path);
    if (completedLines.length === 0) return;

    setIsPostProcessing(true);
    addLog(`Post-processing ${completedLines.length} audio files...`);

    try {
      const files = completedLines.map(l => ({
        input_path: l.output_path!,
        output_path: l.output_path!.replace('.mp3', '_processed.mp3'),
      }));

      const result = await ipcClient.batchProcessAudio(files, postProcessSettings);
      addLog(`Post-processing complete: ${result.success}/${result.total} successful`);
      
      if (result.failed > 0) {
        addLog(`Warning: ${result.failed} files failed to process`);
      }
    } catch (err) {
      addLog(`ERROR: Post-processing failed - ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsPostProcessing(false);
      setShowPostProcessDialog(false);
    }
  };

  const totalCharacters = lines.reduce((sum, l) => sum + l.text.length, 0);
  const pendingCharacters = lines.filter((l) => l.status === 'pending').reduce((sum, l) => sum + l.text.length, 0);
  const pendingCount = lines.filter((l) => l.status === 'pending').length;
  const completedCount = lines.filter((l) => l.status === 'done').length;
  
  // Character limit warning (ElevenLabs recommends max 5000 chars per request)
  const MAX_CHARS_PER_LINE = 5000;
  const linesExceedingLimit = lines.filter((l) => l.text.length > MAX_CHARS_PER_LINE);
  const hasCharacterWarning = linesExceedingLimit.length > 0;

  // Detect language from all lines text
  const detectedLanguage = useMemo<DetectedLanguage | null>(() => {
    if (lines.length === 0) return null;
    // Combine first few lines for detection (limit to avoid performance issues)
    const sampleText = lines.slice(0, 10).map(l => l.text).join(' ');
    if (!sampleText.trim()) return null;
    return detectLanguage(sampleText);
  }, [lines]);

  // Check disabled state
  const isStartDisabled = !outputFolder || !defaultVoiceId || pendingCount === 0;

  return (
    <div className="h-full flex flex-col gap-4 p-4 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-xl font-semibold text-surface-100">{t('tts.title')}</h1>
          <p className="text-sm text-surface-500">
            {lines.length} {t('common.lines')} | {totalCharacters.toLocaleString()} {t('common.characters')}
            {pendingCount > 0 && (
              <span className="ml-2 text-primary-400">
                | Est. cost: {pendingCharacters.toLocaleString()} credits
              </span>
            )}
          </p>
        </div>
        {hasCharacterWarning && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
            <svg className="w-4 h-4 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span className="text-xs text-yellow-400">
              {linesExceedingLimit.length} line(s) exceed {MAX_CHARS_PER_LINE.toLocaleString()} chars
            </span>
          </div>
        )}
      </div>

      {/* Controls bar */}
      <div className="flex items-center gap-4 shrink-0">
        {/* Voice selector */}
        <div className="flex items-center gap-2">
          <label className="text-sm text-surface-400">{t('tts.voice')}:</label>
          <select
            value={defaultVoiceId || ''}
            onChange={handleVoiceChange}
            disabled={isLoadingVoices}
            className="w-64 px-3 py-1.5 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-primary-500"
          >
            <option value="">{t('tts.select_voice')}</option>
            {/* Favorite voices first */}
            {voices.filter(v => favoriteVoiceIds.has(v.voice_id)).length > 0 && (
              <optgroup label="★ Favorites">
                {voices.filter(v => favoriteVoiceIds.has(v.voice_id)).map((voice) => (
                  <option key={voice.voice_id} value={voice.voice_id}>
                    {voice.name} ({voice.category})
                  </option>
                ))}
              </optgroup>
            )}
            {/* All other voices */}
            <optgroup label="All Voices">
              {voices.filter(v => !favoriteVoiceIds.has(v.voice_id)).map((voice) => (
                <option key={voice.voice_id} value={voice.voice_id}>
                  {voice.name} ({voice.category})
                </option>
              ))}
            </optgroup>
          </select>
          {/* Favorite toggle button */}
          {defaultVoiceId && (
            <button
              onClick={() => toggleFavoriteVoice(defaultVoiceId)}
              className={`p-1.5 transition-colors ${favoriteVoiceIds.has(defaultVoiceId) ? 'text-yellow-400' : 'text-surface-500 hover:text-yellow-400'}`}
              title={favoriteVoiceIds.has(defaultVoiceId) ? 'Remove from favorites' : 'Add to favorites'}
            >
              <svg className="w-4 h-4" fill={favoriteVoiceIds.has(defaultVoiceId) ? 'currentColor' : 'none'} viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
              </svg>
            </button>
          )}
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
          <button
            onClick={() => setShowVoiceLibrary(true)}
            className="p-1.5 text-surface-400 hover:text-surface-200 transition-colors"
            title="Browse Voice Library"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </button>
          {lines.length > 0 && (
            <button
              onClick={handleApplyVoiceToAll}
              disabled={!defaultVoiceId}
              className="px-2 py-1 text-xs bg-surface-800 text-surface-400 rounded hover:bg-surface-700 disabled:opacity-50"
            >
              {t('common.apply')}
            </button>
          )}
        </div>

        {/* Output folder */}
        <div className="flex items-center gap-2 flex-1">
          <label className="text-sm text-surface-400">{t('tts.output_folder')}:</label>
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
          <button
            onClick={handleOpenOutputFolder}
            disabled={!outputFolder}
            className="p-1.5 text-surface-400 hover:text-surface-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Open output folder"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
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
          onReorder={reorderLines}
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
            pauseSettings={voiceSettings.pauseSettings}
            detectedLanguage={detectedLanguage}
            onChange={(settings) => setVoiceSettings({
              ...settings,
              pauseSettings: settings.pauseSettings || voiceSettings.pauseSettings,
            })}
            currentVoiceId={defaultVoiceId}
            currentVoiceName={defaultVoiceName}
            voicePresets={voicePresets}
            onSavePreset={addVoicePreset}
            onLoadPreset={(preset) => {
              setDefaultVoice(preset.voiceId, preset.voiceName);
              setVoiceSettings({
                ...voiceSettings,
                ...preset.settings,
              });
            }}
            onDeletePreset={removeVoicePreset}
          />
        </div>
      )}

      {/* Processing controls */}
      {lines.length > 0 && (
        <div className="shrink-0 p-4 bg-surface-900 rounded-lg border border-surface-800 space-y-4">
          {/* Processing mode & thread settings */}
          <div className="flex items-center gap-4 pb-3 border-b border-surface-800">
            <div className="flex items-center gap-2">
              <label className="text-xs text-surface-400">Mode:</label>
              <select
                value={processingMode}
                onChange={(e) => setProcessingMode(e.target.value as ProcessingMode)}
                disabled={isProcessing}
                className="px-2 py-1 text-xs bg-surface-800 border border-surface-700 rounded"
              >
                <option value="parallel">Parallel (Faster)</option>
                <option value="sequential">Sequential (Pausable)</option>
              </select>
            </div>
            {processingMode === 'parallel' && (
              <div className="flex items-center gap-2">
                <label className="text-xs text-surface-400">Threads:</label>
                <input
                  type="number"
                  min={1}
                  max={5}
                  value={threadCount}
                  onChange={(e) => setThreadCount(Math.min(5, Math.max(1, parseInt(e.target.value) || 1)))}
                  disabled={isProcessing}
                  className="w-12 px-2 py-1 text-xs bg-surface-800 border border-surface-700 rounded text-center"
                />
              </div>
            )}
            <div className="flex-1" />
            <div className="flex items-center gap-2">
              <button
                onClick={handleLoadProject}
                disabled={isProcessing}
                className="px-2 py-1 text-xs bg-surface-800 text-surface-400 rounded hover:bg-surface-700 disabled:opacity-50"
                title="Open Project (Ctrl+O)"
              >
                <svg className="w-3.5 h-3.5 inline mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z" />
                </svg>
                Open
              </button>
              <button
                onClick={handleSaveProject}
                disabled={isProcessing || lines.length === 0}
                className="px-2 py-1 text-xs bg-surface-800 text-surface-400 rounded hover:bg-surface-700 disabled:opacity-50"
                title="Save Project (Ctrl+S)"
              >
                <svg className="w-3.5 h-3.5 inline mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
                </svg>
                Save
              </button>
            </div>
          </div>

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
              <button
                onClick={() => setShowPostProcessDialog(true)}
                disabled={completedCount === 0 || isPostProcessing}
                className="px-3 py-1.5 text-sm bg-surface-800 text-surface-300 rounded-lg hover:bg-surface-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <svg className="w-4 h-4 inline mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                </svg>
                {isPostProcessing ? 'Processing...' : 'Post-Process'}
              </button>
              <button
                onClick={() => setShowExportHistory(true)}
                className="px-3 py-1.5 text-sm bg-surface-800 text-surface-300 rounded-lg hover:bg-surface-700 transition-colors"
              >
                <svg className="w-4 h-4 inline mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                History ({exportHistory.length})
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

      {/* Debug Log Panel */}
      <div className="shrink-0 border border-surface-700 rounded-lg overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2 bg-surface-800 border-b border-surface-700">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-surface-300">Debug Log</span>
            <span className={`text-xs px-2 py-0.5 rounded ${isStartDisabled ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'}`}>
              {isStartDisabled ? 'Start Disabled' : 'Ready'}
            </span>
            {!outputFolder && <span className="text-xs text-red-400">No output folder</span>}
            {!defaultVoiceId && <span className="text-xs text-red-400">No voice</span>}
            {pendingCount === 0 && lines.length > 0 && <span className="text-xs text-yellow-400">No pending lines</span>}
          </div>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1 text-xs cursor-pointer">
              <input
                type="checkbox"
                checked={debugMode}
                onChange={(e) => setDebugMode(e.target.checked)}
                className="w-3 h-3 rounded border-surface-600 bg-surface-800 text-primary-500"
              />
              <span className={debugMode ? 'text-yellow-400' : 'text-surface-500'}>Debug</span>
            </label>
            <button
              onClick={() => setLogs([])}
              className="text-xs text-surface-500 hover:text-surface-300"
            >
              Clear
            </button>
            <button
              onClick={() => setShowLogs(!showLogs)}
              className="text-xs text-surface-500 hover:text-surface-300"
            >
              {showLogs ? 'Hide' : 'Show'}
            </button>
          </div>
        </div>
        {showLogs && (
          <div className="h-32 overflow-y-auto bg-surface-900 p-2 font-mono text-xs">
            {logs.length === 0 ? (
              <div className="text-surface-500">No logs yet. Click Start to begin processing.</div>
            ) : (
              logs.map((log, i) => (
                <div key={i} className={`${log.includes('ERROR') ? 'text-red-400' : log.includes('SUCCESS') ? 'text-green-400' : log.includes('DONE') ? 'text-blue-400' : 'text-surface-400'}`}>
                  {log}
                </div>
              ))
            )}
            <div ref={logsEndRef} />
          </div>
        )}
        
        {/* Debug Panel - Shows API request/response */}
        {debugMode && lastDebugData && (
          <div className="mt-2 border-t border-surface-700 pt-2">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-yellow-400">API Debug Output</span>
              <button
                onClick={() => setLastDebugData(null)}
                className="text-xs text-surface-500 hover:text-surface-300"
              >
                Clear Debug
              </button>
            </div>
            <pre className="h-64 overflow-auto bg-surface-950 p-2 rounded text-[10px] text-surface-300 whitespace-pre-wrap">
              {JSON.stringify(lastDebugData, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* Voice Library Dialog */}
      <VoiceLibraryDialog
        isOpen={showVoiceLibrary}
        onClose={() => setShowVoiceLibrary(false)}
        onSelectVoice={(voice) => {
          // Add library voice to local voices list if not already present
          if (!voices.find(v => v.voice_id === voice.voice_id)) {
            setVoices([...voices, voice]);
          }
          setDefaultVoice(voice.voice_id, voice.name);
          addLog(`Selected voice from library: ${voice.name}`);
        }}
      />

      {/* Clear All Confirmation Dialog */}
      <ConfirmDialog
        isOpen={showClearConfirm}
        title="Clear All Lines"
        message="Are you sure you want to clear all lines? This action cannot be undone."
        confirmLabel="Clear All"
        cancelLabel="Cancel"
        kind="danger"
        onConfirm={handleConfirmClear}
        onCancel={() => setShowClearConfirm(false)}
      />

      {/* Recovery Dialog */}
      <ConfirmDialog
        isOpen={showRecoveryDialog}
        title="Recover Previous Session"
        message="We found unsaved work from a previous session. Would you like to restore it?"
        confirmLabel="Restore"
        cancelLabel="Discard"
        kind="info"
        onConfirm={() => {
          restoreFromRecovery();
          setShowRecoveryDialog(false);
        }}
        onCancel={() => {
          clearRecoveryData();
          setShowRecoveryDialog(false);
        }}
      />

      {/* Post-Process Dialog */}
      {showPostProcessDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowPostProcessDialog(false)} />
          <div className="relative w-full max-w-md bg-surface-900 rounded-lg border border-surface-700 shadow-2xl p-6">
            <h3 className="text-lg font-medium text-surface-100 mb-4">Audio Post-Processing</h3>
            <p className="text-sm text-surface-400 mb-4">
              Apply effects to {completedCount} completed audio file{completedCount !== 1 ? 's' : ''}.
            </p>
            
            <div className="space-y-4">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={postProcessSettings.normalize}
                  onChange={(e) => setPostProcessSettings({ ...postProcessSettings, normalize: e.target.checked })}
                  className="w-4 h-4 rounded"
                />
                <div>
                  <div className="text-sm text-surface-200">Normalize Volume</div>
                  <div className="text-xs text-surface-500">Adjust audio to consistent level</div>
                </div>
              </label>
              
              {postProcessSettings.normalize && (
                <div className="ml-7">
                  <label className="text-xs text-surface-400">Target Level (dB):</label>
                  <input
                    type="number"
                    value={postProcessSettings.normalize_level}
                    onChange={(e) => setPostProcessSettings({ ...postProcessSettings, normalize_level: parseFloat(e.target.value) })}
                    className="ml-2 w-16 px-2 py-1 text-xs bg-surface-800 border border-surface-700 rounded"
                    min={-20}
                    max={0}
                  />
                </div>
              )}
              
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={postProcessSettings.trim_silence}
                  onChange={(e) => setPostProcessSettings({ ...postProcessSettings, trim_silence: e.target.checked })}
                  className="w-4 h-4 rounded"
                />
                <div>
                  <div className="text-sm text-surface-200">Trim Silence</div>
                  <div className="text-xs text-surface-500">Remove silence from start/end</div>
                </div>
              </label>
              
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-surface-400">Fade In (ms):</label>
                  <input
                    type="number"
                    value={postProcessSettings.fade_in}
                    onChange={(e) => setPostProcessSettings({ ...postProcessSettings, fade_in: parseInt(e.target.value) || 0 })}
                    className="w-full mt-1 px-2 py-1 text-sm bg-surface-800 border border-surface-700 rounded"
                    min={0}
                    max={2000}
                  />
                </div>
                <div>
                  <label className="text-xs text-surface-400">Fade Out (ms):</label>
                  <input
                    type="number"
                    value={postProcessSettings.fade_out}
                    onChange={(e) => setPostProcessSettings({ ...postProcessSettings, fade_out: parseInt(e.target.value) || 0 })}
                    className="w-full mt-1 px-2 py-1 text-sm bg-surface-800 border border-surface-700 rounded"
                    min={0}
                    max={2000}
                  />
                </div>
              </div>
              
              <div>
                <label className="text-xs text-surface-400">Speed Adjustment:</label>
                <input
                  type="range"
                  value={postProcessSettings.speed}
                  onChange={(e) => setPostProcessSettings({ ...postProcessSettings, speed: parseFloat(e.target.value) })}
                  className="w-full mt-1"
                  min={0.5}
                  max={2}
                  step={0.1}
                />
                <div className="text-xs text-surface-500 text-center">{postProcessSettings.speed}x</div>
              </div>
            </div>
            
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowPostProcessDialog(false)}
                className="flex-1 px-4 py-2 text-sm bg-surface-800 text-surface-300 rounded-lg hover:bg-surface-700"
              >
                Cancel
              </button>
              <button
                onClick={handlePostProcess}
                disabled={isPostProcessing}
                className="flex-1 px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-500 disabled:opacity-50"
              >
                {isPostProcessing ? 'Processing...' : 'Apply'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Export History Panel */}
      {showExportHistory && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/40" onClick={() => setShowExportHistory(false)} />
          <div className="relative w-full max-w-md bg-surface-900 border-l border-surface-700 shadow-2xl flex flex-col animate-in slide-in-from-right duration-200">
            <div className="flex items-center justify-between px-4 py-3 border-b border-surface-700 bg-surface-800/50">
              <h3 className="text-sm font-medium text-surface-100">Export History</h3>
              <div className="flex items-center gap-2">
                {exportHistory.length > 0 && (
                  <button
                    onClick={clearExportHistory}
                    className="text-xs text-red-400 hover:text-red-300"
                  >
                    Clear All
                  </button>
                )}
                <button
                  onClick={() => setShowExportHistory(false)}
                  className="p-1.5 text-surface-400 hover:text-surface-200 hover:bg-surface-700 rounded-lg"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {exportHistory.length === 0 ? (
                <div className="text-center text-surface-500 py-8">
                  <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                  <p>No exports yet</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {exportHistory.map((entry) => (
                    <div
                      key={entry.id}
                      className="p-3 bg-surface-800/50 rounded-lg border border-surface-700 hover:border-surface-600 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-primary-400 font-mono">
                          Line {entry.lineIndex + 1}
                        </span>
                        <span className="text-xs text-surface-500">
                          {new Date(entry.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-sm text-surface-300 truncate mb-1" title={entry.lineText}>
                        {entry.lineText}
                      </p>
                      <div className="flex items-center justify-between text-xs text-surface-500">
                        <span>{entry.voiceName}</span>
                        <span>{(entry.durationMs / 1000).toFixed(1)}s</span>
                      </div>
                      <div className="mt-2 flex items-center gap-2">
                        <button
                          onClick={async () => {
                            try {
                              const { invoke } = await import('@tauri-apps/api/core');
                              await invoke('open_path', { path: entry.outputPath });
                            } catch (err) {
                              console.error('Failed to open file:', err);
                            }
                          }}
                          className="text-xs text-primary-400 hover:text-primary-300"
                        >
                          Play
                        </button>
                        <button
                          onClick={async () => {
                            try {
                              const { invoke } = await import('@tauri-apps/api/core');
                              const folder = entry.outputPath.substring(0, entry.outputPath.lastIndexOf('\\'));
                              await invoke('open_path', { path: folder });
                            } catch (err) {
                              console.error('Failed to open folder:', err);
                            }
                          }}
                          className="text-xs text-surface-400 hover:text-surface-300"
                        >
                          Open Folder
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
