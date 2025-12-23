import {
  JsonRpcRequest,
  JsonRpcResponse,
  HandshakeResult,
  Voice,
  TTSJobParams,
  TTSJobResult,
  ConfigResult,
  APIKey,
  APIKeyStatus,
  Proxy,
  ProgressEvent,
} from './types';
import { getPlatformAPI } from '../platform';

const UI_VERSION = '1.2.4';
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

  async getAPIKeyStatus(): Promise<APIKeyStatus> {
    return this.call<APIKeyStatus>('apikeys.status');
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

  // ============================================
  // TRANSCRIPTION (Speech-to-Text) METHODS
  // ============================================

  async startTranscription(params: {
    file_path: string;
    language?: string;
    diarize?: boolean;
    num_speakers?: number;
  }): Promise<TranscriptionResult> {
    return this.call<TranscriptionResult>('transcription.start', params, 600000);
  }

  async getTranscriptionFormats(): Promise<{ audio: string[]; video: string[] }> {
    return this.call('transcription.supported_formats');
  }

  // ============================================
  // VOICE PRESETS METHODS
  // ============================================

  async getPresets(): Promise<VoicePreset[]> {
    return this.call<VoicePreset[]>('presets.list');
  }

  async savePreset(preset: {
    name: string;
    voice_id: string;
    voice_name?: string;
    settings?: VoiceSettingsParams;
    description?: string;
    tags?: string[];
  }): Promise<VoicePreset> {
    return this.call<VoicePreset>('presets.save', preset);
  }

  async deletePreset(id: string): Promise<void> {
    return this.call<void>('presets.delete', { id });
  }

  // ============================================
  // VOICE MATCHER METHODS
  // ============================================

  async getVoicePatterns(): Promise<VoicePattern[]> {
    return this.call<VoicePattern[]>('voicematcher.patterns.list');
  }

  async addVoicePattern(pattern: {
    name: string;
    pattern: string;
    voice_id: string;
    voice_name?: string;
    match_type?: 'contains' | 'starts_with' | 'ends_with' | 'exact' | 'regex';
    case_sensitive?: boolean;
    priority?: number;
  }): Promise<VoicePattern> {
    return this.call<VoicePattern>('voicematcher.patterns.add', pattern);
  }

  async deleteVoicePattern(id: string): Promise<void> {
    return this.call<void>('voicematcher.patterns.delete', { id });
  }

  async matchVoice(text: string): Promise<VoiceMatchResult> {
    return this.call<VoiceMatchResult>('voicematcher.match', { text });
  }

  async batchMatchVoices(lines: Array<{ id: string; text: string }>): Promise<Array<{
    id: string;
    matched: boolean;
    voice_id?: string;
    voice_name?: string;
  }>> {
    return this.call('voicematcher.batch_match', { lines });
  }

  // ============================================
  // PAUSE PREPROCESSOR METHODS
  // ============================================

  async processPauses(text: string, settings?: PauseSettings): Promise<{ original: string; processed: string }> {
    return this.call('pause.process', { text, settings });
  }

  async batchProcessPauses(lines: Array<{ id: string; text: string }>, settings?: PauseSettings): Promise<Array<{
    id: string;
    original: string;
    processed: string;
  }>> {
    return this.call('pause.batch_process', { lines, settings });
  }

  // ============================================
  // AUDIO POST-PROCESSING METHODS
  // ============================================

  async processAudio(inputPath: string, outputPath: string, settings: AudioProcessingSettings): Promise<{
    success: boolean;
    output_path: string;
  }> {
    return this.call('audio.process', {
      input_path: inputPath,
      output_path: outputPath,
      settings,
    }, 300000);
  }

  async batchProcessAudio(files: Array<{ input_path: string; output_path: string }>, settings: AudioProcessingSettings): Promise<{
    total: number;
    success: number;
    failed: number;
    results: Array<{ input_path: string; output_path: string; success: boolean; message: string }>;
  }> {
    return this.call('audio.batch_process', { files, settings }, 600000);
  }

  // ============================================
  // ANALYTICS METHODS
  // ============================================

  async getAnalytics(): Promise<AnalyticsStats> {
    return this.call<AnalyticsStats>('analytics.get_stats');
  }

  async trackUsage(characters: number, lines: number, voiceId?: string): Promise<void> {
    return this.call<void>('analytics.track_usage', { characters, lines, voice_id: voiceId });
  }

  async resetAnalytics(): Promise<void> {
    return this.call<void>('analytics.reset');
  }

  // ============================================
  // PROXY MANAGEMENT METHODS (extended)
  // ============================================

  async assignProxyToKey(keyId: string, proxyId: string | null): Promise<void> {
    return this.call<void>('proxies.assign_to_key', { key_id: keyId, proxy_id: proxyId });
  }

  // ============================================
  // VOICE LIBRARY METHODS
  // ============================================

  async searchVoices(params: {
    query?: string;
    category?: string;
    gender?: string;
    language?: string;
    use_case?: string;
  }): Promise<Voice[]> {
    return this.call<Voice[]>('voices.search', params);
  }

  async getVoiceDetails(voiceId: string): Promise<VoiceDetails> {
    return this.call<VoiceDetails>('voices.get_details', { voice_id: voiceId });
  }

  // ============================================
  // BATCH TTS (Multi-thread) METHODS
  // ============================================

  async startBatchTTS(params: {
    lines: Array<{
      id: string;
      text: string;
      voice_id: string;
      output_path: string;
    }>;
    thread_count?: number;
    settings?: VoiceSettingsParams;
  }): Promise<BatchTTSResult> {
    return this.call<BatchTTSResult>('tts.batch_start', params, 1800000); // 30 min timeout
  }

  // ============================================
  // LOCALIZATION METHODS
  // ============================================

  async getAvailableLanguages(): Promise<Array<{ code: string; name: string }>> {
    return this.call('i18n.get_languages');
  }

  async getTranslations(language: string): Promise<Record<string, string>> {
    return this.call('i18n.get_translations', { language });
  }

  // ============================================
  // FILE OPERATIONS
  // ============================================
  
  async readTextFile(path: string): Promise<string> {
    const api = await getPlatformAPI();
    return api.invoke('read_text_file', { path });
  }

  async writeTextFile(path: string, contents: string): Promise<void> {
    const api = await getPlatformAPI();
    return api.invoke('write_text_file', { path, contents });
  }

  destroy() {
    if (this.unsubscribe) {
      this.unsubscribe();
    }
    this.eventListeners.clear();
  }
}

// New types for new features
export interface TranscriptionResult {
  job_id: string;
  text: string;
  language: string;
  segments: Array<{
    start: number;
    end: number;
    text: string;
    speaker?: string;
  }>;
  speakers: Array<{ id: string; name: string }>;
}

export interface VoicePreset {
  id: string;
  name: string;
  voice_id: string;
  voice_name: string;
  settings: VoiceSettingsParams;
  description: string;
  created_at: string;
  tags: string[];
}

export interface VoiceSettingsParams {
  stability?: number;
  similarity_boost?: number;
  style?: number;
  use_speaker_boost?: boolean;
  speed?: number;
}

export interface VoicePattern {
  id: string;
  name: string;
  pattern: string;
  voice_id: string;
  voice_name: string;
  match_type: string;
  case_sensitive: boolean;
  priority: number;
}

export interface VoiceMatchResult {
  matched: boolean;
  voice_id?: string;
  voice_name?: string;
  pattern_name?: string;
}

export interface PauseSettings {
  pause_enabled?: boolean;
  short_pause_duration?: number;
  long_pause_duration?: number;
  short_pause_punctuation?: string;
  long_pause_punctuation?: string;
}

export interface AudioProcessingSettings {
  normalize?: boolean;
  normalize_level?: number;
  fade_in?: number;
  fade_out?: number;
  silence_padding_start?: number;
  silence_padding_end?: number;
  trim_silence?: boolean;
  trim_threshold?: number;
  speed?: number;
  pitch_shift?: number;
}

export interface AnalyticsStats {
  total_characters: number;
  total_lines: number;
  total_sessions: number;
  total_processing_time: number;
  voice_usage: Record<string, number>;
  daily_usage: Record<string, number>;
  error_count: number;
  first_use: string | null;
  last_use: string | null;
}

export interface VoiceDetails extends Voice {
  description: string;
  settings: VoiceSettingsParams | null;
}

export interface BatchTTSResult {
  batch_id: string;
  total: number;
  completed: number;
  failed: number;
  results: Array<{
    id: string;
    success: boolean;
    output_path?: string;
    duration_ms?: number;
    language_code?: string;
    error?: string;
  }>;
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
