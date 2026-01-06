// Application tracking module
// This module provides functions to get information about the currently active application

#[cfg(target_os = "macos")]
pub fn get_active_window() -> (Option<String>, Option<String>) {
    use std::process::Command;

    // Use osascript to get the active application name and window title
    let app_script = r#"
        tell application "System Events"
            set frontApp to first application process whose frontmost is true
            return name of frontApp
        end tell
    "#;

    let title_script = r#"
        tell application "System Events"
            set frontApp to first application process whose frontmost is true
            try
                return name of front window of frontApp
            on error
                return ""
            end try
        end tell
    "#;

    let app_name = Command::new("osascript")
        .arg("-e")
        .arg(app_script)
        .output()
        .ok()
        .and_then(|output| {
            String::from_utf8(output.stdout)
                .ok()
                .map(|s| s.trim().to_string())
        })
        .filter(|s| !s.is_empty());

    let window_title = Command::new("osascript")
        .arg("-e")
        .arg(title_script)
        .output()
        .ok()
        .and_then(|output| {
            String::from_utf8(output.stdout)
                .ok()
                .map(|s| s.trim().to_string())
        })
        .filter(|s| !s.is_empty());

    (app_name, window_title)
}

#[cfg(not(target_os = "macos"))]
pub fn get_active_window() -> (Option<String>, Option<String>) {
    // Placeholder for non-macOS systems
    (None, None)
}

pub fn get_running_apps() -> Vec<String> {
    #[cfg(target_os = "macos")]
    {
        use std::process::Command;

        let script = r#"
            tell application "System Events"
                set appList to name of every application process whose background only is false
                return appList
            end tell
        "#;

        Command::new("osascript")
            .arg("-e")
            .arg(script)
            .output()
            .ok()
            .and_then(|output| String::from_utf8(output.stdout).ok())
            .map(|s| {
                s.trim()
                    .split(", ")
                    .map(|app| app.to_string())
                    .collect()
            })
            .unwrap_or_default()
    }

    #[cfg(not(target_os = "macos"))]
    {
        Vec::new()
    }
}
