import { useState, useEffect } from 'react';
import { 
  DetectedLanguage, 
  isLanguageSupported, 
  getBestModelForLanguage,
  MODEL_LANGUAGE_SUPPORT 
} from '../lib/languageDetect';

interface PauseSettings {
  enabled: boolean;
  shortPauseDuration: number;
  longPauseDuration: number;
}

interface VoiceSettingsProps {
  stability: number;
  similarityBoost: number;
  style: number;
  speed: number;
  useSpeakerBoost: boolean;
  modelId: string;
  pauseSettings?: PauseSettings;
  detectedLanguage?: DetectedLanguage | null;
  onChange: (settings: {
    stability: number;
    similarityBoost: number;
    style: number;
    speed: number;
    useSpeakerBoost: boolean;
    modelId: string;
    pauseSettings?: PauseSettings;
  }) => void;
}

const MODELS = [
  { id: 'eleven_v3', name: 'Eleven V3 - Most Expressive (70+ langs, 5k chars)' },
  { id: 'eleven_multilingual_v2', name: 'Multilingual V2 - Stable Quality (29 langs, 10k chars)' },
  { id: 'eleven_turbo_v2_5', name: 'Turbo V2.5 - Balanced (32 langs, 40k chars, ~300ms)' },
  { id: 'eleven_turbo_v2', name: 'Turbo V2 - English Only (30k chars, ~300ms)' },
  { id: 'eleven_flash_v2_5', name: 'Flash V2.5 - Fastest (32 langs, 40k chars, ~75ms)' },
  { id: 'eleven_flash_v2', name: 'Flash V2 - English Only Fast (30k chars, ~75ms)' },
];

export default function VoiceSettings({
  stability,
  similarityBoost,
  style,
  speed,
  useSpeakerBoost,
  modelId,
  pauseSettings = { enabled: false, shortPauseDuration: 300, longPauseDuration: 700 },
  detectedLanguage,
  onChange,
}: VoiceSettingsProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showLanguageWarning, setShowLanguageWarning] = useState(false);
  const [autoSwitched, setAutoSwitched] = useState(false);

  // Check language compatibility and auto-switch if needed
  useEffect(() => {
    if (!detectedLanguage || detectedLanguage.confidence === 'low') {
      setShowLanguageWarning(false);
      return;
    }

    const isSupported = isLanguageSupported(modelId, detectedLanguage.code);
    
    if (!isSupported) {
      // Auto-switch to a compatible model
      const bestModel = getBestModelForLanguage(detectedLanguage.code);
      if (bestModel !== modelId) {
        onChange({
          stability,
          similarityBoost,
          style,
          speed,
          useSpeakerBoost,
          modelId: bestModel,
          pauseSettings,
        });
        setAutoSwitched(true);
        setShowLanguageWarning(false);
        // Reset auto-switched message after 3 seconds
        setTimeout(() => setAutoSwitched(false), 3000);
      } else {
        setShowLanguageWarning(true);
      }
    } else {
      setShowLanguageWarning(false);
    }
  }, [detectedLanguage, modelId]);

  const handleChange = (key: string, value: number | boolean | string | PauseSettings) => {
    onChange({
      stability,
      similarityBoost,
      style,
      speed,
      useSpeakerBoost,
      modelId,
      pauseSettings,
      [key]: value,
    });
  };

  const handlePauseChange = (key: keyof PauseSettings, value: boolean | number) => {
    const newPauseSettings = { ...pauseSettings, [key]: value };
    onChange({
      stability,
      similarityBoost,
      style,
      speed,
      useSpeakerBoost,
      modelId,
      pauseSettings: newPauseSettings,
    });
  };

  return (
    <div className="bg-surface-900 rounded-lg border border-surface-800">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-surface-300 hover:bg-surface-800/50 transition-colors"
      >
        <span className="flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
          </svg>
          Voice Settings
        </span>
        <svg
          className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isExpanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-surface-800">
          {/* Model selector */}
          <div className="pt-4">
            <label className="block text-xs font-medium text-surface-400 mb-2">Model</label>
            <select
              value={modelId}
              onChange={(e) => handleChange('modelId', e.target.value)}
              className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-primary-500"
            >
              {MODELS.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name}
                </option>
              ))}
            </select>

            {/* Language detection info */}
            {detectedLanguage && detectedLanguage.confidence !== 'low' && (
              <div className="mt-2 text-xs text-surface-400">
                Detected: <span className="text-primary-400">{detectedLanguage.name}</span>
                {detectedLanguage.confidence === 'high' && (
                  <span className="ml-1 text-surface-500">(high confidence)</span>
                )}
              </div>
            )}

            {/* Auto-switched notification */}
            {autoSwitched && (
              <div className="mt-2 px-3 py-2 bg-green-500/10 border border-green-500/30 rounded-lg text-xs text-green-400 flex items-center gap-2">
                <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span>Auto-switched to {MODEL_LANGUAGE_SUPPORT[modelId]?.name || modelId} for {detectedLanguage?.name} support</span>
              </div>
            )}

            {/* Language warning */}
            {showLanguageWarning && detectedLanguage && (
              <div className="mt-2 px-3 py-2 bg-yellow-500/10 border border-yellow-500/30 rounded-lg text-xs text-yellow-400 flex items-start gap-2">
                <svg className="w-4 h-4 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div>
                  <span className="font-medium">Language not supported:</span> {MODEL_LANGUAGE_SUPPORT[modelId]?.name || modelId} does not support {detectedLanguage.name}.
                  <br />
                  <span className="text-yellow-500">Recommended:</span> Use Eleven V3, Turbo V2.5, or Flash V2.5 for {detectedLanguage.name}.
                </div>
              </div>
            )}
          </div>

          {/* Sliders */}
          <div className="grid grid-cols-2 gap-4">
            {/* Stability */}
            <div>
              <label className="flex items-center justify-between text-xs text-surface-400 mb-2">
                <span>Stability</span>
                <span className="font-mono">{stability.toFixed(2)}</span>
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={stability}
                onChange={(e) => handleChange('stability', parseFloat(e.target.value))}
                className="w-full accent-primary-500"
              />
              <div className="flex justify-between text-[10px] text-surface-600 mt-1">
                <span>Variable</span>
                <span>Stable</span>
              </div>
            </div>

            {/* Similarity */}
            <div>
              <label className="flex items-center justify-between text-xs text-surface-400 mb-2">
                <span>Similarity</span>
                <span className="font-mono">{similarityBoost.toFixed(2)}</span>
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={similarityBoost}
                onChange={(e) => handleChange('similarityBoost', parseFloat(e.target.value))}
                className="w-full accent-primary-500"
              />
              <div className="flex justify-between text-[10px] text-surface-600 mt-1">
                <span>Low</span>
                <span>High</span>
              </div>
            </div>

            {/* Style */}
            <div>
              <label className="flex items-center justify-between text-xs text-surface-400 mb-2">
                <span>Style Exaggeration</span>
                <span className="font-mono">{style.toFixed(2)}</span>
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={style}
                onChange={(e) => handleChange('style', parseFloat(e.target.value))}
                className="w-full accent-primary-500"
              />
              <div className="flex justify-between text-[10px] text-surface-600 mt-1">
                <span>None</span>
                <span>Exaggerated</span>
              </div>
            </div>

            {/* Speed */}
            <div>
              <label className="flex items-center justify-between text-xs text-surface-400 mb-2">
                <span>Speed</span>
                <span className="font-mono">{speed.toFixed(2)}x</span>
              </label>
              <input
                type="range"
                min="0.5"
                max="2"
                step="0.05"
                value={speed}
                onChange={(e) => handleChange('speed', parseFloat(e.target.value))}
                className="w-full accent-primary-500"
              />
              <div className="flex justify-between text-[10px] text-surface-600 mt-1">
                <span>0.5x</span>
                <span>2x</span>
              </div>
            </div>
          </div>

          {/* Speaker boost toggle */}
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={useSpeakerBoost}
              onChange={(e) => handleChange('useSpeakerBoost', e.target.checked)}
              className="w-4 h-4 rounded border-surface-600 bg-surface-800 text-primary-500 focus:ring-primary-500"
            />
            <span className="text-sm text-surface-300">Speaker Boost</span>
            <span className="text-xs text-surface-500">(Enhances similarity, increases latency)</span>
          </label>

          {/* Pause Settings */}
          <div className="pt-4 border-t border-surface-800">
            <label className="flex items-center gap-3 cursor-pointer mb-3">
              <input
                type="checkbox"
                checked={pauseSettings.enabled}
                onChange={(e) => handlePauseChange('enabled', e.target.checked)}
                className="w-4 h-4 rounded border-surface-600 bg-surface-800 text-primary-500 focus:ring-primary-500"
              />
              <span className="text-sm text-surface-300">Auto Pauses</span>
              <span className="text-xs text-surface-500">(Insert pauses after punctuation)</span>
            </label>

            {pauseSettings.enabled && (
              <div className="grid grid-cols-2 gap-4 pl-7">
                <div>
                  <label className="text-xs text-surface-400 mb-1 block">Short pause (ms)</label>
                  <input
                    type="number"
                    min={100}
                    max={1000}
                    step={50}
                    value={pauseSettings.shortPauseDuration}
                    onChange={(e) => handlePauseChange('shortPauseDuration', parseInt(e.target.value) || 300)}
                    className="w-full px-2 py-1 bg-surface-800 border border-surface-700 rounded text-sm"
                  />
                  <div className="text-[10px] text-surface-600 mt-1">After: , ; :</div>
                </div>
                <div>
                  <label className="text-xs text-surface-400 mb-1 block">Long pause (ms)</label>
                  <input
                    type="number"
                    min={200}
                    max={2000}
                    step={100}
                    value={pauseSettings.longPauseDuration}
                    onChange={(e) => handlePauseChange('longPauseDuration', parseInt(e.target.value) || 700)}
                    className="w-full px-2 py-1 bg-surface-800 border border-surface-700 rounded text-sm"
                  />
                  <div className="text-[10px] text-surface-600 mt-1">After: . ! ?</div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
