use crate::{BackendState, JsonRpcRequest, JsonRpcResponse, JsonRpcError};
use tauri::{AppHandle, Manager, State};
use tokio::sync::oneshot;
use std::time::Duration;

#[tauri::command]
pub async fn ipc_call(
    request_str: String,
    state: State<'_, BackendState>,
) -> Result<String, String> {
    if !state.is_running() {
        let error = state.get_error().unwrap_or_else(|| "Backend not running".to_string());
        let response = JsonRpcResponse {
            jsonrpc: "2.0".to_string(),
            result: None,
            error: Some(JsonRpcError {
                code: -32603,
                message: error,
                data: None,
            }),
            id: None,
        };
        return Ok(serde_json::to_string(&response).unwrap());
    }

    let request: JsonRpcRequest = serde_json::from_str(&request_str).map_err(|e| {
        let response = JsonRpcResponse {
            jsonrpc: "2.0".to_string(),
            result: None,
            error: Some(JsonRpcError {
                code: -32700,
                message: format!("Parse error: {}", e),
                data: None,
            }),
            id: None,
        };
        serde_json::to_string(&response).unwrap()
    })?;

    let id = request.id;
    let (tx, rx) = oneshot::channel();

    state.add_pending(id, tx);

    let mut request_line = request_str.clone();
    if !request_line.ends_with('\n') {
        request_line.push('\n');
    }

    if let Err(e) = state.write(request_line.as_bytes()) {
        state.pending_requests.lock().remove(&id);
        let response = JsonRpcResponse {
            jsonrpc: "2.0".to_string(),
            result: None,
            error: Some(JsonRpcError {
                code: -32603,
                message: e,
                data: None,
            }),
            id: Some(id),
        };
        return Ok(serde_json::to_string(&response).unwrap());
    }

    match tokio::time::timeout(Duration::from_secs(30), rx).await {
        Ok(Ok(response)) => Ok(serde_json::to_string(&response).unwrap()),
        Ok(Err(_)) => {
            let response = JsonRpcResponse {
                jsonrpc: "2.0".to_string(),
                result: None,
                error: Some(JsonRpcError {
                    code: -32603,
                    message: "Request cancelled".to_string(),
                    data: None,
                }),
                id: Some(id),
            };
            Ok(serde_json::to_string(&response).unwrap())
        }
        Err(_) => {
            state.pending_requests.lock().remove(&id);
            let response = JsonRpcResponse {
                jsonrpc: "2.0".to_string(),
                result: None,
                error: Some(JsonRpcError {
                    code: -32603,
                    message: "Request timeout".to_string(),
                    data: None,
                }),
                id: Some(id),
            };
            Ok(serde_json::to_string(&response).unwrap())
        }
    }
}

#[tauri::command]
pub async fn window_minimize(app: AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("main") {
        window.minimize().map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tauri::command]
pub async fn window_maximize(app: AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("main") {
        if window.is_maximized().unwrap_or(false) {
            window.unmaximize().map_err(|e| e.to_string())?;
        } else {
            window.maximize().map_err(|e| e.to_string())?;
        }
    }
    Ok(())
}

#[tauri::command]
pub async fn window_close(app: AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("main") {
        window.close().map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tauri::command]
pub async fn write_text_file(path: String, contents: String) -> Result<(), String> {
    std::fs::write(&path, contents).map_err(|e| format!("Failed to write file: {}", e))
}

#[tauri::command]
pub async fn read_text_file(path: String) -> Result<String, String> {
    std::fs::read_to_string(&path).map_err(|e| format!("Failed to read file: {}", e))
}

#[tauri::command]
pub async fn open_path(path: String) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        std::process::Command::new("explorer")
            .arg(&path)
            .spawn()
            .map_err(|e| format!("Failed to open path: {}", e))?;
    }
    #[cfg(target_os = "macos")]
    {
        std::process::Command::new("open")
            .arg(&path)
            .spawn()
            .map_err(|e| format!("Failed to open path: {}", e))?;
    }
    #[cfg(target_os = "linux")]
    {
        std::process::Command::new("xdg-open")
            .arg(&path)
            .spawn()
            .map_err(|e| format!("Failed to open path: {}", e))?;
    }
    Ok(())
}
