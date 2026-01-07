// Sync service module
// This module handles syncing collected events to the server

use crate::collector::Event;
use crate::AppState;
use chrono::Utc;
use std::sync::Arc;
use tokio::sync::Mutex;

const SYNC_INTERVAL_SECS: u64 = 30;

/// Get server URL from environment, config file, or default to production
pub fn get_server_url() -> String {
    // 1. Environment variable
    if let Ok(url) = std::env::var("OBSERVER_SERVER_URL") {
        return url;
    }

    // 2. Config file
    if let Some(config_dir) = dirs::config_dir() {
        let config_file = config_dir.join("observer").join("server.txt");
        if let Ok(url) = std::fs::read_to_string(&config_file) {
            let url = url.trim();
            if !url.is_empty() {
                return url.to_string();
            }
        }
    }

    // 3. Default to Railway production
    "https://server-production-20d71.up.railway.app".to_string()
}

/// Get dashboard URL from environment, config file, or default to production
pub fn get_dashboard_url() -> String {
    // 1. Environment variable
    if let Ok(url) = std::env::var("OBSERVER_DASHBOARD_URL") {
        return url;
    }

    // 2. Config file
    if let Some(config_dir) = dirs::config_dir() {
        let config_file = config_dir.join("observer").join("dashboard.txt");
        if let Ok(url) = std::fs::read_to_string(&config_file) {
            let url = url.trim();
            if !url.is_empty() {
                return url.to_string();
            }
        }
    }

    // 3. Default to Railway production
    "https://web-production-20d71.up.railway.app".to_string()
}

pub async fn start_sync_service(state: Arc<Mutex<AppState>>) {
    loop {
        tokio::time::sleep(tokio::time::Duration::from_secs(SYNC_INTERVAL_SECS)).await;

        // Get events to sync
        let events: Vec<Event>;
        {
            let mut state = state.lock().await;
            if state.events_buffer.is_empty() {
                continue;
            }
            events = state.events_buffer.drain(..).collect();
        }

        // Try to sync
        match sync_events(&events).await {
            Ok(_) => {
                let mut state = state.lock().await;
                state.last_sync = format_relative_time(Utc::now());
            }
            Err(e) => {
                eprintln!("Sync failed: {}", e);
                // Put events back in buffer
                let mut state = state.lock().await;
                for event in events {
                    state.events_buffer.push(event);
                }
            }
        }
    }
}

async fn sync_events(events: &[Event]) -> Result<(), Box<dyn std::error::Error>> {
    let client = reqwest::Client::new();
    let server_url = get_server_url();

    let payload = serde_json::json!({
        "events": events
    });

    let response = client
        .post(format!("{}/api/v1/events", server_url))
        .json(&payload)
        .send()
        .await?;

    if !response.status().is_success() {
        return Err(format!("Server returned status: {}", response.status()).into());
    }

    Ok(())
}

fn format_relative_time(time: chrono::DateTime<Utc>) -> String {
    let now = Utc::now();
    let diff = now.signed_duration_since(time);

    if diff.num_seconds() < 60 {
        "Just now".to_string()
    } else if diff.num_minutes() < 60 {
        format!("{}m ago", diff.num_minutes())
    } else if diff.num_hours() < 24 {
        format!("{}h ago", diff.num_hours())
    } else {
        format!("{}d ago", diff.num_days())
    }
}

pub async fn manual_sync(state: Arc<Mutex<AppState>>) -> Result<(), String> {
    let events: Vec<Event>;
    {
        let mut state = state.lock().await;
        events = state.events_buffer.drain(..).collect();
    }

    if events.is_empty() {
        return Ok(());
    }

    match sync_events(&events).await {
        Ok(_) => {
            let mut state = state.lock().await;
            state.last_sync = "Just now".to_string();
            Ok(())
        }
        Err(e) => {
            // Put events back in buffer
            let mut state = state.lock().await;
            for event in events {
                state.events_buffer.push(event);
            }
            Err(e.to_string())
        }
    }
}
