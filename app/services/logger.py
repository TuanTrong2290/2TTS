"""Logging system for 2TTS application"""
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler


class AppLogger:
    """Application-wide logging with file output"""
    
    _instance: Optional['AppLogger'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._log_dir = Path.home() / ".2tts" / "logs"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        
        self._log_file = self._log_dir / f"2tts_{datetime.now().strftime('%Y%m%d')}.log"
        
        self._logger = logging.getLogger("2TTS")
        self._logger.setLevel(logging.DEBUG)
        
        if not self._logger.handlers:
            file_handler = RotatingFileHandler(
                self._log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            self._logger.addHandler(file_handler)
            self._logger.addHandler(console_handler)
    
    @property
    def logger(self) -> logging.Logger:
        return self._logger
    
    @property
    def log_file(self) -> Path:
        return self._log_file
    
    @property
    def log_dir(self) -> Path:
        return self._log_dir
    
    def debug(self, message: str):
        self._logger.debug(message)
    
    def info(self, message: str):
        self._logger.info(message)
    
    def warning(self, message: str):
        self._logger.warning(message)
    
    def error(self, message: str, exc_info: bool = False):
        self._logger.error(message, exc_info=exc_info)
    
    def critical(self, message: str, exc_info: bool = True):
        self._logger.critical(message, exc_info=exc_info)
    
    def api_request(self, endpoint: str, status: str, duration_ms: float, details: str = ""):
        self._logger.info(f"API: {endpoint} - {status} ({duration_ms:.0f}ms) {details}")
    
    def tts_request(self, voice_id: str, text_len: int, success: bool, duration_ms: float, error: str = ""):
        status = "SUCCESS" if success else f"FAILED: {error}"
        self._logger.info(f"TTS: voice={voice_id[:8]}... chars={text_len} {status} ({duration_ms:.0f}ms)")
    
    def get_recent_logs(self, lines: int = 100) -> str:
        try:
            with open(self._log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:])
        except:
            return ""
    
    def cleanup_old_logs(self, days: int = 30):
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        for log_file in self._log_dir.glob("2tts_*.log*"):
            if log_file.stat().st_mtime < cutoff:
                try:
                    log_file.unlink()
                except:
                    pass


def get_logger() -> AppLogger:
    return AppLogger()
