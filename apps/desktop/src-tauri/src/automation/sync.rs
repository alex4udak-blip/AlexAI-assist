/// WebSocket sync module for remote automation commands
/// Connects to Observer server for receiving automation tasks

use futures_util::{stream::SplitSink, SinkExt, StreamExt};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::Mutex;
use tokio::time::{sleep, Duration};
use tokio_tungstenite::{connect_async, tungstenite::Message, MaybeTlsStream, WebSocketStream};

const RECONNECT_DELAY: Duration = Duration::from_secs(5);
const PING_INTERVAL: Duration = Duration::from_secs(30);

/// Type alias for WebSocket write handle
type WsWriter = SplitSink<WebSocketStream<MaybeTlsStream<tokio::net::TcpStream>>, Message>;

/// WebSocket message types
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum WsMessage {
    /// Server sends automation task
    #[serde(rename = "automation_task")]
    AutomationTask {
        task: crate::automation::queue::AutomationTask,
    },

    /// Client sends task result
    #[serde(rename = "task_result")]
    TaskResult {
        result: crate::automation::queue::TaskResult,
    },

    /// Client sends status update
    #[serde(rename = "status")]
    Status {
        queue_status: crate::automation::queue::QueueStatus,
    },

    /// Ping/Pong for keep-alive
    #[serde(rename = "ping")]
    Ping { timestamp: i64 },

    #[serde(rename = "pong")]
    Pong { timestamp: i64 },

    /// Authentication
    #[serde(rename = "auth")]
    Auth { token: String },

    #[serde(rename = "auth_success")]
    AuthSuccess { device_id: String },

    #[serde(rename = "auth_error")]
    AuthError { message: String },
}

/// WebSocket connection manager
pub struct AutomationSync {
    ws_url: String,
    auth_token: Option<String>,
    is_connected: Arc<Mutex<bool>>,
    queue: Arc<crate::automation::queue::AutomationQueue>,
    ws_writer: Arc<Mutex<Option<WsWriter>>>,
}

impl AutomationSync {
    /// Create new sync manager
    pub fn new(ws_url: String, queue: Arc<crate::automation::queue::AutomationQueue>) -> Self {
        Self {
            ws_url,
            auth_token: None,
            is_connected: Arc::new(Mutex::new(false)),
            queue,
            ws_writer: Arc::new(Mutex::new(None)),
        }
    }

    /// Set authentication token
    pub fn set_auth_token(&mut self, token: String) {
        self.auth_token = Some(token);
    }

    /// Check if connected
    pub async fn is_connected(&self) -> bool {
        *self.is_connected.lock().await
    }

    /// Start WebSocket connection with auto-reconnect
    pub async fn start(self: Arc<Self>) {
        loop {
            match self.connect().await {
                Ok(_) => {
                    println!("WebSocket connection closed, reconnecting...");
                }
                Err(e) => {
                    eprintln!("WebSocket connection error: {}", e);
                }
            }

            // Update connection status
            {
                let mut connected = self.is_connected.lock().await;
                *connected = false;
            }

            // Wait before reconnecting
            sleep(RECONNECT_DELAY).await;
        }
    }

    /// Connect to WebSocket server
    async fn connect(&self) -> Result<(), String> {
        println!("Connecting to WebSocket: {}", self.ws_url);

        let (ws_stream, _) = connect_async(&self.ws_url)
            .await
            .map_err(|e| format!("Failed to connect: {}", e))?;

        let (write, mut read) = ws_stream.split();

        // Store write handle in struct for send_result/send_status
        {
            let mut writer = self.ws_writer.lock().await;
            *writer = Some(write);
        }

        // Update connection status
        {
            let mut connected = self.is_connected.lock().await;
            *connected = true;
        }

        // Send authentication if token is available
        if let Some(token) = &self.auth_token {
            let auth_msg = WsMessage::Auth {
                token: token.clone(),
            };
            let json = serde_json::to_string(&auth_msg)
                .map_err(|e| format!("Failed to serialize auth: {}", e))?;

            let mut writer = self.ws_writer.lock().await;
            if let Some(w) = writer.as_mut() {
                w.send(Message::Text(json))
                    .await
                    .map_err(|e| format!("Failed to send auth: {}", e))?;
            }
        }

        // Spawn ping task using Arc reference to ws_writer
        let ws_writer_clone = Arc::clone(&self.ws_writer);
        tokio::spawn(async move {
            loop {
                sleep(PING_INTERVAL).await;

                let ping_msg = WsMessage::Ping {
                    timestamp: chrono::Utc::now().timestamp(),
                };

                if let Ok(json) = serde_json::to_string(&ping_msg) {
                    let mut writer = ws_writer_clone.lock().await;
                    if let Some(w) = writer.as_mut() {
                        if w.send(Message::Text(json)).await.is_err() {
                            break;
                        }
                    } else {
                        break;
                    }
                }
            }
        });

        // Handle incoming messages
        while let Some(msg) = read.next().await {
            match msg {
                Ok(Message::Text(text)) => {
                    if let Err(e) = self.handle_message(&text).await {
                        eprintln!("Error handling message: {}", e);
                    }
                }
                Ok(Message::Close(_)) => {
                    println!("WebSocket closed by server");
                    break;
                }
                Ok(Message::Ping(data)) => {
                    let mut writer = self.ws_writer.lock().await;
                    if let Some(w) = writer.as_mut() {
                        let _ = w.send(Message::Pong(data)).await;
                    }
                }
                Err(e) => {
                    eprintln!("WebSocket error: {}", e);
                    break;
                }
                _ => {}
            }
        }

        // Clear write handle on disconnect
        {
            let mut writer = self.ws_writer.lock().await;
            *writer = None;
        }

        Ok(())
    }

    /// Handle incoming WebSocket message
    async fn handle_message(
        &self,
        text: &str,
    ) -> Result<(), String> {
        let msg: WsMessage = serde_json::from_str(text)
            .map_err(|e| format!("Failed to parse message: {}", e))?;

        match msg {
            WsMessage::AutomationTask { task } => {
                // Add task to queue
                match self.queue.add_task(task).await {
                    Ok(task_id) => {
                        println!("Added task to queue: {}", task_id);
                    }
                    Err(e) => {
                        eprintln!("Failed to add task: {}", e);
                    }
                }
            }
            WsMessage::Pong { timestamp } => {
                println!("Received pong: {}", timestamp);
            }
            WsMessage::AuthSuccess { device_id } => {
                println!("Authentication successful: {}", device_id);
            }
            WsMessage::AuthError { message } => {
                eprintln!("Authentication error: {}", message);
            }
            _ => {
                println!("Received unknown message type");
            }
        }

        Ok(())
    }

    /// Send task result to server
    pub async fn send_result(&self, result: crate::automation::queue::TaskResult) -> Result<(), String> {
        let mut writer_guard = self.ws_writer.lock().await;

        let writer = writer_guard
            .as_mut()
            .ok_or_else(|| "WebSocket not connected".to_string())?;

        let msg = WsMessage::TaskResult { result };
        let json = serde_json::to_string(&msg)
            .map_err(|e| format!("Failed to serialize result: {}", e))?;

        writer
            .send(Message::Text(json))
            .await
            .map_err(|e| format!("Failed to send result: {}", e))?;

        Ok(())
    }

    /// Send status update to server
    pub async fn send_status(&self, status: crate::automation::queue::QueueStatus) -> Result<(), String> {
        let mut writer_guard = self.ws_writer.lock().await;

        let writer = writer_guard
            .as_mut()
            .ok_or_else(|| "WebSocket not connected".to_string())?;

        let msg = WsMessage::Status {
            queue_status: status,
        };
        let json = serde_json::to_string(&msg)
            .map_err(|e| format!("Failed to serialize status: {}", e))?;

        writer
            .send(Message::Text(json))
            .await
            .map_err(|e| format!("Failed to send status: {}", e))?;

        Ok(())
    }
}

/// Configuration from file
#[derive(Debug, Clone, Default)]
pub struct AutomationConfig {
    pub ws_url: String,
    pub api_key: Option<String>,
    pub device_id: String,
}

/// Read configuration from file
pub fn read_config() -> AutomationConfig {
    let mut config = AutomationConfig {
        ws_url: "ws://localhost:8000".to_string(),
        api_key: None,
        device_id: get_device_id(),
    };

    // Try environment variables first
    if let Ok(url) = std::env::var("OBSERVER_WS_URL") {
        config.ws_url = url;
    }
    if let Ok(key) = std::env::var("OBSERVER_API_KEY") {
        config.api_key = Some(key);
    }

    // Try to read from config file
    if let Ok(home) = std::env::var("HOME") {
        let config_path = format!("{}/.observer/config.json", home);
        if let Ok(content) = std::fs::read_to_string(&config_path) {
            if let Ok(json) = serde_json::from_str::<serde_json::Value>(&content) {
                if let Some(url) = json.get("ws_url").and_then(|v| v.as_str()) {
                    config.ws_url = url.to_string();
                }
                if let Some(key) = json.get("api_key").and_then(|v| v.as_str()) {
                    config.api_key = Some(key.to_string());
                }
                if let Some(id) = json.get("device_id").and_then(|v| v.as_str()) {
                    config.device_id = id.to_string();
                }
            }
        }
    }

    config
}

/// Get unique device ID
fn get_device_id() -> String {
    // Try to get from environment
    if let Ok(id) = std::env::var("OBSERVER_DEVICE_ID") {
        return id;
    }

    // Generate from machine ID or hostname
    if let Ok(hostname) = std::env::var("HOSTNAME") {
        return format!("mac-{}", hostname);
    }

    // Fallback to random ID
    format!("mac-{}", uuid::Uuid::new_v4().to_string().split('-').next().unwrap_or("unknown"))
}

/// Get WebSocket URL with authentication
pub fn get_websocket_url() -> String {
    let config = read_config();
    let base_url = format!("{}/ws/automation/{}", config.ws_url, config.device_id);

    // Add API key as query parameter if available
    if let Some(api_key) = config.api_key {
        format!("{}?api_key={}", base_url, api_key)
    } else {
        base_url
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_websocket_url() {
        let url = get_websocket_url();
        assert!(url.starts_with("ws://") || url.starts_with("wss://"));
    }

    #[test]
    fn test_ws_message_serialization() {
        let ping = WsMessage::Ping { timestamp: 12345 };
        let json = serde_json::to_string(&ping).unwrap();
        assert!(json.contains("ping"));
        assert!(json.contains("12345"));
    }
}
