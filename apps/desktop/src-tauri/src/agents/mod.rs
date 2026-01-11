//! AI Agents module for Observer
//!
//! Provides integration with Claude Code CLI for autonomous task execution.

pub mod claude_code;
pub mod triggers;

pub use claude_code::{AgentResponse, ask_claude, execute_command, run_agent_task};
pub use triggers::{Trigger, TriggerEngine, check_triggers};

use serde::{Deserialize, Serialize};

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

/// Agent status
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AgentStatus {
    Idle,
    Running,
    WaitingConfirmation,
    Completed,
    Failed,
}

/// Agent manager for coordinating multiple agents
pub struct AgentManager {
    config: AgentConfig,
    status: AgentStatus,
    trigger_engine: TriggerEngine,
}

impl AgentManager {
    /// Create new agent manager
    pub fn new(config: AgentConfig) -> Self {
        Self {
            config,
            status: AgentStatus::Idle,
            trigger_engine: TriggerEngine::new(),
        }
    }

    /// Get current status
    pub fn status(&self) -> AgentStatus {
        self.status
    }

    /// Run agent with context
    pub async fn run(&mut self, context: &str) -> Result<String, String> {
        self.status = AgentStatus::Running;

        let result = run_agent_task(
            context,
            self.config.max_iterations,
            &self.config.claude_path,
        ).await;

        match &result {
            Ok(_) => self.status = AgentStatus::Completed,
            Err(_) => self.status = AgentStatus::Failed,
        }

        result
    }

    /// Check triggers and run agent if triggered
    pub async fn check_and_run(&mut self, ocr_text: &str, app_name: &str) -> Option<String> {
        let triggers = self.trigger_engine.check(ocr_text, app_name);

        if triggers.is_empty() {
            return None;
        }

        println!("[Agent] Triggered by: {:?}", triggers);

        // Build context from triggers
        let context = format!(
            "Triggers: {:?}\nOCR Text: {}\nApp: {}",
            triggers, ocr_text, app_name
        );

        match self.run(&context).await {
            Ok(result) => Some(result),
            Err(e) => {
                eprintln!("[Agent] Error: {}", e);
                None
            }
        }
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
}
