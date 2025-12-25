import { create } from 'zustand';
import { Voice, APIKey, ConfigResult, ProgressEvent, TextLine, ProcessingStats, LineStatus } from '../lib/ipc/types';
import { v4 as uuidv4 } from 'uuid';

interface VersionInfo {
  uiVersion: string;
  backendVersion: string;
  protocolVersion: number;
}

interface Job {
  id: string;
  text: string;
  voiceId: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  message: string;
  outputPath?: string;
  error?: string;
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

interface ExportHistoryEntry {
  id: string;
  timestamp: number;
  outputPath: string;
  lineIndex: number;
  lineText: string;
  voiceName: string;
  durationMs: number;
  sessionFolder: string;
}

interface RecoveryData {
  timestamp: number;
  outputFolder: string;
  defaultVoiceId: string | null;
  defaultVoiceName: string | null;
  lines: Array<{
    id: string;
    index: number;
    text: string;
    voice_id: string | null;
    voice_name: string | null;
    status: string;
  }>;
}

interface AppState {
  isBackendReady: boolean;
  versionInfo: VersionInfo | null;
  config: ConfigResult | null;
  voices: Voice[];
  apiKeys: APIKey[];
  totalCredits: number;
  jobs: Map<string, Job>;
  currentJobId: string | null;
  theme: string;
  backgroundImage: string | null;
  backgroundOpacity: number;
  backgroundBlur: number;
  sidebarCollapsed: boolean;

  // Voice favorites and presets
  favoriteVoiceIds: Set<string>;
  voicePresets: VoicePreset[];

  // Export history and recovery
  exportHistory: ExportHistoryEntry[];
  hasRecoveryData: boolean;

  // Project state
  projectName: string;
  projectPath: string | null;
  lines: TextLine[];
  selectedLineIds: Set<string>;
  defaultVoiceId: string | null;
  defaultVoiceName: string | null;
  outputFolder: string;

  // Processing state
  isProcessing: boolean;
  isPaused: boolean;
  processingStats: ProcessingStats;

  setBackendReady: (ready: boolean) => void;
  setVersionInfo: (info: VersionInfo) => void;
  setConfig: (config: ConfigResult) => void;
  setVoices: (voices: Voice[]) => void;
  setAPIKeys: (keys: APIKey[]) => void;
  setTotalCredits: (credits: number) => void;
  addJob: (job: Job) => void;
  updateJob: (id: string, updates: Partial<Job>) => void;
  removeJob: (id: string) => void;
  setCurrentJobId: (id: string | null) => void;
  handleProgress: (event: ProgressEvent) => void;
  setTheme: (theme: string) => void;
  setBackgroundImage: (url: string | null) => void;
  setBackgroundOpacity: (opacity: number) => void;
  setBackgroundBlur: (blur: number) => void;
  toggleSidebar: () => void;

  // Project actions
  setProjectName: (name: string) => void;
  setProjectPath: (path: string | null) => void;
  setOutputFolder: (folder: string) => void;
  setDefaultVoice: (id: string | null, name: string | null) => void;

  // Lines actions
  setLines: (lines: TextLine[]) => void;
  addLines: (texts: string[], sourceFile?: string) => void;
  updateLine: (id: string, updates: Partial<TextLine>) => void;
  updateLineStatus: (id: string, status: LineStatus, error?: string) => void;
  deleteLine: (id: string) => void;
  deleteLines: (ids: string[]) => void;
  clearLines: () => void;
  setSelectedLineIds: (ids: Set<string>) => void;
  setLineVoice: (id: string, voiceId: string, voiceName: string) => void;
  setAllLinesVoice: (voiceId: string, voiceName: string) => void;
  reorderLines: (fromIndex: number, toIndex: number) => void;

  // Processing actions
  setProcessing: (processing: boolean) => void;
  setPaused: (paused: boolean) => void;
  updateProcessingStats: (stats: Partial<ProcessingStats>) => void;
  resetProcessingStats: () => void;

  // Voice favorites and presets actions
  toggleFavoriteVoice: (voiceId: string) => void;
  addVoicePreset: (preset: Omit<VoicePreset, 'id'>) => void;
  removeVoicePreset: (id: string) => void;
  loadVoicePreset: (id: string) => VoicePreset | undefined;

  // Export history actions
  addExportEntry: (entry: Omit<ExportHistoryEntry, 'id' | 'timestamp'>) => void;
  clearExportHistory: () => void;

  // Recovery actions
  saveRecoveryData: () => void;
  loadRecoveryData: () => RecoveryData | null;
  clearRecoveryData: () => void;
  restoreFromRecovery: () => boolean;
}

const initialProcessingStats: ProcessingStats = {
  total: 0,
  completed: 0,
  failed: 0,
  pending: 0,
  processing: 0,
  characters_processed: 0,
  elapsed_seconds: 0,
};

// Load favorites and presets from localStorage
const loadFavorites = (): Set<string> => {
  try {
    const stored = localStorage.getItem('2tts_favorite_voices');
    return stored ? new Set(JSON.parse(stored)) : new Set();
  } catch {
    return new Set();
  }
};

const loadPresets = (): VoicePreset[] => {
  try {
    const stored = localStorage.getItem('2tts_voice_presets');
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
};

const loadExportHistory = (): ExportHistoryEntry[] => {
  try {
    const stored = localStorage.getItem('2tts_export_history');
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
};

const checkRecoveryData = (): boolean => {
  try {
    const stored = localStorage.getItem('2tts_recovery_data');
    if (!stored) return false;
    const data = JSON.parse(stored);
    // Only consider recovery data valid if it has lines and is less than 24 hours old
    const isValid = data.lines?.length > 0 && (Date.now() - data.timestamp) < 24 * 60 * 60 * 1000;
    return isValid;
  } catch {
    return false;
  }
};

export const useAppStore = create<AppState>((set, get) => ({
  isBackendReady: false,
  versionInfo: null,
  config: null,
  voices: [],
  apiKeys: [],
  totalCredits: 0,
  jobs: new Map(),
  currentJobId: null,
  theme: 'dark',
  backgroundImage: null,
  backgroundOpacity: 0.5,
  backgroundBlur: 0,
  sidebarCollapsed: false,

  // Voice favorites and presets
  favoriteVoiceIds: loadFavorites(),
  voicePresets: loadPresets(),

  // Export history and recovery
  exportHistory: loadExportHistory(),
  hasRecoveryData: checkRecoveryData(),

  // Project state
  projectName: 'Untitled',
  projectPath: null,
  lines: [],
  selectedLineIds: new Set(),
  defaultVoiceId: null,
  defaultVoiceName: null,
  outputFolder: '',

  // Processing state
  isProcessing: false,
  isPaused: false,
  processingStats: { ...initialProcessingStats },

  setBackendReady: (ready) => set({ isBackendReady: ready }),
  setVersionInfo: (info) => set({ versionInfo: info }),
  setConfig: (config) => {
    // Apply theme
    document.documentElement.dataset.theme = config.theme;
    document.documentElement.classList.toggle('dark', config.theme !== 'light');
    
    set({ 
      config, 
      theme: config.theme,
      backgroundImage: config.background_image || null,
      backgroundOpacity: config.background_opacity ?? 0.5,
      backgroundBlur: config.background_blur ?? 0,
      outputFolder: config.default_output_folder || '',
    });
  },
  setVoices: (voices) => set({ voices }),
  setAPIKeys: (keys) => set({ apiKeys: keys }),
  setTotalCredits: (credits) => set({ totalCredits: credits }),

  addJob: (job) =>
    set((state) => {
      const jobs = new Map(state.jobs);
      jobs.set(job.id, job);
      return { jobs };
    }),

  updateJob: (id, updates) =>
    set((state) => {
      const jobs = new Map(state.jobs);
      const existing = jobs.get(id);
      if (existing) {
        jobs.set(id, { ...existing, ...updates });
      }
      return { jobs };
    }),

  removeJob: (id) =>
    set((state) => {
      const jobs = new Map(state.jobs);
      jobs.delete(id);
      return { jobs };
    }),

  setCurrentJobId: (id) => set({ currentJobId: id }),

  handleProgress: (event) => {
    const { job_id, percent, message } = event;
    get().updateJob(job_id, { progress: percent, message, status: 'running' });
  },

  setTheme: (theme) => {
    set({ theme });
    document.documentElement.dataset.theme = theme;
    document.documentElement.classList.toggle('dark', theme !== 'light');
  },
  
  setBackgroundImage: (url) => set({ backgroundImage: url }),
  setBackgroundOpacity: (opacity) => set({ backgroundOpacity: opacity }),
  setBackgroundBlur: (blur) => set({ backgroundBlur: blur }),

  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

  // Project actions
  setProjectName: (name) => set({ projectName: name }),
  setProjectPath: (path) => set({ projectPath: path }),
  setOutputFolder: (folder) => set({ outputFolder: folder }),
  setDefaultVoice: (id, name) => set({ defaultVoiceId: id, defaultVoiceName: name }),

  // Lines actions
  setLines: (lines) => set({ lines, selectedLineIds: new Set() }),

  addLines: (texts, sourceFile) =>
    set((state) => {
      const startIndex = state.lines.length;
      const newLines: TextLine[] = texts.map((text, i) => ({
        id: uuidv4(),
        index: startIndex + i,
        text: text.trim(),
        original_text: text.trim(),
        voice_id: state.defaultVoiceId,
        voice_name: state.defaultVoiceName,
        status: 'pending' as LineStatus,
        error_message: null,
        source_file: sourceFile || null,
        start_time: null,
        end_time: null,
        audio_duration: null,
        output_path: null,
        retry_count: 0,
        detected_language: null,
        model_id: null,
      }));
      return { 
        lines: [...state.lines, ...newLines],
        processingStats: {
          ...state.processingStats,
          total: state.lines.length + newLines.length,
          pending: state.lines.filter(l => l.status === 'pending').length + newLines.length,
        },
      };
    }),

  updateLine: (id, updates) =>
    set((state) => ({
      lines: state.lines.map((line) =>
        line.id === id ? { ...line, ...updates } : line
      ),
    })),

  updateLineStatus: (id, status, error) =>
    set((state) => ({
      lines: state.lines.map((line) =>
        line.id === id ? { ...line, status, error_message: error || null } : line
      ),
    })),

  deleteLine: (id) =>
    set((state) => {
      const lines = state.lines.filter((line) => line.id !== id);
      // Re-index
      lines.forEach((line, i) => (line.index = i));
      const selectedLineIds = new Set(state.selectedLineIds);
      selectedLineIds.delete(id);
      return { lines, selectedLineIds };
    }),

  deleteLines: (ids) =>
    set((state) => {
      const idSet = new Set(ids);
      const lines = state.lines.filter((line) => !idSet.has(line.id));
      // Re-index
      lines.forEach((line, i) => (line.index = i));
      const selectedLineIds = new Set(
        Array.from(state.selectedLineIds).filter((id) => !idSet.has(id))
      );
      return { lines, selectedLineIds };
    }),

  clearLines: () => set({ lines: [], selectedLineIds: new Set() }),

  setSelectedLineIds: (ids) => set({ selectedLineIds: ids }),

  setLineVoice: (id, voiceId, voiceName) =>
    set((state) => ({
      lines: state.lines.map((line) =>
        line.id === id ? { ...line, voice_id: voiceId, voice_name: voiceName } : line
      ),
    })),

  setAllLinesVoice: (voiceId, voiceName) =>
    set((state) => ({
      lines: state.lines.map((line) => ({
        ...line,
        voice_id: voiceId,
        voice_name: voiceName,
      })),
      defaultVoiceId: voiceId,
      defaultVoiceName: voiceName,
    })),

  reorderLines: (fromIndex, toIndex) =>
    set((state) => {
      const newLines = [...state.lines];
      const [removed] = newLines.splice(fromIndex, 1);
      newLines.splice(toIndex, 0, removed);
      // Re-index all lines
      newLines.forEach((line, i) => (line.index = i));
      return { lines: newLines };
    }),

  // Processing actions
  setProcessing: (processing) => set({ isProcessing: processing }),
  setPaused: (paused) => set({ isPaused: paused }),
  
  updateProcessingStats: (stats) =>
    set((state) => ({
      processingStats: { ...state.processingStats, ...stats },
    })),

  resetProcessingStats: () =>
    set((state) => ({
      processingStats: {
        ...initialProcessingStats,
        total: state.lines.length,
        pending: state.lines.filter((l) => l.status === 'pending').length,
      },
    })),

  // Voice favorites and presets actions
  toggleFavoriteVoice: (voiceId) =>
    set((state) => {
      const newFavorites = new Set(state.favoriteVoiceIds);
      if (newFavorites.has(voiceId)) {
        newFavorites.delete(voiceId);
      } else {
        newFavorites.add(voiceId);
      }
      localStorage.setItem('2tts_favorite_voices', JSON.stringify([...newFavorites]));
      return { favoriteVoiceIds: newFavorites };
    }),

  addVoicePreset: (preset) =>
    set((state) => {
      const newPreset: VoicePreset = { ...preset, id: uuidv4() };
      const newPresets = [...state.voicePresets, newPreset];
      localStorage.setItem('2tts_voice_presets', JSON.stringify(newPresets));
      return { voicePresets: newPresets };
    }),

  removeVoicePreset: (id) =>
    set((state) => {
      const newPresets = state.voicePresets.filter((p) => p.id !== id);
      localStorage.setItem('2tts_voice_presets', JSON.stringify(newPresets));
      return { voicePresets: newPresets };
    }),

  loadVoicePreset: (id) => {
    return get().voicePresets.find((p) => p.id === id);
  },

  // Export history actions
  addExportEntry: (entry) =>
    set((state) => {
      const newEntry: ExportHistoryEntry = {
        ...entry,
        id: uuidv4(),
        timestamp: Date.now(),
      };
      // Keep only last 100 entries
      const newHistory = [newEntry, ...state.exportHistory].slice(0, 100);
      localStorage.setItem('2tts_export_history', JSON.stringify(newHistory));
      return { exportHistory: newHistory };
    }),

  clearExportHistory: () =>
    set(() => {
      localStorage.removeItem('2tts_export_history');
      return { exportHistory: [] };
    }),

  // Recovery actions
  saveRecoveryData: () => {
    const state = get();
    if (state.lines.length === 0) return;
    
    const recoveryData: RecoveryData = {
      timestamp: Date.now(),
      outputFolder: state.outputFolder,
      defaultVoiceId: state.defaultVoiceId,
      defaultVoiceName: state.defaultVoiceName,
      lines: state.lines.map((l) => ({
        id: l.id,
        index: l.index,
        text: l.text,
        voice_id: l.voice_id,
        voice_name: l.voice_name,
        status: l.status,
      })),
    };
    localStorage.setItem('2tts_recovery_data', JSON.stringify(recoveryData));
  },

  loadRecoveryData: () => {
    try {
      const stored = localStorage.getItem('2tts_recovery_data');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  },

  clearRecoveryData: () =>
    set(() => {
      localStorage.removeItem('2tts_recovery_data');
      return { hasRecoveryData: false };
    }),

  restoreFromRecovery: () => {
    const recoveryData = get().loadRecoveryData();
    if (!recoveryData || !recoveryData.lines?.length) return false;

    const restoredLines: TextLine[] = recoveryData.lines.map((l, i) => ({
      id: l.id || uuidv4(),
      index: l.index ?? i,
      text: l.text,
      original_text: l.text,
      voice_id: l.voice_id,
      voice_name: l.voice_name,
      status: (l.status === 'done' ? 'done' : 'pending') as LineStatus,
      error_message: null,
      source_file: null,
      start_time: null,
      end_time: null,
      audio_duration: null,
      output_path: null,
      retry_count: 0,
      detected_language: null,
      model_id: null,
    }));

    set({
      lines: restoredLines,
      outputFolder: recoveryData.outputFolder || '',
      defaultVoiceId: recoveryData.defaultVoiceId,
      defaultVoiceName: recoveryData.defaultVoiceName,
      hasRecoveryData: false,
    });

    localStorage.removeItem('2tts_recovery_data');
    return true;
  },
}));
