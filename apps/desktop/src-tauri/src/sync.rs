// Sync service module
// This module handles syncing collected events to the server

use crate::collector::Event;
use crate::AppState;
use chrono::Utc;
use std::sync::Arc;
use tokio::sync::Mutex;

const SYNC_INTERVAL_SECS: u64 = 30;
const SERVER_URL: &str = "http://localhost:8000";

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

    let payload = serde_json::json!({
        "events": events
    });

    let response = client
        .post(format!("{}/api/v1/events", SERVER_URL))
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
