export interface JsonRpcRequest {
  jsonrpc: '2.0';
  method: string;
  params?: Record<string, unknown>;
  id: number | string;
}

export interface JsonRpcResponse<T = unknown> {
  jsonrpc: '2.0';
  result?: T;
  error?: JsonRpcError;
  id: number | string;
}

export interface JsonRpcNotification {
  jsonrpc: '2.0';
  method: string;
  params?: Record<string, unknown>;
}

export interface JsonRpcError {
  code: number;
  message: string;
  data?: unknown;
}

export const ErrorCodes = {
  PARSE_ERROR: -32700,
  INVALID_REQUEST: -32600,
  METHOD_NOT_FOUND: -32601,
  INVALID_PARAMS: -32602,
  INTERNAL_ERROR: -32603,
  APP_ERROR_MIN: -32099,
  APP_ERROR_MAX: -32000,
} as const;

export interface HandshakeParams {
  ui_version: string;
  protocol_version: number;
}

export interface HandshakeResult {
  ui_version: string;
  backend_version: string;
  protocol_version: number;
  compatible: boolean;
  min_ui_version: string;
}

export interface ProgressEvent {
  job_id: string;
  percent: number;
  message: string;
}

export interface Voice {
  voice_id: string;
  name: string;
  category: string;
  labels: Record<string, string>;
  preview_url?: string;
  description?: string;
}

export interface VoiceSettings {
  stability: number;
  similarity_boost: number;
  style?: number;
  use_speaker_boost?: boolean;
}

export interface TTSJobParams {
  text: string;
  voice_id: string;
  model_id?: string;
  output_path: string;
  voice_settings?: VoiceSettings;
}

export interface TTSJobResult {
  job_id: string;
  output_path: string;
  duration_ms: number;
  characters_used: number;
  language_code?: string;
}

export interface ConfigResult {
  theme: string;
  app_language: string;
  default_output_folder: string;
  thread_count: number;
  max_retries: number;
  auto_split_enabled: boolean;
  split_delimiter: string;
  max_chars: number;
  silence_gap: number;
  low_credit_threshold: number;
  pause_enabled: boolean;
  short_pause_duration: number;
  long_pause_duration: number;
  short_pause_punctuation: string;
  long_pause_punctuation: string;
}

export interface APIKey {
  id: string;
  name: string;
  key: string;
  remaining_credits: number;
  is_valid: boolean;
  last_checked: string | null;
  assigned_proxy_id: string | null;
}

export interface APIKeyStatusItem {
  id: string;
  key: string;
  remaining_credits: number;
  is_valid?: boolean;
  is_active?: boolean;
}

export interface APIKeyStatus {
  active_key: APIKeyStatusItem | null;
  available_keys: APIKeyStatusItem[];
  exhausted_keys: APIKeyStatusItem[];
  total_credits: number;
  total_keys: number;
  available_count: number;
  exhausted_count: number;
}

export interface Proxy {
  id: string;
  name: string;
  host: string;
  port: number;
  username: string | null;
  password: string | null;
  proxy_type: string;
  enabled: boolean;
  is_healthy: boolean;
}

// Line status enum
export type LineStatus = 'pending' | 'processing' | 'done' | 'error';

// Text line model (matches Python TextLine)
export interface TextLine {
  id: string;
  index: number;
  text: string;
  original_text: string;
  voice_id: string | null;
  voice_name: string | null;
  status: LineStatus;
  error_message: string | null;
  source_file: string | null;
  start_time: number | null;
  end_time: number | null;
  audio_duration: number | null;
  output_path: string | null;
  retry_count: number;
  detected_language: string | null;
  model_id: string | null;
}

// Project settings
export interface ProjectSettings {
  default_voice_id: string | null;
  default_voice_name: string | null;
  output_folder: string;
  thread_count: number;
  max_retries: number;
  loop_enabled: boolean;
  loop_count: number;
  loop_delay: number;
  silence_gap: number;
  auto_split_enabled: boolean;
  split_delimiter: string;
  max_chars: number;
}

// Project model
export interface Project {
  name: string;
  file_path: string | null;
  lines: TextLine[];
  settings: ProjectSettings;
}

// Processing stats
export interface ProcessingStats {
  total: number;
  completed: number;
  failed: number;
  pending: number;
  processing: number;
  characters_processed: number;
  elapsed_seconds: number;
}

// File import result
export interface FileImportResult {
  lines: TextLine[];
  source_file: string;
  line_count: number;
}

// Batch TTS params
export interface BatchTTSParams {
  lines: { id: string; text: string; voice_id: string; output_path: string }[];
  thread_count: number;
  max_retries: number;
}

// SRT generation params
export interface SRTGenerateParams {
  lines: { text: string; start_time: number; end_time: number }[];
  output_path: string;
}

// MP3 concat params
export interface MP3ConcatParams {
  input_files: string[];
  output_path: string;
  silence_gap: number;
}
