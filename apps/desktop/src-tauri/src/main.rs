#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod collector;
mod commands;
mod sync;
mod tray;

use std::sync::Arc;
use tauri::Manager;
use tokio::sync::Mutex;

pub struct AppState {
    pub collecting: bool,
    pub events_today: u32,
    pub last_sync: String,
    pub events_buffer: Vec<collector::Event>,
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            collecting: true,
            events_today: 0,
            last_sync: "Never".to_string(),
            events_buffer: Vec::new(),
        }
    }
}

fn main() {
    let state = Arc::new(Mutex::new(AppState::default()));

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            None,
        ))
        .manage(state.clone())
        .setup(|app| {
            // Create system tray
            tray::create_tray(app)?;

            // Start collector
            let state_clone = state.clone();
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                collector::start_collector(state_clone, app_handle).await;
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
