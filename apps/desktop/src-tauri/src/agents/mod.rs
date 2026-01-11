//! AI Agents module for Observer
//!
//! Provides integration with Claude Code CLI for autonomous task execution.

pub mod claude_code;
pub mod prompts;
pub mod task_queue;
pub mod triggers;
pub mod types;

pub use claude_code::{AgentTaskResult, run_agent_task};
pub use task_queue::{AgentTask, Priority, TaskQueue, TaskStatus};
pub use triggers::TriggerEngine;
pub use types::{
    ActionItem,
    AgentType,
    ArchitectAgent,
    CodeReviewAgent,
    DevOpsAgent,
    ErrorType,
    GitAssistantAgent,
    HealthStatus,
    MeetingData,
    MeetingNotesAgent,
    ServerMonitorAgent,
};

use serde::{Deserialize, Serialize};

/// Kind of agent for selection
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AgentKind {
    /// DevOps operations (CI/CD, deployments)
    DevOps,
    /// Code review and quality analysis
    CodeReview,
    /// Architecture and design decisions
    Architect,
    /// Server monitoring and health checks
    ServerMonitor,
    /// Git operations and commit assistance
    GitAssistant,
    /// Meeting notes and summarization
    MeetingNotes,
    /// Generic agent - default for backward compatibility
    Generic,
}

impl AgentKind {
    /// Get all available agent kinds
    pub fn all() -> &'static [AgentKind] {
        &[
            AgentKind::DevOps,
            AgentKind::CodeReview,
            AgentKind::Architect,
            AgentKind::ServerMonitor,
            AgentKind::GitAssistant,
            AgentKind::MeetingNotes,
            AgentKind::Generic,
        ]
    }

    /// Get display name for the agent kind
    pub fn display_name(&self) -> &'static str {
        match self {
            AgentKind::DevOps => "DevOps",
            AgentKind::CodeReview => "Code Review",
            AgentKind::Architect => "Architect",
            AgentKind::ServerMonitor => "Server Monitor",
            AgentKind::GitAssistant => "Git Assistant",
            AgentKind::MeetingNotes => "Meeting Notes",
            AgentKind::Generic => "Generic",
        }
    }
}

impl Default for AgentKind {
    fn default() -> Self {
        AgentKind::Generic
    }
}

/// Agent configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentConfig {
    /// Path to Claude CLI binary
    pub claude_path: String,
    /// Maximum iterations for agent loop
    pub max_iterations: u32,
    /// Timeout for Claude CLI calls (seconds)
    pub timeout_secs: u64,
    /// Project path for context
    pub project_path: Option<String>,
}

impl Default for AgentConfig {
    fn default() -> Self {
        Self {
            claude_path: "claude".to_string(),
            max_iterations: 10,
            timeout_secs: 120,
            project_path: None,
        }
    }
}

impl AgentConfig {
    /// Get config file path
    fn config_path() -> std::path::PathBuf {
        dirs::config_dir()
            .unwrap_or_else(|| std::path::PathBuf::from("."))
            .join("observer")
            .join("agent_config.json")
    }

    /// Load config from file
    pub fn load() -> Result<Self, String> {
        let path = Self::config_path();
        if !path.exists() {
            return Ok(Self::default());
        }

        let content = std::fs::read_to_string(&path)
            .map_err(|e| format!("Не удалось прочитать конфиг: {}", e))?;

        serde_json::from_str(&content)
            .map_err(|e| format!("Не удалось распарсить конфиг: {}", e))
    }

    /// Save config to file
    pub fn save(&self) -> Result<(), String> {
        let path = Self::config_path();

        // Ensure parent directory exists
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| format!("Не удалось создать директорию конфига: {}", e))?;
        }

        let content = serde_json::to_string_pretty(self)
            .map_err(|e| format!("Не удалось сериализовать конфиг: {}", e))?;

        std::fs::write(&path, content)
            .map_err(|e| format!("Не удалось записать конфиг: {}", e))
    }
}

/// Agent status
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AgentStatus {
    Idle,
    Running,
    WaitingConfirmation,
    Completed,
    Failed,
}

/// Generic agent for backward compatibility
struct GenericAgent;

impl AgentType for GenericAgent {
    fn name(&self) -> &'static str {
        "Generic"
    }

    fn system_prompt(&self) -> &str {
        "You are a helpful AI assistant. Analyze the context and provide assistance."
    }

    fn should_handle(&self, _app_name: &str, _text: &str) -> bool {
        // Generic agent always handles as fallback
        true
    }
}

/// Agent manager for coordinating multiple agents
pub struct AgentManager {
    config: AgentConfig,
    status: AgentStatus,
    trigger_engine: TriggerEngine,
    current_agent_kind: AgentKind,
    task_queue: TaskQueue,
}

impl AgentManager {
    /// Create new agent manager
    pub fn new(config: AgentConfig) -> Self {
        // Try to load existing task queue, or create new one
        let task_queue = TaskQueue::load().unwrap_or_else(|_| TaskQueue::new());

        Self {
            config,
            status: AgentStatus::Idle,
            trigger_engine: TriggerEngine::new(),
            current_agent_kind: AgentKind::Generic,
            task_queue,
        }
    }

    /// Get current status
    pub fn status(&self) -> AgentStatus {
        self.status
    }

    /// Get current agent kind
    pub fn current_agent_kind(&self) -> AgentKind {
        self.current_agent_kind
    }

    /// Set current agent kind
    pub fn set_agent_kind(&mut self, kind: AgentKind) {
        self.current_agent_kind = kind;
    }

    /// Create an agent instance based on kind
    pub fn create_agent(kind: AgentKind) -> Box<dyn AgentType> {
        match kind {
            AgentKind::DevOps => Box::new(DevOpsAgent::new()),
            AgentKind::CodeReview => Box::new(CodeReviewAgent::new()),
            AgentKind::Architect => Box::new(ArchitectAgent::new()),
            AgentKind::ServerMonitor => Box::new(ServerMonitorAgent::new()),
            AgentKind::GitAssistant => Box::new(GitAssistantAgent::new()),
            AgentKind::MeetingNotes => Box::new(MeetingNotesAgent::new()),
            AgentKind::Generic => Box::new(GenericAgent),
        }
    }

    /// Select the best agent for the given context
    ///
    /// Collects all agents that can handle the context and returns
    /// the one with highest priority (based on `priority()` method).
    /// Falls back to Generic if no specialized agent matches.
    pub fn select_agent_for_context(app_name: &str, text: &str) -> AgentKind {
        let specialized_agents = [
            AgentKind::ServerMonitor,
            AgentKind::DevOps,
            AgentKind::CodeReview,
            AgentKind::GitAssistant,
            AgentKind::Architect,
            AgentKind::MeetingNotes,
        ];

        // Collect all agents that can handle this context with their priorities
        let mut candidates: Vec<(AgentKind, u32)> = Vec::new();

        for kind in specialized_agents {
            let agent = Self::create_agent(kind);
            if agent.should_handle(app_name, text) {
                candidates.push((kind, agent.priority()));
            }
        }

        // Return agent with highest priority, or Generic if no candidates
        candidates
            .into_iter()
            .max_by_key(|(_, priority)| *priority)
            .map(|(kind, _)| kind)
            .unwrap_or(AgentKind::Generic)
    }

    /// Run agent with context (backward compatible)
    pub async fn run(&mut self, context: &str) -> Result<AgentTaskResult, String> {
        self.run_with_kind(context, self.current_agent_kind).await
    }

    /// Run agent with specific kind
    pub async fn run_with_kind(
        &mut self,
        context: &str,
        kind: AgentKind,
    ) -> Result<AgentTaskResult, String> {
        self.status = AgentStatus::Running;
        self.current_agent_kind = kind;

        // Extract data from agent and drop it before await
        // (Box<dyn AgentType> is not Send, so we can't hold it across await)
        let (system_prompt, max_iterations) = {
            let agent = Self::create_agent(kind);
            (
                agent.system_prompt().to_owned(),
                agent.max_iterations().min(self.config.max_iterations),
            )
        };

        // Build context with system prompt
        let full_context = format!(
            "{}\n\n---\n\nContext:\n{}",
            system_prompt, context
        );

        let result = run_agent_task(
            &full_context,
            max_iterations,
            &self.config.claude_path,
            self.config.timeout_secs,
        ).await;

        match &result {
            Ok(task_result) => {
                if task_result.needs_confirmation {
                    self.status = AgentStatus::WaitingConfirmation;
                } else {
                    self.status = AgentStatus::Completed;
                }
            }
            Err(_) => self.status = AgentStatus::Failed,
        }

        result
    }

    /// Check triggers and run agent if triggered
    pub async fn check_and_run(&mut self, ocr_text: &str, app_name: &str) -> Option<AgentTaskResult> {
        let triggers = self.trigger_engine.check(ocr_text, app_name);

        if triggers.is_empty() {
            return None;
        }

        println!("[Agent] Triggered by: {:?}", triggers);

        // Select appropriate agent for context
        let agent_kind = Self::select_agent_for_context(app_name, ocr_text);
        println!("[Agent] Selected agent: {:?}", agent_kind);

        // Build context from triggers
        let context = format!(
            "Triggers: {:?}\nOCR Text: {}\nApp: {}",
            triggers, ocr_text, app_name
        );

        match self.run_with_kind(&context, agent_kind).await {
            Ok(result) => Some(result),
            Err(e) => {
                eprintln!("[Agent] Error: {}", e);
                None
            }
        }
    }

    /// Record user activity (resets idle timer)
    pub fn record_activity(&mut self) {
        self.trigger_engine.record_activity();
    }

    /// Get trigger engine for configuration (mutable)
    pub fn trigger_engine_mut(&mut self) -> &mut TriggerEngine {
        &mut self.trigger_engine
    }

    /// Get trigger engine (immutable)
    pub fn trigger_engine(&self) -> &TriggerEngine {
        &self.trigger_engine
    }

    /// Get current config
    pub fn config(&self) -> &AgentConfig {
        &self.config
    }

    /// Update config
    pub fn set_config(&mut self, config: AgentConfig) {
        self.config = config;
    }

    // ========== Task Queue Methods ==========

    /// Add a task to the queue
    pub fn add_task(&mut self, description: &str, priority: Priority) -> AgentTask {
        let task = self.task_queue.add_task(description, priority);
        // Auto-save after adding
        let _ = self.task_queue.save();
        task
    }

    /// Add a task with project path to the queue
    pub fn add_task_with_project(
        &mut self,
        description: &str,
        priority: Priority,
        project_path: &str,
    ) -> AgentTask {
        let task = self.task_queue.add_task_with_project(description, priority, project_path);
        let _ = self.task_queue.save();
        task
    }

    /// Get the next pending task
    pub fn get_next_task(&self) -> Option<&AgentTask> {
        self.task_queue.get_next_task()
    }

    /// Get the next task matching the current project context
    pub fn get_next_task_for_project(&self, project_path: Option<&str>) -> Option<&AgentTask> {
        self.task_queue.get_next_task_for_project(project_path)
    }

    /// Get pending task count
    pub fn pending_task_count(&self) -> usize {
        self.task_queue.pending_count()
    }

    /// Get all tasks
    pub fn get_all_tasks(&self) -> &[AgentTask] {
        self.task_queue.get_all_tasks()
    }

    /// Process the next task from the queue
    ///
    /// This picks the highest priority task, runs the agent,
    /// and updates the task status based on the result.
    pub async fn process_next_task(&mut self) -> Option<AgentTaskResult> {
        // Get the next task
        let task_id = {
            let task = self.task_queue.get_next_task()?;
            task.id.clone()
        };

        // Start the task
        if let Err(e) = self.task_queue.start_task(&task_id) {
            eprintln!("[TaskQueue] Failed to start task: {}", e);
            return None;
        }
        let _ = self.task_queue.save();

        // Get task details
        let (description, project_path) = {
            let task = self.task_queue.get_task(&task_id)?;
            (task.description.clone(), task.project_path.clone())
        };

        // Build context
        let context = if let Some(path) = &project_path {
            format!("Project: {}\nTask: {}", path, description)
        } else {
            format!("Task: {}", description)
        };

        // Run the agent
        let result = self.run(&context).await;

        // Update task status based on result
        match &result {
            Ok(task_result) => {
                let result_summary = format!(
                    "Action: {}\nReason: {}",
                    task_result.final_action, task_result.reason
                );
                if let Err(e) = self.task_queue.complete_task(&task_id, &result_summary) {
                    eprintln!("[TaskQueue] Failed to complete task: {}", e);
                }
            }
            Err(e) => {
                if let Err(err) = self.task_queue.fail_task(&task_id, e) {
                    eprintln!("[TaskQueue] Failed to mark task as failed: {}", err);
                }
            }
        }

        let _ = self.task_queue.save();
        result.ok()
    }

    /// Cancel a task
    pub fn cancel_task(&mut self, task_id: &str) -> Result<(), String> {
        let result = self.task_queue.cancel_task(task_id);
        let _ = self.task_queue.save();
        result
    }

    /// Cleanup old completed/failed tasks
    pub fn cleanup_old_tasks(&mut self, max_age_days: i64) {
        self.task_queue.cleanup_old_tasks(chrono::Duration::days(max_age_days));
        let _ = self.task_queue.save();
    }

    /// Save task queue to disk
    pub fn save_task_queue(&self) -> Result<(), String> {
        self.task_queue.save()
    }

    /// Get task queue reference
    pub fn task_queue(&self) -> &TaskQueue {
        &self.task_queue
    }

    /// Get mutable task queue reference
    pub fn task_queue_mut(&mut self) -> &mut TaskQueue {
        &mut self.task_queue
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_agent_config_default() {
        let config = AgentConfig::default();
        assert_eq!(config.max_iterations, 10);
        assert_eq!(config.timeout_secs, 120);
    }

    #[test]
    fn test_agent_manager_status() {
        let manager = AgentManager::new(AgentConfig::default());
        assert_eq!(manager.status(), AgentStatus::Idle);
    }

    #[test]
    fn test_agent_kind_default() {
        let kind = AgentKind::default();
        assert_eq!(kind, AgentKind::Generic);
    }

    #[test]
    fn test_agent_kind_all() {
        let all = AgentKind::all();
        assert_eq!(all.len(), 7);
        assert!(all.contains(&AgentKind::DevOps));
        assert!(all.contains(&AgentKind::CodeReview));
        assert!(all.contains(&AgentKind::Architect));
        assert!(all.contains(&AgentKind::ServerMonitor));
        assert!(all.contains(&AgentKind::GitAssistant));
        assert!(all.contains(&AgentKind::MeetingNotes));
        assert!(all.contains(&AgentKind::Generic));
    }

    #[test]
    fn test_agent_kind_display_name() {
        assert_eq!(AgentKind::DevOps.display_name(), "DevOps");
        assert_eq!(AgentKind::CodeReview.display_name(), "Code Review");
        assert_eq!(AgentKind::Generic.display_name(), "Generic");
    }

    #[test]
    fn test_create_agent() {
        // Test all 7 agent kinds
        let agent = AgentManager::create_agent(AgentKind::DevOps);
        assert_eq!(agent.name(), "DevOps");

        let agent = AgentManager::create_agent(AgentKind::CodeReview);
        assert_eq!(agent.name(), "Code Review");

        let agent = AgentManager::create_agent(AgentKind::Architect);
        assert_eq!(agent.name(), "Architect");

        let agent = AgentManager::create_agent(AgentKind::ServerMonitor);
        assert_eq!(agent.name(), "Server Monitor");

        let agent = AgentManager::create_agent(AgentKind::GitAssistant);
        assert_eq!(agent.name(), "Git Assistant");

        let agent = AgentManager::create_agent(AgentKind::MeetingNotes);
        assert_eq!(agent.name(), "Meeting Notes");

        let agent = AgentManager::create_agent(AgentKind::Generic);
        assert_eq!(agent.name(), "Generic");
    }

    #[test]
    fn test_agent_priority() {
        // GitAssistant should have highest priority (80)
        let agent = AgentManager::create_agent(AgentKind::GitAssistant);
        assert_eq!(agent.priority(), 80);

        // Architect should have medium priority (50)
        let agent = AgentManager::create_agent(AgentKind::Architect);
        assert_eq!(agent.priority(), 50);

        // Others should have default priority (0)
        let agent = AgentManager::create_agent(AgentKind::DevOps);
        assert_eq!(agent.priority(), 0);
    }

    #[test]
    fn test_agent_manager_current_kind() {
        let mut manager = AgentManager::new(AgentConfig::default());
        assert_eq!(manager.current_agent_kind(), AgentKind::Generic);

        manager.set_agent_kind(AgentKind::DevOps);
        assert_eq!(manager.current_agent_kind(), AgentKind::DevOps);
    }

    #[test]
    fn test_select_agent_for_context_git() {
        // Git context should select GitAssistant
        let kind = AgentManager::select_agent_for_context("Terminal", "git status");
        assert_eq!(kind, AgentKind::GitAssistant);
    }

    #[test]
    fn test_select_agent_for_context_fallback() {
        // Random text should fall back to Generic
        let kind = AgentManager::select_agent_for_context("TextEdit", "hello world");
        assert_eq!(kind, AgentKind::Generic);
    }
}
