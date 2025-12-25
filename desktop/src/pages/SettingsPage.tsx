import { useState, useEffect } from 'react';
import { ipcClient, VoicePreset, VoicePattern, AnalyticsStats } from '../lib/ipc';
import { getPlatformAPI } from '../lib/platform';
import { checkForUpdates } from '../lib/updater';
import { useAppStore } from '../stores/appStore';
import { Proxy } from '../lib/ipc/types';
import { useTranslation, AVAILABLE_LANGUAGES } from '../lib/i18n';

type SettingsTab = 'general' | 'appearance' | 'apikeys' | 'proxies' | 'presets' | 'patterns' | 'analytics' | 'about';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('general');
  const { setConfig, setAPIKeys, versionInfo } = useAppStore();
  const { language, setLanguage, t } = useTranslation();

  const [outputFolder, setOutputFolder] = useState('');
  const [threadCount, setThreadCount] = useState(5);
  const [maxRetries, setMaxRetries] = useState(3);

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

  const tabs: { id: SettingsTab; labelKey: string }[] = [
    { id: 'general', labelKey: 'settings.general' },
    { id: 'appearance', labelKey: 'settings.appearance' },
    { id: 'apikeys', labelKey: 'settings.api_keys' },
    { id: 'proxies', labelKey: 'settings.proxies' },
    { id: 'presets', labelKey: 'settings.presets' },
    { id: 'patterns', labelKey: 'settings.voice_patterns' },
    { id: 'analytics', labelKey: 'settings.analytics' },
    { id: 'about', labelKey: 'settings.about' },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h1 className="text-2xl font-semibold text-surface-100">{t('settings.title')}</h1>

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
            {t(tab.labelKey)}
          </button>
        ))}
      </div>

      <div className="card" role="tabpanel">
        {activeTab === 'general' && (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-surface-300 mb-2">
                {t('settings.output_folder')}
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
                  {t('common.browse')}
                </button>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-surface-300 mb-2">
                  {t('settings.thread_count')}
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
                <p className="text-xs text-surface-500 mt-1">{t('settings.thread_count_desc')}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-300 mb-2">
                  {t('settings.max_retries')}
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
                <p className="text-xs text-surface-500 mt-1">{t('settings.max_retries_desc')}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-300 mb-2">
                  {t('settings.language')}
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="input"
                  aria-label="Interface language"
                >
                  {AVAILABLE_LANGUAGES.map((lang) => (
                    <option key={lang.code} value={lang.code}>{lang.name}</option>
                  ))}
                </select>
                <p className="text-xs text-surface-500 mt-1">{t('settings.language_desc')}</p>
              </div>
            </div>

            <div className="flex justify-end pt-4 border-t border-surface-800">
              <button onClick={handleSaveGeneral} className="btn-primary">
                {t('settings.save_changes')}
              </button>
            </div>
          </div>
        )}

        {activeTab === 'appearance' && <AppearanceTab />}
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
                <p className="text-sm text-surface-400">{t('about.description')}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-surface-800 rounded-lg">
                <div className="text-xs text-surface-500 uppercase">{t('about.ui_version')}</div>
                <div className="text-lg font-medium text-surface-200">
                  {versionInfo?.uiVersion || t('common.unknown')}
                </div>
              </div>
              <div className="p-3 bg-surface-800 rounded-lg">
                <div className="text-xs text-surface-500 uppercase">{t('about.backend_version')}</div>
                <div className="text-lg font-medium text-surface-200">
                  {versionInfo?.backendVersion || t('common.unknown')}
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
                {t('about.check_updates')}
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
                {t('settings.export_diagnostics')}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function APIKeysTab() {
  const { t } = useTranslation();
  const { apiKeys, setAPIKeys } = useAppStore();
  const [newKeyValue, setNewKeyValue] = useState('');
  const [isAdding, setIsAdding] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isValidatingAll, setIsValidatingAll] = useState(false);
  const [validationProgress, setValidationProgress] = useState({ current: 0, total: 0 });
  const [error, setError] = useState<string | null>(null);
  const [proxies, setProxies] = useState<Proxy[]>([]);
  const [status, setStatus] = useState<{
    active_key: { id: string; key: string; remaining_credits: number } | null;
    exhausted_keys: { id: string; key: string; remaining_credits: number }[];
    total_credits: number;
    available_count: number;
    exhausted_count: number;
  } | null>(null);

  useEffect(() => {
    loadKeys();
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

  async function handleAssignProxy(keyId: string, proxyId: string | null) {
    try {
      await ipcClient.assignProxyToKey(keyId, proxyId);
      // Update local state
      setAPIKeys(apiKeys.map(k => 
        k.id === keyId ? { ...k, assigned_proxy_id: proxyId } : k
      ));
    } catch (err) {
      console.error('Failed to assign proxy:', err);
      setError(err instanceof Error ? err.message : 'Failed to assign proxy');
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
            <h3 className="text-sm font-medium text-surface-200">{t('apikeys.status')}</h3>
            <div className="text-sm text-surface-400">
              {t('apikeys.total')}: {status.total_credits.toLocaleString()} {t('tts.credits').toLowerCase()}
            </div>
          </div>
          
          {/* Active Key */}
          {status.active_key ? (
            <div className="flex items-center gap-3 p-2 bg-green-500/10 border border-green-500/30 rounded">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <div className="flex-1">
                <div className="text-xs text-green-400 uppercase font-medium">{t('apikeys.active')}</div>
                <div className="text-sm text-surface-200 font-mono">{status.active_key.key}</div>
              </div>
              <div className="text-sm text-green-400">
                {status.active_key.remaining_credits.toLocaleString()} {t('tts.credits').toLowerCase()}
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-3 p-2 bg-red-500/10 border border-red-500/30 rounded">
              <div className="w-2 h-2 bg-red-500 rounded-full" />
              <div className="text-sm text-red-400">{t('apikeys.no_active')}</div>
            </div>
          )}

          {/* Exhausted Keys */}
          {status.exhausted_keys.length > 0 && (
            <div className="space-y-1">
              <div className="text-xs text-surface-500 uppercase">{t('apikeys.exhausted')} ({status.exhausted_count})</div>
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
            {apiKeys.length} API key{apiKeys.length !== 1 ? 's' : ''} {t('apikeys.configured')}
          </div>
          <button
            onClick={handleValidateAll}
            disabled={isValidatingAll}
            className="btn-secondary text-sm"
          >
            {isValidatingAll 
              ? `${t('apikeys.validating')} ${validationProgress.current}/${validationProgress.total}...` 
              : t('apikeys.validate_all')}
          </button>
        </div>
      )}

      <div className="space-y-4">
        {apiKeys.map((key) => (
          <div key={key.id} className="p-3 bg-surface-800 rounded-lg space-y-2">
            <div className="flex items-center gap-4">
              <div className="flex-1 min-w-0">
                <div className="font-medium text-surface-200 font-mono">
                  {key.key.substring(0, 8)}...{key.key.substring(key.key.length - 4)}
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm font-medium text-primary-400">
                  {key.remaining_credits.toLocaleString()} {t('tts.credits').toLowerCase()}
                </div>
                <div className={`text-xs ${key.is_valid ? 'text-green-400' : 'text-red-400'}`}>
                  {key.is_valid ? t('apikeys.valid') : t('apikeys.invalid')}
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
            {/* Proxy Assignment */}
            {proxies.length > 0 && (
              <div className="flex items-center gap-2 pt-2 border-t border-surface-700">
                <span className="text-xs text-surface-500">{t('apikeys.proxy') || 'Proxy'}:</span>
                <select
                  value={key.assigned_proxy_id || ''}
                  onChange={(e) => handleAssignProxy(key.id, e.target.value || null)}
                  className="flex-1 px-2 py-1 text-xs bg-surface-900 border border-surface-700 rounded"
                >
                  <option value="">{t('apikeys.no_proxy') || 'Direct (No Proxy)'}</option>
                  {proxies.map(p => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.host}:{p.port}) {!p.is_healthy && '⚠️'}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="text-center py-8 text-surface-500">
            {t('apikeys.loading')}
          </div>
        )}

        {!isLoading && apiKeys.length === 0 && (
          <div className="text-center py-8 text-surface-500">
            {t('apikeys.no_keys')}
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
            placeholder={t('apikeys.add_placeholder')}
            className="input flex-1"
            aria-label="API key"
            onKeyDown={(e) => e.key === 'Enter' && handleAddKey()}
          />
          <button
            onClick={handleAddKey}
            disabled={!newKeyValue.trim() || isAdding}
            className="btn-primary min-w-[100px]"
          >
            {isAdding ? t('apikeys.validating') + '...' : t('common.add')}
          </button>
        </div>
      </div>
    </div>
  );
}

function ProxiesTab() {
  const { t } = useTranslation();
  const [proxies, setProxies] = useState<Proxy[]>([]);
  const [showGuide, setShowGuide] = useState(true);
  const [showAuth, setShowAuth] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [importMode, setImportMode] = useState(false);
  const [importText, setImportText] = useState('');
  const [importError, setImportError] = useState<string | null>(null);
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

  // Parse proxy string in various formats
  function parseProxyString(str: string): { host: string; port: number; username?: string; password?: string; type: string } | null {
    str = str.trim();
    if (!str) return null;

    let type = 'http';
    let host = '';
    let port = 8080;
    let username: string | undefined;
    let password: string | undefined;

    // Remove protocol prefix and detect type
    if (str.startsWith('socks5://')) {
      type = 'socks5';
      str = str.slice(9);
    } else if (str.startsWith('socks://')) {
      type = 'socks5';
      str = str.slice(8);
    } else if (str.startsWith('https://')) {
      type = 'https';
      str = str.slice(8);
    } else if (str.startsWith('http://')) {
      type = 'http';
      str = str.slice(7);
    }

    // Format: user:pass@host:port
    if (str.includes('@')) {
      const [authPart, hostPart] = str.split('@');
      const authParts = authPart.split(':');
      if (authParts.length >= 2) {
        username = authParts[0];
        password = authParts.slice(1).join(':'); // password might contain ':'
      }
      str = hostPart;
    }

    // Handle IPv6 in brackets: [ipv6]:port
    if (str.startsWith('[')) {
      const bracketEnd = str.indexOf(']');
      if (bracketEnd > 0) {
        host = str.slice(1, bracketEnd);
        const remaining = str.slice(bracketEnd + 1);
        if (remaining.startsWith(':')) {
          port = parseInt(remaining.slice(1)) || 8080;
        }
      }
    } else {
      // Format: host:port or host:port:user:pass
      const parts = str.split(':');
      
      if (parts.length === 2) {
        // host:port
        host = parts[0];
        port = parseInt(parts[1]) || 8080;
      } else if (parts.length === 4) {
        // host:port:user:pass
        host = parts[0];
        port = parseInt(parts[1]) || 8080;
        username = parts[2];
        password = parts[3];
      } else if (parts.length >= 4 && parts[0].match(/^[\d.]+$/) || parts[0].match(/^[a-zA-Z0-9.-]+$/)) {
        // Likely host:port:user:pass where pass might contain ':'
        host = parts[0];
        port = parseInt(parts[1]) || 8080;
        username = parts[2];
        password = parts.slice(3).join(':');
      } else {
        // Could be IPv6 without brackets
        // Try to find the last : as port separator
        const lastColon = str.lastIndexOf(':');
        if (lastColon > 0) {
          const potentialPort = parseInt(str.slice(lastColon + 1));
          if (!isNaN(potentialPort) && potentialPort > 0 && potentialPort <= 65535) {
            host = str.slice(0, lastColon);
            port = potentialPort;
          } else {
            host = str;
          }
        } else {
          host = str;
        }
      }
    }

    if (!host) return null;
    return { host, port, username, password, type };
  }

  async function handleQuickImport() {
    setImportError(null);
    const lines = importText.split('\n').filter(l => l.trim());
    
    if (lines.length === 0) {
      setImportError(t('proxies.import_empty') || 'No proxy strings to import');
      return;
    }

    let successCount = 0;
    let failCount = 0;
    const newProxies: Proxy[] = [];

    for (let i = 0; i < lines.length; i++) {
      const parsed = parseProxyString(lines[i]);
      if (parsed) {
        try {
          const proxy = await ipcClient.addProxy({
            name: `Proxy ${proxies.length + newProxies.length + 1}`,
            host: parsed.host,
            port: parsed.port,
            username: parsed.username || null,
            password: parsed.password || null,
            proxy_type: parsed.type,
            enabled: true,
          });
          newProxies.push(proxy);
          successCount++;
        } catch {
          failCount++;
        }
      } else {
        failCount++;
      }
    }

    setProxies([...proxies, ...newProxies]);
    
    if (failCount === 0) {
      setImportText('');
      setImportMode(false);
    } else {
      setImportError(`${t('proxies.import_result') || 'Imported'}: ${successCount} ${t('proxies.import_success') || 'success'}, ${failCount} ${t('proxies.import_failed') || 'failed'}`);
    }
  }

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
      setShowAuth(false);
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
    setTestingId(id);
    try {
      const isHealthy = await ipcClient.testProxy(id);
      setProxies(proxies.map((p) => (p.id === id ? { ...p, is_healthy: isHealthy } : p)));
    } catch (err) {
      console.error('Failed to test proxy:', err);
      setProxies(proxies.map((p) => (p.id === id ? { ...p, is_healthy: false } : p)));
    } finally {
      setTestingId(null);
    }
  }

  return (
    <div className="space-y-6">
      {/* Proxy Guide */}
      {showGuide && (
        <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg relative">
          <button
            onClick={() => setShowGuide(false)}
            className="absolute top-2 right-2 text-surface-400 hover:text-surface-200"
            title={t('proxies.dismiss_guide') || 'Dismiss'}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <div className="flex gap-3">
            <div className="text-blue-400 mt-0.5">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="flex-1 space-y-2">
              <h3 className="font-medium text-blue-300">{t('proxies.guide_title') || 'How to Use Proxies'}</h3>
              <div className="text-sm text-surface-300 space-y-2">
                <p><strong>{t('proxies.guide_what') || 'What are proxies?'}</strong> {t('proxies.guide_what_desc') || 'Proxies route your API requests through an intermediate server, useful for bypassing network restrictions or distributing requests.'}</p>
                <div className="space-y-1">
                  <p className="font-medium text-surface-200">{t('proxies.guide_steps') || 'Quick Setup:'}</p>
                  <ol className="list-decimal list-inside space-y-1 text-surface-400">
                    <li>{t('proxies.guide_step1') || 'Enter a name to identify this proxy'}</li>
                    <li>{t('proxies.guide_step2') || 'Enter the proxy host (e.g., proxy.example.com or 192.168.1.100)'}</li>
                    <li>{t('proxies.guide_step3') || 'Set the port number (common: 8080, 3128, 1080 for SOCKS5)'}</li>
                    <li>{t('proxies.guide_step4') || 'Select proxy type: HTTP for most cases, SOCKS5 for advanced routing'}</li>
                    <li>{t('proxies.guide_step5') || 'Click "Test" to verify the proxy works with ElevenLabs API'}</li>
                  </ol>
                </div>
                <p className="text-xs text-surface-500 italic">{t('proxies.guide_tip') || 'Tip: Proxies are automatically used when assigned to API keys. A green status means the proxy can reach ElevenLabs servers.'}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Show guide button if dismissed */}
      {!showGuide && (
        <button
          onClick={() => setShowGuide(true)}
          className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {t('proxies.show_guide') || 'Show setup guide'}
        </button>
      )}

      {/* Proxy List */}
      <div className="space-y-4">
        {proxies.map((proxy) => (
          <div key={proxy.id} className="flex items-center gap-4 p-3 bg-surface-800 rounded-lg">
            <div className="flex-1 min-w-0">
              <div className="font-medium text-surface-200 truncate">{proxy.name}</div>
              <div className="text-sm text-surface-500 font-mono truncate">
                {proxy.proxy_type.toUpperCase()} · {proxy.host}:{proxy.port}
              </div>
            </div>
            <div className={`text-xs px-2 py-1 rounded ${proxy.is_healthy ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
              {proxy.is_healthy ? t('proxies.healthy') : t('proxies.unhealthy')}
            </div>
            <div className="flex gap-2">
              <button 
                onClick={() => handleTestProxy(proxy.id)} 
                className="btn-ghost p-2" 
                title={t('proxies.test_tooltip') || 'Test connection to ElevenLabs API through this proxy'}
                disabled={testingId === proxy.id}
              >
                {testingId === proxy.id ? (
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                )}
              </button>
              <button 
                onClick={() => handleRemoveProxy(proxy.id)} 
                className="btn-ghost p-2 text-red-400" 
                title={t('proxies.remove_tooltip') || 'Remove this proxy'}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        ))}

        {proxies.length === 0 && (
          <div className="text-center py-8 text-surface-500">
            {t('proxies.no_proxies')}
          </div>
        )}
      </div>

      {/* Add Proxy Form */}
      <div className="pt-4 border-t border-surface-800 space-y-3">
        <div className="flex items-center justify-between">
          <div className="text-sm font-medium text-surface-300">{t('proxies.add_new') || 'Add New Proxy'}</div>
          <div className="flex gap-2">
            <button
              onClick={() => setImportMode(false)}
              className={`text-xs px-2 py-1 rounded ${!importMode ? 'bg-primary-500/20 text-primary-400' : 'text-surface-400 hover:text-surface-200'}`}
            >
              {t('proxies.manual_mode') || 'Manual'}
            </button>
            <button
              onClick={() => setImportMode(true)}
              className={`text-xs px-2 py-1 rounded ${importMode ? 'bg-primary-500/20 text-primary-400' : 'text-surface-400 hover:text-surface-200'}`}
            >
              {t('proxies.import_mode') || 'Quick Import'}
            </button>
          </div>
        </div>

        {importMode ? (
          /* Quick Import Mode */
          <div className="space-y-3">
            <div>
              <textarea
                value={importText}
                onChange={(e) => setImportText(e.target.value)}
                placeholder={t('proxies.import_placeholder') || 'Paste proxy strings (one per line):\nhost:port\nhost:port:user:pass\nuser:pass@host:port\nsocks5://host:port'}
                className="input w-full h-32 font-mono text-sm"
              />
              <p className="text-xs text-surface-500 mt-1">
                {t('proxies.import_formats') || 'Supported formats: host:port, host:port:user:pass, user:pass@host:port, protocol://...'}
              </p>
            </div>
            {importError && (
              <div className="p-2 bg-red-500/10 border border-red-500/30 rounded text-sm text-red-400">
                {importError}
              </div>
            )}
            <button
              onClick={handleQuickImport}
              disabled={!importText.trim()}
              className="btn-primary w-full"
            >
              {t('proxies.import_button') || 'Import Proxies'}
            </button>
          </div>
        ) : (
          /* Manual Mode */
          <>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <input
                  type="text"
                  value={newProxy.name}
                  onChange={(e) => setNewProxy({ ...newProxy, name: e.target.value })}
                  placeholder={t('proxies.name_placeholder') || 'My Proxy'}
                  className="input w-full"
                />
                <p className="text-xs text-surface-500 mt-1">{t('proxies.name_hint') || 'Friendly name to identify this proxy'}</p>
              </div>
              <div>
                <input
                  type="text"
                  value={newProxy.host}
                  onChange={(e) => setNewProxy({ ...newProxy, host: e.target.value })}
                  placeholder={t('proxies.host_placeholder') || 'proxy.example.com'}
                  className="input w-full"
                />
                <p className="text-xs text-surface-500 mt-1">{t('proxies.host_hint') || 'Hostname or IP address'}</p>
              </div>
              <div>
                <input
                  type="number"
                  value={newProxy.port}
                  onChange={(e) => setNewProxy({ ...newProxy, port: parseInt(e.target.value) || 8080 })}
                  placeholder="8080"
                  className="input w-full"
                  min={1}
                  max={65535}
                />
                <p className="text-xs text-surface-500 mt-1">{t('proxies.port_hint') || 'Common: 8080, 3128, 1080'}</p>
              </div>
              <div>
                <select
                  value={newProxy.proxy_type}
                  onChange={(e) => setNewProxy({ ...newProxy, proxy_type: e.target.value })}
                  className="input w-full"
                >
                  <option value="http">HTTP - {t('proxies.type_http_desc') || 'Standard web proxy'}</option>
                  <option value="https">HTTPS - {t('proxies.type_https_desc') || 'Encrypted proxy'}</option>
                  <option value="socks5">SOCKS5 - {t('proxies.type_socks5_desc') || 'Advanced routing'}</option>
                </select>
                <p className="text-xs text-surface-500 mt-1">{t('proxies.type_hint') || 'HTTP works for most cases'}</p>
              </div>
            </div>

            {/* Authentication Toggle */}
            <div>
              <button
                onClick={() => setShowAuth(!showAuth)}
                className="text-sm text-primary-400 hover:text-primary-300 flex items-center gap-1"
              >
                <svg className={`w-3 h-3 transition-transform ${showAuth ? 'rotate-90' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                {t('proxies.auth_toggle') || 'Authentication (optional)'}
              </button>
              
              {showAuth && (
                <div className="grid grid-cols-2 gap-3 mt-2">
                  <div>
                    <input
                      type="text"
                      value={newProxy.username}
                      onChange={(e) => setNewProxy({ ...newProxy, username: e.target.value })}
                      placeholder={t('proxies.username_placeholder') || 'Username'}
                      className="input w-full"
                    />
                  </div>
                  <div>
                    <input
                      type="password"
                      value={newProxy.password}
                      onChange={(e) => setNewProxy({ ...newProxy, password: e.target.value })}
                      placeholder={t('proxies.password_placeholder') || 'Password'}
                      className="input w-full"
                    />
                  </div>
                  <p className="col-span-2 text-xs text-surface-500">{t('proxies.auth_hint') || 'Only required if your proxy requires authentication'}</p>
                </div>
              )}
            </div>

            <button
              onClick={handleAddProxy}
              disabled={!newProxy.name.trim() || !newProxy.host.trim()}
              className="btn-primary w-full"
            >
              {t('proxies.add_button') || 'Add Proxy'}
            </button>
          </>
        )}
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

function AppearanceTab() {
  const { t } = useTranslation();
  const { config, setConfig } = useAppStore();
  const [theme, setTheme] = useState(config?.theme || 'dark');
  const [bgImage, setBgImage] = useState(config?.background_image || '');
  const [bgOpacity, setBgOpacity] = useState(config?.background_opacity ?? 0.5);
  const [bgBlur, setBgBlur] = useState(config?.background_blur ?? 0);

  useEffect(() => {
    if (config) {
      setTheme(config.theme);
      setBgImage(config.background_image || '');
      setBgOpacity(config.background_opacity ?? 0.5);
      setBgBlur(config.background_blur ?? 0);
    }
  }, [config]);

  const applyChanges = async (updates: Record<string, any>) => {
    // 1. Update Backend
    for (const [key, value] of Object.entries(updates)) {
      await ipcClient.setConfig(key, value);
    }
    
    // 2. Update Store
    if (config) {
      // Cast to any to handle extended config fields
      setConfig({ ...config, ...updates } as any);
    }
  };

  const handleThemeChange = async (newTheme: string) => {
    setTheme(newTheme);
    await applyChanges({ theme: newTheme });
  };

  const handleBgImageChange = async (newImage: string) => {
    setBgImage(newImage);
    await applyChanges({ background_image: newImage });
  };

  const handleOpacityChange = async (newOpacity: number) => {
    setBgOpacity(newOpacity);
    await applyChanges({ background_opacity: newOpacity });
  };
  
  const handleBlurChange = async (newBlur: number) => {
    setBgBlur(newBlur);
    await applyChanges({ background_blur: newBlur });
  };

  async function handleBrowseImage() {
    try {
      const api = await getPlatformAPI();
      const file = await api.dialog.openFile({
        title: t('settings.browse_image'),
        filters: [{ name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'webp', 'gif'] }]
      });
      if (file && file.length > 0) {
        handleBgImageChange(file[0]);
      }
    } catch (err) {
      console.error('Failed to open file dialog:', err);
    }
  }

  return (
    <div className="space-y-6">
      {/* Theme Selector */}
      <div>
        <label className="block text-sm font-medium text-surface-300 mb-2">
          {t('settings.theme')}
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { id: 'dark', label: t('settings.theme_default'), color: 'bg-slate-900' },
            { id: 'light', label: t('settings.theme_light'), color: 'bg-white border-2 border-slate-200' },
            { id: 'midnight', label: t('settings.theme_midnight'), color: 'bg-purple-950' },
            { id: 'forest', label: t('settings.theme_forest'), color: 'bg-green-950' },
          ].map((option) => (
            <button
              key={option.id}
              onClick={() => handleThemeChange(option.id)}
              className={`p-3 rounded-lg border-2 text-left transition-all ${
                theme === option.id
                  ? 'border-primary-500 ring-2 ring-primary-500/20'
                  : 'border-surface-700 hover:border-surface-600'
              }`}
            >
              <div className={`w-full h-8 rounded mb-2 ${option.color}`} />
              <div className="text-sm font-medium text-surface-200">{option.label}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Background Image */}
      <div>
        <label className="block text-sm font-medium text-surface-300 mb-2">
          {t('settings.background_image')}
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={bgImage}
            onChange={(e) => handleBgImageChange(e.target.value)}
            placeholder="Image URL or local path..."
            className="input flex-1"
          />
          <button onClick={handleBrowseImage} className="btn-secondary">
            {t('common.browse')}
          </button>
          {bgImage && (
            <button onClick={() => handleBgImageChange('')} className="btn-ghost text-red-400">
              {t('common.clear')}
            </button>
          )}
        </div>
        <p className="text-xs text-surface-500 mt-1">
          Supported: PNG, JPG, WEBP, GIF.
        </p>
      </div>

      {/* Opacity Slider */}
      <div>
        <div className="flex justify-between mb-2">
          <label className="text-sm font-medium text-surface-300">{t('settings.background_opacity')}</label>
          <span className="text-sm text-surface-400">{Math.round(bgOpacity * 100)}%</span>
        </div>
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={bgOpacity}
          onChange={(e) => handleOpacityChange(parseFloat(e.target.value))}
          className="w-full h-2 bg-surface-700 rounded-lg appearance-none cursor-pointer accent-primary-500"
        />
        <p className="text-xs text-surface-500 mt-1">Image opacity (Lower = more transparent/fainter).</p>
      </div>
      
      {/* Blur Slider */}
      <div>
        <div className="flex justify-between mb-2">
          <label className="text-sm font-medium text-surface-300">{t('settings.background_blur')}</label>
          <span className="text-sm text-surface-400">{bgBlur}px</span>
        </div>
        <input
          type="range"
          min="0"
          max="20"
          step="1"
          value={bgBlur}
          onChange={(e) => handleBlurChange(parseInt(e.target.value))}
          className="w-full h-2 bg-surface-700 rounded-lg appearance-none cursor-pointer accent-primary-500"
        />
      </div>
    </div>
  );
}
