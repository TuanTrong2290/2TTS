import { useState, useEffect } from 'react';
import { 
  DetectedLanguage, 
  isLanguageSupported, 
  getBestModelForLanguage,
  MODEL_LANGUAGE_SUPPORT 
} from '../lib/languageDetect';
import { useTranslation } from '../lib/i18n';

interface PauseSettings {
  enabled: boolean;
  shortPauseDuration: number;
  longPauseDuration: number;
}

interface VoicePreset {
  id: string;
  name: string;
  voiceId: string;
  voiceName: string;
  settings: {
    stability: number;
    similarityBoost: number;
    style: number;
    speed: number;
    useSpeakerBoost: boolean;
    modelId: string;
  };
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
  // Preset props
  currentVoiceId?: string | null;
  currentVoiceName?: string | null;
  voicePresets?: VoicePreset[];
  onSavePreset?: (preset: Omit<VoicePreset, 'id'>) => void;
  onLoadPreset?: (preset: VoicePreset) => void;
  onDeletePreset?: (id: string) => void;
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
  currentVoiceId,
  currentVoiceName,
  voicePresets = [],
  onSavePreset,
  onLoadPreset,
  onDeletePreset,
}: VoiceSettingsProps) {
  const { t } = useTranslation();
  const [isExpanded, setIsExpanded] = useState(false);
  const [showLanguageWarning, setShowLanguageWarning] = useState(false);
  const [autoSwitched, setAutoSwitched] = useState(false);
  const [showPresetInput, setShowPresetInput] = useState(false);
  const [presetName, setPresetName] = useState('');

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

  const handleSavePreset = () => {
    if (!presetName.trim() || !currentVoiceId || !onSavePreset) return;
    onSavePreset({
      name: presetName.trim(),
      voiceId: currentVoiceId,
      voiceName: currentVoiceName || 'Unknown',
      settings: {
        stability,
        similarityBoost,
        style,
        speed,
        useSpeakerBoost,
        modelId,
      },
    });
    setPresetName('');
    setShowPresetInput(false);
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
          {t('voice.settings')}
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
          {/* Voice Presets */}
          {(voicePresets.length > 0 || onSavePreset) && (
            <div className="pt-4">
              <label className="block text-xs font-medium text-surface-400 mb-2">Voice Presets</label>
              <div className="flex gap-2">
                {voicePresets.length > 0 && (
                  <select
                    value=""
                    onChange={(e) => {
                      const preset = voicePresets.find(p => p.id === e.target.value);
                      if (preset && onLoadPreset) onLoadPreset(preset);
                    }}
                    className="flex-1 px-3 py-1.5 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-primary-500"
                  >
                    <option value="">Load preset...</option>
                    {voicePresets.map((preset) => (
                      <option key={preset.id} value={preset.id}>
                        {preset.name} ({preset.voiceName})
                      </option>
                    ))}
                  </select>
                )}
                {onSavePreset && currentVoiceId && (
                  <>
                    {showPresetInput ? (
                      <div className="flex gap-1">
                        <input
                          type="text"
                          value={presetName}
                          onChange={(e) => setPresetName(e.target.value)}
                          onKeyDown={(e) => e.key === 'Enter' && handleSavePreset()}
                          placeholder="Preset name..."
                          className="w-32 px-2 py-1.5 bg-surface-800 border border-surface-700 rounded-lg text-sm focus:outline-none focus:border-primary-500"
                          autoFocus
                        />
                        <button
                          onClick={handleSavePreset}
                          disabled={!presetName.trim()}
                          className="px-2 py-1.5 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-500 disabled:opacity-50"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => { setShowPresetInput(false); setPresetName(''); }}
                          className="px-2 py-1.5 bg-surface-700 text-surface-300 rounded-lg text-sm hover:bg-surface-600"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setShowPresetInput(true)}
                        className="px-3 py-1.5 bg-surface-800 text-surface-300 rounded-lg text-sm hover:bg-surface-700 flex items-center gap-1"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                        Save
                      </button>
                    )}
                  </>
                )}
              </div>
              {/* Delete preset buttons */}
              {voicePresets.length > 0 && onDeletePreset && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {voicePresets.map((preset) => (
                    <span key={preset.id} className="inline-flex items-center gap-1 px-2 py-0.5 bg-surface-800 rounded text-xs text-surface-400">
                      {preset.name}
                      <button
                        onClick={() => onDeletePreset(preset.id)}
                        className="text-surface-500 hover:text-red-400"
                      >
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Model selector */}
          <div className="pt-4">
            <label className="block text-xs font-medium text-surface-400 mb-2">{t('voice.model')}</label>
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

            {/* V3 Audio Tags tip */}
            {modelId === 'eleven_v3' && (
              <div className="mt-2 px-3 py-2 bg-primary-500/10 border border-primary-500/30 rounded-lg text-xs text-primary-400 flex items-start gap-2">
                <svg className="w-4 h-4 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <span className="font-medium">V3 Audio Tags:</span> Add emotion with tags like <code className="bg-surface-800 px-1 rounded">[laughs]</code>, <code className="bg-surface-800 px-1 rounded">[whispers]</code>, <code className="bg-surface-800 px-1 rounded">[sarcastic]</code> in your text.
                </div>
              </div>
            )}
          </div>

          {/* Sliders - Only show for non-V3 models */}
          {modelId !== 'eleven_v3' ? (
            <div className="grid grid-cols-2 gap-4">
              {/* Stability */}
              <div>
                <label className="flex items-center justify-between text-xs text-surface-400 mb-2">
                  <span>{t('voice.stability')}</span>
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
                  <span>{t('voice.similarity')}</span>
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
                  <span>{t('voice.style')}</span>
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
                  <span>{t('voice.speed')}</span>
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
          ) : (
            /* V3 only shows Speed slider */
            <div className="grid grid-cols-1 gap-4">
              <div>
                <label className="flex items-center justify-between text-xs text-surface-400 mb-2">
                  <span>{t('voice.speed')}</span>
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
                  <span>1x</span>
                  <span>2x</span>
                </div>
              </div>
            </div>
          )}

          {/* Speaker boost toggle - Not available for V3 model */}
          {modelId !== 'eleven_v3' ? (
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={useSpeakerBoost}
                onChange={(e) => handleChange('useSpeakerBoost', e.target.checked)}
                className="w-4 h-4 rounded border-surface-600 bg-surface-800 text-primary-500 focus:ring-primary-500"
              />
              <span className="text-sm text-surface-300">{t('voice.speaker_boost')}</span>
            </label>
          ) : (
            <div className="flex items-center gap-3 opacity-50">
              <input
                type="checkbox"
                checked={false}
                disabled
                className="w-4 h-4 rounded border-surface-600 bg-surface-800 text-primary-500"
              />
              <span className="text-sm text-surface-400">{t('voice.speaker_boost')}</span>
              <span className="text-xs text-surface-500">(N/A V3)</span>
            </div>
          )}

          {/* Pause Settings */}
          <div className="pt-4 border-t border-surface-800">
            <label className="flex items-center gap-3 cursor-pointer mb-3">
              <input
                type="checkbox"
                checked={pauseSettings.enabled}
                onChange={(e) => handlePauseChange('enabled', e.target.checked)}
                className="w-4 h-4 rounded border-surface-600 bg-surface-800 text-primary-500 focus:ring-primary-500"
              />
              <span className="text-sm text-surface-300">{t('voice.auto_pauses')}</span>
            </label>

            {pauseSettings.enabled && (
              <div className="grid grid-cols-2 gap-4 pl-7">
                <div>
                  <label className="text-xs text-surface-400 mb-1 block">{t('voice.short_pause')}</label>
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
                  <label className="text-xs text-surface-400 mb-1 block">{t('voice.long_pause')}</label>
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
