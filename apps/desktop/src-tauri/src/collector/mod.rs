mod accessibility;
mod apps;
mod browser;
mod messenger;
mod screenshots;
mod system_metrics;

pub use accessibility::macos::*;
pub use browser::BrowserTab;
pub use messenger::Message;
pub use screenshots::{ScreenshotConfig, ScreenshotManager};
pub use system_metrics::{SystemMetrics, SystemMetricsCollector};

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
    // System metrics
    pub system_metrics: Option<SystemMetrics>,
    // Browser input capture (text being typed)
    pub typed_text: Option<String>,
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
            system_metrics: None,
            typed_text: None,
        }
    }

    pub fn with_category(mut self, category: &str) -> Self {
        self.category = Some(category.to_string());
        self
    }
}

fn get_device_id() -> String {
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

/// Check if app is a browser
fn is_browser(app_name: &str) -> bool {
    let app_lower = app_name.to_lowercase();
    app_lower.contains("chrome")
        || app_lower.contains("safari")
        || app_lower.contains("firefox")
        || app_lower.contains("edge")
        || app_lower.contains("arc")
        || app_lower.contains("brave")
        || app_lower.contains("opera")
        || app_lower.contains("vivaldi")
}

/// Get the currently focused application and window information
pub fn get_current_focus() -> Option<FocusInfo> {
    // First try accessibility API for detailed info
    if has_accessibility_permission() {
        if let Some((app_name, mut window_title)) = get_focused_element_info() {
            // If window_title is empty, try AppleScript fallback (works better for Terminal)
            if window_title.is_empty() {
                if let (_, Some(title)) = apps::get_active_window() {
                    window_title = title;
                }
            }

            let selected_text = get_selected_text();

            // For Terminal/iTerm, try to get terminal content (uses different approach than text fields)
            let app_lower = app_name.to_lowercase();
            let is_terminal = app_lower.contains("terminal")
                || app_lower.contains("терминал")
                || app_lower.contains("iterm");

            let text_field_value = if is_terminal {
                println!("[Terminal] Trying to get content from: {}", app_name);
                let content = get_terminal_content();
                if let Some(ref text) = content {
                    println!("[Terminal] Got content: {} chars", text.len());
                } else {
                    println!("[Terminal] No content available");
                }
                content
            } else {
                get_focused_text_field_value()
            };

            // Combine selected_text and text_field_value
            let combined_text = match (selected_text, text_field_value) {
                (Some(sel), Some(val)) => Some(format!("{}\n{}", sel, val)),
                (Some(sel), None) => Some(sel),
                (None, Some(val)) => Some(val),
                (None, None) => None,
            };

            // Get URL using AppleScript for browsers
            let url = if is_browser(&app_name) {
                let browser_monitor = browser::BrowserMonitor::new();
                browser_monitor.get_active_tab(&app_name).map(|tab| {
                    println!("[Browser] {} | {}", app_name, tab.url);
                    tab.url
                })
            } else {
                None
            };

            return Some(FocusInfo {
                app_name,
                window_title,
                selected_text: combined_text,
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
    agent_state: Arc<Mutex<crate::AgentState>>,
    app_handle: AppHandle,
    shutdown_token: CancellationToken,
) {
    let mut last_app: Option<String> = None;
    let mut last_title: Option<String> = None;
    let mut last_typed_text: Option<String> = None;
    // Shared OCR text from background processing
    let last_ocr_text: Arc<std::sync::Mutex<Option<String>>> = Arc::new(std::sync::Mutex::new(None));

    // Initialize collectors
    let metrics_collector = SystemMetricsCollector::new();
    let mut screenshot_manager = ScreenshotManager::new(ScreenshotConfig::default());
    let messenger_monitor = messenger::MessengerMonitor::new();
    let browser_monitor = browser::BrowserMonitor::new();

    println!("[Collector] Initialized: ScreenshotManager, MessengerMonitor, BrowserMonitor, AgentManager, AsyncOCR");

    // Request permissions on start
    #[cfg(target_os = "macos")]
    {
        use crate::automation::{request_accessibility, request_screen_recording};

        if !has_accessibility_permission() {
            println!("[Permissions] Requesting accessibility permission...");
            let granted = request_accessibility();
            if granted {
                println!("[Permissions] Accessibility permission granted!");
            } else {
                eprintln!("[Permissions] Warning: Accessibility permission not granted.");
            }
        }

        // Also request screen recording permission
        request_screen_recording();
    }

    println!("[Collector] Started. Waiting for events...");

    loop {
        tokio::select! {
            _ = shutdown_token.cancelled() => {
                println!("[Collector] Shutdown signal received. Flushing events...");
                flush_events(&state).await;
                println!("[Collector] Shutdown complete.");
                break;
            }
            _ = tokio::time::sleep(tokio::time::Duration::from_millis(500)) => {
                println!("[Loop] Tick - checking focus...");

                // Check if collection is enabled
                {
                    let state = state.lock().await;
                    if !state.collecting {
                        continue;
                    }
                }

                // Get current focus
                let focus_info = get_current_focus();

                let (current_app, current_title) = if let Some(ref info) = focus_info {
                    (Some(info.app_name.clone()), Some(info.window_title.clone()))
                } else {
                    apps::get_active_window()
                };

                // Check if there's a change
                if current_app != last_app || current_title != last_title {
                    if let Some(ref app_name) = current_app {
                        let window_title = current_title.clone().unwrap_or_default();

                        // === DEBUG LOG: Focus Change ===
                        println!("[Focus] {} | {}", app_name, window_title);

                        let mut event = Event::new(
                            "app_focus",
                            current_app.clone(),
                            current_title.clone(),
                        )
                        .with_category(categorize_app(app_name));

                        // === SYSTEM METRICS ===
                        if let Ok(metrics) = metrics_collector.collect() {
                            event.system_metrics = Some(metrics);
                        }

                        // === BROWSER URL ===
                        if is_browser(app_name) {
                            if let Some(tab) = browser_monitor.get_active_tab(app_name) {
                                println!("[Browser] {} | {}", app_name, tab.url);
                                event.url = Some(tab.url.clone());
                                event.browser_tab = Some(tab);
                            }
                        }

                        // Add URL from focus_info if not already set
                        if event.url.is_none() {
                            if let Some(ref info) = focus_info {
                                event.url = info.url.clone();
                            }
                        }

                        // Add selected text to event data
                        if let Some(ref info) = focus_info {
                            if let Some(ref selected) = info.selected_text {
                                if !selected.is_empty() {
                                    event.data = serde_json::json!({
                                        "selected_text": selected
                                    });
                                }
                            }
                        }

                        // === SCREENSHOT CAPTURE ===
                        if let Some(screenshot) = screenshot_manager.maybe_capture(
                            app_name.clone(),
                            window_title.clone(),
                        ).await {
                            let path_str = screenshot.path.to_string_lossy().to_string();
                            println!("[Screenshot] Saved: {}", path_str);
                            event.screenshot_path = Some(path_str.clone());

                            // === SYNC OCR - wait for result to be available for Meta Agent ===
                            #[cfg(target_os = "macos")]
                            {
                                let ocr_path = path_str.clone();
                                let ocr_text_clone = last_ocr_text.clone();

                                // Run OCR in blocking thread pool and await result
                                // This ensures OCR data is available for trigger checking
                                let ocr_handle = tokio::task::spawn_blocking(move || {
                                    crate::automation::ocr::extract_text_from_path(&ocr_path)
                                });

                                match ocr_handle.await {
                                    Ok(Ok(ocr_result)) => {
                                        println!("[OCR] Extracted {} chars", ocr_result.text.len());
                                        if let Ok(mut guard) = ocr_text_clone.lock() {
                                            *guard = Some(ocr_result.text);
                                        }
                                    }
                                    Ok(Err(e)) => {
                                        eprintln!("[OCR] Error: {}", e);
                                    }
                                    Err(e) => {
                                        eprintln!("[OCR] Task join error: {}", e);
                                    }
                                }
                            }
                        }

                        // === MESSENGER MESSAGES ===
                        if messenger_monitor.is_messenger(app_name) {
                            if let Some(msg_state) = messenger_monitor.get_visible_messages(app_name) {
                                let msg_count = msg_state.visible_messages.len();
                                if msg_count > 0 {
                                    println!("[Messenger] {} messages from {}", msg_count, app_name);
                                    event.messages = Some(msg_state.visible_messages);

                                    // Store chat name in data
                                    if let Some(chat) = msg_state.active_chat {
                                        if let serde_json::Value::Object(ref mut map) = event.data {
                                            map.insert("chat_name".to_string(), serde_json::json!(chat));
                                        }
                                    }
                                }
                            }
                        }

                        // === BROWSER INPUT ===
                        if is_browser(app_name) {
                            if let Some((url, typed_text)) = get_browser_input() {
                                if Some(&typed_text) != last_typed_text.as_ref() {
                                    event.typed_text = Some(typed_text.clone());
                                    if url.is_some() && event.url.is_none() {
                                        event.url = url;
                                    }
                                    last_typed_text = Some(typed_text);
                                }
                            } else {
                                last_typed_text = None;
                            }
                        } else {
                            last_typed_text = None;
                        }

                        // === SAVE TO DATABASE AND BUFFER ===
                        let mut state = state.lock().await;

                        let buffer_size = state.events_buffer.len();

                        // Check buffer capacity
                        if buffer_size >= crate::MAX_BUFFER_SIZE {
                            state.events_buffer.remove(0);
                            eprintln!("[Buffer] Warning: Full ({} events). Dropping oldest.", crate::MAX_BUFFER_SIZE);
                        }

                        if buffer_size >= crate::BUFFER_WARNING_THRESHOLD && !state.buffer_warnings_logged {
                            eprintln!(
                                "[Buffer] Warning: {}% full ({}/{} events)",
                                (buffer_size * 100) / crate::MAX_BUFFER_SIZE,
                                buffer_size,
                                crate::MAX_BUFFER_SIZE
                            );
                            state.buffer_warnings_logged = true;
                        }

                        if buffer_size < crate::BUFFER_WARNING_THRESHOLD / 2 {
                            state.buffer_warnings_logged = false;
                        }

                        // Persist to database
                        match state.db.insert_event(&event) {
                            Ok(_) => {
                                println!("[DB] Event saved: {} | {} | {}",
                                    event.id,
                                    event.app_name.as_deref().unwrap_or("?"),
                                    event.url.as_deref().unwrap_or("-")
                                );
                            }
                            Err(e) => {
                                eprintln!("[DB] Error: Failed to save event: {}", e);
                            }
                        }

                        // Update top_apps_cache
                        if let Some(ref app_name) = event.app_name {
                            *state.top_apps_cache.entry(app_name.clone()).or_insert(0) += 1;
                        }

                        state.events_buffer.push(event);
                        state.events_today += 1;
                    }

                    // Record activity on focus change (actual user activity)
                    {
                        let mut agent = agent_state.lock().await;
                        if agent.enabled {
                            agent.manager.record_activity();
                        }
                    }

                    last_app = current_app.clone();
                    last_title = current_title.clone();
                } else {
                    // No focus change, but check for browser input changes
                    if let Some(ref app_name) = current_app {
                        if is_browser(app_name) {
                            if let Some((url, typed_text)) = get_browser_input() {
                                if Some(&typed_text) != last_typed_text.as_ref() && !typed_text.is_empty() {
                                    println!("[BrowserInput] {} | {}", app_name, typed_text);

                                    let mut event = Event::new(
                                        "browser_input",
                                        current_app.clone(),
                                        current_title.clone(),
                                    )
                                    .with_category("browsing");

                                    if let Ok(metrics) = metrics_collector.collect() {
                                        event.system_metrics = Some(metrics);
                                    }

                                    event.typed_text = Some(typed_text.clone());
                                    event.url = url;
                                    last_typed_text = Some(typed_text);

                                    let mut state = state.lock().await;

                                    let buffer_size = state.events_buffer.len();

                                    if buffer_size >= crate::MAX_BUFFER_SIZE {
                                        state.events_buffer.remove(0);
                                    }

                                    match state.db.insert_event(&event) {
                                        Ok(_) => println!("[DB] Browser input saved: {}", event.id),
                                        Err(e) => eprintln!("[DB] Error: {}", e),
                                    }

                                    if let Some(ref app_name) = event.app_name {
                                        *state.top_apps_cache.entry(app_name.clone()).or_insert(0) += 1;
                                    }

                                    state.events_buffer.push(event);
                                    state.events_today += 1;
                                }
                            } else if last_typed_text.is_some() {
                                last_typed_text = None;
                            }
                        }
                    }
                }

                // === AGENT TRIGGER CHECK ===
                // Runs on EVERY tick (500ms), not just on focus change
                // This allows idle trigger and continuous monitoring to work
                {
                    let mut agent = agent_state.lock().await;
                    // Debug: log agent state periodically
                    static AGENT_STATE_LOG: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
                    let now_secs = std::time::SystemTime::now()
                        .duration_since(std::time::UNIX_EPOCH)
                        .unwrap_or_default()
                        .as_secs();
                    let last_state_log = AGENT_STATE_LOG.load(std::sync::atomic::Ordering::Relaxed);
                    if now_secs - last_state_log >= 30 {
                        AGENT_STATE_LOG.store(now_secs, std::sync::atomic::Ordering::Relaxed);
                        println!("[Agent] Статус: enabled={}, status={:?}",
                            agent.enabled, agent.manager.status());
                    }

                    if agent.enabled {
                        // Skip if agent is already running (debounce)
                        if agent.manager.status() == crate::agents::AgentStatus::Running {
                            // Silent skip - don't spam logs
                        } else {
                            // Build trigger_text from ALL available sources:
                            // 1. Window title (always available)
                            // 2. Selected text (when user selects something)
                            // 3. Typed text (browser input)
                            // 4. OCR text (from background processing)
                            let mut text_parts: Vec<String> = Vec::new();

                            // Add window title
                            if let Some(ref title) = current_title {
                                if !title.is_empty() {
                                    text_parts.push(title.clone());
                                }
                            }

                            // Add selected text
                            if let Some(ref info) = focus_info {
                                if let Some(ref selected) = info.selected_text {
                                    if !selected.is_empty() {
                                        text_parts.push(selected.clone());
                                    }
                                }
                            }

                            // Add typed text (browser input)
                            if let Some(ref typed) = last_typed_text {
                                if !typed.is_empty() {
                                    text_parts.push(typed.clone());
                                }
                            }

                            // Add OCR text (from async background processing)
                            if let Ok(guard) = last_ocr_text.lock() {
                                if let Some(ref ocr) = *guard {
                                    if !ocr.is_empty() {
                                        text_parts.push(ocr.clone());
                                    }
                                }
                            }

                            let trigger_text = text_parts.join("\n");
                            let app = current_app.clone().unwrap_or_default();

                            // Debug: log trigger check (every 10 seconds to avoid spam)
                            static LAST_LOG: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
                            let now = std::time::SystemTime::now()
                                .duration_since(std::time::UNIX_EPOCH)
                                .unwrap_or_default()
                                .as_secs();
                            let last = LAST_LOG.load(std::sync::atomic::Ordering::Relaxed);
                            if now - last >= 10 {
                                LAST_LOG.store(now, std::sync::atomic::Ordering::Relaxed);

                                // Log each source separately for debugging
                                let title_len = current_title.as_ref().map(|t| t.len()).unwrap_or(0);
                                let selected_len = focus_info.as_ref()
                                    .and_then(|i| i.selected_text.as_ref())
                                    .map(|t| t.len()).unwrap_or(0);
                                let typed_len = last_typed_text.as_ref().map(|t| t.len()).unwrap_or(0);
                                let ocr_len = last_ocr_text.lock().ok()
                                    .and_then(|g| g.as_ref().map(|t| t.len())).unwrap_or(0);

                                println!("[Trigger] Sources: title={}, selected={}, typed={}, ocr={}",
                                    title_len, selected_len, typed_len, ocr_len);

                                if !trigger_text.is_empty() {
                                    // Safely truncate for UTF-8
                                    let preview: String = trigger_text.chars().take(150).collect();
                                    let suffix = if trigger_text.chars().count() > 150 { "..." } else { "" };
                                    println!("[Trigger] Text: \"{}{}\"", preview.replace('\n', " | "), suffix);
                                }
                            }

                            // Use Meta Agent for intelligent routing
                            // check_and_run() internally uses Meta Agent when enabled,
                            // or falls back to legacy trigger system
                            let agent_state_clone = agent_state.clone();
                            let app_handle_clone = app_handle.clone();
                            let trigger_text_clone = trigger_text.clone();
                            let app_clone = app.clone();

                            // Check if agent is running before spawning
                            if agent.manager.status() == crate::agents::AgentStatus::Running {
                                continue;
                            }

                            drop(agent); // Release lock before spawning

                            tokio::spawn(async move {
                                let mut agent = agent_state_clone.lock().await;
                                // Double-check agent is still enabled and not running
                                if !agent.enabled || agent.manager.status() == crate::agents::AgentStatus::Running {
                                    return;
                                }

                                // Meta Agent decides whether to act and which agent to use
                                if let Some(result) = agent.manager.check_and_run(&trigger_text_clone, &app_clone).await {
                                    let reason_preview: String = result.reason.chars().take(100).collect();
                                    println!("[Agent] Response: action={}, reason={}",
                                        result.final_action, reason_preview);

                                    // Send notification if needed
                                    if result.needs_notification {
                                        if let Err(e) = crate::notifications::notify_info(
                                            &app_handle_clone,
                                            &result.reason
                                        ) {
                                            eprintln!("[Agent] Notification error: {}", e);
                                        }
                                    }
                                }
                            });
                        }
                    }
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
        println!("[Collector] Flushing {} remaining events...", event_count);
    }
}

fn categorize_app(app_name: &str) -> &'static str {
    let app_lower = app_name.to_lowercase();

    if app_lower.contains("code")
        || app_lower.contains("xcode")
        || app_lower.contains("terminal")
        || app_lower.contains("iterm")
        || app_lower.contains("cursor")
    {
        return "coding";
    }

    if is_browser(&app_lower) {
        return "browsing";
    }

    if app_lower.contains("slack")
        || app_lower.contains("discord")
        || app_lower.contains("teams")
        || app_lower.contains("zoom")
        || app_lower.contains("telegram")
        || app_lower.contains("messages")
        || app_lower.contains("whatsapp")
    {
        return "communication";
    }

    if app_lower.contains("word")
        || app_lower.contains("pages")
        || app_lower.contains("notion")
        || app_lower.contains("obsidian")
        || app_lower.contains("notes")
    {
        return "writing";
    }

    if app_lower.contains("figma")
        || app_lower.contains("sketch")
        || app_lower.contains("photoshop")
        || app_lower.contains("illustrator")
    {
        return "design";
    }

    if app_lower.contains("finder")
        || app_lower.contains("preview")
        || app_lower.contains("system preferences")
    {
        return "system";
    }

    "other"
}
