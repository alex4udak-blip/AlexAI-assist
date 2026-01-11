//! AI Agents module for Observer
//!
//! Provides integration with Claude Code CLI for autonomous task execution.

pub mod claude_code;
pub mod triggers;

pub use claude_code::{AgentTaskResult, run_agent_task};
pub use triggers::TriggerEngine;

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
    pub async fn run(&mut self, context: &str) -> Result<AgentTaskResult, String> {
        self.status = AgentStatus::Running;

        let result = run_agent_task(
            context,
            self.config.max_iterations,
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
}
