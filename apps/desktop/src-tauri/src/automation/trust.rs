/// Trust level management for automation commands
/// Controls which actions require user confirmation

use serde::{Serialize, Deserialize};

/// Trust level for automation commands
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum TrustLevel {
    /// Always ask for confirmation before executing any command
    AskAlways,
    /// Ask only for dangerous commands (default)
    AskDangerous,
    /// Never ask, execute all commands (requires explicit user opt-in)
    FullTrust,
}

impl Default for TrustLevel {
    fn default() -> Self {
        TrustLevel::AskDangerous
    }
}

/// Command danger level
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum DangerLevel {
    /// Safe commands that don't modify system state
    Safe,
    /// Commands that might affect user's work but are reversible
    Moderate,
    /// Commands that could cause data loss or system changes
    Dangerous,
}

impl TrustLevel {
    /// Check if a command requires confirmation based on trust level
    pub fn requires_confirmation(&self, danger: DangerLevel) -> bool {
        match self {
            TrustLevel::AskAlways => true,
            TrustLevel::AskDangerous => danger >= DangerLevel::Dangerous,
            TrustLevel::FullTrust => false,
        }
    }

    /// Get human-readable description
    pub fn description(&self) -> &'static str {
        match self {
            TrustLevel::AskAlways => "Ask before every action",
            TrustLevel::AskDangerous => "Ask before dangerous actions (default)",
            TrustLevel::FullTrust => "Never ask (full trust)",
        }
    }

    /// Parse from string
    pub fn from_str(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "ask_always" | "always" => Some(TrustLevel::AskAlways),
            "ask_dangerous" | "dangerous" => Some(TrustLevel::AskDangerous),
            "full_trust" | "full" | "trusted" => Some(TrustLevel::FullTrust),
            _ => None,
        }
    }

    /// Convert to string
    pub fn to_str(&self) -> &'static str {
        match self {
            TrustLevel::AskAlways => "ask_always",
            TrustLevel::AskDangerous => "ask_dangerous",
            TrustLevel::FullTrust => "full_trust",
        }
    }
}

/// Classify command danger level
pub fn classify_command_danger(command: &crate::automation::queue::TaskCommand) -> DangerLevel {
    use crate::automation::queue::TaskCommand;

    match command {
        // Safe commands
        TaskCommand::Screenshot { .. } => DangerLevel::Safe,
        TaskCommand::BrowserGetUrl { .. } => DangerLevel::Safe,
        TaskCommand::Wait { .. } => DangerLevel::Safe,

        // Moderate commands
        TaskCommand::Click { .. } => DangerLevel::Moderate,
        TaskCommand::Type { text } => {
            // Typing passwords or commands could be dangerous
            if text.len() > 100 || text.contains('\n') {
                DangerLevel::Dangerous
            } else {
                DangerLevel::Moderate
            }
        }
        TaskCommand::BrowserNavigate { .. } => DangerLevel::Moderate,

        // Dangerous commands
        TaskCommand::Hotkey { modifiers, key } => {
            // System hotkeys could be dangerous
            if is_dangerous_hotkey(modifiers, key) {
                DangerLevel::Dangerous
            } else {
                DangerLevel::Moderate
            }
        }
        TaskCommand::Custom { .. } => DangerLevel::Dangerous,
    }
}

/// Check if hotkey combination is dangerous
fn is_dangerous_hotkey(modifiers: &[String], key: &str) -> bool {
    let has_cmd_or_ctrl = modifiers
        .iter()
        .any(|m| matches!(m.as_str(), "meta" | "cmd" | "command" | "control" | "ctrl"));

    if has_cmd_or_ctrl {
        // Dangerous system commands
        matches!(
            key.to_lowercase().as_str(),
            "q" | "w" | "delete" | "backspace" | "escape"
        )
    } else {
        false
    }
}

/// Trust settings manager
pub struct TrustManager {
    current_level: std::sync::RwLock<TrustLevel>,
}

impl TrustManager {
    /// Create new trust manager with default level
    pub fn new() -> Self {
        Self {
            current_level: std::sync::RwLock::new(TrustLevel::default()),
        }
    }

    /// Create with specific trust level
    pub fn with_level(level: TrustLevel) -> Self {
        Self {
            current_level: std::sync::RwLock::new(level),
        }
    }

    /// Get current trust level
    pub fn get_level(&self) -> TrustLevel {
        *self.current_level.read().unwrap()
    }

    /// Set trust level
    pub fn set_level(&self, level: TrustLevel) {
        let mut current = self.current_level.write().unwrap();
        *current = level;
    }

    /// Check if command requires confirmation
    pub fn requires_confirmation(&self, command: &crate::automation::queue::TaskCommand) -> bool {
        let level = self.get_level();
        let danger = classify_command_danger(command);
        level.requires_confirmation(danger)
    }
}

impl Default for TrustManager {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::automation::queue::TaskCommand;

    #[test]
    fn test_trust_level_default() {
        assert_eq!(TrustLevel::default(), TrustLevel::AskDangerous);
    }

    #[test]
    fn test_trust_level_requires_confirmation() {
        let ask_always = TrustLevel::AskAlways;
        assert!(ask_always.requires_confirmation(DangerLevel::Safe));
        assert!(ask_always.requires_confirmation(DangerLevel::Dangerous));

        let ask_dangerous = TrustLevel::AskDangerous;
        assert!(!ask_dangerous.requires_confirmation(DangerLevel::Safe));
        assert!(ask_dangerous.requires_confirmation(DangerLevel::Dangerous));

        let full_trust = TrustLevel::FullTrust;
        assert!(!full_trust.requires_confirmation(DangerLevel::Safe));
        assert!(!full_trust.requires_confirmation(DangerLevel::Dangerous));
    }

    #[test]
    fn test_classify_command_danger() {
        let screenshot = TaskCommand::Screenshot { save_path: None };
        assert_eq!(classify_command_danger(&screenshot), DangerLevel::Safe);

        let click = TaskCommand::Click {
            x: 100,
            y: 100,
            button: "left".to_string(),
        };
        assert_eq!(classify_command_danger(&click), DangerLevel::Moderate);
    }

    #[test]
    fn test_trust_manager() {
        let manager = TrustManager::new();
        assert_eq!(manager.get_level(), TrustLevel::AskDangerous);

        manager.set_level(TrustLevel::FullTrust);
        assert_eq!(manager.get_level(), TrustLevel::FullTrust);
    }
}
