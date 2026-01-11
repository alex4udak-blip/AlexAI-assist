//! Meta Agent (Orchestrator)
//!
//! Analyzes full context and decides which specialized agent should handle
//! the current situation, or if any action is needed at all.

use crate::agents::claude_code::ask_claude_raw;
use crate::agents::context::RichContext;
use crate::agents::memory::AgentMemory;
use crate::agents::prompts;
use crate::agents::AgentKind;
use serde::{Deserialize, Serialize};
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::time::{Duration, Instant};

/// Decision made by the Meta Agent
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetaDecision {
    /// Should we act on this context?
    pub should_act: bool,
    /// Reason for the decision
    pub reason: String,
    /// Which agent to use (if should_act is true)
    pub agent: Option<AgentKind>,
    /// Priority level
    pub priority: Priority,
    /// Context summary for the selected agent
    pub context_summary: String,
}

impl Default for MetaDecision {
    fn default() -> Self {
        Self {
            should_act: false,
            reason: "No action needed".to_string(),
            agent: None,
            priority: Priority::Normal,
            context_summary: String::new(),
        }
    }
}

/// Priority levels for agent actions
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Priority {
    Urgent,
    High,
    Normal,
    Low,
}

impl Default for Priority {
    fn default() -> Self {
        Priority::Normal
    }
}

/// Cached decision to avoid repeated API calls for similar contexts
struct CachedDecision {
    context_hash: u64,
    decision: MetaDecision,
    created_at: Instant,
}

/// Meta Agent - the orchestrator that decides which agent to use
pub struct MetaAgent {
    /// Path to Claude CLI
    claude_path: String,
    /// Timeout for Claude calls in seconds
    timeout_secs: u64,
    /// Agent memory for learning from feedback
    memory: AgentMemory,
    /// Cached decision (expires after CACHE_TTL)
    cache: Option<CachedDecision>,
}

/// Cache time-to-live in seconds
const CACHE_TTL_SECS: u64 = 60;

impl MetaAgent {
    /// Create a new Meta Agent
    pub fn new(claude_path: &str, timeout_secs: u64) -> Self {
        Self {
            claude_path: claude_path.to_string(),
            timeout_secs,
            memory: AgentMemory::load().unwrap_or_default(),
            cache: None,
        }
    }

    /// Analyze context and decide what to do
    pub async fn analyze(&mut self, context: &RichContext) -> Result<MetaDecision, String> {
        // Check cache first
        let context_hash = self.hash_context(context);
        if let Some(cached) = &self.cache {
            if cached.context_hash == context_hash
                && cached.created_at.elapsed() < Duration::from_secs(CACHE_TTL_SECS)
            {
                return Ok(cached.decision.clone());
            }
        }

        // Check if we should skip based on memory
        if self.memory.should_skip_context(&context.ocr_text, &context.window_title) {
            return Ok(MetaDecision {
                should_act: false,
                reason: "Similar context was recently processed or rejected".to_string(),
                ..Default::default()
            });
        }

        // Build the prompt for Meta Agent
        let prompt = self.build_prompt(context);

        // Call Claude for decision (raw text response)
        let response_text = ask_claude_raw(&prompt, &self.claude_path, self.timeout_secs).await?;

        // Parse the decision from raw text
        let decision = self.parse_decision(&response_text)?;

        // Cache the decision
        self.cache = Some(CachedDecision {
            context_hash,
            decision: decision.clone(),
            created_at: Instant::now(),
        });

        // Update memory with this decision
        if decision.should_act {
            self.memory.record_trigger(&context.ocr_text, &context.window_title);
        }

        Ok(decision)
    }

    /// Build the prompt for Meta Agent
    fn build_prompt(&self, context: &RichContext) -> String {
        let system_prompt = prompts::load_meta_agent_prompt();
        let context_json = serde_json::to_string_pretty(context).unwrap_or_default();
        let recent_actions = self.memory.get_recent_actions_summary();

        format!(
            "{}\n\nКОНТЕКСТ:\n{}\n\nИСТОРИЯ ДЕЙСТВИЙ:\n{}",
            system_prompt, context_json, recent_actions
        )
    }

    /// Parse Claude's raw text response into a MetaDecision
    fn parse_decision(&self, text: &str) -> Result<MetaDecision, String> {

        // Find JSON in the response
        let json_start = text.find('{');
        let json_end = text.rfind('}');

        if let (Some(start), Some(end)) = (json_start, json_end) {
            let json_str = &text[start..=end];
            if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(json_str) {
                return Ok(MetaDecision {
                    should_act: parsed["should_act"].as_bool().unwrap_or(false),
                    reason: parsed["reason"]
                        .as_str()
                        .unwrap_or("Unknown")
                        .to_string(),
                    agent: self.parse_agent_kind(parsed["agent"].as_str()),
                    priority: self.parse_priority(parsed["priority"].as_str()),
                    context_summary: parsed["context_summary"]
                        .as_str()
                        .unwrap_or("")
                        .to_string(),
                });
            }
        }

        // Fallback: try to infer from text
        Ok(MetaDecision {
            should_act: text.to_lowercase().contains("should_act\": true")
                || text.to_lowercase().contains("\"should_act\":true"),
            reason: "Could not parse structured response".to_string(),
            ..Default::default()
        })
    }

    /// Parse agent kind from string
    fn parse_agent_kind(&self, agent_str: Option<&str>) -> Option<AgentKind> {
        match agent_str?.to_lowercase().as_str() {
            "devops" => Some(AgentKind::DevOps),
            "codereview" | "code_review" => Some(AgentKind::CodeReview),
            "gitassistant" | "git_assistant" | "git" => Some(AgentKind::GitAssistant),
            "architect" => Some(AgentKind::Architect),
            "servermonitor" | "server_monitor" => Some(AgentKind::ServerMonitor),
            "meetingnotes" | "meeting_notes" | "meeting" => Some(AgentKind::MeetingNotes),
            _ => None,
        }
    }

    /// Parse priority from string
    fn parse_priority(&self, priority_str: Option<&str>) -> Priority {
        match priority_str.map(|s| s.to_lowercase()).as_deref() {
            Some("urgent") => Priority::Urgent,
            Some("high") => Priority::High,
            Some("low") => Priority::Low,
            _ => Priority::Normal,
        }
    }

    /// Hash the context for caching
    fn hash_context(&self, context: &RichContext) -> u64 {
        let mut hasher = DefaultHasher::new();
        // Hash key parts of context
        context.current_app.hash(&mut hasher);
        context.window_title.hash(&mut hasher);
        // Hash first 500 chars of OCR to detect similar screens
        context.ocr_text.chars().take(500).collect::<String>().hash(&mut hasher);
        hasher.finish()
    }

    /// Record user feedback on a decision
    pub fn record_feedback(&mut self, context: &str, accepted: bool) {
        self.memory.record_feedback(context, accepted);
        let _ = self.memory.save();
    }

    /// Clear the decision cache
    pub fn clear_cache(&mut self) {
        self.cache = None;
    }

    /// Save memory to disk
    pub fn save_memory(&self) -> Result<(), String> {
        self.memory.save()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_meta_decision_default() {
        let decision = MetaDecision::default();
        assert!(!decision.should_act);
        assert!(decision.agent.is_none());
    }

    #[test]
    fn test_parse_agent_kind() {
        let meta = MetaAgent::new("claude", 300);
        assert_eq!(meta.parse_agent_kind(Some("DevOps")), Some(AgentKind::DevOps));
        assert_eq!(meta.parse_agent_kind(Some("codereview")), Some(AgentKind::CodeReview));
        assert_eq!(meta.parse_agent_kind(Some("git_assistant")), Some(AgentKind::GitAssistant));
        assert_eq!(meta.parse_agent_kind(Some("unknown")), None);
        assert_eq!(meta.parse_agent_kind(None), None);
    }

    #[test]
    fn test_parse_priority() {
        let meta = MetaAgent::new("claude", 300);
        assert_eq!(meta.parse_priority(Some("urgent")), Priority::Urgent);
        assert_eq!(meta.parse_priority(Some("HIGH")), Priority::High);
        assert_eq!(meta.parse_priority(Some("low")), Priority::Low);
        assert_eq!(meta.parse_priority(Some("unknown")), Priority::Normal);
        assert_eq!(meta.parse_priority(None), Priority::Normal);
    }

    #[test]
    fn test_priority_default() {
        assert_eq!(Priority::default(), Priority::Normal);
    }
}
