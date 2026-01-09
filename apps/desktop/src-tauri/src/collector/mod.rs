mod accessibility;
mod apps;
mod browser;
mod messenger;
#[allow(dead_code)]
mod screenshots;

pub use accessibility::macos::*;
// Only export types that are actually used in Event struct
pub use browser::BrowserTab;
pub use messenger::Message;

use crate::AppState;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tauri::AppHandle;
use tokio::sync::Mutex;
use tokio_util::sync::CancellationToken;
use uuid::Uuid;

/// Focus information including app, window, and optional selected text
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FocusInfo {
    pub app_name: String,
    pub window_title: String,
    pub selected_text: Option<String>,
    pub url: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Event {
    pub id: String,
    pub device_id: String,
    pub event_type: String,
    pub timestamp: DateTime<Utc>,
    pub app_name: Option<String>,
    pub window_title: Option<String>,
    pub url: Option<String>,
    pub data: serde_json::Value,
    pub category: Option<String>,
    // Full monitoring fields
    pub browser_tab: Option<BrowserTab>,
    pub messages: Option<Vec<Message>>,
    pub screenshot_path: Option<String>,
}

impl Event {
    pub fn new(
        event_type: &str,
        app_name: Option<String>,
        window_title: Option<String>,
    ) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            device_id: get_device_id(),
            event_type: event_type.to_string(),
            timestamp: Utc::now(),
            app_name,
            window_title,
            url: None,
            data: serde_json::json!({}),
            category: None,
            browser_tab: None,
            messages: None,
            screenshot_path: None,
        }
    }

    pub fn with_category(mut self, category: &str) -> Self {
        self.category = Some(category.to_string());
        self
    }
}

fn get_device_id() -> String {
    // Get or create a persistent device ID
    let config_dir = dirs::config_dir()
        .unwrap_or_else(|| std::path::PathBuf::from("."))
        .join("observer");

    std::fs::create_dir_all(&config_dir).ok();

    let id_file = config_dir.join("device_id");

    if let Ok(id) = std::fs::read_to_string(&id_file) {
        return id.trim().to_string();
    }

    let new_id = Uuid::new_v4().to_string();
    std::fs::write(&id_file, &new_id).ok();
    new_id
}

/// Get the currently focused application and window information
pub fn get_current_focus() -> Option<FocusInfo> {
    // First try accessibility API for detailed info
    if has_accessibility_permission() {
        if let Some((app_name, window_title)) = get_focused_element_info() {
            let selected_text = get_selected_text();
            let url = get_browser_url();

            return Some(FocusInfo {
                app_name,
                window_title,
                selected_text,
                url,
            });
        }
    }

    // Fallback to basic window info
    let (app_name, window_title) = apps::get_active_window();
    if let Some(app) = app_name {
        return Some(FocusInfo {
            app_name: app,
            window_title: window_title.unwrap_or_default(),
            selected_text: None,
            url: None,
        });
    }

    None
}

pub async fn start_collector(
    state: Arc<Mutex<AppState>>,
    _app_handle: AppHandle,
    shutdown_token: CancellationToken,
) {
    let mut last_app: Option<String> = None;
    let mut last_title: Option<String> = None;

    // Check accessibility permission on start
    if !has_accessibility_permission() {
        eprintln!("Warning: Accessibility permission not granted. Some features will be limited.");
    }

    println!("Collector started. Waiting for events...");

    loop {
        // Use select! to handle both the polling and shutdown signal
        tokio::select! {
            _ = shutdown_token.cancelled() => {
                println!("Shutdown signal received. Flushing events and cleaning up...");
                flush_events(&state).await;
                println!("Collector shutdown complete.");
                break;
            }
            _ = tokio::time::sleep(tokio::time::Duration::from_millis(500)) => {
                // Check if collection is enabled
                {
                    let state = state.lock().await;
                    if !state.collecting {
                        continue;
                    }
                }

                // Get current focus using accessibility API when available
                let focus_info = get_current_focus();

                let (current_app, current_title) = if let Some(ref info) = focus_info {
                    (Some(info.app_name.clone()), Some(info.window_title.clone()))
                } else {
                    // Fallback to basic window info
                    apps::get_active_window()
                };

                // Check if there's a change
                if current_app != last_app || current_title != last_title {
                    if let Some(app_name) = &current_app {
                        let mut event = Event::new(
                            "app_focus",
                            current_app.clone(),
                            current_title.clone(),
                        )
                        .with_category(categorize_app(app_name));

                        // Add URL if available from accessibility API
                        if let Some(ref info) = focus_info {
                            event.url = info.url.clone();

                            // Add selected text to event data if available
                            if let Some(ref selected) = info.selected_text {
                                if !selected.is_empty() {
                                    event.data = serde_json::json!({
                                        "selected_text": selected
                                    });
                                }
                            }
                        }

                        // Add to buffer with bounds checking
                        let mut state = state.lock().await;

                        let buffer_size = state.events_buffer.len();

                        // Check if buffer is full
                        if buffer_size >= crate::MAX_BUFFER_SIZE {
                            // Drop oldest event to make room for new one
                            state.events_buffer.remove(0);
                            eprintln!(
                                "Warning: Event buffer full ({} events). Dropping oldest event.",
                                crate::MAX_BUFFER_SIZE
                            );
                        }

                        // Log warning if buffer is filling up (only once per session until it drains)
                        if buffer_size >= crate::BUFFER_WARNING_THRESHOLD && !state.buffer_warnings_logged {
                            eprintln!(
                                "Warning: Event buffer is {}% full ({}/{} events). Events may be lost if sync continues to fail.",
                                (buffer_size * 100) / crate::MAX_BUFFER_SIZE,
                                buffer_size,
                                crate::MAX_BUFFER_SIZE
                            );
                            state.buffer_warnings_logged = true;
                        }

                        // Reset warning flag if buffer has drained significantly
                        if buffer_size < crate::BUFFER_WARNING_THRESHOLD / 2 {
                            state.buffer_warnings_logged = false;
                        }

                        state.events_buffer.push(event);
                        state.events_today += 1;
                    }

                    last_app = current_app;
                    last_title = current_title;
                }
            }
        }
    }
}

/// Flush all remaining events in the buffer
async fn flush_events(state: &Arc<Mutex<AppState>>) {
    let state = state.lock().await;
    let event_count = state.events_buffer.len();

    if event_count > 0 {
        println!("Flushing {} remaining events...", event_count);
        // Events will be flushed by the periodic sync task or app shutdown
        // This ensures we log the intention to flush
    }
}

fn categorize_app(app_name: &str) -> &'static str {
    let app_lower = app_name.to_lowercase();

    if app_lower.contains("code")
        || app_lower.contains("xcode")
        || app_lower.contains("terminal")
        || app_lower.contains("iterm")
    {
        return "coding";
    }

    if app_lower.contains("chrome")
        || app_lower.contains("safari")
        || app_lower.contains("firefox")
        || app_lower.contains("edge")
    {
        return "browsing";
    }

    if app_lower.contains("slack")
        || app_lower.contains("discord")
        || app_lower.contains("teams")
        || app_lower.contains("zoom")
    {
        return "communication";
    }

    if app_lower.contains("word")
        || app_lower.contains("pages")
        || app_lower.contains("notion")
        || app_lower.contains("obsidian")
    {
        return "writing";
    }

    if app_lower.contains("figma")
        || app_lower.contains("sketch")
        || app_lower.contains("photoshop")
    {
        return "design";
    }

    "other"
}
