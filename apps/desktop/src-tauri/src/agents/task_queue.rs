//! Task Queue for Observer
//!
//! Manages user tasks with priority-based scheduling and persistent storage.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use uuid::Uuid;

/// Task priority levels
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum Priority {
    Low = 0,
    Normal = 1,
    High = 2,
    Urgent = 3,
}

impl Default for Priority {
    fn default() -> Self {
        Priority::Normal
    }
}

/// Task execution status
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TaskStatus {
    Pending,
    InProgress,
    Completed,
    Failed,
    Cancelled,
}

impl Default for TaskStatus {
    fn default() -> Self {
        TaskStatus::Pending
    }
}

/// Agent task with metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentTask {
    /// Unique task identifier
    pub id: String,
    /// Task description
    pub description: String,
    /// Project path for task context (optional)
    pub project_path: Option<String>,
    /// Task priority
    pub priority: Priority,
    /// Current status
    pub status: TaskStatus,
    /// When the task was created
    pub created_at: DateTime<Utc>,
    /// When the task started execution
    pub started_at: Option<DateTime<Utc>>,
    /// When the task was completed
    pub completed_at: Option<DateTime<Utc>>,
    /// Result of successful execution
    pub result: Option<String>,
    /// Error message if failed
    pub error: Option<String>,
}

impl AgentTask {
    /// Create a new task with the given description and priority
    pub fn new(description: &str, priority: Priority) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            description: description.to_string(),
            project_path: None,
            priority,
            status: TaskStatus::Pending,
            created_at: Utc::now(),
            started_at: None,
            completed_at: None,
            result: None,
            error: None,
        }
    }

    /// Create a new task with project path
    pub fn with_project_path(description: &str, priority: Priority, project_path: &str) -> Self {
        let mut task = Self::new(description, priority);
        task.project_path = Some(project_path.to_string());
        task
    }
}

/// Persistent task storage for serialization
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
struct TaskQueueStorage {
    tasks: Vec<AgentTask>,
}

/// Task queue manager with priority-based scheduling
pub struct TaskQueue {
    tasks: Vec<AgentTask>,
    config_path: PathBuf,
}

impl TaskQueue {
    /// Create a new empty task queue
    pub fn new() -> Self {
        Self {
            tasks: Vec::new(),
            config_path: Self::default_config_path(),
        }
    }

    /// Get the default config path
    fn default_config_path() -> PathBuf {
        dirs::config_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("observer")
            .join("task_queue.json")
    }

    /// Add a new task to the queue
    pub fn add_task(&mut self, description: &str, priority: Priority) -> AgentTask {
        let task = AgentTask::new(description, priority);
        self.tasks.push(task.clone());
        task
    }

    /// Add a new task with project path
    pub fn add_task_with_project(
        &mut self,
        description: &str,
        priority: Priority,
        project_path: &str,
    ) -> AgentTask {
        let task = AgentTask::with_project_path(description, priority, project_path);
        self.tasks.push(task.clone());
        task
    }

    /// Get the next task to execute based on priority and creation time
    ///
    /// Selection logic:
    /// 1. Higher priority first (Urgent > High > Normal > Low)
    /// 2. Within same priority, older tasks first (by created_at)
    /// 3. Only returns Pending tasks
    pub fn get_next_task(&self) -> Option<&AgentTask> {
        self.tasks
            .iter()
            .filter(|t| t.status == TaskStatus::Pending)
            .max_by(|a, b| {
                // First compare by priority (higher is better)
                match a.priority.cmp(&b.priority) {
                    std::cmp::Ordering::Equal => {
                        // Same priority: older tasks first (smaller created_at is better)
                        // Note: We want older (smaller) created_at to win, so reverse comparison
                        a.created_at.cmp(&b.created_at).reverse()
                    }
                    other => other,
                }
            })
    }

    /// Get the next task that matches the current project context
    ///
    /// If current_project is Some, returns tasks that either:
    /// - Have no project_path (can run anywhere)
    /// - Have matching project_path
    ///
    /// If current_project is None, only returns tasks without project_path
    pub fn get_next_task_for_project(&self, current_project: Option<&str>) -> Option<&AgentTask> {
        self.tasks
            .iter()
            .filter(|t| t.status == TaskStatus::Pending)
            .filter(|t| match (&t.project_path, current_project) {
                // Task has no project requirement - can run anywhere
                (None, _) => true,
                // Task requires project, but no current project - skip
                (Some(_), None) => false,
                // Task requires project, check if it matches
                (Some(task_path), Some(current)) => task_path == current,
            })
            .max_by(|a, b| match a.priority.cmp(&b.priority) {
                std::cmp::Ordering::Equal => a.created_at.cmp(&b.created_at).reverse(),
                other => other,
            })
    }

    /// Start a task by ID
    pub fn start_task(&mut self, id: &str) -> Result<(), String> {
        let task = self
            .tasks
            .iter_mut()
            .find(|t| t.id == id)
            .ok_or_else(|| format!("Task not found: {}", id))?;

        if task.status != TaskStatus::Pending {
            return Err(format!("Cannot start task with status {:?}", task.status));
        }

        task.status = TaskStatus::InProgress;
        task.started_at = Some(Utc::now());
        Ok(())
    }

    /// Mark a task as completed with result
    pub fn complete_task(&mut self, id: &str, result: &str) -> Result<(), String> {
        let task = self
            .tasks
            .iter_mut()
            .find(|t| t.id == id)
            .ok_or_else(|| format!("Task not found: {}", id))?;

        if task.status != TaskStatus::InProgress {
            return Err(format!(
                "Cannot complete task with status {:?}",
                task.status
            ));
        }

        task.status = TaskStatus::Completed;
        task.completed_at = Some(Utc::now());
        task.result = Some(result.to_string());
        Ok(())
    }

    /// Mark a task as failed with error message
    pub fn fail_task(&mut self, id: &str, error: &str) -> Result<(), String> {
        let task = self
            .tasks
            .iter_mut()
            .find(|t| t.id == id)
            .ok_or_else(|| format!("Task not found: {}", id))?;

        if task.status != TaskStatus::InProgress {
            return Err(format!("Cannot fail task with status {:?}", task.status));
        }

        task.status = TaskStatus::Failed;
        task.completed_at = Some(Utc::now());
        task.error = Some(error.to_string());
        Ok(())
    }

    /// Cancel a pending task
    pub fn cancel_task(&mut self, id: &str) -> Result<(), String> {
        let task = self
            .tasks
            .iter_mut()
            .find(|t| t.id == id)
            .ok_or_else(|| format!("Task not found: {}", id))?;

        if task.status != TaskStatus::Pending && task.status != TaskStatus::InProgress {
            return Err(format!("Cannot cancel task with status {:?}", task.status));
        }

        task.status = TaskStatus::Cancelled;
        task.completed_at = Some(Utc::now());
        Ok(())
    }

    /// Get all pending tasks
    pub fn get_pending_tasks(&self) -> Vec<&AgentTask> {
        self.tasks
            .iter()
            .filter(|t| t.status == TaskStatus::Pending)
            .collect()
    }

    /// Get all tasks with a specific status
    pub fn get_tasks_by_status(&self, status: TaskStatus) -> Vec<&AgentTask> {
        self.tasks.iter().filter(|t| t.status == status).collect()
    }

    /// Get a task by ID
    pub fn get_task(&self, id: &str) -> Option<&AgentTask> {
        self.tasks.iter().find(|t| t.id == id)
    }

    /// Get all tasks
    pub fn get_all_tasks(&self) -> &[AgentTask] {
        &self.tasks
    }

    /// Get count of pending tasks
    pub fn pending_count(&self) -> usize {
        self.tasks
            .iter()
            .filter(|t| t.status == TaskStatus::Pending)
            .count()
    }

    /// Get count of in-progress tasks
    pub fn in_progress_count(&self) -> usize {
        self.tasks
            .iter()
            .filter(|t| t.status == TaskStatus::InProgress)
            .count()
    }

    /// Remove completed/failed/cancelled tasks older than the given duration
    pub fn cleanup_old_tasks(&mut self, max_age: chrono::Duration) {
        let cutoff = Utc::now() - max_age;
        self.tasks.retain(|t| match t.status {
            TaskStatus::Pending | TaskStatus::InProgress => true,
            TaskStatus::Completed | TaskStatus::Failed | TaskStatus::Cancelled => t
                .completed_at
                .map(|completed| completed > cutoff)
                .unwrap_or(true),
        });
    }

    /// Load task queue from persistent storage
    pub fn load() -> Result<Self, String> {
        let config_path = Self::default_config_path();

        if !config_path.exists() {
            return Ok(Self::new());
        }

        let content = std::fs::read_to_string(&config_path)
            .map_err(|e| format!("Failed to read task queue: {}", e))?;

        let storage: TaskQueueStorage = serde_json::from_str(&content)
            .map_err(|e| format!("Failed to parse task queue: {}", e))?;

        Ok(Self {
            tasks: storage.tasks,
            config_path,
        })
    }

    /// Save task queue to persistent storage
    pub fn save(&self) -> Result<(), String> {
        // Ensure parent directory exists
        if let Some(parent) = self.config_path.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create config directory: {}", e))?;
        }

        let storage = TaskQueueStorage {
            tasks: self.tasks.clone(),
        };

        let content = serde_json::to_string_pretty(&storage)
            .map_err(|e| format!("Failed to serialize task queue: {}", e))?;

        std::fs::write(&self.config_path, content)
            .map_err(|e| format!("Failed to write task queue: {}", e))
    }
}

impl Default for TaskQueue {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_priority_ordering() {
        assert!(Priority::Urgent > Priority::High);
        assert!(Priority::High > Priority::Normal);
        assert!(Priority::Normal > Priority::Low);
    }

    #[test]
    fn test_add_task() {
        let mut queue = TaskQueue::new();
        let task = queue.add_task("Test task", Priority::Normal);

        assert_eq!(task.description, "Test task");
        assert_eq!(task.priority, Priority::Normal);
        assert_eq!(task.status, TaskStatus::Pending);
        assert!(task.project_path.is_none());
    }

    #[test]
    fn test_add_task_with_project() {
        let mut queue = TaskQueue::new();
        let task = queue.add_task_with_project("Test task", Priority::High, "/path/to/project");

        assert_eq!(task.project_path, Some("/path/to/project".to_string()));
    }

    #[test]
    fn test_get_next_task_priority() {
        let mut queue = TaskQueue::new();

        queue.add_task("Low priority", Priority::Low);
        queue.add_task("Urgent priority", Priority::Urgent);
        queue.add_task("Normal priority", Priority::Normal);

        let next = queue.get_next_task().unwrap();
        assert_eq!(next.priority, Priority::Urgent);
    }

    #[test]
    fn test_get_next_task_creation_order() {
        let mut queue = TaskQueue::new();

        let task1 = queue.add_task("First task", Priority::Normal);
        let _task2 = queue.add_task("Second task", Priority::Normal);

        let next = queue.get_next_task().unwrap();
        assert_eq!(next.id, task1.id);
    }

    #[test]
    fn test_start_task() {
        let mut queue = TaskQueue::new();
        let task = queue.add_task("Test task", Priority::Normal);

        queue.start_task(&task.id).unwrap();

        let updated = queue.get_task(&task.id).unwrap();
        assert_eq!(updated.status, TaskStatus::InProgress);
        assert!(updated.started_at.is_some());
    }

    #[test]
    fn test_complete_task() {
        let mut queue = TaskQueue::new();
        let task = queue.add_task("Test task", Priority::Normal);

        queue.start_task(&task.id).unwrap();
        queue
            .complete_task(&task.id, "Task completed successfully")
            .unwrap();

        let updated = queue.get_task(&task.id).unwrap();
        assert_eq!(updated.status, TaskStatus::Completed);
        assert!(updated.completed_at.is_some());
        assert_eq!(
            updated.result,
            Some("Task completed successfully".to_string())
        );
    }

    #[test]
    fn test_fail_task() {
        let mut queue = TaskQueue::new();
        let task = queue.add_task("Test task", Priority::Normal);

        queue.start_task(&task.id).unwrap();
        queue.fail_task(&task.id, "Something went wrong").unwrap();

        let updated = queue.get_task(&task.id).unwrap();
        assert_eq!(updated.status, TaskStatus::Failed);
        assert_eq!(updated.error, Some("Something went wrong".to_string()));
    }

    #[test]
    fn test_cancel_task() {
        let mut queue = TaskQueue::new();
        let task = queue.add_task("Test task", Priority::Normal);

        queue.cancel_task(&task.id).unwrap();

        let updated = queue.get_task(&task.id).unwrap();
        assert_eq!(updated.status, TaskStatus::Cancelled);
    }

    #[test]
    fn test_get_pending_tasks() {
        let mut queue = TaskQueue::new();

        let task1 = queue.add_task("Task 1", Priority::Normal);
        let task2 = queue.add_task("Task 2", Priority::High);
        queue.add_task("Task 3", Priority::Low);

        queue.start_task(&task1.id).unwrap();
        queue.complete_task(&task1.id, "Done").unwrap();

        queue.start_task(&task2.id).unwrap();

        let pending = queue.get_pending_tasks();
        assert_eq!(pending.len(), 1);
        assert_eq!(pending[0].description, "Task 3");
    }

    #[test]
    fn test_get_next_task_for_project() {
        let mut queue = TaskQueue::new();

        queue.add_task_with_project("Project A task", Priority::Urgent, "/path/to/project-a");
        queue.add_task("Global task", Priority::High);
        queue.add_task_with_project("Project B task", Priority::High, "/path/to/project-b");

        // With no current project, only global tasks should be returned
        let next = queue.get_next_task_for_project(None).unwrap();
        assert_eq!(next.description, "Global task");

        // With project-a, should return the urgent project-a task
        let next = queue
            .get_next_task_for_project(Some("/path/to/project-a"))
            .unwrap();
        assert_eq!(next.description, "Project A task");

        // With project-b, should return project-b task (higher priority than global)
        let next = queue
            .get_next_task_for_project(Some("/path/to/project-b"))
            .unwrap();
        assert_eq!(next.description, "Project B task");
    }

    #[test]
    fn test_cannot_start_non_pending_task() {
        let mut queue = TaskQueue::new();
        let task = queue.add_task("Test task", Priority::Normal);

        queue.start_task(&task.id).unwrap();
        let result = queue.start_task(&task.id);

        assert!(result.is_err());
    }

    #[test]
    fn test_cannot_complete_non_in_progress_task() {
        let mut queue = TaskQueue::new();
        let task = queue.add_task("Test task", Priority::Normal);

        let result = queue.complete_task(&task.id, "Done");

        assert!(result.is_err());
    }

    #[test]
    fn test_pending_count() {
        let mut queue = TaskQueue::new();

        queue.add_task("Task 1", Priority::Normal);
        queue.add_task("Task 2", Priority::High);
        let task3 = queue.add_task("Task 3", Priority::Low);

        assert_eq!(queue.pending_count(), 3);

        queue.start_task(&task3.id).unwrap();
        assert_eq!(queue.pending_count(), 2);
    }
}
