import { useState, useEffect, useCallback, useRef } from 'react';
import { ipcClient } from '../lib/ipc';
import { Voice } from '../lib/ipc/types';

interface VoiceLibraryDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectVoice: (voice: Voice) => void;
}

export default function VoiceLibraryDialog({
  isOpen,
  onClose,
  onSelectVoice,
}: VoiceLibraryDialogProps) {
  const [voices, setVoices] = useState<Voice[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState({
    category: '',
    gender: '',
    language: '',
  });
  const [previewingId, setPreviewingId] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const PAGE_SIZE = 30;

  const searchVoices = useCallback(async (page = 0, append = false) => {
    if (page === 0) {
      setIsLoading(true);
    } else {
      setIsLoadingMore(true);
    }
    
    try {
      const results = await ipcClient.searchVoices({
        query: searchQuery || undefined,
        category: filters.category || undefined,
        gender: filters.gender || undefined,
        language: filters.language || undefined,
        page_size: PAGE_SIZE,
        page,
      });
      
      if (append) {
        setVoices(prev => [...prev, ...results.voices]);
      } else {
        setVoices(results.voices);
      }
      setHasMore(results.has_more);
      setTotalCount(results.total_count);
      setCurrentPage(results.page);
    } catch (err) {
      console.error('Failed to search voices:', err);
    } finally {
      setIsLoading(false);
      setIsLoadingMore(false);
    }
  }, [searchQuery, filters]);

  const handleLoadMore = () => {
    searchVoices(currentPage + 1, true);
  };

  useEffect(() => {
    if (isOpen) {
      setCurrentPage(0);
      searchVoices(0, false);
    } else {
      // Clean up audio when dialog closes
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      setPreviewingId(null);
    }
  }, [isOpen]);

  // Reset and search when filters change
  useEffect(() => {
    if (isOpen) {
      setCurrentPage(0);
      searchVoices(0, false);
    }
  }, [filters]);

  const handlePreview = async (voice: Voice) => {
    if (!voice.preview_url) return;
    
    // If same voice is playing, pause it
    if (previewingId === voice.voice_id && audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
      setPreviewingId(null);
      return;
    }
    
    // Stop any currently playing audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    
    setPreviewingId(voice.voice_id);
    try {
      const audio = new Audio(voice.preview_url);
      audioRef.current = audio;
      audio.onended = () => {
        setPreviewingId(null);
        audioRef.current = null;
      };
      audio.onerror = () => {
        setPreviewingId(null);
        audioRef.current = null;
      };
      await audio.play();
    } catch (err) {
      console.error('Failed to play preview:', err);
      setPreviewingId(null);
      audioRef.current = null;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-surface-900 rounded-xl border border-surface-700 w-[700px] max-h-[80vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-surface-700 shrink-0">
          <h2 className="text-lg font-semibold text-surface-100">Voice Library</h2>
          <button onClick={onClose} className="text-surface-400 hover:text-surface-200">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Search & Filters */}
        <div className="p-4 border-b border-surface-700 shrink-0 space-y-3">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && searchVoices()}
            placeholder="Search voices..."
            className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm"
          />
          <div className="flex gap-3">
            <select
              value={filters.category}
              onChange={(e) => setFilters({ ...filters, category: e.target.value })}
              className="px-3 py-1.5 bg-surface-800 border border-surface-700 rounded text-sm"
            >
              <option value="">All Categories</option>
              <option value="professional">Professional</option>
              <option value="high_quality">High Quality</option>
              <option value="generated">Generated</option>
              <option value="cloned">Cloned</option>
            </select>
            <select
              value={filters.gender}
              onChange={(e) => setFilters({ ...filters, gender: e.target.value })}
              className="px-3 py-1.5 bg-surface-800 border border-surface-700 rounded text-sm"
            >
              <option value="">All Genders</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="neutral">Neutral</option>
            </select>
            <select
              value={filters.language}
              onChange={(e) => setFilters({ ...filters, language: e.target.value })}
              className="px-3 py-1.5 bg-surface-800 border border-surface-700 rounded text-sm"
            >
              <option value="">All Languages</option>
              <option value="en">English</option>
              <option value="vi">Vietnamese</option>
              <option value="zh">Chinese</option>
              <option value="ja">Japanese</option>
              <option value="ko">Korean</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
              <option value="de">German</option>
            </select>
            <button 
              onClick={() => { setCurrentPage(0); searchVoices(0, false); }} 
              className="btn-secondary text-sm px-4"
            >
              Search
            </button>
          </div>
        </div>

        {/* Voice List */}
        <div className="flex-1 overflow-y-auto p-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8 text-surface-400">
              <svg className="w-6 h-6 animate-spin mr-2" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Loading voices...
            </div>
          ) : voices.length === 0 ? (
            <div className="text-center py-8 text-surface-500">No voices found</div>
          ) : (
            <>
            <div className="grid grid-cols-2 gap-3">
              {voices.map((voice) => (
                <div
                  key={voice.voice_id}
                  className="p-3 bg-surface-800/50 rounded-lg border border-surface-700 hover:border-primary-500/50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-surface-200 truncate">{voice.name}</div>
                      <div className="text-xs text-surface-500">{voice.category}</div>
                      {voice.labels && Object.keys(voice.labels).length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {Object.entries(voice.labels).slice(0, 3).map(([key, value]) => (
                            <span key={key} className="text-[10px] px-1.5 py-0.5 bg-surface-700 rounded">
                              {value}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="flex gap-1 ml-2">
                      {voice.preview_url && (
                        <button
                          onClick={() => handlePreview(voice)}
                          className="p-1.5 text-surface-400 hover:text-surface-200 hover:bg-surface-700 rounded"
                          title="Preview"
                        >
                          {previewingId === voice.voice_id ? (
                            <svg className="w-4 h-4 animate-pulse text-primary-400" fill="currentColor" viewBox="0 0 24 24">
                              <path d="M6 6h4v12H6zM14 6h4v12h-4z" />
                            </svg>
                          ) : (
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                          )}
                        </button>
                      )}
                      <button
                        onClick={() => {
                          onSelectVoice(voice);
                          onClose();
                        }}
                        className="p-1.5 text-primary-400 hover:text-primary-300 hover:bg-surface-700 rounded"
                        title="Select"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Load More Button */}
            {hasMore && (
              <div className="flex justify-center pt-4">
                <button
                  onClick={handleLoadMore}
                  disabled={isLoadingMore}
                  className="px-6 py-2 bg-surface-800 hover:bg-surface-700 text-surface-300 rounded-lg text-sm transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  {isLoadingMore ? (
                    <>
                      <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Loading...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                      Load More
                    </>
                  )}
                </button>
              </div>
            )}
            </>
          )}
        </div>

        <div className="px-4 py-3 border-t border-surface-700 shrink-0 text-xs text-surface-500 flex items-center justify-between">
          <span>
            Showing {voices.length}{totalCount > 0 ? ` of ${totalCount.toLocaleString()}` : ''} voice{voices.length !== 1 ? 's' : ''}
          </span>
          {hasMore && (
            <span className="text-primary-400">More available</span>
          )}
        </div>
      </div>
    </div>
  );
}
