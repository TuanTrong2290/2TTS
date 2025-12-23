/**
 * Platform API for Tauri
 */

import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { open, save } from '@tauri-apps/plugin-dialog';
import type { JsonRpcResponse } from './ipc/types';

interface DebugInfo {
  isDev: boolean;
  isPackaged: boolean;
  resourcesPath: string;
  appPath: string;
  userDataPath: string;
  backendError: string | null;
  backendRunning: boolean;
}

interface PlatformAPI {
  ipcCall: (request: string) => Promise<JsonRpcResponse>;
  invoke: <T>(cmd: string, args?: Record<string, unknown>) => Promise<T>;
  onBackendEvent: (callback: (data: { method: string; params: unknown }) => void) => () => void;
  onDebugInfo: (callback: (data: DebugInfo) => void) => () => void;
  dialog: {
    openDirectory: (title?: string) => Promise<string | null>;
    openFile: (options?: { title?: string; filters?: { name: string; extensions: string[] }[]; multiple?: boolean }) => Promise<string[] | null>;
    saveFile: (options?: { title?: string; defaultPath?: string; filters?: { name: string; extensions: string[] }[] }) => Promise<string | null>;
  };
  window: {
    minimize: () => Promise<void>;
    maximize: () => Promise<void>;
    close: () => Promise<void>;
  };
}

function createTauriAPI(): PlatformAPI {
  return {
    ipcCall: async (request: string) => {
      const responseStr = await invoke<string>('ipc_call', { requestStr: request });
      return JSON.parse(responseStr);
    },

    invoke: async <T>(cmd: string, args?: Record<string, unknown>): Promise<T> => {
      return invoke<T>(cmd, args);
    },

    onBackendEvent: (callback) => {
      let unlisten: (() => void) | null = null;
      
      listen<{ method: string; params: unknown }>('backend-event', (event) => {
        callback(event.payload);
      }).then((fn) => {
        unlisten = fn;
      });

      return () => {
        if (unlisten) unlisten();
      };
    },

    onDebugInfo: (callback) => {
      let unlisten: (() => void) | null = null;
      
      listen<DebugInfo>('debug-info', (event) => {
        callback(event.payload);
      }).then((fn) => {
        unlisten = fn;
      });

      return () => {
        if (unlisten) unlisten();
      };
    },

    dialog: {
      openDirectory: async (title?: string) => {
        const result = await open({
          directory: true,
          title: title || 'Select Folder',
        });
        return result as string | null;
      },

      openFile: async (options) => {
        const result = await open({
          directory: false,
          multiple: options?.multiple ?? false,
          title: options?.title || 'Select File',
          filters: options?.filters,
        });
        if (!result) return null;
        return Array.isArray(result) ? result : [result];
      },

      saveFile: async (options) => {
        const result = await save({
          title: options?.title || 'Save File',
          defaultPath: options?.defaultPath,
          filters: options?.filters,
        });
        return result;
      },
    },

    window: {
      minimize: async () => {
        await invoke('window_minimize');
      },
      maximize: async () => {
        await invoke('window_maximize');
      },
      close: async () => {
        await invoke('window_close');
      },
    },
  };
}

// Singleton instance
let platformAPI: PlatformAPI | null = null;

export async function getPlatformAPI(): Promise<PlatformAPI> {
  if (!platformAPI) {
    platformAPI = createTauriAPI();
  }
  return platformAPI;
}
