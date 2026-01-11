//! Agent types for different use cases
//!
//! This module contains specialized agent implementations for various tasks.
//! Each agent implements the `AgentType` trait and provides domain-specific
//! logic for handling different scenarios.

pub mod architect;
pub mod code_review;
pub mod devops;
pub mod git_assistant;
pub mod meeting_notes;
pub mod server_monitor;

pub use architect::ArchitectAgent;
pub use code_review::CodeReviewAgent;
pub use devops::DevOpsAgent;
pub use git_assistant::GitAssistantAgent;
pub use meeting_notes::MeetingNotesAgent;
pub use server_monitor::ServerMonitorAgent;

/// Common trait for all agent types
///
/// Each agent type implements specific logic for:
/// - Determining when to activate (`should_handle`)
/// - Providing context-specific system prompts (`system_prompt`)
/// - Controlling iteration limits (`max_iterations`)
pub trait AgentType {
    /// Get the agent name
    fn name(&self) -> &'static str;

    /// Get the system prompt for this agent
    fn system_prompt(&self) -> &str;

    /// Check if this agent should handle the given context
    ///
    /// # Arguments
    /// * `app_name` - Name of the current application
    /// * `text` - OCR text or log content to analyze
    ///
    /// # Returns
    /// `true` if this agent should handle the current context
    fn should_handle(&self, app_name: &str, text: &str) -> bool;

    /// Get max iterations for this agent type
    ///
    /// Lower values are more conservative (e.g., for production operations).
    /// Default is 10 iterations.
    fn max_iterations(&self) -> u32 {
        10
    }

    /// Get agent priority (higher = more important)
    ///
    /// When multiple agents can handle a context, the one with
    /// highest priority is selected first.
    fn priority(&self) -> u32 {
        0
    }
}
