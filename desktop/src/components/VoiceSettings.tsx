import { useState } from 'react';

interface VoiceSettingsProps {
  stability: number;
  similarityBoost: number;
  style: number;
  speed: number;
  useSpeakerBoost: boolean;
  modelId: string;
  onChange: (settings: {
    stability: number;
    similarityBoost: number;
    style: number;
    speed: number;
    useSpeakerBoost: boolean;
    modelId: string;
  }) => void;
}

const MODELS = [
  { id: 'eleven_v3', name: 'Eleven V3 (Best Quality)' },
  { id: 'eleven_turbo_v2_5', name: 'Turbo V2.5 (Fast)' },
  { id: 'eleven_multilingual_v2', name: 'Multilingual V2' },
  { id: 'eleven_flash_v2_5', name: 'Flash V2.5 (Fastest)' },
  { id: 'eleven_flash_v2', name: 'Flash V2' },
];

export default function VoiceSettings({
  stability,
  similarityBoost,
  style,
  speed,
  useSpeakerBoost,
  modelId,
  onChange,
}: VoiceSettingsProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleChange = (key: string, value: number | boolean | string) => {
    onChange({
      stability,
      similarityBoost,
      style,
      speed,
      useSpeakerBoost,
      modelId,
      [key]: value,
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
        </div>
      )}
    </div>
  );
}
