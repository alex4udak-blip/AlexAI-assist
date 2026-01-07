mod accessibility;
mod apps;

pub use accessibility::*;

use crate::AppState;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tauri::AppHandle;
use tokio::sync::Mutex;
use uuid::Uuid;

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

pub async fn start_collector(state: Arc<Mutex<AppState>>, _app_handle: AppHandle) {
    let mut last_app: Option<String> = None;
    let mut last_title: Option<String> = None;

    loop {
        // Check if collection is enabled
        {
            let state = state.lock().await;
            if !state.collecting {
                tokio::time::sleep(tokio::time::Duration::from_millis(1000)).await;
                continue;
            }
        }

        // Get current active app and window
        let (current_app, current_title) = apps::get_active_window();

        // Check if there's a change
        if current_app != last_app || current_title != last_title {
            if let Some(app_name) = &current_app {
                let event = Event::new(
                    "app_focus",
                    current_app.clone(),
                    current_title.clone(),
                )
                .with_category(categorize_app(app_name));

                // Add to buffer
                let mut state = state.lock().await;
                state.events_buffer.push(event);
                state.events_today += 1;
            }

            last_app = current_app;
            last_title = current_title;
        }

        // Poll every 500ms
        tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
    }
}

fn categorize_app(app_name: &str) -> &'static str {
    let app_lower = app_name.to_lowercase();

    // Coding tools
    if app_lower.contains("code")
        || app_lower.contains("xcode")
        || app_lower.contains("terminal")
        || app_lower.contains("iterm")
        || app_lower.contains("intellij")
        || app_lower.contains("pycharm")
        || app_lower.contains("webstorm")
        || app_lower.contains("vim")
        || app_lower.contains("neovim")
        || app_lower.contains("sublime")
        || app_lower.contains("atom")
    {
        return "coding";
    }

    // Research/Knowledge tools (check BEFORE writing!)
    if app_lower.contains("notion")
        || app_lower.contains("obsidian")
        || app_lower.contains("roam")
        || app_lower.contains("logseq")
        || app_lower.contains("evernote")
        || app_lower.contains("devonthink")
        || app_lower.contains("anki")
        || app_lower.contains("reader")
        || app_lower.contains("readwise")
    {
        return "research";
    }

    // Writing tools
    if app_lower.contains("word")
        || app_lower.contains("pages")
        || app_lower.contains("docs")
        || app_lower.contains("typora")
        || app_lower.contains("ulysses")
        || app_lower.contains("ia writer")
        || app_lower.contains("bear")
        || app_lower.contains("scrivener")
    {
        return "writing";
    }

    // Browsing
    if app_lower.contains("chrome")
        || app_lower.contains("safari")
        || app_lower.contains("firefox")
        || app_lower.contains("edge")
        || app_lower.contains("arc")
        || app_lower.contains("brave")
        || app_lower.contains("opera")
    {
        return "browsing";
    }

    // Communication
    if app_lower.contains("slack")
        || app_lower.contains("discord")
        || app_lower.contains("teams")
        || app_lower.contains("zoom")
        || app_lower.contains("telegram")
        || app_lower.contains("messages")
        || app_lower.contains("mail")
        || app_lower.contains("outlook")
    {
        return "communication";
    }

    // Design tools
    if app_lower.contains("figma")
        || app_lower.contains("sketch")
        || app_lower.contains("photoshop")
        || app_lower.contains("illustrator")
        || app_lower.contains("affinity")
        || app_lower.contains("canva")
        || app_lower.contains("framer")
    {
        return "design";
    }

    // Entertainment
    if app_lower.contains("spotify")
        || app_lower.contains("music")
        || app_lower.contains("netflix")
        || app_lower.contains("youtube")
        || app_lower.contains("steam")
        || app_lower.contains("twitch")
    {
        return "entertainment";
    }

    "other"
}
