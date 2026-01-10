use crate::collector::{
    get_current_focus, has_accessibility_permission, request_accessibility_permission, FocusInfo,
};
use crate::sync::{get_dashboard_url, manual_sync, validate_url};
use crate::tray;
use crate::AppState;
use crate::automation;
use crate::permissions;
use serde::Serialize;
use std::sync::Arc;
use tauri::State;
use tokio::sync::Mutex;

#[derive(Serialize)]
pub struct Stats {
    #[serde(rename = "eventsToday")]
    pub events_today: u32,
    #[serde(rename = "lastSync")]
    pub last_sync: String,
    pub status: String,
    #[serde(rename = "bufferSize")]
    pub buffer_size: usize,
    #[serde(rename = "bufferCapacity")]
    pub buffer_capacity: usize,
}

#[derive(Serialize)]
pub struct DetailedStats {
    #[serde(rename = "eventsToday")]
    pub events_today: u32,
    #[serde(rename = "lastSync")]
    pub last_sync: String,
    pub status: String,
    #[serde(rename = "topApps")]
    pub top_apps: Vec<AppUsage>,
    #[serde(rename = "activeTime")]
    pub active_time: u32,
    #[serde(rename = "bufferSize")]
    pub buffer_size: usize,
    #[serde(rename = "bufferCapacity")]
    pub buffer_capacity: usize,
    #[serde(rename = "bufferUtilization")]
    pub buffer_utilization: f32,
}

#[derive(Serialize)]
pub struct AppUsage {
    pub name: String,
    pub count: u32,
}

#[tauri::command]
pub async fn get_stats(state: State<'_, Arc<Mutex<AppState>>>) -> Result<Stats, String> {
    let state = state.lock().await;
    Ok(Stats {
        events_today: state.events_today,
        last_sync: state.last_sync.clone(),
        status: if state.collecting {
            "collecting".to_string()
        } else {
            "paused".to_string()
        },
        buffer_size: state.events_buffer.len(),
        buffer_capacity: crate::MAX_BUFFER_SIZE,
    })
}

#[tauri::command]
pub async fn get_detailed_stats(
    state: State<'_, Arc<Mutex<AppState>>>,
) -> Result<DetailedStats, String> {
    let state = state.lock().await;

    // Use cached top apps (persists across syncs)
    let mut top_apps: Vec<AppUsage> = state.top_apps_cache
        .iter()
        .map(|(name, count)| AppUsage { name: name.clone(), count: *count })
        .collect();
    top_apps.sort_by(|a, b| b.count.cmp(&a.count));
    top_apps.truncate(10);

    let buffer_size = state.events_buffer.len();
    let buffer_capacity = crate::MAX_BUFFER_SIZE;
    let buffer_utilization = if buffer_capacity > 0 {
        (buffer_size as f32 / buffer_capacity as f32) * 100.0
    } else {
        0.0
    };

    Ok(DetailedStats {
        events_today: state.events_today,
        last_sync: state.last_sync.clone(),
        status: if state.collecting {
            "collecting".to_string()
        } else {
            "paused".to_string()
        },
        top_apps,
        active_time: (state.events_today * 2).min(480), // Rough estimate
        buffer_size,
        buffer_capacity,
        buffer_utilization,
    })
}

#[tauri::command]
pub async fn toggle_collection(state: State<'_, Arc<Mutex<AppState>>>) -> Result<(), String> {
    let mut state = state.lock().await;
    state.collecting = !state.collecting;
    Ok(())
}

#[tauri::command]
pub async fn sync_now(state: State<'_, Arc<Mutex<AppState>>>) -> Result<(), String> {
    // Actually sync events to server using the sync module
    let state_arc = state.inner().clone();
    manual_sync(state_arc).await
}

#[tauri::command]
pub async fn open_dashboard() -> Result<(), String> {
    let dashboard_url = get_dashboard_url();

    // Validate URL before opening to prevent opening malicious URLs
    validate_url(&dashboard_url)?;

    // Open the validated URL
    open::that(dashboard_url).map_err(|e| e.to_string())
}

/// Check if the app has accessibility permission (macOS)
#[tauri::command]
pub fn check_permissions() -> bool {
    has_accessibility_permission()
}

/// Request accessibility permission (macOS) - opens System Preferences
#[tauri::command]
pub fn request_permissions() -> bool {
    request_accessibility_permission()
}

/// Get current focused application and window information
#[tauri::command]
pub fn get_focus() -> Option<FocusInfo> {
    get_current_focus()
}

/// Notify that window visibility changed (for tray icon sync)
#[tauri::command]
pub fn set_window_visible(visible: bool) {
    tray::set_window_visible(visible);
}

/// Open settings - for macOS this opens Accessibility preferences
#[tauri::command]
pub fn open_settings() -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        // Open Privacy & Security > Accessibility settings
        std::process::Command::new("open")
            .arg("x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility")
            .spawn()
            .map_err(|e| e.to_string())?;
    }

    #[cfg(target_os = "windows")]
    {
        // Open Windows Settings app (ms-settings: URI scheme)
        std::process::Command::new("cmd")
            .args(["/C", "start", "ms-settings:"])
            .spawn()
            .map_err(|e| e.to_string())?;
    }

    #[cfg(target_os = "linux")]
    {
        // Try various common settings applications on Linux
        let settings_commands = [
            "gnome-control-center",  // GNOME
            "unity-control-center",  // Unity
            "systemsettings5",       // KDE Plasma 5
            "xfce4-settings-manager", // XFCE
            "mate-control-center",   // MATE
            "lxqt-config",           // LXQt
        ];

        let mut opened = false;
        for cmd in &settings_commands {
            if let Ok(_) = std::process::Command::new(cmd)
                .spawn()
            {
                opened = true;
                break;
            }
        }

        if !opened {
            return Err("Could not find a settings application. Please install gnome-control-center or your desktop environment's settings manager.".to_string());
        }
    }

    Ok(())
}

// ============================================================================
// AUTOMATION COMMANDS
// ============================================================================

/// Check all automation permissions
#[tauri::command]
pub fn check_all_permissions() -> permissions::AllPermissions {
    permissions::check_all_permissions()
}

/// Request specific permission
#[tauri::command]
pub fn request_permission(permission: String) -> Result<bool, String> {
    let perm_type = match permission.as_str() {
        "accessibility" => permissions::PermissionType::Accessibility,
        "screen_recording" => permissions::PermissionType::ScreenRecording,
        _ => return Err(format!("Unknown permission type: {}", permission)),
    };

    permissions::request_permission(perm_type)
}

/// Open permission settings
#[tauri::command]
pub fn open_permission_settings(permission: String) -> Result<(), String> {
    let perm_type = match permission.as_str() {
        "accessibility" => permissions::PermissionType::Accessibility,
        "screen_recording" => permissions::PermissionType::ScreenRecording,
        _ => return Err(format!("Unknown permission type: {}", permission)),
    };

    permissions::open_permission_settings(perm_type)
}

/// Click at coordinates
#[tauri::command]
pub fn automation_click(x: i32, y: i32, button: Option<String>) -> Result<(), String> {
    let btn = match button.as_deref() {
        Some("right") => automation::input::MouseButton::Right,
        Some("middle") => automation::input::MouseButton::Middle,
        _ => automation::input::MouseButton::Left,
    };

    automation::input::click_at(x, y, btn)
}

/// Type text
#[tauri::command]
pub fn automation_type(text: String) -> Result<(), String> {
    automation::input::type_text(&text)
}

/// Press hotkey
#[tauri::command]
pub fn automation_hotkey(modifiers: Vec<String>, key: String) -> Result<(), String> {
    let mods: Vec<automation::input::Modifier> = modifiers
        .iter()
        .filter_map(|m| match m.as_str() {
            "control" | "ctrl" => Some(automation::input::Modifier::Control),
            "alt" | "option" => Some(automation::input::Modifier::Alt),
            "shift" => Some(automation::input::Modifier::Shift),
            "meta" | "cmd" | "command" => Some(automation::input::Modifier::Meta),
            _ => None,
        })
        .collect();

    automation::input::press_hotkey(&mods, &key)
}

/// Capture screenshot
#[tauri::command]
pub fn automation_screenshot() -> Result<String, String> {
    let image = automation::screen::capture_screenshot()?;
    automation::screen::encode_to_base64(&image)
}

/// Capture screenshot as JPEG
#[tauri::command]
pub fn automation_screenshot_jpeg(quality: Option<u8>) -> Result<String, String> {
    let image = automation::screen::capture_screenshot()?;
    let q = quality.unwrap_or(85);
    automation::screen::encode_to_base64_jpeg(&image, q)
}

/// Get list of monitors
#[tauri::command]
pub fn automation_get_monitors() -> Result<Vec<automation::screen::MonitorInfo>, String> {
    automation::screen::get_monitors()
}

/// Extract text from screenshot using OCR
#[tauri::command]
pub fn automation_ocr() -> Result<automation::ocr::OcrResult, String> {
    let image = automation::screen::capture_screenshot()?;
    automation::ocr::extract_text_from_image(&image)
}

/// Get current browser URL
#[tauri::command]
pub fn automation_browser_url(browser: String) -> Result<String, String> {
    let browser_enum = parse_browser(&browser)?;
    automation::browser::get_browser_url(browser_enum)
}

/// Navigate browser to URL
#[tauri::command]
pub fn automation_browser_navigate(browser: String, url: String) -> Result<(), String> {
    let browser_enum = parse_browser(&browser)?;
    automation::browser::navigate_to_url(browser_enum, &url)
}

/// Detect active browser
#[tauri::command]
pub fn automation_detect_browser() -> Result<Option<String>, String> {
    match automation::browser::detect_active_browser()? {
        Some(browser) => Ok(Some(format!("{:?}", browser).to_lowercase())),
        None => Ok(None),
    }
}

/// Add task to automation queue
#[tauri::command]
pub async fn queue_add_task(
    queue: State<'_, Arc<automation::queue::AutomationQueue>>,
    task: automation::queue::AutomationTask,
) -> Result<String, String> {
    queue.add_task(task).await
}

/// Get queue status
#[tauri::command]
pub async fn queue_status(
    queue: State<'_, Arc<automation::queue::AutomationQueue>>,
) -> Result<automation::queue::QueueStatus, String> {
    Ok(queue.status().await)
}

/// Pause queue
#[tauri::command]
pub async fn queue_pause(
    queue: State<'_, Arc<automation::queue::AutomationQueue>>,
) -> Result<(), String> {
    queue.pause().await;
    Ok(())
}

/// Resume queue
#[tauri::command]
pub async fn queue_resume(
    queue: State<'_, Arc<automation::queue::AutomationQueue>>,
) -> Result<(), String> {
    queue.resume().await;
    Ok(())
}

/// Clear queue
#[tauri::command]
pub async fn queue_clear(
    queue: State<'_, Arc<automation::queue::AutomationQueue>>,
) -> Result<(), String> {
    queue.clear().await;
    Ok(())
}

// ============================================================================
// SETTINGS COMMANDS
// ============================================================================

use serde::Deserialize;

#[derive(Serialize, Deserialize, Clone)]
pub struct AppSettings {
    #[serde(rename = "apiUrl")]
    pub api_url: String,
    #[serde(rename = "syncInterval")]
    pub sync_interval: u32,
    #[serde(rename = "launchAtStartup")]
    pub launch_at_startup: bool,
}

impl Default for AppSettings {
    fn default() -> Self {
        Self {
            api_url: get_dashboard_url(),
            sync_interval: 30,
            launch_at_startup: false,
        }
    }
}

fn get_settings_path() -> std::path::PathBuf {
    dirs::config_dir()
        .unwrap_or_else(|| std::path::PathBuf::from("."))
        .join("observer")
        .join("settings.json")
}

/// Get app settings
#[tauri::command]
pub fn get_settings() -> Result<AppSettings, String> {
    let path = get_settings_path();

    if path.exists() {
        let content = std::fs::read_to_string(&path)
            .map_err(|e| format!("Failed to read settings: {}", e))?;
        serde_json::from_str(&content)
            .map_err(|e| format!("Failed to parse settings: {}", e))
    } else {
        Ok(AppSettings::default())
    }
}

/// Save app settings
#[tauri::command]
pub fn save_settings(settings: AppSettings) -> Result<(), String> {
    let path = get_settings_path();

    // Ensure directory exists
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| format!("Failed to create config directory: {}", e))?;
    }

    let content = serde_json::to_string_pretty(&settings)
        .map_err(|e| format!("Failed to serialize settings: {}", e))?;

    std::fs::write(&path, content)
        .map_err(|e| format!("Failed to write settings: {}", e))?;

    // Handle launch at startup (macOS)
    #[cfg(target_os = "macos")]
    {
        if settings.launch_at_startup {
            // Add to Login Items using AppleScript
            let _ = std::process::Command::new("osascript")
                .args(["-e", "tell application \"System Events\" to make login item at end with properties {path:\"/Applications/Observer.app\", hidden:false}"])
                .output();
        } else {
            // Remove from Login Items
            let _ = std::process::Command::new("osascript")
                .args(["-e", "tell application \"System Events\" to delete login item \"Observer\""])
                .output();
        }
    }

    Ok(())
}

/// Open system preferences to a specific pane
#[tauri::command]
pub fn open_system_preferences(pane: String) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        let url = match pane.as_str() {
            "privacy" => "x-apple.systempreferences:com.apple.preference.security?Privacy",
            "accessibility" => "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
            "screen_recording" => "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
            "login_items" => "x-apple.systempreferences:com.apple.LoginItems-Settings.extension",
            _ => "x-apple.systempreferences:",
        };

        std::process::Command::new("open")
            .arg(url)
            .spawn()
            .map_err(|e| format!("Failed to open system preferences: {}", e))?;
    }

    Ok(())
}

/// Get debug info for troubleshooting
#[derive(Serialize)]
pub struct DebugInfo {
    pub version: String,
    pub accessibility_permission: bool,
    pub screen_recording_permission: bool,
    pub config_path: String,
    pub log_path: String,
    pub platform: String,
}

#[tauri::command]
pub fn get_debug_info() -> Result<DebugInfo, String> {
    let config_path = dirs::config_dir()
        .map(|p| p.join("observer").to_string_lossy().to_string())
        .unwrap_or_else(|| "unknown".to_string());

    let log_path = dirs::data_local_dir()
        .map(|p| p.join("observer").join("logs").to_string_lossy().to_string())
        .unwrap_or_else(|| "unknown".to_string());

    Ok(DebugInfo {
        version: env!("CARGO_PKG_VERSION").to_string(),
        accessibility_permission: has_accessibility_permission(),
        screen_recording_permission: permissions::check_permission(permissions::PermissionType::ScreenRecording)
            .unwrap_or(false),
        config_path,
        log_path,
        platform: std::env::consts::OS.to_string(),
    })
}

/// Force check for updates (manual trigger)
#[tauri::command]
pub async fn check_updates(app: tauri::AppHandle) -> Result<String, String> {
    use tauri_plugin_updater::UpdaterExt;

    match app.updater() {
        Ok(updater) => {
            match updater.check().await {
                Ok(Some(update)) => {
                    Ok(format!("Update available: v{}", update.version))
                }
                Ok(None) => {
                    Ok(format!("App is up to date (v{})", env!("CARGO_PKG_VERSION")))
                }
                Err(e) => {
                    Err(format!("Update check failed: {}", e))
                }
            }
        }
        Err(e) => {
            Err(format!("Updater not available: {}", e))
        }
    }
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/// Parse browser string to enum
fn parse_browser(browser: &str) -> Result<automation::browser::Browser, String> {
    match browser.to_lowercase().as_str() {
        "chrome" => Ok(automation::browser::Browser::Chrome),
        "safari" => Ok(automation::browser::Browser::Safari),
        "arc" => Ok(automation::browser::Browser::Arc),
        "firefox" => Ok(automation::browser::Browser::Firefox),
        _ => Err(format!("Unknown browser: {}", browser)),
    }
}
