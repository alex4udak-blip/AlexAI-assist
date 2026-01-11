//! Agent Memory System
//!
//! Stores and learns from agent actions and user feedback.
//! Persists to ~/.config/observer/agent_memory.json

use chrono::{DateTime, Duration, Utc};
use serde::{Deserialize, Serialize};
use std::collections::hash_map::DefaultHasher;
use std::collections::HashMap;
use std::hash::{Hash, Hasher};
use std::path::PathBuf;

/// Maximum number of actions to keep in history
const MAX_HISTORY_SIZE: usize = 1000;

/// Maximum age of actions to keep (7 days)
const MAX_ACTION_AGE_DAYS: i64 = 7;

/// Cooldown period for similar contexts (5 minutes)
const CONTEXT_COOLDOWN_SECS: i64 = 300;

/// Agent memory for learning from past actions
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AgentMemory {
    /// History of agent actions
    actions: Vec<ActionRecord>,
    /// Context hashes that were recently triggered (for deduplication)
    recent_contexts: HashMap<u64, DateTime<Utc>>,
    /// Feedback on specific context patterns
    feedback: HashMap<u64, FeedbackRecord>,
    /// Statistics per agent
    agent_stats: HashMap<String, AgentStats>,
}

/// Record of an agent action
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActionRecord {
    /// Timestamp of the action
    pub timestamp: DateTime<Utc>,
    /// Agent that performed the action
    pub agent: String,
    /// Brief description of what was done
    pub action: String,
    /// Context hash for deduplication
    pub context_hash: u64,
    /// User feedback if received
    pub feedback: Option<FeedbackType>,
}

/// User feedback on an action
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum FeedbackType {
    Accepted,
    Rejected,
}

/// Aggregated feedback for a context pattern
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct FeedbackRecord {
    /// Number of times accepted
    pub accepted_count: u32,
    /// Number of times rejected
    pub rejected_count: u32,
    /// Last feedback time
    pub last_feedback: Option<DateTime<Utc>>,
}

/// Statistics for an agent
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AgentStats {
    /// Total number of triggers
    pub total_triggers: u64,
    /// Number of accepted actions
    pub accepted: u64,
    /// Number of rejected actions
    pub rejected: u64,
}

impl AgentMemory {
    /// Create a new empty memory
    pub fn new() -> Self {
        Self::default()
    }

    /// Load memory from disk
    pub fn load() -> Result<Self, String> {
        let path = Self::config_path();

        if !path.exists() {
            return Ok(Self::new());
        }

        let content =
            std::fs::read_to_string(&path).map_err(|e| format!("Failed to read memory: {}", e))?;

        serde_json::from_str(&content).map_err(|e| format!("Failed to parse memory: {}", e))
    }

    /// Save memory to disk
    pub fn save(&self) -> Result<(), String> {
        let path = Self::config_path();

        // Ensure parent directory exists
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create config dir: {}", e))?;
        }

        let content = serde_json::to_string_pretty(self)
            .map_err(|e| format!("Failed to serialize memory: {}", e))?;

        std::fs::write(&path, content).map_err(|e| format!("Failed to write memory: {}", e))
    }

    /// Get the config file path
    fn config_path() -> PathBuf {
        dirs::config_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("observer")
            .join("agent_memory.json")
    }

    /// Record a trigger event
    pub fn record_trigger(&mut self, ocr_text: &str, window_title: &str) {
        let hash = Self::hash_context(ocr_text, window_title);
        self.recent_contexts.insert(hash, Utc::now());

        // Cleanup old contexts
        self.cleanup_old_contexts();
    }

    /// Record an agent action
    pub fn record_action(&mut self, agent: &str, action: &str, ocr_text: &str, window_title: &str) {
        let hash = Self::hash_context(ocr_text, window_title);

        let record = ActionRecord {
            timestamp: Utc::now(),
            agent: agent.to_string(),
            action: action.to_string(),
            context_hash: hash,
            feedback: None,
        };

        self.actions.push(record);

        // Update agent stats
        let stats = self.agent_stats.entry(agent.to_string()).or_default();
        stats.total_triggers += 1;

        // Trim history if needed
        self.trim_history();
    }

    /// Record user feedback
    pub fn record_feedback(&mut self, context: &str, accepted: bool) {
        let hash = Self::hash_string(context);
        let feedback_type = if accepted {
            FeedbackType::Accepted
        } else {
            FeedbackType::Rejected
        };

        // Update the most recent action with this context
        for action in self.actions.iter_mut().rev() {
            if action.context_hash == hash && action.feedback.is_none() {
                action.feedback = Some(feedback_type);

                // Update agent stats
                let stats = self
                    .agent_stats
                    .entry(action.agent.clone())
                    .or_default();
                if accepted {
                    stats.accepted += 1;
                } else {
                    stats.rejected += 1;
                }

                break;
            }
        }

        // Update feedback record
        let feedback_record = self.feedback.entry(hash).or_default();
        if accepted {
            feedback_record.accepted_count += 1;
        } else {
            feedback_record.rejected_count += 1;
        }
        feedback_record.last_feedback = Some(Utc::now());
    }

    /// Check if we should skip this context (recently processed or rejected)
    pub fn should_skip_context(&self, ocr_text: &str, window_title: &str) -> bool {
        let hash = Self::hash_context(ocr_text, window_title);

        // Check if recently triggered
        if let Some(last_time) = self.recent_contexts.get(&hash) {
            let age = Utc::now().signed_duration_since(*last_time);
            if age.num_seconds() < CONTEXT_COOLDOWN_SECS {
                return true;
            }
        }

        // Check if this pattern is usually rejected
        if let Some(feedback) = self.feedback.get(&hash) {
            // Skip if rejected more than 3 times and rejection rate > 70%
            let total = feedback.accepted_count + feedback.rejected_count;
            if total >= 3 {
                let rejection_rate = feedback.rejected_count as f32 / total as f32;
                if rejection_rate > 0.7 {
                    return true;
                }
            }
        }

        false
    }

    /// Get summary of recent actions for Meta Agent prompt
    pub fn get_recent_actions_summary(&self) -> String {
        let cutoff = Utc::now() - Duration::minutes(5);

        let recent: Vec<_> = self
            .actions
            .iter()
            .rev()
            .filter(|a| a.timestamp > cutoff)
            .take(10)
            .collect();

        if recent.is_empty() {
            return "No recent actions".to_string();
        }

        recent
            .iter()
            .map(|a| {
                let feedback_str = match a.feedback {
                    Some(FeedbackType::Accepted) => " [ACCEPTED]",
                    Some(FeedbackType::Rejected) => " [REJECTED]",
                    None => "",
                };
                format!(
                    "- {} ({}): {}{}",
                    a.agent,
                    a.timestamp.format("%H:%M"),
                    a.action,
                    feedback_str
                )
            })
            .collect::<Vec<_>>()
            .join("\n")
    }

    /// Get statistics for an agent
    pub fn get_agent_stats(&self, agent: &str) -> Option<&AgentStats> {
        self.agent_stats.get(agent)
    }

    /// Calculate success rate for an agent
    pub fn agent_success_rate(&self, agent: &str) -> Option<f32> {
        let stats = self.agent_stats.get(agent)?;
        let total_feedback = stats.accepted + stats.rejected;
        if total_feedback == 0 {
            return None;
        }
        Some(stats.accepted as f32 / total_feedback as f32)
    }

    /// Hash context for deduplication
    fn hash_context(ocr_text: &str, window_title: &str) -> u64 {
        let mut hasher = DefaultHasher::new();
        window_title.hash(&mut hasher);
        // Hash first 500 chars of OCR
        ocr_text.chars().take(500).collect::<String>().hash(&mut hasher);
        hasher.finish()
    }

    /// Hash a string
    fn hash_string(s: &str) -> u64 {
        let mut hasher = DefaultHasher::new();
        s.hash(&mut hasher);
        hasher.finish()
    }

    /// Cleanup old contexts from the recent_contexts map
    fn cleanup_old_contexts(&mut self) {
        let cutoff = Utc::now() - Duration::seconds(CONTEXT_COOLDOWN_SECS * 2);
        self.recent_contexts.retain(|_, time| *time > cutoff);
    }

    /// Trim history to MAX_HISTORY_SIZE and remove old entries
    fn trim_history(&mut self) {
        // Remove old entries
        let cutoff = Utc::now() - Duration::days(MAX_ACTION_AGE_DAYS);
        self.actions.retain(|a| a.timestamp > cutoff);

        // Trim to max size
        if self.actions.len() > MAX_HISTORY_SIZE {
            let remove_count = self.actions.len() - MAX_HISTORY_SIZE;
            self.actions.drain(0..remove_count);
        }
    }

    /// Clear all memory (for testing or reset)
    pub fn clear(&mut self) {
        self.actions.clear();
        self.recent_contexts.clear();
        self.feedback.clear();
        self.agent_stats.clear();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_record_and_check_trigger() {
        let mut memory = AgentMemory::new();

        // First time should not skip
        assert!(!memory.should_skip_context("error: not found", "Terminal"));

        // Record trigger
        memory.record_trigger("error: not found", "Terminal");

        // Same context should be skipped now
        assert!(memory.should_skip_context("error: not found", "Terminal"));
    }

    #[test]
    fn test_record_action() {
        let mut memory = AgentMemory::new();

        memory.record_action("DevOps", "Fixed npm error", "npm ERR!", "Terminal");

        assert_eq!(memory.actions.len(), 1);
        assert_eq!(memory.actions[0].agent, "DevOps");
    }

    #[test]
    fn test_feedback_recording() {
        let mut memory = AgentMemory::new();

        memory.record_action("DevOps", "Fixed error", "error", "Terminal");
        memory.record_feedback("error", true);

        let stats = memory.get_agent_stats("DevOps").unwrap();
        assert_eq!(stats.accepted, 1);
        assert_eq!(stats.rejected, 0);
    }

    #[test]
    fn test_rejection_skip() {
        let mut memory = AgentMemory::new();

        // Record multiple rejections for the same context
        let hash = AgentMemory::hash_context("spam text", "Annoying App");
        memory.feedback.insert(
            hash,
            FeedbackRecord {
                accepted_count: 0,
                rejected_count: 5,
                last_feedback: Some(Utc::now()),
            },
        );

        // Should skip this context
        assert!(memory.should_skip_context("spam text", "Annoying App"));
    }

    #[test]
    fn test_recent_actions_summary() {
        let mut memory = AgentMemory::new();

        memory.record_action("DevOps", "Fixed npm error", "npm ERR!", "Terminal");

        let summary = memory.get_recent_actions_summary();
        assert!(summary.contains("DevOps"));
        assert!(summary.contains("Fixed npm error"));
    }

    #[test]
    fn test_success_rate() {
        let mut memory = AgentMemory::new();

        memory.agent_stats.insert(
            "DevOps".to_string(),
            AgentStats {
                total_triggers: 10,
                accepted: 8,
                rejected: 2,
            },
        );

        let rate = memory.agent_success_rate("DevOps").unwrap();
        assert!((rate - 0.8).abs() < 0.01);
    }

    #[test]
    fn test_trim_history() {
        let mut memory = AgentMemory::new();

        // Add more than MAX_HISTORY_SIZE actions
        for i in 0..MAX_HISTORY_SIZE + 100 {
            memory.record_action("Test", &format!("Action {}", i), "text", "Title");
        }

        // Should be trimmed to MAX_HISTORY_SIZE
        assert!(memory.actions.len() <= MAX_HISTORY_SIZE);
    }
}
