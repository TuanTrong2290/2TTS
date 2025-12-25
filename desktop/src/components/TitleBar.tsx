import { useState } from 'react';
import { useAppStore } from '../stores/appStore';
import { getPlatformAPI } from '../lib/platform';
import { ipcClient } from '../lib/ipc';
import { TextLine } from '../lib/ipc/types';

export default function TitleBar() {
  const { versionInfo, totalCredits, setTotalCredits, lines, outputFolder, defaultVoiceId, setLines, setOutputFolder, setDefaultVoice } = useAppStore();
  const [showProjectMenu, setShowProjectMenu] = useState(false);
  const [projectName, setProjectName] = useState<string | null>(null);
  const [isRefreshingCredits, setIsRefreshingCredits] = useState(false);

  const handleRefreshCredits = async () => {
    setIsRefreshingCredits(true);
    try {
      const credits = await ipcClient.getCredits();
      setTotalCredits(credits);
    } catch (err) {
      console.error('Failed to refresh credits:', err);
    } finally {
      setIsRefreshingCredits(false);
    }
  };

  const handleSaveProject = async () => {
    try {
      const api = await getPlatformAPI();
      const filePath = await api.dialog.saveFile({
        title: 'Save Project',
        defaultPath: projectName || '2tts_project.json',
        filters: [{ name: 'Project Files', extensions: ['json'] }],
      });
      if (!filePath) return;
      
      const project = {
        version: '1.0',
        savedAt: new Date().toISOString(),
        outputFolder,
        defaultVoiceId,
        lines: lines.map(l => ({
          id: l.id,
          index: l.index,
          text: l.text,
          voice_id: l.voice_id,
          voice_name: l.voice_name,
          status: l.status === 'done' ? 'done' : 'pending',
          output_path: l.output_path,
        })),
      };
      await ipcClient.writeTextFile(filePath, JSON.stringify(project, null, 2));
      setProjectName(filePath.split(/[/\\]/).pop()?.replace('.json', '') || null);
      setShowProjectMenu(false);
    } catch (err) {
      console.error('Failed to save project:', err);
    }
  };

  const handleLoadProject = async () => {
    try {
      const api = await getPlatformAPI();
      const filePaths = await api.dialog.openFile({
        title: 'Load Project',
        filters: [{ name: 'Project Files', extensions: ['json'] }],
        multiple: false,
      });
      if (!filePaths || filePaths.length === 0) return;
      
      const content = await ipcClient.readTextFile(filePaths[0]);
      const project = JSON.parse(content);
      
      if (project.outputFolder) setOutputFolder(project.outputFolder);
      if (project.defaultVoiceId) setDefaultVoice(project.defaultVoiceId, null);
      if (project.lines) {
        const loadedLines: TextLine[] = project.lines.map((l: { id?: string; index?: number; text: string; voice_id?: string; voice_name?: string; status?: string; output_path?: string }, i: number) => ({
          id: l.id || crypto.randomUUID(),
          index: l.index ?? i,
          text: l.text,
          original_text: l.text,
          voice_id: l.voice_id || null,
          voice_name: l.voice_name || null,
          status: (l.status === 'done' ? 'done' : 'pending') as TextLine['status'],
          error_message: null,
          source_file: null,
          start_time: null,
          end_time: null,
          audio_duration: null,
          output_path: l.output_path || null,
          retry_count: 0,
          detected_language: null,
          model_id: null,
        }));
        setLines(loadedLines);
      }
      setProjectName(filePaths[0].split(/[/\\]/).pop()?.replace('.json', '') || null);
      setShowProjectMenu(false);
    } catch (err) {
      console.error('Failed to load project:', err);
    }
  };

  const handleNewProject = () => {
    setLines([]);
    setOutputFolder('');
    setProjectName(null);
    setShowProjectMenu(false);
  };

  const handleMinimize = async () => {
    const api = await getPlatformAPI();
    api.window.minimize();
  };
  const handleMaximize = async () => {
    const api = await getPlatformAPI();
    api.window.maximize();
  };
  const handleClose = async () => {
    const api = await getPlatformAPI();
    api.window.close();
  };

  return (
    <div className="h-10 bg-surface-900/80 backdrop-blur-sm border-b border-surface-800 flex items-center justify-between px-4 drag-region select-none">
      <div className="flex items-center gap-3 no-drag">
        <div className="w-6 h-6 rounded-lg bg-primary-600 flex items-center justify-center">
          <span className="text-xs font-bold text-white">2T</span>
        </div>
        <span className="text-sm font-medium text-surface-200">2TTS</span>
        {versionInfo && (
          <span className="text-xs text-surface-500">v{versionInfo.uiVersion}</span>
        )}
        
        {/* Project Menu */}
        <div className="relative ml-4">
          <button
            onClick={() => setShowProjectMenu(!showProjectMenu)}
            className="flex items-center gap-1 px-2 py-1 text-sm text-surface-300 hover:text-surface-100 hover:bg-surface-800 rounded transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
            <span>{projectName || 'Project'}</span>
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          
          {showProjectMenu && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setShowProjectMenu(false)} />
              <div className="absolute top-full left-0 mt-1 w-40 py-1 bg-surface-800 border border-surface-700 rounded-lg shadow-lg z-50">
                <button
                  onClick={handleNewProject}
                  className="w-full px-3 py-2 text-left text-sm text-surface-300 hover:bg-surface-700 hover:text-surface-100"
                >
                  New Project
                </button>
                <button
                  onClick={handleLoadProject}
                  className="w-full px-3 py-2 text-left text-sm text-surface-300 hover:bg-surface-700 hover:text-surface-100"
                >
                  Open Project...
                </button>
                <button
                  onClick={handleSaveProject}
                  className="w-full px-3 py-2 text-left text-sm text-surface-300 hover:bg-surface-700 hover:text-surface-100"
                >
                  Save Project...
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 no-drag">
          <div className="flex items-center gap-1.5 px-2 py-1 bg-surface-800 rounded-lg">
            <svg
              className="w-4 h-4 text-primary-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span className="text-sm font-medium text-surface-200">
              {totalCredits.toLocaleString()}
            </span>
            <button
              onClick={handleRefreshCredits}
              disabled={isRefreshingCredits}
              className="p-0.5 text-surface-500 hover:text-surface-300 transition-colors disabled:opacity-50"
              title="Refresh credits"
            >
              <svg className={`w-3.5 h-3.5 ${isRefreshingCredits ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>

        <div className="flex items-center no-drag">
          <button
            onClick={handleMinimize}
            className="w-10 h-10 flex items-center justify-center text-surface-400 hover:text-surface-100 hover:bg-surface-800 transition-colors"
            aria-label="Minimize"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M5 10h10" stroke="currentColor" strokeWidth="2" />
            </svg>
          </button>
          <button
            onClick={handleMaximize}
            className="w-10 h-10 flex items-center justify-center text-surface-400 hover:text-surface-100 hover:bg-surface-800 transition-colors"
            aria-label="Maximize"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 14 14">
              <rect
                x="1"
                y="1"
                width="12"
                height="12"
                rx="1"
                stroke="currentColor"
                strokeWidth="2"
              />
            </svg>
          </button>
          <button
            onClick={handleClose}
            className="w-10 h-10 flex items-center justify-center text-surface-400 hover:text-white hover:bg-red-600 transition-colors"
            aria-label="Close"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 16 16">
              <path
                d="M4 4l8 8M12 4l-8 8"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
