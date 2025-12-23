import { useState, useEffect } from 'react';
import { useAppStore } from '../stores/appStore';
import { ipcClient } from '../lib/ipc';
import { getPlatformAPI } from '../lib/platform';
import { Voice, VoiceSettings } from '../lib/ipc/types';
import { v4 as uuidv4 } from 'uuid';

export default function HomePage() {
  const { voices, setVoices, addJob, updateJob, handleProgress, totalCredits, setTotalCredits } =
    useAppStore();
  const [text, setText] = useState('');
  const [selectedVoice, setSelectedVoice] = useState<Voice | null>(null);
  const [outputFolder, setOutputFolder] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [voiceSettings, setVoiceSettings] = useState<VoiceSettings>({
    stability: 0.5,
    similarity_boost: 0.75,
    style: 0,
    use_speaker_boost: true,
  });

  useEffect(() => {
    loadVoices();
    loadConfig();

    const unsubProgress = ipcClient.onProgress(handleProgress);
    const unsubCredits = ipcClient.onCreditsUpdate(({ total }) => setTotalCredits(total));

    return () => {
      unsubProgress();
      unsubCredits();
    };
  }, []);

  async function loadVoices() {
    try {
      const voiceList = await ipcClient.getVoices();
      setVoices(voiceList);
      if (voiceList.length > 0 && !selectedVoice) {
        setSelectedVoice(voiceList[0]);
      }
    } catch (err) {
      console.error('Failed to load voices:', err);
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

  async function handleSelectFolder() {
    try {
      const api = await getPlatformAPI();
      const folder = await api.dialog.openDirectory('Select Output Folder');
      if (folder) {
        setOutputFolder(folder);
      }
    } catch (err) {
      console.error('Failed to open folder dialog:', err);
    }
  }

  async function handleGenerate() {
    if (!text.trim() || !selectedVoice || !outputFolder) return;

    const jobId = uuidv4();
    const outputPath = `${outputFolder}\\${Date.now()}_output.mp3`;

    addJob({
      id: jobId,
      text: text.substring(0, 100),
      voiceId: selectedVoice.voice_id,
      status: 'pending',
      progress: 0,
      message: 'Starting...',
      outputPath,
    });

    setIsLoading(true);

    try {
      const result = await ipcClient.startTTSJob({
        text,
        voice_id: selectedVoice.voice_id,
        output_path: outputPath,
        voice_settings: voiceSettings,
      });

      updateJob(jobId, {
        status: 'completed',
        progress: 100,
        message: 'Complete',
        outputPath: result.output_path,
      });
    } catch (err) {
      updateJob(jobId, {
        status: 'failed',
        error: err instanceof Error ? err.message : 'Unknown error',
      });
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-surface-100">Text to Speech</h1>
        <div className="text-sm text-surface-400">
          Credits: <span className="text-primary-400 font-medium">{totalCredits.toLocaleString()}</span>
        </div>
      </div>

      <div className="card space-y-4">
        <div>
          <label htmlFor="text" className="block text-sm font-medium text-surface-300 mb-2">
            Text
          </label>
          <textarea
            id="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Enter text to convert to speech..."
            className="input min-h-[200px] resize-y"
            aria-label="Text to convert"
          />
          <div className="mt-1 text-xs text-surface-500 text-right">
            {text.length.toLocaleString()} characters
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="voice" className="block text-sm font-medium text-surface-300 mb-2">
              Voice
            </label>
            <select
              id="voice"
              value={selectedVoice?.voice_id || ''}
              onChange={(e) => {
                const voice = voices.find((v) => v.voice_id === e.target.value);
                setSelectedVoice(voice || null);
              }}
              className="input"
              aria-label="Select voice"
            >
              {voices.map((voice) => (
                <option key={voice.voice_id} value={voice.voice_id}>
                  {voice.name} ({voice.category})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="output" className="block text-sm font-medium text-surface-300 mb-2">
              Output Folder
            </label>
            <div className="flex gap-2">
              <input
                id="output"
                type="text"
                value={outputFolder}
                onChange={(e) => setOutputFolder(e.target.value)}
                className="input flex-1"
                placeholder="Select output folder..."
                aria-label="Output folder path"
              />
              <button onClick={handleSelectFolder} className="btn-secondary" aria-label="Browse folders">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                  />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <h3 className="text-sm font-medium text-surface-300">Voice Settings</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="flex items-center justify-between text-sm text-surface-400 mb-1">
                <span>Stability</span>
                <span>{voiceSettings.stability.toFixed(2)}</span>
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={voiceSettings.stability}
                onChange={(e) =>
                  setVoiceSettings((s) => ({ ...s, stability: parseFloat(e.target.value) }))
                }
                className="w-full"
                aria-label="Voice stability"
              />
            </div>
            <div>
              <label className="flex items-center justify-between text-sm text-surface-400 mb-1">
                <span>Similarity</span>
                <span>{voiceSettings.similarity_boost.toFixed(2)}</span>
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={voiceSettings.similarity_boost}
                onChange={(e) =>
                  setVoiceSettings((s) => ({ ...s, similarity_boost: parseFloat(e.target.value) }))
                }
                className="w-full"
                aria-label="Voice similarity"
              />
            </div>
          </div>
        </div>

        <div className="flex justify-end pt-4 border-t border-surface-800">
          <button
            onClick={handleGenerate}
            disabled={!text.trim() || !selectedVoice || !outputFolder || isLoading}
            className="btn-primary"
          >
            {isLoading ? (
              <>
                <svg
                  className="w-4 h-4 mr-2 animate-spin"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Generating...
              </>
            ) : (
              <>
                <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                Generate Speech
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
