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

/// Check if we're running in development mode
fn is_dev_mode() -> bool {
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
/// 3. Development fallback (localhost)
///
/// Note: Production deployments MUST set OBSERVER_SERVER_URL environment variable
/// or configure server URL via config file
pub fn get_server_url() -> String {
    // Development fallback
    let default_url = if is_dev_mode() {
        "http://localhost:8000"
    } else {
        // Production MUST configure URL via env var or config file
        // Using localhost as safe fallback (will fail to connect, prompting user to configure)
        eprintln!(
            "WARNING: OBSERVER_SERVER_URL not configured. Please set environment variable or create config file at ~/.config/observer/server.txt"
        );
        "http://localhost:8000"
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
/// 3. Development fallback (localhost)
///
/// Note: Production deployments MUST set OBSERVER_DASHBOARD_URL environment variable
/// or configure dashboard URL via config file
pub fn get_dashboard_url() -> String {
    // Development fallback
    let default_url = if is_dev_mode() {
        "http://localhost:5173"
    } else {
        // Production MUST configure URL via env var or config file
        // Using localhost as safe fallback (will fail to connect, prompting user to configure)
        eprintln!(
            "WARNING: OBSERVER_DASHBOARD_URL not configured. Please set environment variable or create config file at ~/.config/observer/dashboard.txt"
        );
        "http://localhost:5173"
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
                let error_msg = e.to_string(); // Convert to String before await
                drop(e); // Drop error to make future Send
                eprintln!("Sync failed: {}", error_msg);
                // Put events back in buffer with bounds checking
                let mut state = state.lock().await;
                let mut dropped_count = 0;

                for event in events {
                    if state.events_buffer.len() >= crate::MAX_BUFFER_SIZE {
                        // Drop oldest events to make room
                        state.events_buffer.remove(0);
                        dropped_count += 1;
                    }
                    state.events_buffer.push(event);
                }

                if dropped_count > 0 {
                    eprintln!(
                        "Warning: Dropped {} old events due to buffer overflow after failed sync",
                        dropped_count
                    );
                }

                // Set warning flag if buffer is over threshold
                if state.events_buffer.len() >= crate::BUFFER_WARNING_THRESHOLD {
                    state.buffer_warnings_logged = true;
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

async fn sync_events(events: &[Event]) -> Result<(), Box<dyn std::error::Error>> {
    let client = create_http_client()?;
    let server_url = get_server_url();

    let payload = serde_json::json!({
        "events": events
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

        match client
            .post(format!("{}/api/v1/events", server_url))
            .json(&payload)
            .send()
            .await
        {
            Ok(response) => {
                let status = response.status();

                if status.is_success() {
                    return Ok(());
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
            let error_msg = e.to_string(); // Convert to String before await
            drop(e); // Drop error to make future Send

            // Put events back in buffer with bounds checking
            let mut state = state.lock().await;
            let mut dropped_count = 0;

            for event in events {
                if state.events_buffer.len() >= crate::MAX_BUFFER_SIZE {
                    // Drop oldest events to make room
                    state.events_buffer.remove(0);
                    dropped_count += 1;
                }
                state.events_buffer.push(event);
            }

            if dropped_count > 0 {
                eprintln!(
                    "Warning: Dropped {} old events due to buffer overflow after failed manual sync",
                    dropped_count
                );
            }

            // Set warning flag if buffer is over threshold
            if state.events_buffer.len() >= crate::BUFFER_WARNING_THRESHOLD {
                state.buffer_warnings_logged = true;
            }

            Err(error_msg)
        }
    }
}
