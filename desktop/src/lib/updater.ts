import { check, Update } from '@tauri-apps/plugin-updater';
import { relaunch } from '@tauri-apps/plugin-process';
import { getVersion } from '@tauri-apps/api/app';

export interface UpdateInfo {
  version: string;
  currentVersion: string;
  releaseNotes?: string;
  releaseDate?: string;
}

export interface UpdateState {
  checking: boolean;
  available: boolean;
  downloading: boolean;
  progress: number;
  error: string | null;
  updateInfo: UpdateInfo | null;
}

type UpdateListener = (state: UpdateState) => void;

class UpdateManager {
  private state: UpdateState = {
    checking: false,
    available: false,
    downloading: false,
    progress: 0,
    error: null,
    updateInfo: null,
  };
  
  private listeners: Set<UpdateListener> = new Set();
  private pendingUpdate: Update | null = null;
  private totalBytes = 0;
  private downloadedBytes = 0;

  subscribe(listener: UpdateListener): () => void {
    this.listeners.add(listener);
    listener(this.state);
    return () => this.listeners.delete(listener);
  }

  private notify() {
    this.listeners.forEach(listener => listener({ ...this.state }));
  }

  private setState(updates: Partial<UpdateState>) {
    this.state = { ...this.state, ...updates };
    this.notify();
  }

  async checkForUpdates(_silent = false): Promise<boolean> {
    if (this.state.checking || this.state.downloading) return false;

    this.setState({ checking: true, error: null });

    try {
      console.log('[Updater] Checking for updates...');
      const update = await check();
      const currentVersion = await getVersion();

      if (update) {
        console.log(`[Updater] Update available: ${update.version}`);
        this.pendingUpdate = update;
        
        this.setState({
          checking: false,
          available: true,
          updateInfo: {
            version: update.version,
            currentVersion,
            releaseNotes: update.body || undefined,
            releaseDate: update.date || undefined,
          },
        });
        return true;
      } else {
        console.log('[Updater] No updates available');
        this.setState({
          checking: false,
          available: false,
          updateInfo: null,
        });
        return false;
      }
    } catch (error) {
      console.error('[Updater] Error checking for updates:', error);
      this.setState({
        checking: false,
        error: error instanceof Error ? error.message : String(error),
      });
      return false;
    }
  }

  async downloadAndInstall(): Promise<void> {
    if (!this.pendingUpdate || this.state.downloading) return;

    this.setState({ downloading: true, progress: 0, error: null });
    this.totalBytes = 0;
    this.downloadedBytes = 0;

    try {
      console.log('[Updater] Downloading update...');

      await this.pendingUpdate.downloadAndInstall((progress) => {
        if (progress.event === 'Started') {
          this.totalBytes = progress.data.contentLength || 0;
          console.log(`[Updater] Download started, total: ${this.totalBytes} bytes`);
        } else if (progress.event === 'Progress') {
          this.downloadedBytes += progress.data.chunkLength;
          const percent = this.totalBytes > 0 
            ? Math.round((this.downloadedBytes / this.totalBytes) * 100)
            : 0;
          this.setState({ progress: Math.min(percent, 99) });
        } else if (progress.event === 'Finished') {
          console.log('[Updater] Download finished');
          this.setState({ progress: 100 });
        }
      });

      console.log('[Updater] Update installed, relaunching...');
      await relaunch();
    } catch (error) {
      console.error('[Updater] Error installing update:', error);
      this.setState({
        downloading: false,
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }

  dismiss() {
    this.setState({
      available: false,
      updateInfo: null,
    });
    this.pendingUpdate = null;
  }

  getState(): UpdateState {
    return { ...this.state };
  }
}

export const updateManager = new UpdateManager();

// Legacy function for backward compatibility
export async function checkForUpdates(silent = false): Promise<void> {
  await updateManager.checkForUpdates(silent);
}
