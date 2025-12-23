import { useState, useEffect } from 'react';
import { ipcClient } from '../lib/ipc';
import { getPlatformAPI } from '../lib/platform';
import { useAppStore } from '../stores/appStore';
import { Proxy } from '../lib/ipc/types';

type SettingsTab = 'general' | 'apikeys' | 'proxies' | 'about';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('general');
  const { setConfig, setAPIKeys, versionInfo } = useAppStore();

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

  const tabs: { id: SettingsTab; label: string }[] = [
    { id: 'general', label: 'General' },
    { id: 'apikeys', label: 'API Keys' },
    { id: 'proxies', label: 'Proxies' },
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

            <div className="grid grid-cols-2 gap-4">
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

            <div className="pt-4 border-t border-surface-800">
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
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyValue, setNewKeyValue] = useState('');
  const [isAdding, setIsAdding] = useState(false);

  async function handleAddKey() {
    if (!newKeyName.trim() || !newKeyValue.trim()) return;
    setIsAdding(true);

    try {
      const key = await ipcClient.addAPIKey(newKeyName, newKeyValue);
      setAPIKeys([...apiKeys, key]);
      setNewKeyName('');
      setNewKeyValue('');
    } catch (err) {
      console.error('Failed to add API key:', err);
    } finally {
      setIsAdding(false);
    }
  }

  async function handleRemoveKey(id: string) {
    try {
      await ipcClient.removeAPIKey(id);
      setAPIKeys(apiKeys.filter((k) => k.id !== id));
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

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        {apiKeys.map((key) => (
          <div key={key.id} className="flex items-center gap-4 p-3 bg-surface-800 rounded-lg">
            <div className="flex-1 min-w-0">
              <div className="font-medium text-surface-200 truncate">{key.name}</div>
              <div className="text-sm text-surface-500 font-mono truncate">
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

        {apiKeys.length === 0 && (
          <div className="text-center py-8 text-surface-500">
            No API keys configured. Add one below.
          </div>
        )}
      </div>

      <div className="pt-4 border-t border-surface-800 space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <input
            type="text"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            placeholder="Key name"
            className="input"
            aria-label="New API key name"
          />
          <input
            type="password"
            value={newKeyValue}
            onChange={(e) => setNewKeyValue(e.target.value)}
            placeholder="API key"
            className="input"
            aria-label="New API key value"
          />
        </div>
        <button
          onClick={handleAddKey}
          disabled={!newKeyName.trim() || !newKeyValue.trim() || isAdding}
          className="btn-primary w-full"
        >
          {isAdding ? 'Adding...' : 'Add API Key'}
        </button>
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
