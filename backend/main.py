#!/usr/bin/env python3
"""2TTS Backend - JSON-RPC 2.0 server over stdio"""
import sys
from pathlib import Path

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
