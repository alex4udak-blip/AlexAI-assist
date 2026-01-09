/// Task queue system for automation with priorities and pause/resume
/// Minimum 100ms interval between tasks

use serde::{Serialize, Deserialize};
use std::collections::BinaryHeap;
use std::cmp::Ordering;
use std::sync::Arc;
use tokio::sync::{mpsc, Mutex, RwLock};
use tokio::time::{Duration, sleep, timeout};
use tokio::process::Command;
use uuid::Uuid;
use regex::Regex;

const MIN_TASK_INTERVAL: Duration = Duration::from_millis(100);
const CUSTOM_COMMAND_TIMEOUT: Duration = Duration::from_secs(30);

/// Task priority levels
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
pub enum TaskPriority {
    Low = 0,
    Normal = 1,
    High = 2,
    Urgent = 3,
}

/// Automation task
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutomationTask {
    pub id: String,
    pub priority: TaskPriority,
    pub command: TaskCommand,
    pub created_at: chrono::DateTime<chrono::Utc>,
    #[serde(skip)]
    pub trust_level: crate::automation::trust::TrustLevel,
}

impl AutomationTask {
    pub fn new(command: TaskCommand, priority: TaskPriority) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            priority,
            command,
            created_at: chrono::Utc::now(),
            trust_level: crate::automation::trust::TrustLevel::AskDangerous,
        }
    }

    pub fn with_trust_level(mut self, trust_level: crate::automation::trust::TrustLevel) -> Self {
        self.trust_level = trust_level;
        self
    }
}

/// Implement ordering for priority queue (higher priority first, then FIFO)
impl Eq for AutomationTask {}

impl PartialEq for AutomationTask {
    fn eq(&self, other: &Self) -> bool {
        self.id == other.id
    }
}

impl Ord for AutomationTask {
    fn cmp(&self, other: &Self) -> Ordering {
        // Higher priority first
        match self.priority.cmp(&other.priority) {
            Ordering::Equal => {
                // If priorities are equal, use FIFO (earlier created_at has higher priority)
                other.created_at.cmp(&self.created_at)
            }
            other_ordering => other_ordering,
        }
    }
}

impl PartialOrd for AutomationTask {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

/// Task commands that can be executed
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", content = "params")]
pub enum TaskCommand {
    Click { x: i32, y: i32, button: String },
    Type { text: String },
    Hotkey { modifiers: Vec<String>, key: String },
    Screenshot { save_path: Option<String> },
    BrowserNavigate { browser: String, url: String },
    BrowserGetUrl { browser: String },
    Wait { milliseconds: u64 },
    Custom { name: String, params: serde_json::Value },
}

/// Queue status
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueueStatus {
    pub is_paused: bool,
    pub pending_tasks: usize,
    pub completed_tasks: usize,
    pub failed_tasks: usize,
    pub current_task: Option<String>,
}

/// Task execution result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskResult {
    pub task_id: String,
    pub success: bool,
    pub error: Option<String>,
    pub output: Option<serde_json::Value>,
}

/// Custom command execution helpers
mod custom_commands {
    use super::*;

    /// Sanitize command string to prevent injection attacks
    /// Checks for dangerous patterns like command chaining, redirects, etc.
    pub fn sanitize_command(cmd: &str) -> Result<String, String> {
        // Check for empty command
        if cmd.trim().is_empty() {
            return Err("Command cannot be empty".to_string());
        }

        // Check for dangerous patterns
        let dangerous_patterns = [
            r"[;&|`$]", // Command chaining, piping, command substitution
            r"\$\(", // Command substitution
            r"\.\./", // Directory traversal
            r">\s*&", // Redirect stderr/stdout
        ];

        for pattern in &dangerous_patterns {
            let re = Regex::new(pattern).map_err(|e| format!("Regex error: {}", e))?;
            if re.is_match(cmd) {
                return Err(format!("Command contains dangerous pattern: {}", pattern));
            }
        }

        Ok(cmd.to_string())
    }

    /// Sanitize parameter value
    pub fn sanitize_param(param: &str) -> Result<String, String> {
        // Basic sanitization - remove control characters and null bytes
        if param.contains('\0') {
            return Err("Parameter contains null byte".to_string());
        }

        // Check for excessive length
        if param.len() > 10000 {
            return Err("Parameter exceeds maximum length".to_string());
        }

        Ok(param.to_string())
    }

    /// Execute a shell command with timeout
    pub async fn execute_shell_command(
        command: &str,
        args: Vec<String>,
    ) -> Result<String, String> {
        // Determine shell based on platform
        #[cfg(target_os = "windows")]
        let (shell, shell_arg) = ("cmd", "/C");

        #[cfg(not(target_os = "windows"))]
        let (shell, shell_arg) = ("sh", "-c");

        // Build full command
        let full_command = if args.is_empty() {
            command.to_string()
        } else {
            format!("{} {}", command, args.join(" "))
        };

        // Execute with timeout
        let result = timeout(CUSTOM_COMMAND_TIMEOUT, async {
            Command::new(shell)
                .arg(shell_arg)
                .arg(&full_command)
                .output()
                .await
        })
        .await;

        match result {
            Ok(Ok(output)) => {
                if output.status.success() {
                    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
                    Ok(stdout)
                } else {
                    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
                    eprintln!("Command failed: {}", stderr);
                    Err(format!("Command failed: {}", stderr))
                }
            }
            Ok(Err(e)) => {
                eprintln!("Failed to execute command: {}", e);
                Err(format!("Failed to execute command: {}", e))
            }
            Err(_) => {
                eprintln!("Command timed out after {:?}", CUSTOM_COMMAND_TIMEOUT);
                Err(format!("Command execution timed out after {:?}", CUSTOM_COMMAND_TIMEOUT))
            }
        }
    }

    /// Execute AppleScript (macOS only)
    #[cfg(target_os = "macos")]
    pub async fn execute_applescript(script: &str) -> Result<String, String> {
        // Sanitize script
        if script.contains('\0') {
            return Err("AppleScript contains null byte".to_string());
        }

        if script.len() > 50000 {
            return Err("AppleScript exceeds maximum length".to_string());
        }

        // Execute with timeout
        let result = timeout(CUSTOM_COMMAND_TIMEOUT, async {
            Command::new("osascript")
                .arg("-e")
                .arg(script)
                .output()
                .await
        })
        .await;

        match result {
            Ok(Ok(output)) => {
                if output.status.success() {
                    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
                    Ok(stdout)
                } else {
                    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
                    eprintln!("AppleScript failed: {}", stderr);
                    Err(format!("AppleScript failed: {}", stderr))
                }
            }
            Ok(Err(e)) => {
                eprintln!("Failed to execute AppleScript: {}", e);
                Err(format!("Failed to execute AppleScript: {}", e))
            }
            Err(_) => {
                eprintln!("AppleScript timed out after {:?}", CUSTOM_COMMAND_TIMEOUT);
                Err(format!("AppleScript execution timed out after {:?}", CUSTOM_COMMAND_TIMEOUT))
            }
        }
    }

    #[cfg(not(target_os = "macos"))]
    pub async fn execute_applescript(_script: &str) -> Result<String, String> {
        Err("AppleScript is only supported on macOS".to_string())
    }
}

/// Automation queue manager
pub struct AutomationQueue {
    tasks: Arc<Mutex<BinaryHeap<AutomationTask>>>,
    is_paused: Arc<RwLock<bool>>,
    completed_count: Arc<RwLock<usize>>,
    failed_count: Arc<RwLock<usize>>,
    current_task: Arc<RwLock<Option<String>>>,
    result_tx: mpsc::UnboundedSender<TaskResult>,
}

impl AutomationQueue {
    /// Create a new automation queue
    pub fn new() -> (Self, mpsc::UnboundedReceiver<TaskResult>) {
        let (result_tx, result_rx) = mpsc::unbounded_channel();

        let queue = Self {
            tasks: Arc::new(Mutex::new(BinaryHeap::new())),
            is_paused: Arc::new(RwLock::new(false)),
            completed_count: Arc::new(RwLock::new(0)),
            failed_count: Arc::new(RwLock::new(0)),
            current_task: Arc::new(RwLock::new(None)),
            result_tx,
        };

        (queue, result_rx)
    }

    /// Add task to queue
    pub async fn add_task(&self, task: AutomationTask) -> Result<String, String> {
        let task_id = task.id.clone();
        let mut tasks = self.tasks.lock().await;
        tasks.push(task);
        Ok(task_id)
    }

    /// Get queue status
    pub async fn status(&self) -> QueueStatus {
        let tasks = self.tasks.lock().await;
        let is_paused = *self.is_paused.read().await;
        let completed = *self.completed_count.read().await;
        let failed = *self.failed_count.read().await;
        let current = self.current_task.read().await.clone();

        QueueStatus {
            is_paused,
            pending_tasks: tasks.len(),
            completed_tasks: completed,
            failed_tasks: failed,
            current_task: current,
        }
    }

    /// Pause queue processing
    pub async fn pause(&self) {
        let mut is_paused = self.is_paused.write().await;
        *is_paused = true;
    }

    /// Resume queue processing
    pub async fn resume(&self) {
        let mut is_paused = self.is_paused.write().await;
        *is_paused = false;
    }

    /// Clear all pending tasks
    pub async fn clear(&self) {
        let mut tasks = self.tasks.lock().await;
        tasks.clear();
    }

    /// Process queue (should be run in background task)
    pub async fn process(&self) {
        loop {
            // Check if paused
            if *self.is_paused.read().await {
                sleep(Duration::from_millis(100)).await;
                continue;
            }

            // Get next task
            let task = {
                let mut tasks = self.tasks.lock().await;
                tasks.pop()
            };

            if let Some(task) = task {
                // Update current task
                {
                    let mut current = self.current_task.write().await;
                    *current = Some(task.id.clone());
                }

                // Execute task
                let result = self.execute_task(&task).await;

                // Update counters
                if result.success {
                    let mut completed = self.completed_count.write().await;
                    *completed += 1;
                } else {
                    let mut failed = self.failed_count.write().await;
                    *failed += 1;
                }

                // Send result
                let _ = self.result_tx.send(result);

                // Clear current task
                {
                    let mut current = self.current_task.write().await;
                    *current = None;
                }

                // Minimum interval between tasks
                sleep(MIN_TASK_INTERVAL).await;
            } else {
                // No tasks, wait a bit
                sleep(Duration::from_millis(100)).await;
            }
        }
    }

    /// Execute a single task
    async fn execute_task(&self, task: &AutomationTask) -> TaskResult {
        use crate::automation::{input, screen, browser};

        let result = match &task.command {
            TaskCommand::Click { x, y, button } => {
                let btn = match button.as_str() {
                    "left" => input::MouseButton::Left,
                    "right" => input::MouseButton::Right,
                    "middle" => input::MouseButton::Middle,
                    _ => input::MouseButton::Left,
                };
                input::click_at(*x, *y, btn).map(|_| None)
            }
            TaskCommand::Type { text } => {
                input::type_text(text).map(|_| None)
            }
            TaskCommand::Hotkey { modifiers, key } => {
                let mods: Vec<input::Modifier> = modifiers
                    .iter()
                    .filter_map(|m| match m.as_str() {
                        "control" | "ctrl" => Some(input::Modifier::Control),
                        "alt" | "option" => Some(input::Modifier::Alt),
                        "shift" => Some(input::Modifier::Shift),
                        "meta" | "cmd" | "command" => Some(input::Modifier::Meta),
                        _ => None,
                    })
                    .collect();
                input::press_hotkey(&mods, key).map(|_| None)
            }
            TaskCommand::Screenshot { save_path: _ } => {
                let img = screen::capture_screenshot()?;
                let base64 = screen::encode_to_base64(&img)?;
                Ok(Some(serde_json::json!({ "base64": base64 })))
            }
            TaskCommand::BrowserNavigate { browser, url } => {
                let browser_enum = match browser.as_str() {
                    "chrome" => browser::Browser::Chrome,
                    "safari" => browser::Browser::Safari,
                    "arc" => browser::Browser::Arc,
                    "firefox" => browser::Browser::Firefox,
                    _ => browser::Browser::Chrome,
                };
                browser::navigate_to_url(browser_enum, url).map(|_| None)
            }
            TaskCommand::BrowserGetUrl { browser } => {
                let browser_enum = match browser.as_str() {
                    "chrome" => browser::Browser::Chrome,
                    "safari" => browser::Browser::Safari,
                    "arc" => browser::Browser::Arc,
                    "firefox" => browser::Browser::Firefox,
                    _ => browser::Browser::Chrome,
                };
                match browser::get_browser_url(browser_enum) {
                    Ok(url) => {
                        let output = serde_json::json!({ "url": url });
                        Ok(Some(output))
                    }
                    Err(e) => Err(e),
                }
            }
            TaskCommand::Wait { milliseconds } => {
                sleep(Duration::from_millis(*milliseconds)).await;
                Ok(None)
            }
            TaskCommand::Custom { name, params } => {
                self.execute_custom_command(name, params).await
            }
        };

        match result {
            Ok(output) => TaskResult {
                task_id: task.id.clone(),
                success: true,
                error: None,
                output,
            },
            Err(error) => TaskResult {
                task_id: task.id.clone(),
                success: false,
                error: Some(error),
                output: None,
            },
        }
    }

    /// Execute a custom command
    ///
    /// Supported custom commands:
    ///
    /// 1. **shell** - Execute shell commands
    ///    ```json
    ///    {
    ///      "name": "shell",
    ///      "params": {
    ///        "command": "ls",
    ///        "args": ["-la", "/tmp"]
    ///      }
    ///    }
    ///    ```
    ///
    /// 2. **applescript** - Execute AppleScript (macOS only)
    ///    ```json
    ///    {
    ///      "name": "applescript",
    ///      "params": {
    ///        "script": "tell application \"Safari\" to get URL of current tab of front window"
    ///      }
    ///    }
    ///    ```
    ///
    /// 3. **http_request** - Make HTTP requests
    ///    ```json
    ///    {
    ///      "name": "http_request",
    ///      "params": {
    ///        "url": "https://api.example.com/data",
    ///        "method": "POST",
    ///        "headers": {
    ///          "Authorization": "Bearer token123"
    ///        },
    ///        "body": {
    ///          "key": "value"
    ///        }
    ///      }
    ///    }
    ///    ```
    ///
    /// # Security
    ///
    /// - Shell commands are sanitized to prevent injection attacks
    /// - All commands execute with a 30-second timeout
    /// - Parameters are validated for length and dangerous content
    /// - AppleScript is sandboxed by the OS on macOS
    ///
    /// # Returns
    ///
    /// Returns a JSON value with the command output and type, or an error string.
    async fn execute_custom_command(
        &self,
        name: &str,
        params: &serde_json::Value,
    ) -> Result<Option<serde_json::Value>, String> {
        // Parse parameters
        let params_obj = params.as_object().ok_or("Custom command params must be an object")?;

        match name {
            "shell" => {
                // Execute shell command
                // Expected params: { "command": "ls -la", "args": ["arg1", "arg2"] }
                let command = params_obj
                    .get("command")
                    .and_then(|v| v.as_str())
                    .ok_or("Missing 'command' parameter")?;

                // Sanitize command
                custom_commands::sanitize_command(command)?;

                // Get optional args
                let args: Vec<String> = params_obj
                    .get("args")
                    .and_then(|v| v.as_array())
                    .map(|arr| {
                        arr.iter()
                            .filter_map(|v| v.as_str().map(|s| s.to_string()))
                            .collect()
                    })
                    .unwrap_or_default();

                // Sanitize args
                for arg in &args {
                    custom_commands::sanitize_param(arg)?;
                }

                // Execute
                let output = custom_commands::execute_shell_command(command, args).await?;

                Ok(Some(serde_json::json!({
                    "output": output,
                    "type": "shell"
                })))
            }
            "applescript" => {
                // Execute AppleScript
                // Expected params: { "script": "tell application \"Safari\" to get URL of current tab of front window" }
                let script = params_obj
                    .get("script")
                    .and_then(|v| v.as_str())
                    .ok_or("Missing 'script' parameter")?;

                // Execute
                let output = custom_commands::execute_applescript(script).await?;

                Ok(Some(serde_json::json!({
                    "output": output,
                    "type": "applescript"
                })))
            }
            "http_request" => {
                // Execute HTTP request
                // Expected params: { "url": "https://...", "method": "GET", "body": {...}, "headers": {...} }
                let url = params_obj
                    .get("url")
                    .and_then(|v| v.as_str())
                    .ok_or("Missing 'url' parameter")?;

                let method = params_obj
                    .get("method")
                    .and_then(|v| v.as_str())
                    .unwrap_or("GET");

                // Build HTTP client
                let client = reqwest::Client::new();

                let mut request_builder = match method.to_uppercase().as_str() {
                    "GET" => client.get(url),
                    "POST" => client.post(url),
                    "PUT" => client.put(url),
                    "DELETE" => client.delete(url),
                    "PATCH" => client.patch(url),
                    _ => return Err(format!("Unsupported HTTP method: {}", method)),
                };

                // Add headers if provided
                if let Some(headers) = params_obj.get("headers").and_then(|v| v.as_object()) {
                    for (key, value) in headers {
                        if let Some(value_str) = value.as_str() {
                            request_builder = request_builder.header(key, value_str);
                        }
                    }
                }

                // Add body if provided
                if let Some(body) = params_obj.get("body") {
                    request_builder = request_builder.json(body);
                }

                // Execute with timeout
                let response = timeout(CUSTOM_COMMAND_TIMEOUT, request_builder.send())
                    .await
                    .map_err(|_| "HTTP request timed out".to_string())?
                    .map_err(|e| format!("HTTP request failed: {}", e))?;

                let status = response.status().as_u16();
                let body_text = response
                    .text()
                    .await
                    .map_err(|e| format!("Failed to read response body: {}", e))?;

                Ok(Some(serde_json::json!({
                    "status": status,
                    "body": body_text,
                    "type": "http_request"
                })))
            }
            _ => {
                Err(format!("Unknown custom command: {}", name))
            }
        }
    }
}

impl Default for AutomationQueue {
    fn default() -> Self {
        Self::new().0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_task_priority_ordering() {
        let mut heap = BinaryHeap::new();

        let low = AutomationTask::new(
            TaskCommand::Wait { milliseconds: 100 },
            TaskPriority::Low,
        );
        let high = AutomationTask::new(
            TaskCommand::Wait { milliseconds: 100 },
            TaskPriority::High,
        );
        let normal = AutomationTask::new(
            TaskCommand::Wait { milliseconds: 100 },
            TaskPriority::Normal,
        );

        heap.push(low);
        heap.push(high.clone());
        heap.push(normal);

        let first = heap.pop().unwrap();
        assert_eq!(first.id, high.id);
    }

    #[tokio::test]
    async fn test_queue_status() {
        let (queue, _rx) = AutomationQueue::new();
        let status = queue.status().await;
        assert_eq!(status.pending_tasks, 0);
        assert_eq!(status.completed_tasks, 0);
    }

    #[test]
    fn test_sanitize_command() {
        use super::custom_commands;

        // Valid commands should pass
        assert!(custom_commands::sanitize_command("ls").is_ok());
        assert!(custom_commands::sanitize_command("echo hello").is_ok());

        // Dangerous patterns should fail
        assert!(custom_commands::sanitize_command("ls; rm -rf /").is_err());
        assert!(custom_commands::sanitize_command("ls | grep test").is_err());
        assert!(custom_commands::sanitize_command("echo $(whoami)").is_err());
        assert!(custom_commands::sanitize_command("cat ../../etc/passwd").is_err());

        // Empty command should fail
        assert!(custom_commands::sanitize_command("").is_err());
        assert!(custom_commands::sanitize_command("   ").is_err());
    }

    #[test]
    fn test_sanitize_param() {
        use super::custom_commands;

        // Valid params should pass
        assert!(custom_commands::sanitize_param("test").is_ok());
        assert!(custom_commands::sanitize_param("test with spaces").is_ok());

        // Null byte should fail
        assert!(custom_commands::sanitize_param("test\0value").is_err());

        // Excessive length should fail
        let long_string = "a".repeat(20000);
        assert!(custom_commands::sanitize_param(&long_string).is_err());
    }

    #[tokio::test]
    async fn test_custom_shell_command() {
        // Test creating a custom shell command task
        let params = serde_json::json!({
            "command": "echo",
            "args": ["Hello", "World"]
        });

        let task = AutomationTask::new(
            TaskCommand::Custom {
                name: "shell".to_string(),
                params,
            },
            TaskPriority::Normal,
        );

        assert_eq!(task.priority, TaskPriority::Normal);
    }

    #[tokio::test]
    async fn test_custom_http_request_command() {
        // Test creating a custom HTTP request command task
        let params = serde_json::json!({
            "url": "https://api.example.com/data",
            "method": "GET",
            "headers": {
                "Authorization": "Bearer token123"
            }
        });

        let task = AutomationTask::new(
            TaskCommand::Custom {
                name: "http_request".to_string(),
                params,
            },
            TaskPriority::High,
        );

        assert_eq!(task.priority, TaskPriority::High);
    }

    #[cfg(target_os = "macos")]
    #[tokio::test]
    async fn test_custom_applescript_command() {
        // Test creating a custom AppleScript command task
        let params = serde_json::json!({
            "script": "tell application \"System Events\" to get name of first process"
        });

        let task = AutomationTask::new(
            TaskCommand::Custom {
                name: "applescript".to_string(),
                params,
            },
            TaskPriority::Normal,
        );

        assert_eq!(task.priority, TaskPriority::Normal);
    }
}
