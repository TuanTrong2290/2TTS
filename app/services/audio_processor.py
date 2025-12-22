"""Audio post-processing service for 2TTS"""
import os
import subprocess
import tempfile
from typing import Optional, Tuple, List
from pathlib import Path
from dataclasses import dataclass


@dataclass
class AudioProcessingSettings:
    """Settings for audio post-processing"""
    normalize: bool = False
    normalize_level: float = -3.0  # dB
    fade_in: float = 0.0  # seconds
    fade_out: float = 0.0  # seconds
    silence_padding_start: float = 0.0  # seconds
    silence_padding_end: float = 0.0  # seconds
    trim_silence: bool = False
    trim_threshold: float = -40.0  # dB
    speed: float = 1.0
    pitch_shift: float = 0.0  # semitones
    
    def to_dict(self) -> dict:
        return {
            "normalize": self.normalize,
            "normalize_level": self.normalize_level,
            "fade_in": self.fade_in,
            "fade_out": self.fade_out,
            "silence_padding_start": self.silence_padding_start,
            "silence_padding_end": self.silence_padding_end,
            "trim_silence": self.trim_silence,
            "trim_threshold": self.trim_threshold,
            "speed": self.speed,
            "pitch_shift": self.pitch_shift
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AudioProcessingSettings':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class AudioProcessor:
    """Audio post-processing using FFmpeg"""
    
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self._ffmpeg = ffmpeg_path
    
    def process(
        self,
        input_path: str,
        output_path: str,
        settings: AudioProcessingSettings
    ) -> Tuple[bool, str]:
        """Apply post-processing to audio file"""
        if not os.path.exists(input_path):
            return False, "Input file not found"
        
        filters = []
        
        # Trim silence at start/end
        if settings.trim_silence:
            filters.append(f"silenceremove=start_periods=1:start_threshold={settings.trim_threshold}dB")
            filters.append(f"areverse,silenceremove=start_periods=1:start_threshold={settings.trim_threshold}dB,areverse")
        
        # Speed adjustment
        if settings.speed != 1.0:
            filters.extend(self._get_speed_filters(settings.speed))
        
        # Pitch shift
        if settings.pitch_shift != 0.0:
            # Use rubberband for pitch shifting if available, else asetrate
            semitones = settings.pitch_shift
            ratio = 2 ** (semitones / 12)
            filters.append(f"asetrate=44100*{ratio},aresample=44100")
        
        # Normalize
        if settings.normalize:
            filters.append(f"loudnorm=I=-16:TP={settings.normalize_level}:LRA=11")
        
        # Fade in/out
        if settings.fade_in > 0:
            filters.append(f"afade=t=in:st=0:d={settings.fade_in}")
        
        if settings.fade_out > 0:
            filters.append(f"afade=t=out:st=-{settings.fade_out}:d={settings.fade_out}")
        
        try:
            # Handle silence padding separately as it requires generating silence
            if settings.silence_padding_start > 0 or settings.silence_padding_end > 0:
                return self._process_with_padding(input_path, output_path, filters, settings)
            
            if not filters:
                # No processing needed, just copy
                import shutil
                shutil.copy2(input_path, output_path)
                return True, "No processing needed"
            
            filter_str = ",".join(filters)
            cmd = [
                self._ffmpeg, '-y',
                '-i', input_path,
                '-af', filter_str,
                '-c:a', 'libmp3lame',
                '-q:a', '2',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                return True, "Success"
            return False, result.stderr[:500]
            
        except subprocess.TimeoutExpired:
            return False, "Processing timeout"
        except FileNotFoundError:
            return False, "FFmpeg not found"
        except Exception as e:
            return False, str(e)
    
    def _process_with_padding(
        self,
        input_path: str,
        output_path: str,
        filters: List[str],
        settings: AudioProcessingSettings
    ) -> Tuple[bool, str]:
        """Process audio with silence padding"""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                processed_path = os.path.join(tmpdir, "processed.mp3")
                
                # First apply filters
                if filters:
                    filter_str = ",".join(filters)
                    cmd = [
                        self._ffmpeg, '-y',
                        '-i', input_path,
                        '-af', filter_str,
                        '-c:a', 'libmp3lame',
                        '-q:a', '2',
                        processed_path
                    ]
                    result = subprocess.run(cmd, capture_output=True, timeout=300)
                    if result.returncode != 0:
                        return False, "Filter processing failed"
                else:
                    processed_path = input_path
                
                # Generate silence files
                files_to_concat = []
                
                if settings.silence_padding_start > 0:
                    start_silence = os.path.join(tmpdir, "start_silence.mp3")
                    self._generate_silence(start_silence, settings.silence_padding_start)
                    files_to_concat.append(start_silence)
                
                files_to_concat.append(processed_path)
                
                if settings.silence_padding_end > 0:
                    end_silence = os.path.join(tmpdir, "end_silence.mp3")
                    self._generate_silence(end_silence, settings.silence_padding_end)
                    files_to_concat.append(end_silence)
                
                # Concatenate
                if len(files_to_concat) > 1:
                    list_file = os.path.join(tmpdir, "concat.txt")
                    with open(list_file, 'w') as f:
                        for fp in files_to_concat:
                            f.write(f"file '{fp}'\n")
                    
                    cmd = [
                        self._ffmpeg, '-y',
                        '-f', 'concat',
                        '-safe', '0',
                        '-i', list_file,
                        '-c:a', 'libmp3lame',
                        '-q:a', '2',
                        output_path
                    ]
                    result = subprocess.run(cmd, capture_output=True, timeout=300)
                    if result.returncode != 0:
                        return False, "Concatenation failed"
                else:
                    import shutil
                    shutil.copy2(processed_path, output_path)
                
                return True, "Success"
                
        except Exception as e:
            return False, str(e)
    
    def _generate_silence(self, output_path: str, duration: float) -> bool:
        """Generate a silent audio file"""
        try:
            cmd = [
                self._ffmpeg, '-y',
                '-f', 'lavfi',
                '-i', f'anullsrc=r=44100:cl=stereo:d={duration}',
                '-c:a', 'libmp3lame',
                '-q:a', '2',
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            return result.returncode == 0
        except:
            return False
    
    def _get_speed_filters(self, speed: float) -> List[str]:
        """Get atempo filters for speed adjustment"""
        filters = []
        remaining = speed
        
        while remaining > 2.0:
            filters.append("atempo=2.0")
            remaining /= 2.0
        while remaining < 0.5:
            filters.append("atempo=0.5")
            remaining *= 2.0
        
        if remaining != 1.0:
            filters.append(f"atempo={remaining}")
        
        return filters
    
    def get_audio_info(self, file_path: str) -> Optional[dict]:
        """Get audio file information"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                format_info = data.get("format", {})
                stream_info = data.get("streams", [{}])[0]
                
                return {
                    "duration": float(format_info.get("duration", 0)),
                    "size": int(format_info.get("size", 0)),
                    "bitrate": int(format_info.get("bit_rate", 0)),
                    "sample_rate": int(stream_info.get("sample_rate", 0)),
                    "channels": int(stream_info.get("channels", 0)),
                    "codec": stream_info.get("codec_name", "")
                }
        except:
            pass
        return None
    
    def batch_process(
        self,
        files: List[str],
        output_dir: str,
        settings: AudioProcessingSettings,
        on_progress: callable = None
    ) -> List[Tuple[str, bool, str]]:
        """Process multiple audio files"""
        results = []
        os.makedirs(output_dir, exist_ok=True)
        
        for i, input_path in enumerate(files):
            if on_progress:
                on_progress(i, len(files))
            
            filename = os.path.basename(input_path)
            output_path = os.path.join(output_dir, f"processed_{filename}")
            
            success, message = self.process(input_path, output_path, settings)
            results.append((input_path, success, message if not success else output_path))
        
        if on_progress:
            on_progress(len(files), len(files))
        
        return results
