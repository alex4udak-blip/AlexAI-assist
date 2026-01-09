use crate::collector::{
    get_current_focus, has_accessibility_permission, request_accessibility_permission, FocusInfo,
};
use crate::sync::{get_dashboard_url, validate_url};
use crate::AppState;
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

    // Calculate top apps from events buffer
    let mut app_counts: std::collections::HashMap<String, u32> = std::collections::HashMap::new();
    for event in &state.events_buffer {
        if let Some(app_name) = &event.app_name {
            *app_counts.entry(app_name.clone()).or_insert(0) += 1;
        }
    }

    let mut top_apps: Vec<AppUsage> = app_counts
        .into_iter()
        .map(|(name, count)| AppUsage { name, count })
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
    let mut state = state.lock().await;

    // Perform sync (in real implementation, this would call the sync module)
    state.last_sync = "Just now".to_string();
    state.events_buffer.clear();

    Ok(())
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

    #[cfg(not(target_os = "macos"))]
    {
        // For other platforms, we could open app settings or system settings
        println!("Settings not yet implemented for this platform");
    }

    Ok(())
}
