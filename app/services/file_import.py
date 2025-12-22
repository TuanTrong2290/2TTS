"""File import service for various formats"""
import os
import re
from pathlib import Path
from typing import List, Tuple, Optional
from core.models import TextLine


class FileImporter:
    """Handles importing text from various file formats"""
    
    SUPPORTED_EXTENSIONS = {'.srt', '.txt', '.docx'}
    
    def import_file(self, file_path: str) -> List[TextLine]:
        """Import a single file and return list of TextLines"""
        path = Path(file_path)
        ext = path.suffix.lower()
        
        if ext == '.srt':
            return self._import_srt(file_path)
        elif ext == '.txt':
            return self._import_txt(file_path)
        elif ext == '.docx':
            return self._import_docx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    def import_folder(self, folder_path: str) -> Tuple[List[TextLine], List[str]]:
        """Import all supported files from a folder recursively
        Returns: (lines, error_messages)
        """
        lines = []
        errors = []
        folder = Path(folder_path)
        
        for file_path in folder.rglob('*'):
            if file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                try:
                    file_lines = self.import_file(str(file_path))
                    lines.extend(file_lines)
                except Exception as e:
                    errors.append(f"{file_path.name}: {str(e)}")
        
        return lines, errors
    
    def _import_srt(self, file_path: str) -> List[TextLine]:
        """Import SRT subtitle file"""
        lines = []
        
        try:
            import pysrt
            subs = pysrt.open(file_path, encoding='utf-8')
            
            for i, sub in enumerate(subs):
                start_seconds = (sub.start.hours * 3600 + 
                               sub.start.minutes * 60 + 
                               sub.start.seconds + 
                               sub.start.milliseconds / 1000)
                end_seconds = (sub.end.hours * 3600 + 
                             sub.end.minutes * 60 + 
                             sub.end.seconds + 
                             sub.end.milliseconds / 1000)
                
                text = sub.text.replace('\n', ' ').strip()
                if text:
                    line = TextLine(
                        index=i,
                        text=text,
                        original_text=text,
                        source_file=os.path.basename(file_path),
                        start_time=start_seconds,
                        end_time=end_seconds
                    )
                    lines.append(line)
        except ImportError:
            # Fallback parser if pysrt not available
            lines = self._parse_srt_manual(file_path)
        
        return lines
    
    def _parse_srt_manual(self, file_path: str) -> List[TextLine]:
        """Manual SRT parser as fallback"""
        lines = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # SRT pattern: index, timestamp, text
        pattern = r'(\d+)\s*\n(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\s*\n((?:(?!\d+\s*\n\d{2}:\d{2}:\d{2}).)+)'
        matches = re.findall(pattern, content, re.MULTILINE)
        
        for i, match in enumerate(matches):
            index, start, end, text = match
            start_seconds = self._parse_srt_time(start)
            end_seconds = self._parse_srt_time(end)
            text = text.strip().replace('\n', ' ')
            
            if text:
                line = TextLine(
                    index=i,
                    text=text,
                    original_text=text,
                    source_file=os.path.basename(file_path),
                    start_time=start_seconds,
                    end_time=end_seconds
                )
                lines.append(line)
        
        return lines
    
    def _parse_srt_time(self, time_str: str) -> float:
        """Parse SRT timestamp to seconds"""
        hours, minutes, seconds = time_str.replace(',', '.').split(':')
        return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
    
    def _import_txt(self, file_path: str) -> List[TextLine]:
        """Import plain text file, one line per entry"""
        lines = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line_text in enumerate(f):
                text = line_text.strip()
                if text:
                    line = TextLine(
                        index=i,
                        text=text,
                        original_text=text,
                        source_file=os.path.basename(file_path)
                    )
                    lines.append(line)
        
        return lines
    
    def _import_docx(self, file_path: str) -> List[TextLine]:
        """Import DOCX file, one paragraph per entry"""
        lines = []
        
        try:
            from docx import Document
            doc = Document(file_path)
            
            for i, para in enumerate(doc.paragraphs):
                text = para.text.strip()
                if text:
                    line = TextLine(
                        index=i,
                        text=text,
                        original_text=text,
                        source_file=os.path.basename(file_path)
                    )
                    lines.append(line)
        except ImportError:
            raise ImportError("python-docx is required for DOCX import. Install with: pip install python-docx")
        
        return lines
    
    @staticmethod
    def is_supported(file_path: str) -> bool:
        """Check if a file format is supported"""
        return Path(file_path).suffix.lower() in FileImporter.SUPPORTED_EXTENSIONS


class TextSplitter:
    """Handles splitting long text into smaller chunks"""
    
    def __init__(self, max_chars: int = 5000, delimiters: str = ".,?!;"):
        self.max_chars = max_chars
        self.delimiters = delimiters
    
    def split_text(self, text: str) -> List[str]:
        """Split text if it exceeds max_chars"""
        if len(text) <= self.max_chars:
            return [text]
        
        chunks = []
        remaining = text
        
        while len(remaining) > self.max_chars:
            # Find split point
            split_pos = self._find_split_position(remaining)
            chunk = remaining[:split_pos].strip()
            if chunk:
                chunks.append(chunk)
            remaining = remaining[split_pos:].strip()
        
        if remaining:
            chunks.append(remaining)
        
        return chunks
    
    def _find_split_position(self, text: str) -> int:
        """Find the best position to split text"""
        search_text = text[:self.max_chars]
        
        # Try to split at punctuation
        best_pos = -1
        for delimiter in self.delimiters:
            pos = search_text.rfind(delimiter)
            if pos > best_pos:
                best_pos = pos + 1  # Include the delimiter
        
        if best_pos > 0:
            return best_pos
        
        # Fall back to splitting at space
        space_pos = search_text.rfind(' ')
        if space_pos > 0:
            return space_pos
        
        # Last resort: hard split
        return self.max_chars
    
    def split_lines(self, lines: List[TextLine]) -> List[TextLine]:
        """Split all lines that exceed max_chars"""
        result = []
        
        for line in lines:
            if len(line.text) <= self.max_chars:
                result.append(line)
            else:
                chunks = self.split_text(line.text)
                for i, chunk in enumerate(chunks):
                    new_line = TextLine(
                        index=len(result),
                        text=chunk,
                        original_text=line.original_text,
                        source_file=line.source_file,
                        voice_id=line.voice_id,
                        voice_name=line.voice_name,
                        detected_language=line.detected_language
                    )
                    result.append(new_line)
        
        # Re-index
        for i, line in enumerate(result):
            line.index = i
        
        return result
