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

interface AppState {
  isBackendReady: boolean;
  versionInfo: VersionInfo | null;
  config: ConfigResult | null;
  voices: Voice[];
  apiKeys: APIKey[];
  totalCredits: number;
  jobs: Map<string, Job>;
  currentJobId: string | null;
  theme: 'light' | 'dark';
  sidebarCollapsed: boolean;

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
  setTheme: (theme: 'light' | 'dark') => void;
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

  // Processing actions
  setProcessing: (processing: boolean) => void;
  setPaused: (paused: boolean) => void;
  updateProcessingStats: (stats: Partial<ProcessingStats>) => void;
  resetProcessingStats: () => void;
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
  sidebarCollapsed: false,

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
  setConfig: (config) => set({ 
    config, 
    theme: config.theme === 'light' ? 'light' : 'dark',
    outputFolder: config.default_output_folder || '',
  }),
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
    document.documentElement.classList.toggle('dark', theme === 'dark');
  },

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
}));
