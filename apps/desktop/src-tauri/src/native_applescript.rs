//! AppleScript execution via osascript command
//! Using osascript ensures Automation permission dialogs are triggered properly.

use std::process::Command;

/// Execute AppleScript using osascript command
/// Returns the result as a String, or None if execution failed
#[cfg(target_os = "macos")]
pub fn execute(script: &str) -> Option<String> {
    let output = Command::new("osascript")
        .arg("-e")
        .arg(script)
        .output()
        .ok()?;

    if output.status.success() {
        let result = String::from_utf8_lossy(&output.stdout).trim().to_string();
        Some(result)
    } else {
        let err = String::from_utf8_lossy(&output.stderr);
        eprintln!("[AppleScript] Error: {}", err);
        None
    }
}

#[cfg(not(target_os = "macos"))]
pub fn execute(_script: &str) -> Option<String> {
    None
}

/// Execute AppleScript and return true/false result
#[allow(dead_code)]
pub fn execute_bool(script: &str) -> bool {
    execute(script)
        .map(|s| s.trim().to_lowercase() == "true")
        .unwrap_or(false)
}

/// Check if we have Automation permission for a specific app
pub fn check_app_permission(app_name: &str) -> bool {
    let script = format!(
        r#"tell application "{}"
            return name
        end tell"#,
        app_name
    );
    execute(&script).is_some()
}

/// Request Automation permission for a specific app
/// This will trigger macOS permission dialog if not already granted
pub fn request_app_permission(app_name: &str) -> bool {
    let script = format!(
        r#"tell application "{}"
            return name
        end tell"#,
        app_name
    );
    execute(&script).is_some()
}

/// Trigger automation permission request for a specific app
/// This spawns osascript as a child process which properly triggers
/// macOS permission dialogs
pub fn trigger_permission_for_app(app_name: &str) -> bool {
    let script = format!(r#"tell application "{}" to name"#, app_name);
    Command::new("osascript")
        .arg("-e")
        .arg(&script)
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}
