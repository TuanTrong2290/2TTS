use parking_lot::Mutex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use tauri::{Emitter, Manager, WindowEvent};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;
use tokio::sync::oneshot;

mod commands;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcRequest {
    jsonrpc: String,
    method: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    params: Option<serde_json::Value>,
    id: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcResponse {
    jsonrpc: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    result: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<JsonRpcError>,
    id: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcError {
    code: i32,
    message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    data: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize)]
pub struct DebugInfo {
    is_dev: bool,
    is_packaged: bool,
    resources_path: String,
    app_path: String,
    user_data_path: String,
    backend_error: Option<String>,
    backend_running: bool,
}

type PendingRequests = Arc<Mutex<HashMap<u64, oneshot::Sender<JsonRpcResponse>>>>;

pub struct BackendState {
    child: Mutex<Option<CommandChild>>,
    pending_requests: PendingRequests,
    request_id: AtomicU64,
    backend_error: Mutex<Option<String>>,
}

impl BackendState {
    pub fn new() -> Self {
        Self {
            child: Mutex::new(None),
            pending_requests: Arc::new(Mutex::new(HashMap::new())),
            request_id: AtomicU64::new(0),
            backend_error: Mutex::new(None),
        }
    }

    pub fn next_id(&self) -> u64 {
        self.request_id.fetch_add(1, Ordering::SeqCst)
    }

    pub fn set_child(&self, child: CommandChild) {
        *self.child.lock() = Some(child);
    }

    pub fn set_error(&self, error: String) {
        *self.backend_error.lock() = Some(error);
    }

    pub fn get_error(&self) -> Option<String> {
        self.backend_error.lock().clone()
    }

    pub fn is_running(&self) -> bool {
        self.child.lock().is_some()
    }

    pub fn write(&self, data: &[u8]) -> Result<(), String> {
        let mut guard = self.child.lock();
        if let Some(ref mut child) = *guard {
            child
                .write(data)
                .map_err(|e| format!("Failed to write to backend: {}", e))
        } else {
            Err("Backend not running".to_string())
        }
    }

    pub fn add_pending(&self, id: u64, sender: oneshot::Sender<JsonRpcResponse>) {
        self.pending_requests.lock().insert(id, sender);
    }

    pub fn resolve_pending(&self, id: u64, response: JsonRpcResponse) {
        if let Some(sender) = self.pending_requests.lock().remove(&id) {
            let _ = sender.send(response);
        }
    }
}

impl Default for BackendState {
    fn default() -> Self {
        Self::new()
    }
}

fn spawn_backend(app: &tauri::AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let state = app.state::<BackendState>();
    let shell = app.shell();

    // Log current directory for debugging
    if let Ok(cwd) = std::env::current_dir() {
        log::info!("Current working directory: {:?}", cwd);
    }

    let sidecar = shell.sidecar("backend").map_err(|e| {
        log::error!("Failed to create sidecar command: {} - Make sure backend-x86_64-pc-windows-msvc.exe exists", e);
        e
    })?;

    let (mut rx, child) = sidecar.spawn().map_err(|e| {
        let error = format!("Failed to spawn backend: {}", e);
        log::error!("{}", error);
        state.set_error(error.clone());
        e
    })?;

    state.set_child(child);
    log::info!("Backend sidecar spawned successfully");

    let app_handle = app.clone();
    let pending = state.pending_requests.clone();

    tauri::async_runtime::spawn(async move {
        let mut buffer = String::new();

        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line_bytes) => {
                    let line = String::from_utf8_lossy(&line_bytes);
                    buffer.push_str(&line);

                    while let Some(newline_pos) = buffer.find('\n') {
                        let json_line = buffer[..newline_pos].trim().to_string();
                        buffer = buffer[newline_pos + 1..].to_string();

                        if json_line.is_empty() {
                            continue;
                        }

                        match serde_json::from_str::<JsonRpcResponse>(&json_line) {
                            Ok(response) => {
                                if let Some(id) = response.id {
                                    if let Some(sender) = pending.lock().remove(&id) {
                                        let _ = sender.send(response);
                                    }
                                } else if let Some(ref result) = response.result {
                                    if let Some(method) = result.get("method").and_then(|m| m.as_str()) {
                                        let _ = app_handle.emit("backend-event", serde_json::json!({
                                            "method": method,
                                            "params": result.get("params")
                                        }));
                                    }
                                }
                            }
                            Err(e) => {
                                log::warn!("Failed to parse backend response: {} - {}", e, json_line);
                            }
                        }
                    }
                }
                CommandEvent::Stderr(line_bytes) => {
                    let line = String::from_utf8_lossy(&line_bytes);
                    log::warn!("Backend stderr: {}", line);
                }
                CommandEvent::Error(error) => {
                    log::error!("Backend error: {}", error);
                }
                CommandEvent::Terminated(payload) => {
                    log::info!("Backend terminated with code: {:?}", payload.code);
                    break;
                }
                _ => {}
            }
        }
    });

    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_focus();
            }
        }))
        .manage(BackendState::new())
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            if let Err(e) = spawn_backend(app.handle()) {
                log::error!("Failed to spawn backend: {}", e);
            }

            let _app_handle = app.handle().clone();
            let state = app.state::<BackendState>();
            let debug_info = DebugInfo {
                is_dev: cfg!(debug_assertions),
                is_packaged: !cfg!(debug_assertions),
                resources_path: app
                    .path()
                    .resource_dir()
                    .map(|p| p.to_string_lossy().to_string())
                    .unwrap_or_default(),
                app_path: app
                    .path()
                    .app_data_dir()
                    .map(|p| p.to_string_lossy().to_string())
                    .unwrap_or_default(),
                user_data_path: app
                    .path()
                    .app_local_data_dir()
                    .map(|p| p.to_string_lossy().to_string())
                    .unwrap_or_default(),
                backend_error: state.get_error(),
                backend_running: state.is_running(),
            };

            if let Some(window) = app.get_webview_window("main") {
                let _ = window.emit("debug-info", debug_info);

                // Listen for drag-drop events and forward to frontend
                let window_clone = window.clone();
                window.on_window_event(move |event| {
                    if let WindowEvent::DragDrop(tauri::DragDropEvent::Drop { paths, .. }) = event {
                        let file_paths: Vec<String> = paths
                            .iter()
                            .map(|p| p.to_string_lossy().to_string())
                            .collect();
                        let _ = window_clone.emit("files-dropped", file_paths);
                    }
                });
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::ipc_call,
            commands::window_minimize,
            commands::window_maximize,
            commands::window_close,
            commands::write_text_file,
            commands::read_text_file,
            commands::open_path,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
