#[cfg(target_os = "macos")]
use core_foundation::base::{CFRelease, TCFType};
#[cfg(target_os = "macos")]
use core_foundation::string::{CFString, CFStringRef};
#[cfg(target_os = "macos")]
use core_foundation::array::{CFArray, CFArrayRef};

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use std::collections::HashSet;

#[cfg(target_os = "macos")]
type AXUIElementRef = *const std::ffi::c_void;

#[cfg(target_os = "macos")]
#[link(name = "ApplicationServices", kind = "framework")]
extern "C" {
    fn AXUIElementCreateApplication(pid: i32) -> AXUIElementRef;
    fn AXUIElementCopyAttributeValue(
        element: AXUIElementRef,
        attribute: CFStringRef,
        value: *mut *const std::ffi::c_void,
    ) -> i32;
    fn AXUIElementGetPid(element: AXUIElementRef, pid: *mut i32) -> i32;
}

/// Represents a single messenger message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub id: String,
    pub app: String,
    pub sender: Option<String>,
    pub content: String,
    pub timestamp: DateTime<Utc>,
    pub chat_name: Option<String>,
    pub is_outgoing: bool,
}

impl Message {
    pub fn new(app: String, content: String) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            app,
            sender: None,
            content,
            timestamp: Utc::now(),
            chat_name: None,
            is_outgoing: false,
        }
    }

    pub fn with_sender(mut self, sender: String) -> Self {
        self.sender = Some(sender);
        self
    }

    pub fn with_chat(mut self, chat_name: String) -> Self {
        self.chat_name = Some(chat_name);
        self
    }

    pub fn with_outgoing(mut self, is_outgoing: bool) -> Self {
        self.is_outgoing = is_outgoing;
        self
    }
}

/// Represents the current state of a messenger app
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MessengerState {
    pub app: String,
    pub active_chat: Option<String>,
    pub visible_messages: Vec<Message>,
}

impl MessengerState {
    pub fn new(app: String) -> Self {
        Self {
            app,
            active_chat: None,
            visible_messages: Vec::new(),
        }
    }
}

/// Monitor for capturing messages from messenger applications
pub struct MessengerMonitor {
    supported_messengers: HashSet<String>,
}

impl MessengerMonitor {
    /// Create a new messenger monitor
    pub fn new() -> Self {
        let mut supported_messengers = HashSet::new();
        supported_messengers.insert("Telegram".to_string());
        supported_messengers.insert("Slack".to_string());
        supported_messengers.insert("Discord".to_string());
        supported_messengers.insert("Microsoft Teams".to_string());

        Self {
            supported_messengers,
        }
    }

    /// Check if the given app name is a supported messenger
    pub fn is_messenger(&self, app_name: &str) -> bool {
        self.supported_messengers.contains(app_name)
    }

    /// Get visible messages from a messenger app
    #[cfg(target_os = "macos")]
    pub fn get_visible_messages(&self, app_name: &str) -> Option<MessengerState> {
        if !self.is_messenger(app_name) {
            return None;
        }

        match app_name {
            "Telegram" => self.get_telegram_messages(),
            "Slack" => self.get_slack_messages(),
            "Discord" => self.get_discord_messages(),
            "Microsoft Teams" => self.get_teams_messages(),
            _ => None,
        }
    }

    #[cfg(not(target_os = "macos"))]
    pub fn get_visible_messages(&self, _app_name: &str) -> Option<MessengerState> {
        None
    }

    /// Get Telegram messages
    #[cfg(target_os = "macos")]
    fn get_telegram_messages(&self) -> Option<MessengerState> {
        self.extract_messages_via_ax("Telegram")
    }

    #[cfg(not(target_os = "macos"))]
    fn get_telegram_messages(&self) -> Option<MessengerState> {
        None
    }

    /// Get Slack messages
    #[cfg(target_os = "macos")]
    fn get_slack_messages(&self) -> Option<MessengerState> {
        self.extract_messages_via_ax("Slack")
    }

    #[cfg(not(target_os = "macos"))]
    fn get_slack_messages(&self) -> Option<MessengerState> {
        None
    }

    /// Get Discord messages
    #[cfg(target_os = "macos")]
    fn get_discord_messages(&self) -> Option<MessengerState> {
        self.extract_messages_via_ax("Discord")
    }

    #[cfg(not(target_os = "macos"))]
    fn get_discord_messages(&self) -> Option<MessengerState> {
        None
    }

    /// Get Microsoft Teams messages
    #[cfg(target_os = "macos")]
    fn get_teams_messages(&self) -> Option<MessengerState> {
        self.extract_messages_via_ax("Microsoft Teams")
    }

    #[cfg(not(target_os = "macos"))]
    fn get_teams_messages(&self) -> Option<MessengerState> {
        None
    }

    /// Extract messages using Accessibility API
    #[cfg(target_os = "macos")]
    fn extract_messages_via_ax(&self, app_name: &str) -> Option<MessengerState> {
        let app_element = self.get_app_ax_element(app_name)?;
        let window = self.get_focused_window(app_element)?;

        let chat_name = self.get_active_chat_name(app_name);
        let mut messages = Vec::new();

        self.find_message_elements(window, app_name, &mut messages);

        // Release the window element
        unsafe {
            if !window.is_null() {
                CFRelease(window as *const std::ffi::c_void);
            }
            if !app_element.is_null() {
                CFRelease(app_element as *const std::ffi::c_void);
            }
        }

        let mut state = MessengerState::new(app_name.to_string());
        state.active_chat = chat_name;
        state.visible_messages = messages;

        Some(state)
    }

    /// Get the AXUIElement for the specified application
    #[cfg(target_os = "macos")]
    fn get_app_ax_element(&self, app_name: &str) -> Option<AXUIElementRef> {
        use std::process::Command;

        // Get the PID of the application
        let output = Command::new("pgrep")
            .arg("-x")
            .arg(app_name)
            .output()
            .ok()?;

        if !output.status.success() {
            return None;
        }

        let pid_str = String::from_utf8_lossy(&output.stdout);
        let pid: i32 = pid_str.trim().parse().ok()?;

        unsafe {
            let app_element = AXUIElementCreateApplication(pid);
            if app_element.is_null() {
                None
            } else {
                Some(app_element)
            }
        }
    }

    /// Get the focused window of the application
    #[cfg(target_os = "macos")]
    fn get_focused_window(&self, app_element: AXUIElementRef) -> Option<AXUIElementRef> {
        if app_element.is_null() {
            return None;
        }

        unsafe {
            let attr_name = CFString::new("AXFocusedWindow");
            let mut value: *const std::ffi::c_void = std::ptr::null();

            let result = AXUIElementCopyAttributeValue(
                app_element,
                attr_name.as_concrete_TypeRef(),
                &mut value,
            );

            if result == 0 && !value.is_null() {
                Some(value as AXUIElementRef)
            } else {
                None
            }
        }
    }

    /// Find message elements in the window
    #[cfg(target_os = "macos")]
    fn find_message_elements(
        &self,
        window: AXUIElementRef,
        app_name: &str,
        messages: &mut Vec<Message>,
    ) {
        self.traverse_for_messages(window, app_name, messages, 0);
    }

    /// Recursively traverse the AX tree to find messages
    #[cfg(target_os = "macos")]
    fn traverse_for_messages(
        &self,
        element: AXUIElementRef,
        app_name: &str,
        messages: &mut Vec<Message>,
        depth: usize,
    ) {
        const MAX_DEPTH: usize = 30;

        if element.is_null() || depth > MAX_DEPTH {
            return;
        }

        unsafe {
            // Get the role of the element
            let role_attr = CFString::new("AXRole");
            let mut role_value: *const std::ffi::c_void = std::ptr::null();

            let role_result = AXUIElementCopyAttributeValue(
                element,
                role_attr.as_concrete_TypeRef(),
                &mut role_value,
            );

            let mut is_text_element = false;

            if role_result == 0 && !role_value.is_null() {
                let role_string = CFString::wrap_under_get_rule(role_value as CFStringRef);
                let role = role_string.to_string();

                // Look for text-containing elements
                is_text_element = role.contains("Text")
                    || role.contains("StaticText")
                    || role.contains("TextField")
                    || role == "AXGroup";
            }

            // Try to get the text value
            if is_text_element {
                let value_attr = CFString::new("AXValue");
                let mut text_value: *const std::ffi::c_void = std::ptr::null();

                let value_result = AXUIElementCopyAttributeValue(
                    element,
                    value_attr.as_concrete_TypeRef(),
                    &mut text_value,
                );

                if value_result == 0 && !text_value.is_null() {
                    let text_string = CFString::wrap_under_get_rule(text_value as CFStringRef);
                    let text = text_string.to_string();

                    if self.looks_like_message(&text, app_name) {
                        let message = Message::new(app_name.to_string(), text);
                        messages.push(message);
                    }
                }
            }

            // Traverse children
            let children_attr = CFString::new("AXChildren");
            let mut children_value: *const std::ffi::c_void = std::ptr::null();

            let children_result = AXUIElementCopyAttributeValue(
                element,
                children_attr.as_concrete_TypeRef(),
                &mut children_value,
            );

            if children_result == 0 && !children_value.is_null() {
                let children_array = CFArray::<AXUIElementRef>::wrap_under_get_rule(
                    children_value as CFArrayRef
                );

                for i in 0..children_array.len() {
                    if let Some(child) = children_array.get(i) {
                        self.traverse_for_messages(*child, app_name, messages, depth + 1);
                    }
                }
            }
        }
    }

    /// Determine if text looks like a message (not UI elements)
    fn looks_like_message(&self, text: &str, app_name: &str) -> bool {
        let trimmed = text.trim();

        // Filter by length
        if trimmed.len() < 2 || trimmed.len() > 5000 {
            return false;
        }

        // Common UI elements to filter out
        let ui_elements = [
            "Search",
            "Settings",
            "Send",
            "Type a message",
            "Message",
            "Mute",
            "Pin",
            "Edit",
            "Delete",
            "Reply",
            "Forward",
            "Copy",
            "Select",
            "Archive",
            "Block",
            "Report",
            "Call",
            "Video",
            "Voice",
            "Attach",
            "Emoji",
            "Sticker",
            "GIF",
            "File",
            "Photo",
            "Contact",
            "Location",
            "Poll",
            "Close",
            "Back",
            "Menu",
            "More",
            "Options",
            "Help",
            "About",
            "Notifications",
            "Privacy",
            "Security",
            "Profile",
            "Status",
            "Online",
            "Offline",
            "Away",
            "Busy",
            "Do Not Disturb",
            "Last seen",
            "typing...",
            "recording...",
        ];

        // Check if text matches common UI elements
        let lower = trimmed.to_lowercase();
        for ui_element in &ui_elements {
            if lower == ui_element.to_lowercase() {
                return false;
            }
        }

        // Filter out pure timestamps (HH:MM format)
        let timestamp_pattern = regex::Regex::new(r"^\d{1,2}:\d{2}(\s?[AP]M)?$").unwrap();
        if timestamp_pattern.is_match(trimmed) {
            return false;
        }

        // Filter out date strings
        let date_pattern = regex::Regex::new(
            r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Today|Yesterday)$"
        ).unwrap();
        if date_pattern.is_match(trimmed) {
            return false;
        }

        // App-specific filtering
        match app_name {
            "Slack" => {
                // Filter out Slack-specific UI elements
                if lower.contains("thread") && trimmed.len() < 20 {
                    return false;
                }
                if lower.contains("reaction") && trimmed.len() < 20 {
                    return false;
                }
            }
            "Discord" => {
                // Filter out Discord-specific UI elements
                if lower.starts_with("#") && trimmed.len() < 30 {
                    return false;
                }
                if lower.contains("channel") && trimmed.len() < 20 {
                    return false;
                }
            }
            "Telegram" => {
                // Filter out Telegram-specific UI elements
                if lower.contains("viewed") || lower.contains("edited") {
                    return false;
                }
            }
            "Microsoft Teams" => {
                // Filter out Teams-specific UI elements
                if lower.contains("meeting") && trimmed.len() < 20 {
                    return false;
                }
            }
            _ => {}
        }

        // Must contain at least some alphanumeric content
        trimmed.chars().any(|c| c.is_alphanumeric())
    }

    /// Get the active chat name from window title
    #[cfg(target_os = "macos")]
    fn get_active_chat_name(&self, app_name: &str) -> Option<String> {
        use std::process::Command;

        // Use AppleScript to get the window title
        let script = format!(
            r#"tell application "System Events"
                tell process "{}"
                    try
                        get title of front window
                    on error
                        return ""
                    end try
                end tell
            end tell"#,
            app_name
        );

        let output = Command::new("osascript")
            .arg("-e")
            .arg(&script)
            .output()
            .ok()?;

        if output.status.success() {
            let title = String::from_utf8_lossy(&output.stdout).trim().to_string();
            if !title.is_empty() && title != app_name {
                return Some(title);
            }
        }

        None
    }

    #[cfg(not(target_os = "macos"))]
    fn get_active_chat_name(&self, _app_name: &str) -> Option<String> {
        None
    }
}

impl Default for MessengerMonitor {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_messenger() {
        let monitor = MessengerMonitor::new();
        assert!(monitor.is_messenger("Telegram"));
        assert!(monitor.is_messenger("Slack"));
        assert!(monitor.is_messenger("Discord"));
        assert!(monitor.is_messenger("Microsoft Teams"));
        assert!(!monitor.is_messenger("Chrome"));
        assert!(!monitor.is_messenger("Safari"));
    }

    #[test]
    fn test_looks_like_message() {
        let monitor = MessengerMonitor::new();

        // Valid messages
        assert!(monitor.looks_like_message("Hello, how are you?", "Telegram"));
        assert!(monitor.looks_like_message("Meeting at 3pm", "Slack"));
        assert!(monitor.looks_like_message("Check out this link: https://example.com", "Discord"));

        // Invalid messages (UI elements)
        assert!(!monitor.looks_like_message("Send", "Telegram"));
        assert!(!monitor.looks_like_message("Settings", "Slack"));
        assert!(!monitor.looks_like_message("Search", "Discord"));
        assert!(!monitor.looks_like_message("Type a message", "Teams"));

        // Invalid messages (timestamps)
        assert!(!monitor.looks_like_message("10:30", "Telegram"));
        assert!(!monitor.looks_like_message("3:45 PM", "Slack"));

        // Invalid messages (dates)
        assert!(!monitor.looks_like_message("Today", "Discord"));
        assert!(!monitor.looks_like_message("Monday", "Teams"));

        // Invalid messages (too short or too long)
        assert!(!monitor.looks_like_message("a", "Telegram"));
        assert!(!monitor.looks_like_message(&"x".repeat(6000), "Slack"));
    }

    #[test]
    fn test_message_creation() {
        let message = Message::new("Telegram".to_string(), "Test message".to_string())
            .with_sender("John Doe".to_string())
            .with_chat("Work Chat".to_string())
            .with_outgoing(true);

        assert_eq!(message.app, "Telegram");
        assert_eq!(message.content, "Test message");
        assert_eq!(message.sender, Some("John Doe".to_string()));
        assert_eq!(message.chat_name, Some("Work Chat".to_string()));
        assert!(message.is_outgoing);
    }

    #[test]
    fn test_messenger_state() {
        let mut state = MessengerState::new("Slack".to_string());
        state.active_chat = Some("general".to_string());
        state.visible_messages.push(
            Message::new("Slack".to_string(), "Hello everyone".to_string())
        );

        assert_eq!(state.app, "Slack");
        assert_eq!(state.active_chat, Some("general".to_string()));
        assert_eq!(state.visible_messages.len(), 1);
    }
}
