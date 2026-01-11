//! Trigger system for AI agents
//!
//! Defines triggers that automatically activate agents based on
//! screen content, user activity, schedules, and app patterns.

use serde::{Deserialize, Serialize};
use std::time::{Duration, Instant};
use regex::Regex;

/// Trigger types for agent activation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Trigger {
    /// Error detected in terminal/app
    Error { pattern: String },
    /// User has been idle for specified minutes
    Idle { minutes: u32 },
    /// Scheduled trigger (cron-like)
    Schedule { cron: String },
    /// Pattern detected in specific app
    Pattern { app: String, event: String },
}

/// Triggered event with metadata
#[derive(Debug, Clone)]
pub struct TriggeredEvent {
    pub trigger: Trigger,
    pub matched_text: Option<String>,
    pub app_name: Option<String>,
    pub timestamp: Instant,
}

/// Trigger configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TriggerConfig {
    /// Error patterns to watch for
    pub error_patterns: Vec<String>,
    /// Idle timeout in minutes
    pub idle_timeout_minutes: u32,
    /// App patterns (app_name -> event patterns)
    pub app_patterns: Vec<(String, String)>,
    /// Enable/disable triggers
    pub enabled: bool,
}

impl Default for TriggerConfig {
    fn default() -> Self {
        Self {
            error_patterns: vec![
                r"(?i)error:".to_string(),
                r"(?i)exception:".to_string(),
                r"(?i)failed:".to_string(),
                r"(?i)panic:".to_string(),
                r"(?i)fatal:".to_string(),
                r"(?i)cannot find module".to_string(),
                r"(?i)module not found".to_string(),
                r"(?i)command not found".to_string(),
                r"(?i)permission denied".to_string(),
                r"(?i)connection refused".to_string(),
            ],
            idle_timeout_minutes: 5,
            app_patterns: vec![
                ("GitHub".to_string(), "Pull Request".to_string()),
                ("Terminal".to_string(), "npm ERR!".to_string()),
                ("Terminal".to_string(), "cargo error".to_string()),
            ],
            enabled: true,
        }
    }
}

/// Engine for checking and managing triggers
pub struct TriggerEngine {
    config: TriggerConfig,
    last_activity: Instant,
    compiled_error_patterns: Vec<Regex>,
}

impl TriggerEngine {
    /// Create new trigger engine with default config
    pub fn new() -> Self {
        let config = TriggerConfig::default();
        let compiled = Self::compile_patterns(&config.error_patterns);
        Self {
            config,
            last_activity: Instant::now(),
            compiled_error_patterns: compiled,
        }
    }

    /// Create trigger engine with custom config
    pub fn with_config(config: TriggerConfig) -> Self {
        let compiled = Self::compile_patterns(&config.error_patterns);
        Self {
            config,
            last_activity: Instant::now(),
            compiled_error_patterns: compiled,
        }
    }

    /// Compile regex patterns
    fn compile_patterns(patterns: &[String]) -> Vec<Regex> {
        patterns
            .iter()
            .filter_map(|p| Regex::new(p).ok())
            .collect()
    }

    /// Update last activity time
    pub fn record_activity(&mut self) {
        self.last_activity = Instant::now();
    }

    /// Check if user is idle
    pub fn is_idle(&self) -> bool {
        let idle_duration = Duration::from_secs(self.config.idle_timeout_minutes as u64 * 60);
        self.last_activity.elapsed() >= idle_duration
    }

    /// Check all triggers against current context
    pub fn check(&self, ocr_text: &str, app_name: &str) -> Vec<TriggeredEvent> {
        if !self.config.enabled {
            return Vec::new();
        }

        let mut triggered = Vec::new();

        // Check error patterns
        for (pattern, regex) in self.config.error_patterns.iter().zip(&self.compiled_error_patterns) {
            if let Some(mat) = regex.find(ocr_text) {
                triggered.push(TriggeredEvent {
                    trigger: Trigger::Error { pattern: pattern.clone() },
                    matched_text: Some(mat.as_str().to_string()),
                    app_name: Some(app_name.to_string()),
                    timestamp: Instant::now(),
                });
            }
        }

        // Check app-specific patterns
        for (target_app, event_pattern) in &self.config.app_patterns {
            if app_name.contains(target_app) && ocr_text.contains(event_pattern) {
                triggered.push(TriggeredEvent {
                    trigger: Trigger::Pattern {
                        app: target_app.clone(),
                        event: event_pattern.clone(),
                    },
                    matched_text: Some(event_pattern.clone()),
                    app_name: Some(app_name.to_string()),
                    timestamp: Instant::now(),
                });
            }
        }

        // Check idle trigger
        if self.is_idle() {
            triggered.push(TriggeredEvent {
                trigger: Trigger::Idle { minutes: self.config.idle_timeout_minutes },
                matched_text: None,
                app_name: None,
                timestamp: Instant::now(),
            });
        }

        triggered
    }

    /// Add error pattern
    pub fn add_error_pattern(&mut self, pattern: &str) {
        if let Ok(regex) = Regex::new(pattern) {
            self.config.error_patterns.push(pattern.to_string());
            self.compiled_error_patterns.push(regex);
        }
    }

    /// Add app pattern
    pub fn add_app_pattern(&mut self, app: &str, event: &str) {
        self.config.app_patterns.push((app.to_string(), event.to_string()));
    }

    /// Enable/disable triggers
    pub fn set_enabled(&mut self, enabled: bool) {
        self.config.enabled = enabled;
    }

    /// Get config
    pub fn config(&self) -> &TriggerConfig {
        &self.config
    }
}

impl Default for TriggerEngine {
    fn default() -> Self {
        Self::new()
    }
}

/// Check triggers from Screenpipe frame (convenience function)
pub fn check_triggers(ocr_text: &str, app_name: &str) -> Vec<Trigger> {
    let engine = TriggerEngine::new();
    engine.check(ocr_text, app_name)
        .into_iter()
        .map(|e| e.trigger)
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_trigger() {
        let engine = TriggerEngine::new();
        let triggers = engine.check("Error: Module 'lodash' not found", "Terminal");
        assert!(!triggers.is_empty());

        if let Trigger::Error { pattern } = &triggers[0].trigger {
            assert!(pattern.contains("error"));
        }
    }

    #[test]
    fn test_app_pattern_trigger() {
        let engine = TriggerEngine::new();
        let triggers = engine.check("npm ERR! missing dependency", "Terminal");
        assert!(!triggers.is_empty());
    }

    #[test]
    fn test_no_trigger() {
        let engine = TriggerEngine::new();
        let triggers = engine.check("Build successful", "Terminal");
        // Only idle trigger may be present
        let non_idle: Vec<_> = triggers.iter()
            .filter(|t| !matches!(t.trigger, Trigger::Idle { .. }))
            .collect();
        assert!(non_idle.is_empty());
    }

    #[test]
    fn test_disabled_triggers() {
        let mut engine = TriggerEngine::new();
        engine.set_enabled(false);
        let triggers = engine.check("Error: something failed", "Terminal");
        assert!(triggers.is_empty());
    }

    #[test]
    fn test_add_custom_pattern() {
        let mut engine = TriggerEngine::new();
        engine.add_error_pattern(r"CUSTOM_ERROR");
        let triggers = engine.check("CUSTOM_ERROR occurred", "App");
        assert!(!triggers.is_empty());
    }
}
