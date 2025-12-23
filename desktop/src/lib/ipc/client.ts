import {
  JsonRpcRequest,
  JsonRpcResponse,
  HandshakeResult,
  Voice,
  TTSJobParams,
  TTSJobResult,
  ConfigResult,
  APIKey,
  Proxy,
  ProgressEvent,
} from './types';
import { getPlatformAPI } from '../platform';

const UI_VERSION = '1.0.8';
const PROTOCOL_VERSION = 1;
const DEFAULT_TIMEOUT = 30000;

type EventCallback<T> = (data: T) => void;

class IPCClient {
  private requestId = 0;
  private eventListeners: Map<string, Set<EventCallback<unknown>>> = new Map();
  private unsubscribe: (() => void) | null = null;

  constructor() {
    this.init();
  }

  private async init() {
    try {
      const api = await getPlatformAPI();
      this.unsubscribe = api.onBackendEvent((data) => {
        const { method, params } = data;
        const listeners = this.eventListeners.get(method);
        if (listeners) {
          listeners.forEach((callback) => callback(params));
        }
      });
    } catch (e) {
      console.error('[IPCClient] Failed to initialize platform API:', e);
    }
  }

  private getNextId(): number {
    return ++this.requestId;
  }

  async call<T>(method: string, params?: Record<string, unknown>, timeout = DEFAULT_TIMEOUT): Promise<T> {
    const api = await getPlatformAPI();
    
    const request: JsonRpcRequest = {
      jsonrpc: '2.0',
      method,
      params,
      id: this.getNextId(),
    };

    const response = await Promise.race([
      api.ipcCall(JSON.stringify(request)),
      new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error(`Request timeout after ${timeout}ms`)), timeout)
      ),
    ]) as JsonRpcResponse<T>;

    if (response.error) {
      throw new IPCError(response.error.code, response.error.message, response.error.data);
    }

    return response.result as T;
  }

  on<T>(event: string, callback: EventCallback<T>): () => void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, new Set());
    }
    this.eventListeners.get(event)!.add(callback as EventCallback<unknown>);

    return () => {
      const listeners = this.eventListeners.get(event);
      if (listeners) {
        listeners.delete(callback as EventCallback<unknown>);
      }
    };
  }

  async handshake(): Promise<HandshakeResult> {
    return this.call<HandshakeResult>('system.handshake', {
      ui_version: UI_VERSION,
      protocol_version: PROTOCOL_VERSION,
    });
  }

  async getVoices(): Promise<Voice[]> {
    return this.call<Voice[]>('voices.list');
  }

  async getVoice(voiceId: string): Promise<Voice> {
    return this.call<Voice>('voices.get', { voice_id: voiceId });
  }

  async refreshVoices(): Promise<Voice[]> {
    return this.call<Voice[]>('voices.refresh');
  }

  async startTTSJob(params: TTSJobParams): Promise<TTSJobResult> {
    return this.call<TTSJobResult>('tts.start', params as unknown as Record<string, unknown>, 300000);
  }

  async cancelJob(jobId: string): Promise<void> {
    return this.call<void>('jobs.cancel', { job_id: jobId });
  }

  async getConfig(): Promise<ConfigResult> {
    return this.call<ConfigResult>('config.get');
  }

  async setConfig(key: string, value: unknown): Promise<void> {
    return this.call<void>('config.set', { key, value });
  }

  async getAPIKeys(): Promise<APIKey[]> {
    return this.call<APIKey[]>('apikeys.list');
  }

  async addAPIKey(name: string, key: string): Promise<APIKey> {
    return this.call<APIKey>('apikeys.add', { name, key });
  }

  async removeAPIKey(id: string): Promise<void> {
    return this.call<void>('apikeys.remove', { id });
  }

  async validateAPIKey(id: string): Promise<APIKey> {
    return this.call<APIKey>('apikeys.validate', { id });
  }

  async getProxies(): Promise<Proxy[]> {
    return this.call<Proxy[]>('proxies.list');
  }

  async addProxy(proxy: Omit<Proxy, 'id' | 'is_healthy'>): Promise<Proxy> {
    return this.call<Proxy>('proxies.add', proxy);
  }

  async removeProxy(id: string): Promise<void> {
    return this.call<void>('proxies.remove', { id });
  }

  async testProxy(id: string): Promise<boolean> {
    return this.call<boolean>('proxies.test', { id });
  }

  async exportDiagnostics(): Promise<string> {
    return this.call<string>('system.export_diagnostics');
  }

  async getCredits(): Promise<number> {
    return this.call<number>('credits.total');
  }

  // File import methods
  async importFiles(filePaths: string[], options?: {
    auto_split?: boolean;
    max_chars?: number;
    split_delimiter?: string;
  }): Promise<{ lines: Array<{
    id: string;
    index: number;
    text: string;
    original_text: string;
    source_file: string | null;
    start_time: number | null;
    end_time: number | null;
  }>; errors: string[] }> {
    return this.call('files.import', {
      file_paths: filePaths,
      ...options,
    }, 60000);
  }

  async parseText(text: string, options?: {
    split_by?: 'line' | 'sentence' | 'paragraph';
    auto_split?: boolean;
    max_chars?: number;
  }): Promise<{ lines: Array<{
    id: string;
    index: number;
    text: string;
    original_text: string;
  }>; errors: string[] }> {
    return this.call('files.parse_text', {
      text,
      ...options,
    });
  }

  // SRT generation
  async generateSRT(lines: Array<{
    index: number;
    text: string;
    audio_duration: number | null;
  }>, outputPath: string, options?: {
    gap?: number;
    offset?: number;
  }): Promise<{ success: boolean; output_path: string }> {
    return this.call('srt.generate', {
      lines,
      output_path: outputPath,
      ...options,
    });
  }

  // MP3 concatenation
  async concatenateAudio(inputFiles: string[], outputPath: string, options?: {
    silence_gap?: number;
  }): Promise<{ success: boolean; output_path: string }> {
    return this.call('audio.concatenate', {
      input_files: inputFiles,
      output_path: outputPath,
      ...options,
    }, 600000); // 10 min timeout for large files
  }

  // Project save/load
  async saveProject(filePath: string, project: unknown): Promise<{ success: boolean; file_path: string }> {
    return this.call('project.save', {
      file_path: filePath,
      project,
    });
  }

  async loadProject(filePath: string): Promise<{ success: boolean; project: unknown }> {
    return this.call('project.load', {
      file_path: filePath,
    });
  }

  onProgress(callback: EventCallback<ProgressEvent>): () => void {
    return this.on('event.progress', callback);
  }

  onJobComplete(callback: EventCallback<{ job_id: string; result: TTSJobResult }>): () => void {
    return this.on('event.job_complete', callback);
  }

  onJobError(callback: EventCallback<{ job_id: string; error: string }>): () => void {
    return this.on('event.job_error', callback);
  }

  onCreditsUpdate(callback: EventCallback<{ total: number }>): () => void {
    return this.on('event.credits_update', callback);
  }

  destroy() {
    if (this.unsubscribe) {
      this.unsubscribe();
    }
    this.eventListeners.clear();
  }
}

export class IPCError extends Error {
  constructor(
    public code: number,
    message: string,
    public data?: unknown
  ) {
    super(message);
    this.name = 'IPCError';
  }
}

export const ipcClient = new IPCClient();
