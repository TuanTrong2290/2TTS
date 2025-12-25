#!/usr/bin/env python3
"""2TTS Backend - JSON-RPC 2.0 server over stdio"""
import sys
import io
from pathlib import Path

# Force UTF-8 encoding for stdin/stdout on Windows BEFORE any other imports
# This fixes Vietnamese and other non-ASCII text encoding issues
if sys.platform == 'win32':
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', newline='\n')

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from ipc.server import JsonRpcServer
from ipc.handlers import register_handlers


def main():
    server = JsonRpcServer()
    register_handlers(server)
    server.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
