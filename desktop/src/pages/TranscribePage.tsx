import { useState } from 'react';
import { getPlatformAPI } from '../lib/platform';

export default function TranscribePage() {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  async function handleSelectFile() {
    try {
      const api = await getPlatformAPI();
      const file = await api.dialog.openFile({
        title: 'Select Audio File',
        filters: [
          {
            name: 'Audio',
            extensions: ['mp3', 'wav', 'ogg', 'flac', 'm4a'],
          },
        ],
      });
      if (file) {
        setSelectedFile(file);
        setResult(null);
      }
    } catch (err) {
      console.error('Failed to open file dialog:', err);
    }
  }

  async function handleTranscribe() {
    if (!selectedFile) return;
    setIsProcessing(true);
    setResult(null);

    try {
      // TODO: Call backend transcription API
      // const result = await ipcClient.transcribe({ file_path: selectedFile });
      // setResult(result.text);
      
      // Placeholder for demo
      await new Promise((resolve) => setTimeout(resolve, 2000));
      setResult('Transcription feature coming soon...');
    } catch (err) {
      console.error('Transcription failed:', err);
    } finally {
      setIsProcessing(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h1 className="text-2xl font-semibold text-surface-100">Transcribe Audio</h1>

      <div className="card space-y-4">
        <div>
          <label className="block text-sm font-medium text-surface-300 mb-2">
            Audio File
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={selectedFile || ''}
              readOnly
              placeholder="Select an audio file..."
              className="input flex-1"
              aria-label="Selected audio file"
            />
            <button onClick={handleSelectFile} className="btn-secondary">
              <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
                />
              </svg>
              Browse
            </button>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            onClick={handleTranscribe}
            disabled={!selectedFile || isProcessing}
            className="btn-primary"
          >
            {isProcessing ? (
              <>
                <svg className="w-4 h-4 mr-2 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Transcribing...
              </>
            ) : (
              <>
                <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                Transcribe
              </>
            )}
          </button>
        </div>
      </div>

      {result && (
        <div className="card animate-fade-in">
          <h2 className="text-lg font-medium text-surface-200 mb-3">Result</h2>
          <div className="p-4 bg-surface-800 rounded-lg">
            <p className="text-surface-300 whitespace-pre-wrap">{result}</p>
          </div>
          <div className="flex justify-end mt-4">
            <button
              onClick={() => navigator.clipboard.writeText(result)}
              className="btn-ghost text-sm"
            >
              <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
              </svg>
              Copy
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
