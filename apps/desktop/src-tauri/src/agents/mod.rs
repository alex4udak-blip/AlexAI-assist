//! AI Agents module for Observer
//!
//! Provides integration with Claude Code CLI for autonomous task execution.

pub mod claude_code;
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
}

impl AgentManager {
    /// Create new agent manager
    pub fn new(config: AgentConfig) -> Self {
        Self {
            config,
            status: AgentStatus::Idle,
            trigger_engine: TriggerEngine::new(),
            current_agent_kind: AgentKind::Generic,
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

        let agent = Self::create_agent(kind);
        let system_prompt = agent.system_prompt();
        let max_iterations = agent.max_iterations().min(self.config.max_iterations);

        // Build context with system prompt
        let full_context = format!(
            "{}\n\n---\n\nContext:\n{}",
            system_prompt, context
        );

        let result = run_agent_task(
            &full_context,
            max_iterations,
            &self.config.claude_path,
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
