/// WebSocket sync module for remote automation commands
/// Connects to Observer server for receiving automation tasks

use futures_util::{SinkExt, StreamExt};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::Mutex;
use tokio::time::{sleep, Duration};
use tokio_tungstenite::{connect_async, tungstenite::Message};

const RECONNECT_DELAY: Duration = Duration::from_secs(5);
const PING_INTERVAL: Duration = Duration::from_secs(30);

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
}

impl AutomationSync {
    /// Create new sync manager
    pub fn new(ws_url: String, queue: Arc<crate::automation::queue::AutomationQueue>) -> Self {
        Self {
            ws_url,
            auth_token: None,
            is_connected: Arc::new(Mutex::new(false)),
            queue,
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

        let (mut write, mut read) = ws_stream.split();

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

            write
                .send(Message::Text(json))
                .await
                .map_err(|e| format!("Failed to send auth: {}", e))?;
        }

        // Spawn ping task
        let mut write_clone = write.clone();
        tokio::spawn(async move {
            loop {
                sleep(PING_INTERVAL).await;

                let ping_msg = WsMessage::Ping {
                    timestamp: chrono::Utc::now().timestamp(),
                };

                if let Ok(json) = serde_json::to_string(&ping_msg) {
                    if write_clone.send(Message::Text(json)).await.is_err() {
                        break;
                    }
                }
            }
        });

        // Handle incoming messages
        while let Some(msg) = read.next().await {
            match msg {
                Ok(Message::Text(text)) => {
                    if let Err(e) = self.handle_message(&text, &mut write).await {
                        eprintln!("Error handling message: {}", e);
                    }
                }
                Ok(Message::Close(_)) => {
                    println!("WebSocket closed by server");
                    break;
                }
                Ok(Message::Ping(data)) => {
                    let _ = write.send(Message::Pong(data)).await;
                }
                Err(e) => {
                    eprintln!("WebSocket error: {}", e);
                    break;
                }
                _ => {}
            }
        }

        Ok(())
    }

    /// Handle incoming WebSocket message
    async fn handle_message(
        &self,
        text: &str,
        write: &mut futures_util::stream::SplitSink<
            tokio_tungstenite::WebSocketStream<
                tokio_tungstenite::MaybeTlsStream<tokio::net::TcpStream>,
            >,
            Message,
        >,
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
        // This would need to maintain a write handle reference
        // For now, results are logged locally
        println!("Task result: {:?}", result);
        Ok(())
    }

    /// Send status update to server
    pub async fn send_status(&self, status: crate::automation::queue::QueueStatus) -> Result<(), String> {
        // This would need to maintain a write handle reference
        println!("Queue status: {:?}", status);
        Ok(())
    }
}

/// Get WebSocket URL from environment or config
pub fn get_websocket_url() -> String {
    // Try to get from environment variable
    if let Ok(url) = std::env::var("OBSERVER_WS_URL") {
        return url;
    }

    // Try to read from config file
    if let Ok(home) = std::env::var("HOME") {
        let config_path = format!("{}/.observer/config.json", home);
        if let Ok(content) = std::fs::read_to_string(config_path) {
            if let Ok(json) = serde_json::from_str::<serde_json::Value>(&content) {
                if let Some(url) = json.get("ws_url").and_then(|v| v.as_str()) {
                    return url.to_string();
                }
            }
        }
    }

    // Default to localhost
    "ws://localhost:8000/ws/automation".to_string()
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
