"""Audio processing services"""
import os
import subprocess
from typing import List, Optional, Callable
from pathlib import Path

from core.models import TextLine


class SRTGenerator:
    """Generate SRT files with timing based on audio duration"""
    
    @staticmethod
    def format_time(seconds: float) -> str:
        """Format seconds to SRT timestamp (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def generate(
        self,
        lines: List[TextLine],
        output_path: str,
        gap: float = 0.0,
        offset: float = 0.0
    ) -> bool:
        """
        Generate SRT file from processed lines
        
        Args:
            lines: List of processed TextLines with audio_duration
            output_path: Path for output SRT file
            gap: Silence gap between segments in seconds
            offset: Global timing offset in seconds
        """
        try:
            srt_content = []
            current_time = offset
            
            for i, line in enumerate(lines):
                if line.audio_duration is None:
                    continue
                
                start_time = current_time
                end_time = start_time + line.audio_duration
                
                srt_content.append(f"{i + 1}")
                srt_content.append(f"{self.format_time(start_time)} --> {self.format_time(end_time)}")
                srt_content.append(line.text)
                srt_content.append("")
                
                current_time = end_time + gap
            
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(srt_content))
            
            return True
        except Exception as e:
            return False


class MP3Concatenator:
    """Concatenate multiple MP3 files into one using ffmpeg"""
    
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self._ffmpeg = ffmpeg_path
    
    def concatenate(
        self,
        input_files: List[str],
        output_path: str,
        silence_gap: float = 0.0,
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> tuple[bool, str]:
        """
        Concatenate MP3 files
        
        Args:
            input_files: List of input MP3 file paths
            output_path: Output file path
            silence_gap: Silence to insert between files (seconds)
            on_progress: Callback (current, total)
            
        Returns:
            (success, message)
        """
        if not input_files:
            return False, "No input files"
        
        try:
            # Create temporary list file for ffmpeg
            list_file = output_path + ".txt"
            
            with open(list_file, 'w', encoding='utf-8') as f:
                for i, file_path in enumerate(input_files):
                    # Escape single quotes in path
                    escaped_path = file_path.replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")
                    
                    # Add silence gap if needed (except after last file)
                    if silence_gap > 0 and i < len(input_files) - 1:
                        # Generate silence using anullsrc
                        f.write(f"file 'anullsrc=r=44100:cl=stereo:d={silence_gap}'\n")
            
            # Build ffmpeg command
            if silence_gap > 0:
                # Complex filter for silence insertion
                cmd = [
                    self._ffmpeg,
                    '-y',  # Overwrite output
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', list_file,
                    '-c:a', 'libmp3lame',
                    '-q:a', '2',
                    output_path
                ]
            else:
                # Simple concatenation without re-encoding
                cmd = [
                    self._ffmpeg,
                    '-y',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', list_file,
                    '-c', 'copy',
                    output_path
                ]
            
            # Run ffmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            # Clean up list file
            try:
                os.remove(list_file)
            except:
                pass
            
            if result.returncode == 0:
                return True, "Success"
            else:
                return False, result.stderr[:500]
                
        except subprocess.TimeoutExpired:
            return False, "FFmpeg timeout"
        except FileNotFoundError:
            return False, "FFmpeg not found. Please install FFmpeg."
        except Exception as e:
            return False, str(e)
    
    def concatenate_streaming(
        self,
        lines: List[TextLine],
        output_path: str,
        silence_gap: float = 0.0,
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> tuple[bool, str]:
        """
        Concatenate audio from processed lines using streaming for memory efficiency
        """
        input_files = []
        for line in lines:
            if line.output_path and os.path.exists(line.output_path):
                input_files.append(line.output_path)
        
        return self.concatenate(input_files, output_path, silence_gap, on_progress)


class AudioUtils:
    """Utility functions for audio processing"""
    
    @staticmethod
    def get_duration(file_path: str) -> Optional[float]:
        """Get duration of audio file using ffprobe"""
        try:
            result = subprocess.run(
                [
                    'ffprobe',
                    '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    file_path
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return float(result.stdout.strip())
        except:
            pass
        
        # Fallback using pydub
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(file_path)
            return len(audio) / 1000.0
        except:
            pass
        
        return None
    
    @staticmethod
    def apply_speed(input_path: str, output_path: str, speed: float) -> bool:
        """Apply speed change to audio file"""
        if speed == 1.0:
            return True
        
        try:
            # atempo filter only accepts values between 0.5 and 2.0
            # For values outside this range, chain multiple filters
            filters = []
            remaining_speed = speed
            
            while remaining_speed > 2.0:
                filters.append("atempo=2.0")
                remaining_speed /= 2.0
            while remaining_speed < 0.5:
                filters.append("atempo=0.5")
                remaining_speed *= 2.0
            
            if remaining_speed != 1.0:
                filters.append(f"atempo={remaining_speed}")
            
            filter_str = ",".join(filters)
            
            result = subprocess.run(
                [
                    'ffmpeg',
                    '-y',
                    '-i', input_path,
                    '-af', filter_str,
                    '-c:a', 'libmp3lame',
                    '-q:a', '2',
                    output_path
                ],
                capture_output=True,
                timeout=300
            )
            
            return result.returncode == 0
        except:
            return False
