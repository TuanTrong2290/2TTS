"""JSON-RPC 2.0 server over stdio"""
import sys
import json
import threading
from typing import Callable, Any, Optional, Dict
from .types import JsonRpcError, ErrorCodes, make_response, make_notification


Handler = Callable[..., Any]


class JsonRpcServer:
    def __init__(self):
        self._handlers: Dict[str, Handler] = {}
        self._running = False
        self._write_lock = threading.Lock()
    
    def register(self, method: str, handler: Handler):
        """Register a handler for a method"""
        self._handlers[method] = handler
    
    def method(self, name: str):
        """Decorator to register a method handler"""
        def decorator(func: Handler):
            self.register(name, func)
            return func
        return decorator
    
    def send_notification(self, method: str, params: dict):
        """Send a notification to the frontend"""
        notification = make_notification(method, params)
        self._write_line(json.dumps(notification))
    
    def send_progress(self, job_id: str, percent: float, message: str):
        """Send a progress update"""
        self.send_notification("event.progress", {
            "job_id": job_id,
            "percent": percent,
            "message": message
        })
    
    def _write_line(self, line: str):
        """Write a line to stdout (thread-safe)"""
        with self._write_lock:
            sys.stdout.write(line + "\n")
            sys.stdout.flush()
    
    def _handle_request(self, request: dict) -> Optional[dict]:
        """Handle a single JSON-RPC request"""
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})
        
        if not method:
            if request_id is not None:
                return make_response(
                    request_id,
                    error=JsonRpcError(ErrorCodes.INVALID_REQUEST, "Method is required")
                )
            return None
        
        handler = self._handlers.get(method)
        if not handler:
            if request_id is not None:
                return make_response(
                    request_id,
                    error=JsonRpcError(ErrorCodes.METHOD_NOT_FOUND, f"Method not found: {method}")
                )
            return None
        
        try:
            result = handler(params, self)
            
            if request_id is not None:
                return make_response(request_id, result=result)
            return None
            
        except JsonRpcError as e:
            if request_id is not None:
                return make_response(request_id, error=e)
            return None
            
        except Exception as e:
            if request_id is not None:
                return make_response(
                    request_id,
                    error=JsonRpcError(ErrorCodes.INTERNAL_ERROR, str(e))
                )
            return None
    
    def run(self):
        """Run the server, reading from stdin"""
        self._running = True
        
        while self._running:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    request = json.loads(line)
                except json.JSONDecodeError as e:
                    response = make_response(
                        None,
                        error=JsonRpcError(ErrorCodes.PARSE_ERROR, f"Parse error: {e}")
                    )
                    self._write_line(json.dumps(response))
                    continue
                
                response = self._handle_request(request)
                if response:
                    self._write_line(json.dumps(response))
                    
            except Exception as e:
                sys.stderr.write(f"Server error: {e}\n")
                sys.stderr.flush()
    
    def shutdown(self):
        """Shutdown the server"""
        self._running = False
