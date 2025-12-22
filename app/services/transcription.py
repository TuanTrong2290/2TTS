"""Transcription service for Speech-to-Text functionality"""
import os
import json
import threading
import subprocess
import tempfile
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.models import (
    TranscriptionJob, TranscriptionResult, TranscriptionSegment,
    JobStatus, APIKey, Proxy
)
from services.elevenlabs import ElevenLabsAPI


# Supported audio/video formats
SUPPORTED_AUDIO_FORMATS = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma'}
SUPPORTED_VIDEO_FORMATS = {'.mp4', '.mkv', '.avi', '.mov', '.webm', '.wmv', '.flv'}
SUPPORTED_FORMATS = SUPPORTED_AUDIO_FORMATS | SUPPORTED_VIDEO_FORMATS

MAX_FILE_SIZE = 3 * 1024 * 1024 * 1024  # 3GB


def is_video_file(file_path: str) -> bool:
    """Check if file is a video format"""
    ext = Path(file_path).suffix.lower()
    return ext in SUPPORTED_VIDEO_FORMATS


def convert_video_to_audio(video_path: str, output_path: Optional[str] = None, 
                           bitrate: str = "128k", on_log: Optional[Callable[[str], None]] = None) -> tuple[bool, str, Optional[str]]:
    """
    Convert video file to MP3 audio using ffmpeg.
    
    Args:
        video_path: Path to the video file
        output_path: Optional output path for MP3. If None, creates temp file.
        bitrate: Audio bitrate (default: 128k for smaller file size)
        on_log: Optional logging callback
        
    Returns:
        (success, message, audio_path or None)
    """
    def log(msg: str):
        if on_log:
            on_log(msg)
    
    if not os.path.exists(video_path):
        return False, "Video file not found", None
    
    # Generate output path if not provided
    if output_path is None:
        video_name = Path(video_path).stem
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, f"{video_name}_audio.mp3")
    
    log(f"Converting video to audio: {Path(video_path).name} -> {Path(output_path).name}")
    
    try:
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-vn',  # No video
            '-acodec', 'libmp3lame',
            '-ab', bitrate,
            '-ar', '44100',  # Sample rate
            '-ac', '2',  # Stereo
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=600  # 10 minute timeout for large files
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            # Get file sizes for logging
            video_size = os.path.getsize(video_path)
            audio_size = os.path.getsize(output_path)
            reduction = ((video_size - audio_size) / video_size) * 100 if video_size > 0 else 0
            
            log(f"Conversion complete: {video_size / (1024*1024):.1f}MB -> {audio_size / (1024*1024):.1f}MB ({reduction:.1f}% reduction)")
            return True, "Success", output_path
        else:
            # Decode stderr safely, ignoring encoding errors
            error_msg = result.stderr.decode('utf-8', errors='ignore')[:500] if result.stderr else "Unknown error"
            return False, f"FFmpeg error: {error_msg}", None
            
    except subprocess.TimeoutExpired:
        return False, "Conversion timeout (exceeded 10 minutes)", None
    except FileNotFoundError:
        return False, "FFmpeg not found. Please install FFmpeg.", None
    except Exception as e:
        return False, f"Conversion error: {str(e)}", None


def is_supported_format(file_path: str) -> bool:
    """Check if file format is supported"""
    ext = Path(file_path).suffix.lower()
    return ext in SUPPORTED_FORMATS


def get_file_info(file_path: str) -> Dict[str, Any]:
    """Get file metadata"""
    path = Path(file_path)
    stat = path.stat()
    
    duration = None
    try:
        from pydub import AudioSegment
        if path.suffix.lower() in SUPPORTED_AUDIO_FORMATS:
            audio = AudioSegment.from_file(file_path)
            duration = len(audio) / 1000.0
    except:
        pass
    
    return {
        "name": path.name,
        "size": stat.st_size,
        "duration": duration,
        "extension": path.suffix.lower()
    }


class TranscriptionExporter:
    """Export transcription results to various formats"""
    
    @staticmethod
    def format_timestamp_srt(seconds: float) -> str:
        """Format timestamp for SRT: HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    @staticmethod
    def format_timestamp_vtt(seconds: float) -> str:
        """Format timestamp for VTT: HH:MM:SS.mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
    
    @classmethod
    def export_srt(cls, result: TranscriptionResult, output_path: str, include_speakers: bool = True) -> bool:
        """Export to SRT subtitle format"""
        try:
            lines = []
            for i, segment in enumerate(result.segments, 1):
                start = cls.format_timestamp_srt(segment.start)
                end = cls.format_timestamp_srt(segment.end)
                
                text = segment.text
                if include_speakers and segment.speaker_id:
                    speaker_name = result.get_speaker_name(segment.speaker_id)
                    text = f"[{speaker_name}] {text}"
                
                lines.append(f"{i}")
                lines.append(f"{start} --> {end}")
                lines.append(text)
                lines.append("")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))
            return True
        except Exception:
            return False
    
    @classmethod
    def export_vtt(cls, result: TranscriptionResult, output_path: str, include_speakers: bool = True) -> bool:
        """Export to WebVTT subtitle format"""
        try:
            lines = ["WEBVTT", ""]
            
            for i, segment in enumerate(result.segments, 1):
                start = cls.format_timestamp_vtt(segment.start)
                end = cls.format_timestamp_vtt(segment.end)
                
                text = segment.text
                if include_speakers and segment.speaker_id:
                    speaker_name = result.get_speaker_name(segment.speaker_id)
                    text = f"<v {speaker_name}>{text}"
                
                lines.append(f"{i}")
                lines.append(f"{start} --> {end}")
                lines.append(text)
                lines.append("")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))
            return True
        except Exception:
            return False
    
    @classmethod
    def export_txt(cls, result: TranscriptionResult, output_path: str, include_speakers: bool = True, include_timestamps: bool = False) -> bool:
        """Export to plain text"""
        try:
            lines = []
            
            for segment in result.segments:
                line_parts = []
                
                if include_timestamps:
                    timestamp = f"[{cls.format_timestamp_srt(segment.start)}]"
                    line_parts.append(timestamp)
                
                if include_speakers and segment.speaker_id:
                    speaker_name = result.get_speaker_name(segment.speaker_id)
                    line_parts.append(f"{speaker_name}:")
                
                line_parts.append(segment.text)
                lines.append(" ".join(line_parts))
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))
            return True
        except Exception:
            return False
    
    @classmethod
    def export_json(cls, result: TranscriptionResult, output_path: str) -> bool:
        """Export to JSON with full metadata"""
        try:
            data = result.to_dict()
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False


class TranscriptionEngine:
    """Engine for processing transcription jobs"""
    
    def __init__(
        self,
        api_keys: List[APIKey],
        proxies: Optional[List[Proxy]] = None,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        on_progress: Optional[Callable[[TranscriptionJob], None]] = None,
        on_log: Optional[Callable[[str], None]] = None
    ):
        self._api = ElevenLabsAPI()
        self._api_keys = api_keys
        self._proxies = proxies or []
        self._proxy_map = {p.id: p for p in self._proxies}
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._on_progress = on_progress
        self._on_log = on_log
        
        self._jobs: List[TranscriptionJob] = []
        self._is_running = False
        self._should_stop = False
        self._executor: Optional[ThreadPoolExecutor] = None
        self._lock = threading.Lock()
    
    @property
    def is_running(self) -> bool:
        return self._is_running
    
    @property
    def jobs(self) -> List[TranscriptionJob]:
        return self._jobs.copy()
    
    def _log(self, message: str):
        if self._on_log:
            self._on_log(message)
    
    def _get_available_key(self) -> Optional[tuple]:
        """Get an available API key and its proxy"""
        for key in self._api_keys:
            if key.is_available:
                proxy = self._proxy_map.get(key.assigned_proxy_id)
                return key, proxy
        return None, None
    
    def add_job(self, file_path: str, language: Optional[str] = None, diarize: bool = False, num_speakers: Optional[int] = None) -> Optional[TranscriptionJob]:
        """Add a new transcription job"""
        if not os.path.exists(file_path):
            self._log(f"File not found: {file_path}")
            return None
        
        if not is_supported_format(file_path):
            self._log(f"Unsupported format: {file_path}")
            return None
        
        file_info = get_file_info(file_path)
        
        if file_info["size"] > MAX_FILE_SIZE:
            self._log(f"File too large: {file_path} ({file_info['size'] / (1024**3):.2f}GB)")
            return None
        
        job = TranscriptionJob(
            input_path=file_path,
            file_name=file_info["name"],
            file_size=file_info["size"],
            duration=file_info["duration"],
            language=language,
            num_speakers=num_speakers,
            diarize=diarize
        )
        
        with self._lock:
            self._jobs.append(job)
        
        self._log(f"Added job: {job.file_name}")
        return job
    
    def remove_job(self, job_id: str) -> bool:
        """Remove a job from the queue"""
        with self._lock:
            for i, job in enumerate(self._jobs):
                if job.id == job_id and job.status == JobStatus.PENDING:
                    del self._jobs[i]
                    return True
        return False
    
    def clear_completed(self):
        """Remove completed jobs"""
        with self._lock:
            self._jobs = [j for j in self._jobs if j.status not in (JobStatus.DONE, JobStatus.ERROR)]
    
    def _process_job(self, job: TranscriptionJob):
        """Process a single transcription job with retry logic"""
        if self._should_stop:
            return
        
        job.status = JobStatus.PROCESSING
        if self._on_progress:
            self._on_progress(job)
        
        # Check if input is a video file - convert to audio first
        file_to_transcribe = job.input_path
        temp_audio_path = None
        
        if is_video_file(job.input_path):
            self._log(f"Video file detected, converting to audio: {job.file_name}")
            success, message, audio_path = convert_video_to_audio(
                job.input_path, 
                on_log=self._log
            )
            
            if not success:
                job.status = JobStatus.ERROR
                job.error = f"Video conversion failed: {message}"
                self._log(f"Failed to convert video: {job.file_name} - {message}")
                if self._on_progress:
                    self._on_progress(job)
                return
            
            file_to_transcribe = audio_path
            temp_audio_path = audio_path  # Track for cleanup
        
        retry_count = 0
        last_error = None
        
        try:
            while retry_count <= self._max_retries:
                if self._should_stop:
                    return
                
                api_key, proxy = self._get_available_key()
                if not api_key:
                    job.status = JobStatus.ERROR
                    job.error = "No available API key"
                    self._log(f"No API key available for: {job.file_name}")
                    if self._on_progress:
                        self._on_progress(job)
                    return
                
                if retry_count > 0:
                    self._log(f"Retry {retry_count}/{self._max_retries}: {job.file_name}")
                    import time
                    time.sleep(self._retry_delay)
                else:
                    if temp_audio_path:
                        self._log(f"Transcribing: {job.file_name} (using converted audio: {Path(file_to_transcribe).name})")
                    else:
                        self._log(f"Transcribing: {job.file_name}")
                
                success, message, result = self._api.transcribe(
                    file_path=file_to_transcribe,
                    api_key=api_key,
                    language=job.language,
                    diarize=job.diarize,
                    num_speakers=job.num_speakers,
                    proxy=proxy
                )
                
                if success and result:
                    job.status = JobStatus.DONE
                    job.result = result
                    job.completed_at = datetime.now()
                    self._log(f"Completed: {job.file_name} ({result.language})")
                    if self._on_progress:
                        self._on_progress(job)
                    return
                
                last_error = message
                
                # Don't retry on certain errors
                if message in ("Invalid API key", "File too large"):
                    break
                
                # Check for rate limit - wait longer before retry
                if message == "RATE_LIMIT":
                    self._log(f"Rate limited, waiting 60s before retry...")
                    import time
                    time.sleep(60)
                
                retry_count += 1
            
            # All retries failed
            job.status = JobStatus.ERROR
            job.error = last_error or "Unknown error after retries"
            self._log(f"Failed after {retry_count} retries: {job.file_name} - {last_error}")
            
            if self._on_progress:
                self._on_progress(job)
        finally:
            # Clean up temporary audio file from video conversion
            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                    self._log(f"Cleaned up temp audio file: {Path(temp_audio_path).name}")
                except Exception as e:
                    self._log(f"Warning: Could not remove temp file: {e}")
    
    def start(self):
        """Start processing pending jobs"""
        if self._is_running:
            return
        
        self._is_running = True
        self._should_stop = False
        
        def run():
            try:
                pending_jobs = [j for j in self._jobs if j.status == JobStatus.PENDING]
                for job in pending_jobs:
                    if self._should_stop:
                        break
                    self._process_job(job)
            finally:
                self._is_running = False
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
    
    def stop(self):
        """Stop processing"""
        self._should_stop = True
    
    def transcribe_single(self, file_path: str, language: Optional[str] = None, diarize: bool = False, num_speakers: Optional[int] = None) -> Optional[TranscriptionJob]:
        """Transcribe a single file synchronously"""
        job = self.add_job(file_path, language, diarize, num_speakers)
        if job:
            self._process_job(job)
        return job
