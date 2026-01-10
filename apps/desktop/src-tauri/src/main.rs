#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod automation;
mod collector;
mod commands;
mod db;
mod notifications;
mod permissions;
mod sync;
mod tray;
mod updater;

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
    pub db: Arc<db::EventDatabase>,
    /// Cached top apps - persists across syncs (updated when events are collected)
    pub top_apps_cache: std::collections::HashMap<String, u32>,
}

fn main() {
    // Initialize database
    let db = Arc::new(
        db::EventDatabase::new()
            .expect("Failed to initialize event database")
    );

    // Load existing events from database
    let existing_events = db.load_all_events()
        .unwrap_or_else(|e| {
            eprintln!("Warning: Failed to load events from database: {}", e);
            Vec::new()
        });

    let events_count = existing_events.len();
    if events_count > 0 {
        println!("Loaded {} existing events from database", events_count);
    }

    // Build initial top_apps_cache from existing events
    let mut initial_top_apps: std::collections::HashMap<String, u32> = std::collections::HashMap::new();
    for event in &existing_events {
        if let Some(app_name) = &event.app_name {
            *initial_top_apps.entry(app_name.clone()).or_insert(0) += 1;
        }
    }

    // Create app state with database
    let state = Arc::new(Mutex::new(AppState {
        collecting: true,
        events_today: existing_events.len() as u32,
        last_sync: "Never".to_string(),
        events_buffer: existing_events,
        buffer_warnings_logged: false,
        db: db.clone(),
        top_apps_cache: initial_top_apps,
    }));
    let shutdown_token = CancellationToken::new();

    // Create automation queue
    let (automation_queue, mut result_rx) = automation::queue::AutomationQueue::new();
    let automation_queue = Arc::new(automation_queue);

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
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .manage(state.clone())
        .manage(automation_queue.clone())
        .setup(move |app| {
            // Create system tray
            tray::create_tray(app)?;

            // Check for updates in background
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                updater::check_for_updates(app_handle).await;
            });

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

            // Start automation queue processor
            let queue_clone = automation_queue.clone();
            tauri::async_runtime::spawn(async move {
                queue_clone.process().await;
            });

            // Create WebSocket automation sync
            let ws_url = automation::sync::get_websocket_url();
            let sync = Arc::new(automation::sync::AutomationSync::new(
                ws_url,
                automation_queue.clone(),
            ));

            // Handle automation task results
            let app_handle = app.handle().clone();
            let sync_for_results = sync.clone();
            tauri::async_runtime::spawn(async move {
                while let Some(result) = result_rx.recv().await {
                    println!("Task {} completed: {}", result.task_id, result.success);
                    if let Some(error) = &result.error {
                        eprintln!("Task error: {}", error);
                        // Send notification
                        let _ = notifications::notify_error(&app_handle, error);
                    }

                    // Send result back to server via WebSocket
                    if let Err(e) = sync_for_results.send_result(result).await {
                        eprintln!("Failed to send result to server: {}", e);
                    }
                }
            });

            // Start WebSocket automation sync
            tauri::async_runtime::spawn(async move {
                sync.start().await;
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_stats,
            commands::get_detailed_stats,
            commands::toggle_collection,
            commands::sync_now,
            commands::open_dashboard,
            commands::open_settings,
            commands::check_permissions,
            commands::request_permissions,
            commands::get_focus,
            commands::set_window_visible,
            // Automation commands
            commands::check_all_permissions,
            commands::request_permission,
            commands::open_permission_settings,
            commands::automation_click,
            commands::automation_type,
            commands::automation_hotkey,
            commands::automation_screenshot,
            commands::automation_screenshot_jpeg,
            commands::automation_get_monitors,
            commands::automation_ocr,
            commands::automation_browser_url,
            commands::automation_browser_navigate,
            commands::automation_detect_browser,
            commands::queue_add_task,
            commands::queue_status,
            commands::queue_pause,
            commands::queue_resume,
            commands::queue_clear,
            // Settings commands
            commands::get_settings,
            commands::save_settings,
            commands::open_system_preferences,
            // Debug commands
            commands::get_debug_info,
            commands::check_updates,
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            match event {
                // Handle dock icon click on macOS (applicationShouldHandleReopen)
                tauri::RunEvent::Reopen { .. } => {
                    println!("Dock icon clicked - showing main window");
                    if let Some(window) = app_handle.get_webview_window("main") {
                        let _ = window.show();
                        let _ = window.set_focus();
                        tray::set_window_visible(true);
                    }
                }
                tauri::RunEvent::ExitRequested { api, .. } => {
                    // Prevent exit, just hide window (tray app behavior)
                    api.prevent_exit();
                }
                _ => {}
            }
        });
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
