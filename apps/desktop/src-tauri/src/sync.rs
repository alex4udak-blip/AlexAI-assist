// Sync service module
// This module handles syncing collected events to the server

use crate::collector::Event;
use crate::AppState;
use chrono::Utc;
use std::net::IpAddr;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::Mutex;
use url::Url;

const SYNC_INTERVAL_SECS: u64 = 30;
const CONNECT_TIMEOUT_SECS: u64 = 10;
const REQUEST_TIMEOUT_SECS: u64 = 30;
const MAX_RETRIES: u32 = 3;
const INITIAL_RETRY_DELAY_MS: u64 = 1000;

/// Get API key from environment or config file
///
/// Priority:
/// 1. OBSERVER_API_KEY environment variable
/// 2. ~/.config/observer/api_key.txt config file
/// 3. Empty string (no authentication - development only)
fn get_api_key() -> Option<String> {
    // 1. Environment variable
    if let Ok(key) = std::env::var("OBSERVER_API_KEY") {
        let key = key.trim();
        if !key.is_empty() {
            return Some(key.to_string());
        }
    }

    // 2. Config file
    if let Some(config_dir) = dirs::config_dir() {
        let config_file = config_dir.join("observer").join("api_key.txt");
        if let Ok(key) = std::fs::read_to_string(&config_file) {
            let key = key.trim();
            if !key.is_empty() {
                return Some(key.to_string());
            }
        }
    }

    // 3. No API key (development mode)
    None
}

/// Check if we're running in development mode
pub fn is_dev_mode() -> bool {
    std::env::var("OBSERVER_DEV")
        .map(|v| v == "1" || v.to_lowercase() == "true")
        .unwrap_or(false)
        || cfg!(debug_assertions)
}

/// Check if an IP address is internal/private
fn is_internal_ip(ip: IpAddr) -> bool {
    match ip {
        IpAddr::V4(ipv4) => {
            let octets = ipv4.octets();
            // Loopback: 127.0.0.0/8
            octets[0] == 127
                // Private: 10.0.0.0/8
                || octets[0] == 10
                // Private: 172.16.0.0/12
                || (octets[0] == 172 && (16..=31).contains(&octets[1]))
                // Private: 192.168.0.0/16
                || (octets[0] == 192 && octets[1] == 168)
                // Link-local: 169.254.0.0/16
                || (octets[0] == 169 && octets[1] == 254)
                // Multicast: 224.0.0.0/4
                || octets[0] >= 224
        }
        IpAddr::V6(ipv6) => {
            // Loopback: ::1
            ipv6.is_loopback()
                // Link-local: fe80::/10
                || (ipv6.segments()[0] & 0xffc0) == 0xfe80
                // Unique local: fc00::/7
                || (ipv6.segments()[0] & 0xfe00) == 0xfc00
                // Multicast: ff00::/8
                || ipv6.is_multicast()
        }
    }
}

/// Validate URL for security (SSRF prevention, scheme validation)
pub fn validate_url(url_str: &str) -> Result<Url, String> {
    // Parse URL
    let url = Url::parse(url_str).map_err(|e| format!("Invalid URL: {}", e))?;

    // Validate scheme
    let scheme = url.scheme();
    let is_dev = is_dev_mode();

    match scheme {
        "https" => {
            // HTTPS is always allowed
        }
        "http" => {
            // HTTP is only allowed in dev mode or for localhost
            let host = url.host_str().ok_or("URL must have a host")?;
            let is_localhost = host == "localhost"
                || host == "127.0.0.1"
                || host == "[::1]"
                || host.starts_with("127.")
                || host.starts_with("localhost:");

            if !is_dev && !is_localhost {
                return Err(
                    "HTTP URLs are only allowed for localhost in production mode".to_string(),
                );
            }
        }
        _ => {
            return Err(format!(
                "Invalid URL scheme '{}': only http and https are allowed",
                scheme
            ));
        }
    }

    // Validate host exists
    let host = url.host_str().ok_or("URL must have a host")?;

    // Prevent SSRF attacks by blocking internal IPs (except in dev mode)
    if !is_dev {
        // Check if host is an IP address
        if let Ok(ip) = host.parse::<IpAddr>() {
            if is_internal_ip(ip) {
                return Err(format!(
                    "Access to internal IP address {} is not allowed in production mode",
                    ip
                ));
            }
        }

        // Also check resolved IP addresses for domain names
        // Note: We do basic validation here. DNS resolution happens at request time.
        // For stricter validation, we could resolve DNS here, but that adds latency.
        // The HTTP client should also be configured to reject internal IPs.
    }

    // Validate port is not in restricted range if specified
    if let Some(port) = url.port() {
        // Block commonly restricted ports (like 25 for SMTP, etc.)
        const BLOCKED_PORTS: &[u16] = &[
            0,    // Invalid
            25,   // SMTP
            110,  // POP3
            143,  // IMAP
            465,  // SMTPS
            587,  // SMTP submission
            993,  // IMAPS
            995,  // POP3S
        ];

        if BLOCKED_PORTS.contains(&port) {
            return Err(format!("Port {} is not allowed", port));
        }
    }

    Ok(url)
}

/// Get server URL from environment or config file
///
/// Priority:
/// 1. OBSERVER_SERVER_URL environment variable
/// 2. ~/.config/observer/server.txt config file
/// 3. Default fallback (localhost for dev, Railway URL for production)
///
/// Environment variable:
///   OBSERVER_SERVER_URL - Server API URL (e.g., https://your-server.railway.app)
///
/// Note: Production deployments should set OBSERVER_SERVER_URL environment variable
/// or configure server URL via config file (~/.config/observer/server.txt)
pub fn get_server_url() -> String {
    // Default URL: localhost for dev, Railway URL for production (fallback)
    let default_url = if is_dev_mode() {
        "http://localhost:8000"
    } else {
        // Production Railway URL (fallback - override with OBSERVER_SERVER_URL)
        "https://server-production-0b14.up.railway.app"
    };

    // 1. Environment variable
    if let Ok(url) = std::env::var("OBSERVER_SERVER_URL") {
        let url = url.trim();
        if !url.is_empty() {
            match validate_url(url) {
                Ok(validated) => return validated.to_string(),
                Err(e) => {
                    eprintln!("Invalid OBSERVER_SERVER_URL: {}. Using default.", e);
                    return default_url.to_string();
                }
            }
        }
    }

    // 2. Config file
    if let Some(config_dir) = dirs::config_dir() {
        let config_file = config_dir.join("observer").join("server.txt");
        if let Ok(url) = std::fs::read_to_string(&config_file) {
            let url = url.trim();
            if !url.is_empty() {
                match validate_url(url) {
                    Ok(validated) => return validated.to_string(),
                    Err(e) => {
                        eprintln!("Invalid server URL in config file: {}. Using default.", e);
                        return default_url.to_string();
                    }
                }
            }
        }
    }

    // 3. Default fallback
    default_url.to_string()
}

/// Get dashboard URL from environment or config file
///
/// Priority:
/// 1. OBSERVER_DASHBOARD_URL environment variable
/// 2. ~/.config/observer/dashboard.txt config file
/// 3. Default fallback (localhost for dev, Railway URL for production)
///
/// Environment variable:
///   OBSERVER_DASHBOARD_URL - Web dashboard URL (e.g., https://your-web-app.railway.app)
///
/// Note: Production deployments should set OBSERVER_DASHBOARD_URL environment variable
/// or configure dashboard URL via config file (~/.config/observer/dashboard.txt)
pub fn get_dashboard_url() -> String {
    // Default URL: localhost for dev, Railway URL for production (fallback)
    let default_url = if is_dev_mode() {
        "http://localhost:5173"
    } else {
        // Production Railway URL (fallback - override with OBSERVER_DASHBOARD_URL)
        "https://web-production-20d71.up.railway.app"
    };

    // 1. Environment variable
    if let Ok(url) = std::env::var("OBSERVER_DASHBOARD_URL") {
        let url = url.trim();
        if !url.is_empty() {
            match validate_url(url) {
                Ok(validated) => return validated.to_string(),
                Err(e) => {
                    eprintln!("Invalid OBSERVER_DASHBOARD_URL: {}. Using default.", e);
                    return default_url.to_string();
                }
            }
        }
    }

    // 2. Config file
    if let Some(config_dir) = dirs::config_dir() {
        let config_file = config_dir.join("observer").join("dashboard.txt");
        if let Ok(url) = std::fs::read_to_string(&config_file) {
            let url = url.trim();
            if !url.is_empty() {
                match validate_url(url) {
                    Ok(validated) => return validated.to_string(),
                    Err(e) => {
                        eprintln!(
                            "Invalid dashboard URL in config file: {}. Using default.",
                            e
                        );
                        return default_url.to_string();
                    }
                }
            }
        }
    }

    // 3. Default fallback
    default_url.to_string()
}

pub async fn start_sync_service(state: Arc<Mutex<AppState>>) {
    loop {
        tokio::time::sleep(tokio::time::Duration::from_secs(SYNC_INTERVAL_SECS)).await;

        // Get events to sync (clone instead of drain to keep in buffer until ACKed)
        let events: Vec<Event>;
        {
            let state = state.lock().await;
            if state.events_buffer.is_empty() {
                continue;
            }
            events = state.events_buffer.clone();
        }

        // Try to sync - convert error to String immediately to make future Send
        match sync_events(&events).await.map_err(|e| e.to_string()) {
            Ok(acked_event_ids) => {
                let mut state = state.lock().await;
                state.last_sync = format_relative_time(Utc::now());

                // Remove only ACKed events from buffer
                let acked_set: std::collections::HashSet<String> =
                    acked_event_ids.into_iter().collect();
                state.events_buffer.retain(|e| !acked_set.contains(&e.id));

                // Delete successfully synced events from database
                let acked_ids: Vec<String> = acked_set.into_iter().collect();
                if let Err(e) = state.db.delete_events(&acked_ids) {
                    eprintln!("Warning: Failed to delete synced events from database: {}", e);
                }
            }
            Err(error_msg) => {
                eprintln!("Sync failed: {}", error_msg);
                // Events remain in buffer for retry

                // Set warning flag if buffer is over threshold
                let state = state.lock().await;
                if state.events_buffer.len() >= crate::BUFFER_WARNING_THRESHOLD {
                    eprintln!(
                        "Warning: Event buffer is {}% full ({}/{} events). Events may be lost if sync continues to fail.",
                        (state.events_buffer.len() * 100) / crate::MAX_BUFFER_SIZE,
                        state.events_buffer.len(),
                        crate::MAX_BUFFER_SIZE
                    );
                }
            }
        }
    }
}

/// Create HTTP client with configured timeouts
fn create_http_client() -> Result<reqwest::Client, Box<dyn std::error::Error>> {
    let client = reqwest::Client::builder()
        .connect_timeout(Duration::from_secs(CONNECT_TIMEOUT_SECS))
        .timeout(Duration::from_secs(REQUEST_TIMEOUT_SECS))
        .build()?;
    Ok(client)
}

/// Check if error is transient and should be retried
fn is_transient_error(error: &reqwest::Error) -> bool {
    // Retry on timeout, connection errors, or server errors (5xx)
    error.is_timeout()
        || error.is_connect()
        || error.status().map_or(false, |s| s.is_server_error())
}

/// Response from server after syncing events
#[derive(Debug, serde::Deserialize)]
struct SyncResponse {
    acked_event_ids: Vec<String>,
}

async fn sync_events(events: &[Event]) -> Result<Vec<String>, Box<dyn std::error::Error>> {
    let client = create_http_client()?;
    let server_url = get_server_url();
    let api_key = get_api_key();

    // Map events to include event_id field
    let events_payload: Vec<serde_json::Value> = events
        .iter()
        .map(|e| {
            serde_json::json!({
                "event_id": e.id,
                "device_id": e.device_id,
                "event_type": e.event_type,
                "timestamp": e.timestamp,
                "app_name": e.app_name,
                "window_title": e.window_title,
                "url": e.url,
                "data": e.data,
                "category": e.category,
            })
        })
        .collect();

    let payload = serde_json::json!({
        "events": events_payload
    });

    let mut last_error = None;

    // Retry loop with exponential backoff
    for attempt in 0..=MAX_RETRIES {
        if attempt > 0 {
            let delay_ms = INITIAL_RETRY_DELAY_MS * 2_u64.pow(attempt - 1);
            eprintln!("Retrying request (attempt {}/{}) after {}ms delay",
                     attempt, MAX_RETRIES, delay_ms);
            tokio::time::sleep(Duration::from_millis(delay_ms)).await;
        }

        // Build request with optional API key authentication
        let mut request = client
            .post(format!("{}/api/v1/events", server_url))
            .json(&payload);

        if let Some(ref key) = api_key {
            request = request.header("X-API-Key", key);
        }

        match request.send().await
        {
            Ok(response) => {
                let status = response.status();

                if status.is_success() {
                    // Parse response to get ACKed event IDs
                    match response.json::<SyncResponse>().await {
                        Ok(sync_response) => {
                            return Ok(sync_response.acked_event_ids);
                        }
                        Err(e) => {
                            eprintln!("Failed to parse response: {}", e);
                            // If we can't parse the response, assume all events were ACKed
                            // to maintain backward compatibility
                            return Ok(events.iter().map(|e| e.id.clone()).collect());
                        }
                    }
                }

                // Check if we should retry based on status code
                if status.is_server_error() && attempt < MAX_RETRIES {
                    eprintln!("Server error: {} - will retry", status);
                    last_error = Some(format!("Server returned status: {}", status));
                    continue;
                }

                // Client errors (4xx) should not be retried
                return Err(format!("Server returned status: {}", status).into());
            }
            Err(e) => {
                eprintln!("Request failed: {}", e);

                // Check if error is transient and we have retries left
                if is_transient_error(&e) && attempt < MAX_RETRIES {
                    last_error = Some(e.to_string());
                    continue;
                }

                // Non-transient error or out of retries
                return Err(e.into());
            }
        }
    }

    // If we exhausted all retries
    Err(last_error
        .unwrap_or_else(|| "Max retries exceeded".to_string())
        .into())
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
        let state = state.lock().await;
        if state.events_buffer.is_empty() {
            return Ok(());
        }
        events = state.events_buffer.clone();
    }

    // Convert error to String immediately to make future Send
    match sync_events(&events).await.map_err(|e| e.to_string()) {
        Ok(acked_event_ids) => {
            let mut state = state.lock().await;
            state.last_sync = "Just now".to_string();

            // Remove only ACKed events from buffer
            let acked_set: std::collections::HashSet<String> =
                acked_event_ids.into_iter().collect();
            state.events_buffer.retain(|e| !acked_set.contains(&e.id));

            // Delete successfully synced events from database
            let acked_ids: Vec<String> = acked_set.into_iter().collect();
            if let Err(e) = state.db.delete_events(&acked_ids) {
                eprintln!("Warning: Failed to delete synced events from database: {}", e);
            }

            Ok(())
        }
        Err(error_msg) => {
            // Events remain in buffer for retry
            eprintln!("Manual sync failed: {}", error_msg);
            Err(error_msg)
        }
    }
}
