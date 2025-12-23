import { useState, useEffect } from 'react';
import { ipcClient, VoicePreset, VoicePattern, AnalyticsStats } from '../lib/ipc';
import { getPlatformAPI } from '../lib/platform';
import { checkForUpdates } from '../lib/updater';
import { useAppStore } from '../stores/appStore';
import { Proxy } from '../lib/ipc/types';

type SettingsTab = 'general' | 'apikeys' | 'proxies' | 'presets' | 'patterns' | 'analytics' | 'about';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('general');
  const { setConfig, setAPIKeys, versionInfo } = useAppStore();

  const [outputFolder, setOutputFolder] = useState('');
  const [threadCount, setThreadCount] = useState(5);
  const [maxRetries, setMaxRetries] = useState(3);
  const [language, setLanguage] = useState('en');
  const [availableLanguages] = useState<Array<{ code: string; name: string }>>([
    { code: 'en', name: 'English' },
    { code: 'vi', name: 'Vietnamese' },
    { code: 'zh', name: 'Chinese' },
    { code: 'ja', name: 'Japanese' },
    { code: 'ko', name: 'Korean' },
  ]);

  useEffect(() => {
    loadSettings();
  }, []);

  async function loadSettings() {
    try {
      const cfg = await ipcClient.getConfig();
      setConfig(cfg);
      setOutputFolder(cfg.default_output_folder);
      setThreadCount(cfg.thread_count);
      setMaxRetries(cfg.max_retries);

      const keys = await ipcClient.getAPIKeys();
      setAPIKeys(keys);
    } catch (err) {
      console.error('Failed to load settings:', err);
    }
  }

  async function handleSelectFolder() {
    try {
      const api = await getPlatformAPI();
      const folder = await api.dialog.openDirectory('Select Default Output Folder');
      if (folder) {
        setOutputFolder(folder);
        await ipcClient.setConfig('default_output_folder', folder);
      }
    } catch (err) {
      console.error('Failed to open folder dialog:', err);
    }
  }

  async function handleSaveGeneral() {
    try {
      await ipcClient.setConfig('thread_count', threadCount);
      await ipcClient.setConfig('max_retries', maxRetries);
    } catch (err) {
      console.error('Failed to save settings:', err);
    }
  }

  async function handleExportDiagnostics() {
    try {
      const path = await ipcClient.exportDiagnostics();
      alert(`Diagnostics exported to: ${path}`);
    } catch (err) {
      console.error('Failed to export diagnostics:', err);
    }
  }

  const tabs: { id: SettingsTab; label: string }[] = [
    { id: 'general', label: 'General' },
    { id: 'apikeys', label: 'API Keys' },
    { id: 'proxies', label: 'Proxies' },
    { id: 'presets', label: 'Presets' },
    { id: 'patterns', label: 'Voice Patterns' },
    { id: 'analytics', label: 'Analytics' },
    { id: 'about', label: 'About' },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h1 className="text-2xl font-semibold text-surface-100">Settings</h1>

      <div className="flex gap-1 border-b border-surface-800">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab.id
                ? 'text-primary-400 border-primary-400'
                : 'text-surface-400 border-transparent hover:text-surface-200'
            }`}
            role="tab"
            aria-selected={activeTab === tab.id}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="card" role="tabpanel">
        {activeTab === 'general' && (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-surface-300 mb-2">
                Default Output Folder
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={outputFolder}
                  onChange={(e) => setOutputFolder(e.target.value)}
                  className="input flex-1"
                  aria-label="Default output folder"
                />
                <button onClick={handleSelectFolder} className="btn-secondary">
                  Browse
                </button>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-surface-300 mb-2">
                  Thread Count
                </label>
                <input
                  type="number"
                  min="1"
                  max="20"
                  value={threadCount}
                  onChange={(e) => setThreadCount(parseInt(e.target.value) || 1)}
                  className="input"
                  aria-label="Thread count"
                />
                <p className="text-xs text-surface-500 mt-1">Parallel TTS processes</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-300 mb-2">
                  Max Retries
                </label>
                <input
                  type="number"
                  min="0"
                  max="10"
                  value={maxRetries}
                  onChange={(e) => setMaxRetries(parseInt(e.target.value) || 0)}
                  className="input"
                  aria-label="Max retries"
                />
                <p className="text-xs text-surface-500 mt-1">On API failure</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-300 mb-2">
                  Language
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="input"
                  aria-label="Interface language"
                >
                  {availableLanguages.map((lang) => (
                    <option key={lang.code} value={lang.code}>{lang.name}</option>
                  ))}
                </select>
                <p className="text-xs text-surface-500 mt-1">UI language</p>
              </div>
            </div>

            <div className="flex justify-end pt-4 border-t border-surface-800">
              <button onClick={handleSaveGeneral} className="btn-primary">
                Save Changes
              </button>
            </div>
          </div>
        )}

        {activeTab === 'apikeys' && <APIKeysTab />}
        {activeTab === 'proxies' && <ProxiesTab />}
        {activeTab === 'presets' && <PresetsTab />}
        {activeTab === 'patterns' && <VoicePatternsTab />}
        {activeTab === 'analytics' && <AnalyticsTab />}

        {activeTab === 'about' && (
          <div className="space-y-6">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-xl bg-primary-600 flex items-center justify-center">
                <span className="text-2xl font-bold text-white">2T</span>
              </div>
              <div>
                <h2 className="text-xl font-semibold text-surface-100">2TTS</h2>
                <p className="text-sm text-surface-400">Text-to-Speech Tool</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-surface-800 rounded-lg">
                <div className="text-xs text-surface-500 uppercase">UI Version</div>
                <div className="text-lg font-medium text-surface-200">
                  {versionInfo?.uiVersion || 'Unknown'}
                </div>
              </div>
              <div className="p-3 bg-surface-800 rounded-lg">
                <div className="text-xs text-surface-500 uppercase">Backend Version</div>
                <div className="text-lg font-medium text-surface-200">
                  {versionInfo?.backendVersion || 'Unknown'}
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-surface-800 flex gap-3">
              <button onClick={() => checkForUpdates(false)} className="btn-primary">
                <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
                Check for Updates
              </button>
              <button onClick={handleExportDiagnostics} className="btn-secondary">
                <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                Export Diagnostics
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function APIKeysTab() {
  const { apiKeys, setAPIKeys } = useAppStore();
  const [newKeyValue, setNewKeyValue] = useState('');
  const [isAdding, setIsAdding] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isValidatingAll, setIsValidatingAll] = useState(false);
  const [validationProgress, setValidationProgress] = useState({ current: 0, total: 0 });
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<{
    active_key: { id: string; key: string; remaining_credits: number } | null;
    exhausted_keys: { id: string; key: string; remaining_credits: number }[];
    total_credits: number;
    available_count: number;
    exhausted_count: number;
  } | null>(null);

  useEffect(() => {
    loadKeys();
  }, []);

  async function loadKeys() {
    setIsLoading(true);
    try {
      const [keys, keyStatus] = await Promise.all([
        ipcClient.getAPIKeys(),
        ipcClient.getAPIKeyStatus()
      ]);
      console.log('[APIKeysTab] Loaded keys:', keys);
      console.log('[APIKeysTab] Status:', keyStatus);
      setAPIKeys(keys);
      setStatus(keyStatus);
    } catch (err) {
      console.error('[APIKeysTab] Failed to load API keys:', err);
      setError(err instanceof Error ? err.message : 'Failed to load API keys');
    } finally {
      setIsLoading(false);
    }
  }

  async function handleAddKey() {
    if (!newKeyValue.trim()) return;
    setIsAdding(true);
    setError(null);

    try {
      const keyName = `Key ${apiKeys.length + 1}`;
      console.log('[APIKeysTab] Adding key:', keyName);
      const key = await ipcClient.addAPIKey(keyName, newKeyValue.trim());
      console.log('[APIKeysTab] Key added:', key);
      setAPIKeys([...apiKeys, key]);
      setNewKeyValue('');
      // Refresh status
      const keyStatus = await ipcClient.getAPIKeyStatus();
      setStatus(keyStatus);
    } catch (err) {
      console.error('[APIKeysTab] Failed to add API key:', err);
      setError(err instanceof Error ? err.message : 'Failed to add API key');
    } finally {
      setIsAdding(false);
    }
  }

  async function handleRemoveKey(id: string) {
    try {
      await ipcClient.removeAPIKey(id);
      setAPIKeys(apiKeys.filter((k) => k.id !== id));
      // Refresh status
      const keyStatus = await ipcClient.getAPIKeyStatus();
      setStatus(keyStatus);
    } catch (err) {
      console.error('Failed to remove API key:', err);
    }
  }

  async function handleValidateKey(id: string) {
    try {
      const updated = await ipcClient.validateAPIKey(id);
      setAPIKeys(apiKeys.map((k) => (k.id === id ? updated : k)));
    } catch (err) {
      console.error('Failed to validate API key:', err);
    }
  }

  async function handleValidateAll() {
    if (apiKeys.length === 0) return;
    setIsValidatingAll(true);
    setValidationProgress({ current: 0, total: apiKeys.length });
    setError(null);

    const updatedKeys = [...apiKeys];
    let failedCount = 0;

    for (let i = 0; i < apiKeys.length; i++) {
      setValidationProgress({ current: i + 1, total: apiKeys.length });
      try {
        const updated = await ipcClient.validateAPIKey(apiKeys[i].id);
        updatedKeys[i] = updated;
      } catch (err) {
        console.error(`Failed to validate key ${apiKeys[i].id}:`, err);
        failedCount++;
      }
    }

    setAPIKeys(updatedKeys);
    setIsValidatingAll(false);

    // Refresh status after validation
    try {
      const keyStatus = await ipcClient.getAPIKeyStatus();
      setStatus(keyStatus);
    } catch (err) {
      console.error('Failed to refresh status:', err);
    }

    if (failedCount > 0) {
      setError(`${failedCount} key(s) failed validation`);
    }
  }

  return (
    <div className="space-y-6">
      {/* Status Section */}
      {status && apiKeys.length > 0 && (
        <div className="p-4 bg-surface-800/50 rounded-lg border border-surface-700 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-surface-200">API Key Status</h3>
            <div className="text-sm text-surface-400">
              Total: {status.total_credits.toLocaleString()} credits
            </div>
          </div>
          
          {/* Active Key */}
          {status.active_key ? (
            <div className="flex items-center gap-3 p-2 bg-green-500/10 border border-green-500/30 rounded">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <div className="flex-1">
                <div className="text-xs text-green-400 uppercase font-medium">Currently Active</div>
                <div className="text-sm text-surface-200 font-mono">{status.active_key.key}</div>
              </div>
              <div className="text-sm text-green-400">
                {status.active_key.remaining_credits.toLocaleString()} credits
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-3 p-2 bg-red-500/10 border border-red-500/30 rounded">
              <div className="w-2 h-2 bg-red-500 rounded-full" />
              <div className="text-sm text-red-400">No active API key available</div>
            </div>
          )}

          {/* Exhausted Keys */}
          {status.exhausted_keys.length > 0 && (
            <div className="space-y-1">
              <div className="text-xs text-surface-500 uppercase">Exhausted Keys ({status.exhausted_count})</div>
              {status.exhausted_keys.map((k) => (
                <div key={k.id} className="flex items-center gap-3 p-2 bg-surface-700/50 rounded text-sm">
                  <div className="w-2 h-2 bg-red-500/50 rounded-full" />
                  <div className="font-mono text-surface-400">{k.key}</div>
                  <div className="text-surface-500">{k.remaining_credits} credits</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {apiKeys.length > 0 && (
        <div className="flex justify-between items-center">
          <div className="text-sm text-surface-400">
            {apiKeys.length} API key{apiKeys.length !== 1 ? 's' : ''} configured
          </div>
          <button
            onClick={handleValidateAll}
            disabled={isValidatingAll}
            className="btn-secondary text-sm"
          >
            {isValidatingAll 
              ? `Validating ${validationProgress.current}/${validationProgress.total}...` 
              : 'Validate All'}
          </button>
        </div>
      )}

      <div className="space-y-4">
        {apiKeys.map((key) => (
          <div key={key.id} className="flex items-center gap-4 p-3 bg-surface-800 rounded-lg">
            <div className="flex-1 min-w-0">
              <div className="font-medium text-surface-200 font-mono">
                {key.key.substring(0, 8)}...{key.key.substring(key.key.length - 4)}
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm font-medium text-primary-400">
                {key.remaining_credits.toLocaleString()} credits
              </div>
              <div className={`text-xs ${key.is_valid ? 'text-green-400' : 'text-red-400'}`}>
                {key.is_valid ? 'Valid' : 'Invalid'}
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handleValidateKey(key.id)}
                className="btn-ghost p-2"
                title="Validate"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
              </button>
              <button
                onClick={() => handleRemoveKey(key.id)}
                className="btn-ghost p-2 text-red-400 hover:text-red-300"
                title="Remove"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </button>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="text-center py-8 text-surface-500">
            Loading API keys...
          </div>
        )}

        {!isLoading && apiKeys.length === 0 && (
          <div className="text-center py-8 text-surface-500">
            No API keys configured. Add one below.
          </div>
        )}
      </div>

      <div className="pt-4 border-t border-surface-800 space-y-3">
        {error && (
          <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}
        <div className="flex gap-3">
          <input
            type="password"
            value={newKeyValue}
            onChange={(e) => setNewKeyValue(e.target.value)}
            placeholder="Enter your ElevenLabs API key"
            className="input flex-1"
            aria-label="API key"
            onKeyDown={(e) => e.key === 'Enter' && handleAddKey()}
          />
          <button
            onClick={handleAddKey}
            disabled={!newKeyValue.trim() || isAdding}
            className="btn-primary min-w-[100px]"
          >
            {isAdding ? 'Validating...' : 'Add'}
          </button>
        </div>
      </div>
    </div>
  );
}

function ProxiesTab() {
  const [proxies, setProxies] = useState<Proxy[]>([]);
  const [newProxy, setNewProxy] = useState({
    name: '',
    host: '',
    port: 8080,
    username: '',
    password: '',
    proxy_type: 'http',
    enabled: true,
  });

  useEffect(() => {
    loadProxies();
  }, []);

  async function loadProxies() {
    try {
      const list = await ipcClient.getProxies();
      setProxies(list);
    } catch (err) {
      console.error('Failed to load proxies:', err);
    }
  }

  async function handleAddProxy() {
    if (!newProxy.name.trim() || !newProxy.host.trim()) return;

    try {
      const proxy = await ipcClient.addProxy({
        ...newProxy,
        username: newProxy.username || null,
        password: newProxy.password || null,
      });
      setProxies([...proxies, proxy]);
      setNewProxy({
        name: '',
        host: '',
        port: 8080,
        username: '',
        password: '',
        proxy_type: 'http',
        enabled: true,
      });
    } catch (err) {
      console.error('Failed to add proxy:', err);
    }
  }

  async function handleRemoveProxy(id: string) {
    try {
      await ipcClient.removeProxy(id);
      setProxies(proxies.filter((p) => p.id !== id));
    } catch (err) {
      console.error('Failed to remove proxy:', err);
    }
  }

  async function handleTestProxy(id: string) {
    try {
      const isHealthy = await ipcClient.testProxy(id);
      setProxies(proxies.map((p) => (p.id === id ? { ...p, is_healthy: isHealthy } : p)));
    } catch (err) {
      console.error('Failed to test proxy:', err);
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        {proxies.map((proxy) => (
          <div key={proxy.id} className="flex items-center gap-4 p-3 bg-surface-800 rounded-lg">
            <div className="flex-1 min-w-0">
              <div className="font-medium text-surface-200 truncate">{proxy.name}</div>
              <div className="text-sm text-surface-500 font-mono truncate">
                {proxy.host}:{proxy.port}
              </div>
            </div>
            <div className={`text-xs px-2 py-1 rounded ${proxy.is_healthy ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
              {proxy.is_healthy ? 'Healthy' : 'Unhealthy'}
            </div>
            <div className="flex gap-2">
              <button onClick={() => handleTestProxy(proxy.id)} className="btn-ghost p-2" title="Test">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </button>
              <button onClick={() => handleRemoveProxy(proxy.id)} className="btn-ghost p-2 text-red-400" title="Remove">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        ))}

        {proxies.length === 0 && (
          <div className="text-center py-8 text-surface-500">
            No proxies configured.
          </div>
        )}
      </div>

      <div className="pt-4 border-t border-surface-800 space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <input
            type="text"
            value={newProxy.name}
            onChange={(e) => setNewProxy({ ...newProxy, name: e.target.value })}
            placeholder="Proxy name"
            className="input"
          />
          <input
            type="text"
            value={newProxy.host}
            onChange={(e) => setNewProxy({ ...newProxy, host: e.target.value })}
            placeholder="Host"
            className="input"
          />
          <input
            type="number"
            value={newProxy.port}
            onChange={(e) => setNewProxy({ ...newProxy, port: parseInt(e.target.value) || 8080 })}
            placeholder="Port"
            className="input"
          />
          <select
            value={newProxy.proxy_type}
            onChange={(e) => setNewProxy({ ...newProxy, proxy_type: e.target.value })}
            className="input"
          >
            <option value="http">HTTP</option>
            <option value="https">HTTPS</option>
            <option value="socks5">SOCKS5</option>
          </select>
        </div>
        <button
          onClick={handleAddProxy}
          disabled={!newProxy.name.trim() || !newProxy.host.trim()}
          className="btn-primary w-full"
        >
          Add Proxy
        </button>
      </div>
    </div>
  );
}

// Voice Presets Tab
function PresetsTab() {
  const [presets, setPresets] = useState<VoicePreset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [newPreset, setNewPreset] = useState({
    name: '',
    voice_id: '',
    voice_name: '',
    description: '',
    stability: 0.5,
    similarity_boost: 0.75,
    style: 0,
    speed: 1.0,
  });
  const { voices } = useAppStore();

  useEffect(() => {
    loadPresets();
  }, []);

  async function loadPresets() {
    try {
      const data = await ipcClient.getPresets();
      setPresets(data);
    } catch (err) {
      console.error('Failed to load presets:', err);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSavePreset() {
    if (!newPreset.name || !newPreset.voice_id) return;
    try {
      const preset = await ipcClient.savePreset({
        name: newPreset.name,
        voice_id: newPreset.voice_id,
        voice_name: newPreset.voice_name,
        description: newPreset.description,
        settings: {
          stability: newPreset.stability,
          similarity_boost: newPreset.similarity_boost,
          style: newPreset.style,
          speed: newPreset.speed,
        },
      });
      setPresets([...presets, preset]);
      setShowForm(false);
      setNewPreset({ name: '', voice_id: '', voice_name: '', description: '', stability: 0.5, similarity_boost: 0.75, style: 0, speed: 1.0 });
    } catch (err) {
      console.error('Failed to save preset:', err);
    }
  }

  async function handleDeletePreset(id: string) {
    try {
      await ipcClient.deletePreset(id);
      setPresets(presets.filter(p => p.id !== id));
    } catch (err) {
      console.error('Failed to delete preset:', err);
    }
  }

  if (isLoading) {
    return <div className="text-surface-400">Loading presets...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-medium text-surface-200">Voice Presets</h2>
        <button onClick={() => setShowForm(!showForm)} className="btn-secondary text-sm">
          {showForm ? 'Cancel' : 'New Preset'}
        </button>
      </div>

      {showForm && (
        <div className="p-4 bg-surface-800/50 rounded-lg space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input
              type="text"
              value={newPreset.name}
              onChange={(e) => setNewPreset({ ...newPreset, name: e.target.value })}
              placeholder="Preset name"
              className="input"
            />
            <select
              value={newPreset.voice_id}
              onChange={(e) => {
                const voice = voices.find(v => v.voice_id === e.target.value);
                setNewPreset({ ...newPreset, voice_id: e.target.value, voice_name: voice?.name || '' });
              }}
              className="input"
            >
              <option value="">Select voice...</option>
              {voices.map(v => (
                <option key={v.voice_id} value={v.voice_id}>{v.name}</option>
              ))}
            </select>
          </div>
          <input
            type="text"
            value={newPreset.description}
            onChange={(e) => setNewPreset({ ...newPreset, description: e.target.value })}
            placeholder="Description (optional)"
            className="input w-full"
          />
          <div className="grid grid-cols-4 gap-3">
            <div>
              <label className="text-xs text-surface-500">Stability</label>
              <input
                type="number"
                min={0} max={1} step={0.1}
                value={newPreset.stability}
                onChange={(e) => setNewPreset({ ...newPreset, stability: parseFloat(e.target.value) })}
                className="input w-full"
              />
            </div>
            <div>
              <label className="text-xs text-surface-500">Similarity</label>
              <input
                type="number"
                min={0} max={1} step={0.1}
                value={newPreset.similarity_boost}
                onChange={(e) => setNewPreset({ ...newPreset, similarity_boost: parseFloat(e.target.value) })}
                className="input w-full"
              />
            </div>
            <div>
              <label className="text-xs text-surface-500">Style</label>
              <input
                type="number"
                min={0} max={1} step={0.1}
                value={newPreset.style}
                onChange={(e) => setNewPreset({ ...newPreset, style: parseFloat(e.target.value) })}
                className="input w-full"
              />
            </div>
            <div>
              <label className="text-xs text-surface-500">Speed</label>
              <input
                type="number"
                min={0.5} max={2} step={0.1}
                value={newPreset.speed}
                onChange={(e) => setNewPreset({ ...newPreset, speed: parseFloat(e.target.value) })}
                className="input w-full"
              />
            </div>
          </div>
          <button onClick={handleSavePreset} disabled={!newPreset.name || !newPreset.voice_id} className="btn-primary w-full">
            Save Preset
          </button>
        </div>
      )}

      {presets.length === 0 ? (
        <div className="text-center py-8 text-surface-500">No presets saved yet</div>
      ) : (
        <div className="space-y-2">
          {presets.map(preset => (
            <div key={preset.id} className="p-3 bg-surface-800/50 rounded-lg flex items-center justify-between">
              <div>
                <div className="font-medium text-surface-200">{preset.name}</div>
                <div className="text-xs text-surface-500">{preset.voice_name} | S:{preset.settings.stability} B:{preset.settings.similarity_boost}</div>
                {preset.description && <div className="text-xs text-surface-400 mt-1">{preset.description}</div>}
              </div>
              <button onClick={() => handleDeletePreset(preset.id)} className="text-red-400 hover:text-red-300 p-1">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Voice Patterns Tab
function VoicePatternsTab() {
  const [patterns, setPatterns] = useState<VoicePattern[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [newPattern, setNewPattern] = useState<{
    name: string;
    pattern: string;
    voice_id: string;
    voice_name: string;
    match_type: 'contains' | 'starts_with' | 'ends_with' | 'exact' | 'regex';
    case_sensitive: boolean;
    priority: number;
  }>({
    name: '',
    pattern: '',
    voice_id: '',
    voice_name: '',
    match_type: 'contains',
    case_sensitive: false,
    priority: 0,
  });
  const { voices } = useAppStore();

  useEffect(() => {
    loadPatterns();
  }, []);

  async function loadPatterns() {
    try {
      const data = await ipcClient.getVoicePatterns();
      setPatterns(data);
    } catch (err) {
      console.error('Failed to load patterns:', err);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleAddPattern() {
    if (!newPattern.name || !newPattern.pattern || !newPattern.voice_id) return;
    try {
      const pattern = await ipcClient.addVoicePattern({
        name: newPattern.name,
        pattern: newPattern.pattern,
        voice_id: newPattern.voice_id,
        voice_name: newPattern.voice_name,
        match_type: newPattern.match_type,
        case_sensitive: newPattern.case_sensitive,
        priority: newPattern.priority,
      });
      setPatterns([...patterns, pattern]);
      setShowForm(false);
      setNewPattern({ name: '', pattern: '', voice_id: '', voice_name: '', match_type: 'contains', case_sensitive: false, priority: 0 });
    } catch (err) {
      console.error('Failed to add pattern:', err);
    }
  }

  async function handleDeletePattern(id: string) {
    try {
      await ipcClient.deleteVoicePattern(id);
      setPatterns(patterns.filter(p => p.id !== id));
    } catch (err) {
      console.error('Failed to delete pattern:', err);
    }
  }

  if (isLoading) {
    return <div className="text-surface-400">Loading patterns...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-lg font-medium text-surface-200">Voice Patterns</h2>
          <p className="text-xs text-surface-500">Auto-assign voices based on text patterns</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="btn-secondary text-sm">
          {showForm ? 'Cancel' : 'New Pattern'}
        </button>
      </div>

      {showForm && (
        <div className="p-4 bg-surface-800/50 rounded-lg space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input
              type="text"
              value={newPattern.name}
              onChange={(e) => setNewPattern({ ...newPattern, name: e.target.value })}
              placeholder="Pattern name (e.g., Narrator)"
              className="input"
            />
            <input
              type="text"
              value={newPattern.pattern}
              onChange={(e) => setNewPattern({ ...newPattern, pattern: e.target.value })}
              placeholder="Pattern (e.g., [Narrator])"
              className="input"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <select
              value={newPattern.voice_id}
              onChange={(e) => {
                const voice = voices.find(v => v.voice_id === e.target.value);
                setNewPattern({ ...newPattern, voice_id: e.target.value, voice_name: voice?.name || '' });
              }}
              className="input"
            >
              <option value="">Select voice...</option>
              {voices.map(v => (
                <option key={v.voice_id} value={v.voice_id}>{v.name}</option>
              ))}
            </select>
            <select
              value={newPattern.match_type}
              onChange={(e) => setNewPattern({ ...newPattern, match_type: e.target.value as typeof newPattern.match_type })}
              className="input"
            >
              <option value="contains">Contains</option>
              <option value="starts_with">Starts with</option>
              <option value="ends_with">Ends with</option>
              <option value="exact">Exact match</option>
              <option value="regex">Regex</option>
            </select>
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={newPattern.case_sensitive}
                onChange={(e) => setNewPattern({ ...newPattern, case_sensitive: e.target.checked })}
                className="w-4 h-4"
              />
              <span className="text-sm text-surface-300">Case sensitive</span>
            </label>
            <div className="flex items-center gap-2">
              <label className="text-sm text-surface-400">Priority:</label>
              <input
                type="number"
                value={newPattern.priority}
                onChange={(e) => setNewPattern({ ...newPattern, priority: parseInt(e.target.value) || 0 })}
                className="input w-20"
              />
            </div>
          </div>
          <button onClick={handleAddPattern} disabled={!newPattern.name || !newPattern.pattern || !newPattern.voice_id} className="btn-primary w-full">
            Add Pattern
          </button>
        </div>
      )}

      {patterns.length === 0 ? (
        <div className="text-center py-8 text-surface-500">No patterns configured</div>
      ) : (
        <div className="space-y-2">
          {patterns.map(pattern => (
            <div key={pattern.id} className="p-3 bg-surface-800/50 rounded-lg flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-surface-200">{pattern.name}</span>
                  <span className="text-xs px-2 py-0.5 bg-surface-700 rounded">{pattern.match_type}</span>
                  {pattern.case_sensitive && <span className="text-xs px-2 py-0.5 bg-surface-700 rounded">Aa</span>}
                </div>
                <div className="text-xs text-surface-500 font-mono mt-1">"{pattern.pattern}" → {pattern.voice_name}</div>
              </div>
              <button onClick={() => handleDeletePattern(pattern.id)} className="text-red-400 hover:text-red-300 p-1">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Analytics Tab
function AnalyticsTab() {
  const [stats, setStats] = useState<AnalyticsStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  async function loadStats() {
    try {
      const data = await ipcClient.getAnalytics();
      setStats(data);
    } catch (err) {
      console.error('Failed to load analytics:', err);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleReset() {
    if (!confirm('Are you sure you want to reset all analytics data?')) return;
    try {
      await ipcClient.resetAnalytics();
      setStats(null);
      loadStats();
    } catch (err) {
      console.error('Failed to reset analytics:', err);
    }
  }

  if (isLoading) {
    return <div className="text-surface-400">Loading analytics...</div>;
  }

  if (!stats) {
    return <div className="text-surface-400">No analytics data available</div>;
  }

  const topVoices = Object.entries(stats.voice_usage)
    .sort(([,a], [,b]) => b - a)
    .slice(0, 5);

  const recentDays = Object.entries(stats.daily_usage)
    .sort(([a], [b]) => b.localeCompare(a))
    .slice(0, 7)
    .reverse();

  const maxDaily = Math.max(...recentDays.map(([,v]) => v), 1);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-medium text-surface-200">Usage Analytics</h2>
        <button onClick={handleReset} className="btn-ghost text-sm text-red-400">Reset Data</button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="p-4 bg-surface-800/50 rounded-lg">
          <div className="text-2xl font-bold text-primary-400">{stats.total_characters.toLocaleString()}</div>
          <div className="text-xs text-surface-500">Total Characters</div>
        </div>
        <div className="p-4 bg-surface-800/50 rounded-lg">
          <div className="text-2xl font-bold text-green-400">{stats.total_lines.toLocaleString()}</div>
          <div className="text-xs text-surface-500">Total Lines</div>
        </div>
        <div className="p-4 bg-surface-800/50 rounded-lg">
          <div className="text-2xl font-bold text-blue-400">{stats.total_sessions}</div>
          <div className="text-xs text-surface-500">Sessions</div>
        </div>
        <div className="p-4 bg-surface-800/50 rounded-lg">
          <div className="text-2xl font-bold text-red-400">{stats.error_count}</div>
          <div className="text-xs text-surface-500">Errors</div>
        </div>
      </div>

      {/* Daily Usage Chart */}
      {recentDays.length > 0 && (
        <div className="p-4 bg-surface-800/50 rounded-lg">
          <h3 className="text-sm font-medium text-surface-300 mb-3">Daily Usage (Last 7 days)</h3>
          <div className="flex items-end gap-2 h-32">
            {recentDays.map(([date, chars]) => (
              <div key={date} className="flex-1 flex flex-col items-center">
                <div
                  className="w-full bg-primary-500/50 rounded-t"
                  style={{ height: `${(chars / maxDaily) * 100}%`, minHeight: chars > 0 ? '4px' : '0' }}
                />
                <div className="text-xs text-surface-500 mt-1">{date.slice(5)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top Voices */}
      {topVoices.length > 0 && (
        <div className="p-4 bg-surface-800/50 rounded-lg">
          <h3 className="text-sm font-medium text-surface-300 mb-3">Top Voices</h3>
          <div className="space-y-2">
            {topVoices.map(([voiceId, count]) => (
              <div key={voiceId} className="flex items-center justify-between">
                <span className="text-sm text-surface-400 font-mono truncate max-w-[200px]">{voiceId}</span>
                <span className="text-sm text-surface-300">{count.toLocaleString()} chars</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Timestamps */}
      <div className="text-xs text-surface-500 flex gap-4">
        {stats.first_use && <span>First use: {new Date(stats.first_use).toLocaleDateString()}</span>}
        {stats.last_use && <span>Last use: {new Date(stats.last_use).toLocaleDateString()}</span>}
      </div>
    </div>
  );
}
