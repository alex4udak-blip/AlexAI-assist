#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod collector;
mod commands;
mod sync;
mod tray;

use std::sync::Arc;
use tokio::sync::Mutex;
use tokio_util::sync::CancellationToken;

// Maximum number of events to keep in buffer before dropping old events
pub const MAX_BUFFER_SIZE: usize = 10_000;
// Threshold to start warning about buffer filling up (80%)
pub const BUFFER_WARNING_THRESHOLD: usize = 8_000;

pub struct AppState {
    pub collecting: bool,
    pub events_today: u32,
    pub last_sync: String,
    pub events_buffer: Vec<collector::Event>,
    pub buffer_warnings_logged: bool,
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            collecting: true,
            events_today: 0,
            last_sync: "Never".to_string(),
            events_buffer: Vec::new(),
            buffer_warnings_logged: false,
        }
    }
}

fn main() {
    let state = Arc::new(Mutex::new(AppState::default()));
    let shutdown_token = CancellationToken::new();

    // Set up signal handlers for graceful shutdown
    let shutdown_token_clone = shutdown_token.clone();
    tauri::async_runtime::spawn(async move {
        setup_signal_handlers(shutdown_token_clone).await;
    });

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            None,
        ))
        .manage(state.clone())
        .setup(move |app| {
            // Create system tray
            tray::create_tray(app)?;

            // Start collector with shutdown token
            let state_clone = state.clone();
            let app_handle = app.handle().clone();
            let shutdown_token_clone = shutdown_token.clone();
            tauri::async_runtime::spawn(async move {
                collector::start_collector(state_clone, app_handle, shutdown_token_clone).await;
            });

            // Start sync service
            let state_clone = state.clone();
            tauri::async_runtime::spawn(async move {
                sync::start_sync_service(state_clone).await;
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_stats,
            commands::get_detailed_stats,
            commands::toggle_collection,
            commands::sync_now,
            commands::open_dashboard,
            commands::check_permissions,
            commands::request_permissions,
            commands::get_focus,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

/// Set up signal handlers for graceful shutdown (SIGTERM, SIGINT)
async fn setup_signal_handlers(shutdown_token: CancellationToken) {
    #[cfg(unix)]
    {
        use tokio::signal::unix::{signal, SignalKind};

        let mut sigterm = signal(SignalKind::terminate())
            .expect("Failed to create SIGTERM handler");
        let mut sigint = signal(SignalKind::interrupt())
            .expect("Failed to create SIGINT handler");

        tokio::select! {
            _ = sigterm.recv() => {
                println!("Received SIGTERM signal");
                shutdown_token.cancel();
            }
            _ = sigint.recv() => {
                println!("Received SIGINT signal");
                shutdown_token.cancel();
            }
        }
    }

    #[cfg(windows)]
    {
        use tokio::signal;

        tokio::select! {
            _ = signal::ctrl_c() => {
                println!("Received CTRL+C signal");
                shutdown_token.cancel();
            }
        }
    }
}
