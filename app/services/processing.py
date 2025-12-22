"""Multi-threaded TTS processing engine"""
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue, Empty
from typing import List, Optional, Callable, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from core.models import TextLine, LineStatus, APIKey, Proxy, Voice, VoiceSettings, Project
from services.elevenlabs import ElevenLabsAPI, APIKeyManager



@dataclass
class ThreadInfo:
    """Information about a single thread's activity"""
    thread_id: int
    status: str = "idle"  # idle, working, waiting
    current_line_index: Optional[int] = None
    lines_processed: int = 0
    last_activity: Optional[datetime] = None


@dataclass
class ProcessingStats:
    total: int = 0
    completed: int = 0
    failed: int = 0
    processing: int = 0
    start_time: Optional[datetime] = None
    current_loop: int = 1
    thread_info: Dict[int, ThreadInfo] = field(default_factory=dict)
    
    @property
    def pending(self) -> int:
        return self.total - self.completed - self.failed - self.processing
    
    @property
    def progress_percent(self) -> float:
        if self.total == 0:
            return 0
        return (self.completed / self.total) * 100
    
    @property
    def elapsed_time(self) -> float:
        if not self.start_time:
            return 0
        return (datetime.now() - self.start_time).total_seconds()
    
    @property
    def active_threads(self) -> int:
        return sum(1 for t in self.thread_info.values() if t.status == "working")
    
    def get_thread_display(self) -> Dict[int, str]:
        """Get thread info formatted for display"""
        return {
            tid: f"Line {info.current_line_index + 1}" if info.current_line_index is not None else info.status
            for tid, info in self.thread_info.items()
        }


class ProcessingEngine:
    """Multi-threaded TTS processing engine"""
    
    def __init__(
        self,
        api_keys: List[APIKey],
        proxies: List[Proxy],
        voices: Dict[str, Voice],
        output_folder: str,
        thread_count: int = 5,
        max_retries: int = 3,
        default_voice_id: Optional[str] = None,
        request_delay: float = 0.0,
        on_progress: Optional[Callable[[ProcessingStats], None]] = None,
        on_line_update: Optional[Callable[[TextLine], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
        on_credit_used: Optional[Callable[[APIKey, int], None]] = None,
        on_key_removed: Optional[Callable[[APIKey, str], None]] = None
    ):
        self._api = ElevenLabsAPI()
        self._on_key_removed = on_key_removed
        self._key_manager = APIKeyManager(api_keys, on_key_removed=self._handle_key_removed)
        self._proxies = {p.id: p for p in proxies}
        self._voices = voices
        self._output_folder = output_folder
        self._thread_count = min(max(1, thread_count), 50)
        self._max_retries = max_retries
        self._default_voice_id = default_voice_id
        self._request_delay = max(0.0, request_delay)
        
        self._on_progress = on_progress
        self._on_line_update = on_line_update
        self._on_log = on_log
        self._on_credit_used = on_credit_used
        
        self._running = False
        self._paused = False
        self._stop_requested = False
        self._stats = ProcessingStats()
        self._lock = threading.Lock()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused initially
        
        # Loop mode
        self._loop_enabled = False
        self._loop_count = 0
        self._loop_delay = 5
    
    def _log(self, message: str):
        if self._on_log:
            self._on_log(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def _handle_key_removed(self, key: APIKey, reason: str):
        """Handle API key removal due to low credits"""
        self._log(f"API key '{key.name or key.id[:8]}' removed: {reason}")
        if self._on_key_removed:
            self._on_key_removed(key, reason)
    
    def _update_stats(self):
        if self._on_progress:
            self._on_progress(self._stats)
    
    def _update_line(self, line: TextLine):
        if self._on_line_update:
            self._on_line_update(line)
    
    def _get_proxy_for_key(self, key: APIKey) -> Optional[Proxy]:
        if key.assigned_proxy_id:
            proxy = self._proxies.get(key.assigned_proxy_id)
            if proxy and proxy.enabled and proxy.is_healthy:
                return proxy
        return None
    
    def _process_line(self, line: TextLine, thread_id: int = 0) -> bool:
        """Process a single line. Returns True if successful."""
        if self._stop_requested:
            return False
        
        # Update thread info
        with self._lock:
            if thread_id not in self._stats.thread_info:
                self._stats.thread_info[thread_id] = ThreadInfo(thread_id=thread_id)
            self._stats.thread_info[thread_id].status = "working"
            self._stats.thread_info[thread_id].current_line_index = line.index
            self._stats.thread_info[thread_id].last_activity = datetime.now()
        
        # Wait if paused
        self._pause_event.wait()
        
        if self._stop_requested:
            return False
        
        # Get available API key
        api_key = self._key_manager.get_next_available_key()
        if not api_key:
            self._log(f"No available API keys for line {line.index + 1}")
            return False
        
        # Get voice ID - use default if not set
        voice_id = line.voice_id or self._default_voice_id
        if not voice_id:
            self._log(f"No voice assigned for line {line.index + 1}")
            line.status = LineStatus.ERROR
            line.error_message = "No voice assigned"
            self._update_line(line)
            return False
        
        # Get voice settings
        voice = self._voices.get(voice_id)
        settings = voice.settings if voice else VoiceSettings()
        
        # Get proxy
        proxy = self._get_proxy_for_key(api_key)
        
        # Generate output path
        output_path = os.path.join(
            self._output_folder,
            f"{line.index + 1:05d}.mp3"
        )
        
        # Update status
        with self._lock:
            line.status = LineStatus.PROCESSING
            self._stats.processing += 1
        self._update_line(line)
        
        # Log processing start with model info
        self._log(f"Processing line {line.index + 1} with model: {settings.model.value}")
        self._log(f"[DEBUG] Original text: {line.text[:100]}..." if len(line.text) > 100 else f"[DEBUG] Original text: {line.text}")
        
        processed_text = line.text
        
        self._log(f"[DEBUG] Final text to TTS ({len(processed_text)} chars): {processed_text[:150]}..." if len(processed_text) > 150 else f"[DEBUG] Final text to TTS ({len(processed_text)} chars): {processed_text}")
        
        # Process with retries
        success = False
        last_error = ""
        
        for attempt in range(self._max_retries + 1):
            if self._stop_requested:
                break
            
            if attempt > 0:
                self._log(f"Retry {attempt}/{self._max_retries} for line {line.index + 1}")
                time.sleep(min(2 ** attempt, 30))  # Exponential backoff
            
            self._log(f"[DEBUG] Calling TTS API: voice={voice_id[:8]}..., key={api_key.key[:8]}..., output={output_path}")
            try:
                success, message, duration = self._api.text_to_speech(
                    text=processed_text,
                    voice_id=voice_id,
                    api_key=api_key,
                    output_path=output_path,
                    settings=settings,
                    proxy=proxy
                )
                self._log(f"[DEBUG] TTS API response: success={success}, message={message[:100] if message else 'None'}, duration={duration}")
            except Exception as e:
                self._log(f"[ERROR] TTS API exception: {type(e).__name__}: {str(e)}")
                success = False
                message = f"Exception: {type(e).__name__}: {str(e)}"
                duration = None
            
            # Apply request delay to avoid rate limiting
            if self._request_delay > 0:
                time.sleep(self._request_delay)
            
            if success:
                line.status = LineStatus.DONE
                line.output_path = output_path
                line.audio_duration = duration
                line.error_message = None
                line.model_used = settings.model.value  # Store which model was used
                
                # Log the model used
                self._log(f"Line {line.index + 1} completed with model: {settings.model.value}")
                
                # Fetch actual credit usage from ElevenLabs API
                chars_used = len(line.text)
                self._api.refresh_subscription(api_key, proxy)
                if self._on_credit_used:
                    self._on_credit_used(api_key, chars_used)
                
                break
            
            last_error = message
            
            # Handle rate limiting
            if message == "RATE_LIMIT":
                self._log(f"Rate limit hit on key {api_key.name or api_key.id[:8]}, rotating...")
                self._key_manager.mark_key_rate_limited(api_key, 60)
                # Try with a different key
                api_key = self._key_manager.get_next_available_key()
                if not api_key:
                    break
                proxy = self._get_proxy_for_key(api_key)
            
            # Check if all keys exhausted
            if self._key_manager.all_keys_exhausted():
                self._log("All API keys exhausted")
                break
        
        # Update final status
        with self._lock:
            self._stats.processing -= 1
            if success:
                self._stats.completed += 1
            else:
                line.status = LineStatus.ERROR
                line.error_message = last_error
                line.retry_count += 1
                self._stats.failed += 1
            
            # Update thread info
            if thread_id in self._stats.thread_info:
                self._stats.thread_info[thread_id].status = "idle"
                self._stats.thread_info[thread_id].current_line_index = None
                self._stats.thread_info[thread_id].lines_processed += 1
        
        self._update_line(line)
        self._update_stats()
        
        return success
    
    def start(self, lines: List[TextLine]):
        """Start processing lines"""
        if self._running:
            return
        
        self._running = True
        self._stop_requested = False
        self._paused = False
        self._pause_event.set()
        
        # Filter pending and error lines, reset error lines to pending for reprocessing
        pending_lines = [l for l in lines if l.status in (LineStatus.PENDING, LineStatus.ERROR)]
        for line in pending_lines:
            if line.status == LineStatus.ERROR:
                line.status = LineStatus.PENDING
                line.error_message = None
                self._update_line(line)
        
        # Reset stats
        self._stats = ProcessingStats(
            total=len(pending_lines),
            start_time=datetime.now()
        )
        self._update_stats()
        
        # Ensure output folder exists
        os.makedirs(self._output_folder, exist_ok=True)
        
        self._log(f"Starting processing of {len(pending_lines)} lines with {self._thread_count} threads")
        
        # Start processing thread
        self._process_thread = threading.Thread(
            target=self._process_all,
            args=(pending_lines,),
            daemon=True
        )
        self._process_thread.start()
    
    def _process_all(self, lines: List[TextLine]):
        """Process all lines using thread pool"""
        current_loop = 1
        
        while True:
            self._stats.current_loop = current_loop
            self._update_stats()
            
            # Reset failed lines for new loop
            if current_loop > 1:
                for line in lines:
                    if line.status == LineStatus.ERROR:
                        line.status = LineStatus.PENDING
                        self._update_line(line)
            
            pending = [l for l in lines if l.status == LineStatus.PENDING]
            
            # Initialize thread info for all threads
            for i in range(self._thread_count):
                self._stats.thread_info[i] = ThreadInfo(thread_id=i)
            
            with ThreadPoolExecutor(max_workers=self._thread_count) as executor:
                # Submit tasks with thread_id tracking
                futures = {}
                thread_id_counter = [0]  # Use list for mutable reference
                
                def submit_with_thread_id(line):
                    tid = thread_id_counter[0] % self._thread_count
                    thread_id_counter[0] += 1
                    return executor.submit(self._process_line, line, tid), line
                
                for line in pending:
                    future, ln = submit_with_thread_id(line)
                    futures[future] = ln
                
                for future in as_completed(futures):
                    if self._stop_requested:
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    try:
                        future.result()
                    except Exception as e:
                        self._log(f"Error: {str(e)}")
            
            # Check if should loop
            if self._stop_requested:
                break
            
            if not self._loop_enabled:
                break
            
            if self._loop_count > 0 and current_loop >= self._loop_count:
                break
            
            # Delay before next loop
            self._log(f"Loop {current_loop} complete. Starting loop {current_loop + 1} in {self._loop_delay}s...")
            for _ in range(self._loop_delay):
                if self._stop_requested:
                    break
                time.sleep(1)
            
            current_loop += 1
            
            # Reset stats for new loop
            self._stats.completed = 0
            self._stats.failed = 0
        
        self._running = False
        self._log("Processing complete")
    
    def stop(self):
        """Stop processing gracefully"""
        self._stop_requested = True
        self._pause_event.set()  # Unpause to allow threads to exit
        self._log("Stop requested, waiting for current tasks to complete...")
    
    def pause(self):
        """Pause processing"""
        if self._running and not self._paused:
            self._paused = True
            self._pause_event.clear()
            self._log("Processing paused")
    
    def resume(self):
        """Resume processing"""
        if self._running and self._paused:
            self._paused = False
            self._pause_event.set()
            self._log("Processing resumed")
    
    def set_loop_mode(self, enabled: bool, count: int = 0, delay: int = 5):
        """Configure loop mode"""
        self._loop_enabled = enabled
        self._loop_count = count
        self._loop_delay = delay
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def is_paused(self) -> bool:
        return self._paused
    
    @property
    def stats(self) -> ProcessingStats:
        return self._stats
