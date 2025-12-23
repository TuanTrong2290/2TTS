"""JSON-RPC 2.0 types and error codes"""
from dataclasses import dataclass
from typing import Any, Optional
from enum import IntEnum


class ErrorCodes(IntEnum):
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # Application-defined errors (-32099 to -32000)
    APP_BACKEND_NOT_READY = -32099
    APP_INVALID_API_KEY = -32098
    APP_RATE_LIMITED = -32097
    APP_JOB_CANCELLED = -32096
    APP_FILE_NOT_FOUND = -32095
    APP_PERMISSION_DENIED = -32094
    APP_TTS_FAILED = -32093


@dataclass
class JsonRpcError(Exception):
    code: int
    message: str
    data: Optional[Any] = None
    
    def to_dict(self) -> dict:
        result = {"code": self.code, "message": self.message}
        if self.data is not None:
            result["data"] = self.data
        return result


def make_response(id: Any, result: Any = None, error: Optional[JsonRpcError] = None) -> dict:
    """Create a JSON-RPC 2.0 response"""
    response = {"jsonrpc": "2.0", "id": id}
    if error:
        response["error"] = error.to_dict()
    else:
        response["result"] = result
    return response


def make_notification(method: str, params: dict) -> dict:
    """Create a JSON-RPC 2.0 notification (no id)"""
    return {"jsonrpc": "2.0", "method": method, "params": params}
