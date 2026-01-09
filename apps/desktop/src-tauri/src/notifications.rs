/// Notification management module
/// Uses tauri_plugin_notification for cross-platform notifications

use tauri_plugin_notification::NotificationExt;
use serde::{Serialize, Deserialize};

/// Notification priority
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum NotificationPriority {
    Low,
    Normal,
    High,
    Urgent,
}

/// Notification configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NotificationConfig {
    pub title: String,
    pub body: String,
    pub priority: NotificationPriority,
    pub action: Option<String>,
}

/// Send a notification
pub fn send_notification(
    app: &tauri::AppHandle,
    config: NotificationConfig,
) -> Result<(), String> {
    let notification = app.notification();

    // Note: Action buttons are not supported in tauri_plugin_notification
    // The action field in config is stored for potential future use
    let _action = config.action; // Suppress unused warning

    notification.builder()
        .title(config.title)
        .body(config.body)
        .show()
        .map_err(|e| format!("Failed to show notification: {}", e))?;

    Ok(())
}

/// Send permission request notification
pub fn notify_permission_required(
    app: &tauri::AppHandle,
    permission_name: &str,
) -> Result<(), String> {
    let config = NotificationConfig {
        title: "Permission Required".to_string(),
        body: format!("{} permission is required for automation features.", permission_name),
        priority: NotificationPriority::High,
        action: Some("Open Settings".to_string()),
    };

    send_notification(app, config)
}

/// Send automation task started notification
pub fn notify_task_started(
    app: &tauri::AppHandle,
    task_name: &str,
) -> Result<(), String> {
    let config = NotificationConfig {
        title: "Automation Task Started".to_string(),
        body: format!("Running: {}", task_name),
        priority: NotificationPriority::Normal,
        action: None,
    };

    send_notification(app, config)
}

/// Send automation task completed notification
pub fn notify_task_completed(
    app: &tauri::AppHandle,
    task_name: &str,
    success: bool,
) -> Result<(), String> {
    let config = NotificationConfig {
        title: if success {
            "Task Completed".to_string()
        } else {
            "Task Failed".to_string()
        },
        body: format!("{}: {}", if success { "Completed" } else { "Failed" }, task_name),
        priority: if success {
            NotificationPriority::Normal
        } else {
            NotificationPriority::High
        },
        action: None,
    };

    send_notification(app, config)
}

/// Send error notification
pub fn notify_error(
    app: &tauri::AppHandle,
    error: &str,
) -> Result<(), String> {
    let config = NotificationConfig {
        title: "Error".to_string(),
        body: error.to_string(),
        priority: NotificationPriority::Urgent,
        action: None,
    };

    send_notification(app, config)
}

/// Send sync notification
pub fn notify_sync_status(
    app: &tauri::AppHandle,
    success: bool,
    message: &str,
) -> Result<(), String> {
    let config = NotificationConfig {
        title: if success {
            "Sync Complete".to_string()
        } else {
            "Sync Failed".to_string()
        },
        body: message.to_string(),
        priority: NotificationPriority::Low,
        action: None,
    };

    send_notification(app, config)
}

/// Send update available notification
pub fn notify_update_available(
    app: &tauri::AppHandle,
    version: &str,
) -> Result<(), String> {
    let config = NotificationConfig {
        title: "Update Available".to_string(),
        body: format!("Version {} is now available.", version),
        priority: NotificationPriority::Normal,
        action: Some("Update Now".to_string()),
    };

    send_notification(app, config)
}

/// Notification manager for controlling notification behavior
pub struct NotificationManager {
    enabled: std::sync::RwLock<bool>,
    min_priority: std::sync::RwLock<NotificationPriority>,
}

impl NotificationManager {
    /// Create new notification manager
    pub fn new() -> Self {
        Self {
            enabled: std::sync::RwLock::new(true),
            min_priority: std::sync::RwLock::new(NotificationPriority::Low),
        }
    }

    /// Enable/disable notifications
    pub fn set_enabled(&self, enabled: bool) {
        let mut e = self.enabled.write().unwrap();
        *e = enabled;
    }

    /// Check if notifications are enabled
    pub fn is_enabled(&self) -> bool {
        *self.enabled.read().unwrap()
    }

    /// Set minimum priority for notifications
    pub fn set_min_priority(&self, priority: NotificationPriority) {
        let mut p = self.min_priority.write().unwrap();
        *p = priority;
    }

    /// Check if notification should be shown based on priority
    pub fn should_show(&self, priority: NotificationPriority) -> bool {
        if !self.is_enabled() {
            return false;
        }

        let min_priority = *self.min_priority.read().unwrap();
        priority_level(priority) >= priority_level(min_priority)
    }

    /// Send notification if allowed by settings
    pub fn send_if_allowed(
        &self,
        app: &tauri::AppHandle,
        config: NotificationConfig,
    ) -> Result<(), String> {
        if self.should_show(config.priority) {
            send_notification(app, config)
        } else {
            Ok(())
        }
    }
}

impl Default for NotificationManager {
    fn default() -> Self {
        Self::new()
    }
}

/// Convert priority to numeric level for comparison
fn priority_level(priority: NotificationPriority) -> u8 {
    match priority {
        NotificationPriority::Low => 0,
        NotificationPriority::Normal => 1,
        NotificationPriority::High => 2,
        NotificationPriority::Urgent => 3,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_priority_levels() {
        assert!(priority_level(NotificationPriority::Urgent) > priority_level(NotificationPriority::Low));
        assert_eq!(priority_level(NotificationPriority::Normal), 1);
    }

    #[test]
    fn test_notification_manager() {
        let manager = NotificationManager::new();
        assert!(manager.is_enabled());

        manager.set_enabled(false);
        assert!(!manager.is_enabled());

        assert!(!manager.should_show(NotificationPriority::High));

        manager.set_enabled(true);
        manager.set_min_priority(NotificationPriority::High);
        assert!(!manager.should_show(NotificationPriority::Normal));
        assert!(manager.should_show(NotificationPriority::High));
    }
}
