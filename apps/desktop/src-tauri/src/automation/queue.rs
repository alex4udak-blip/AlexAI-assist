/// Task queue system for automation with priorities and pause/resume
/// Minimum 100ms interval between tasks

use serde::{Serialize, Deserialize};
use std::collections::BinaryHeap;
use std::cmp::Ordering;
use std::sync::Arc;
use tokio::sync::{mpsc, Mutex, RwLock};
use tokio::time::{Duration, sleep};
use uuid::Uuid;

const MIN_TASK_INTERVAL: Duration = Duration::from_millis(100);

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
                match screen::capture_screenshot() {
                    Ok(img) => {
                        match screen::encode_to_base64(&img) {
                            Ok(base64) => {
                                let output = serde_json::json!({ "base64": base64 });
                                Ok(Some(output))
                            }
                            Err(e) => Err(e),
                        }
                    }
                    Err(e) => Err(e),
                }
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
            TaskCommand::Custom { name: _, params: _ } => {
                Err("Custom commands not yet implemented".to_string())
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
}
