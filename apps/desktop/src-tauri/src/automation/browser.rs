/// Browser automation module via AppleScript
/// Supports Chrome, Safari, Arc, and Firefox

use std::process::Command;
use serde::{Serialize, Deserialize};

/// Supported browsers
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum Browser {
    Chrome,
    Safari,
    Arc,
    Firefox,
}

impl Browser {
    /// Get browser bundle identifier for macOS
    fn bundle_id(&self) -> &'static str {
        match self {
            Browser::Chrome => "com.google.Chrome",
            Browser::Safari => "com.apple.Safari",
            Browser::Arc => "company.thebrowser.Browser",
            Browser::Firefox => "org.mozilla.firefox",
        }
    }

    /// Get browser name for AppleScript
    fn applescript_name(&self) -> &'static str {
        match self {
            Browser::Chrome => "Google Chrome",
            Browser::Safari => "Safari",
            Browser::Arc => "Arc",
            Browser::Firefox => "Firefox",
        }
    }

    /// Check if browser is running
    pub fn is_running(&self) -> Result<bool, String> {
        #[cfg(target_os = "macos")]
        {
            let script = format!(
                r#"tell application "System Events"
                    return (name of processes) contains "{}"
                end tell"#,
                self.applescript_name()
            );

            let output = execute_applescript(&script)?;
            Ok(output.trim() == "true")
        }

        #[cfg(not(target_os = "macos"))]
        {
            Err("Browser automation only supported on macOS".to_string())
        }
    }

    /// Launch browser if not running
    pub fn launch(&self) -> Result<(), String> {
        #[cfg(target_os = "macos")]
        {
            let script = format!(
                r#"tell application "{}" to activate"#,
                self.applescript_name()
            );

            execute_applescript(&script)?;
            Ok(())
        }

        #[cfg(not(target_os = "macos"))]
        {
            Err("Browser automation only supported on macOS".to_string())
        }
    }
}

/// Get current URL from active tab in specified browser
pub fn get_browser_url(browser: Browser) -> Result<String, String> {
    #[cfg(target_os = "macos")]
    {
        if !browser.is_running()? {
            return Err(format!("{:?} is not running", browser));
        }

        let script = match browser {
            Browser::Chrome | Browser::Arc => {
                format!(
                    r#"tell application "{}"
                        return URL of active tab of front window
                    end tell"#,
                    browser.applescript_name()
                )
            }
            Browser::Safari => {
                r#"tell application "Safari"
                    return URL of current tab of front window
                end tell"#
                    .to_string()
            }
            Browser::Firefox => {
                // Firefox requires more complex AppleScript
                r#"tell application "Firefox"
                    tell application "System Events"
                        keystroke "l" using command down
                        keystroke "c" using command down
                    end tell
                end tell
                delay 0.1
                return the clipboard"#
                    .to_string()
            }
        };

        let url = execute_applescript(&script)?;
        Ok(url.trim().to_string())
    }

    #[cfg(not(target_os = "macos"))]
    {
        Err("Browser automation only supported on macOS".to_string())
    }
}

/// Navigate to URL in specified browser
pub fn navigate_to_url(browser: Browser, url: &str) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        // Launch browser if not running
        if !browser.is_running()? {
            browser.launch()?;
            // Wait for browser to launch
            std::thread::sleep(std::time::Duration::from_secs(2));
        }

        let script = match browser {
            Browser::Chrome | Browser::Arc => {
                format!(
                    r#"tell application "{}"
                        if (count of windows) = 0 then
                            make new window
                        end if
                        set URL of active tab of front window to "{}"
                        activate
                    end tell"#,
                    browser.applescript_name(),
                    url
                )
            }
            Browser::Safari => {
                format!(
                    r#"tell application "Safari"
                        if (count of windows) = 0 then
                            make new document
                        end if
                        set URL of current tab of front window to "{}"
                        activate
                    end tell"#,
                    url
                )
            }
            Browser::Firefox => {
                // Firefox requires different approach
                format!(
                    r#"tell application "Firefox"
                        activate
                        open location "{}"
                    end tell"#,
                    url
                )
            }
        };

        execute_applescript(&script)?;
        Ok(())
    }

    #[cfg(not(target_os = "macos"))]
    {
        Err("Browser automation only supported on macOS".to_string())
    }
}

/// Create new tab in specified browser
pub fn new_tab(browser: Browser, url: Option<&str>) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        if !browser.is_running()? {
            browser.launch()?;
        }

        let script = match browser {
            Browser::Chrome | Browser::Arc => {
                if let Some(url) = url {
                    format!(
                        r#"tell application "{}"
                            tell front window
                                make new tab with properties {{URL:"{}"}}
                            end tell
                        end tell"#,
                        browser.applescript_name(),
                        url
                    )
                } else {
                    format!(
                        r#"tell application "{}"
                            tell front window to make new tab
                        end tell"#,
                        browser.applescript_name()
                    )
                }
            }
            Browser::Safari => {
                if let Some(url) = url {
                    format!(
                        r#"tell application "Safari"
                            tell front window
                                set current tab to (make new tab with properties {{URL:"{}"}})
                            end tell
                        end tell"#,
                        url
                    )
                } else {
                    r#"tell application "Safari"
                        tell front window to make new tab
                    end tell"#
                        .to_string()
                }
            }
            Browser::Firefox => {
                format!(
                    r#"tell application "Firefox"
                        activate
                        tell application "System Events"
                            keystroke "t" using command down
                        end tell
                    end tell"#
                )
            }
        };

        execute_applescript(&script)?;
        Ok(())
    }

    #[cfg(not(target_os = "macos"))]
    {
        Err("Browser automation only supported on macOS".to_string())
    }
}

/// Close current tab in specified browser
pub fn close_tab(browser: Browser) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        if !browser.is_running()? {
            return Err(format!("{:?} is not running", browser));
        }

        let script = match browser {
            Browser::Chrome | Browser::Arc => {
                format!(
                    r#"tell application "{}"
                        close active tab of front window
                    end tell"#,
                    browser.applescript_name()
                )
            }
            Browser::Safari => {
                r#"tell application "Safari"
                    close current tab of front window
                end tell"#
                    .to_string()
            }
            Browser::Firefox => {
                r#"tell application "Firefox"
                    tell application "System Events"
                        keystroke "w" using command down
                    end tell
                end tell"#
                    .to_string()
            }
        };

        execute_applescript(&script)?;
        Ok(())
    }

    #[cfg(not(target_os = "macos"))]
    {
        Err("Browser automation only supported on macOS".to_string())
    }
}

/// Execute AppleScript and return output
#[cfg(target_os = "macos")]
fn execute_applescript(script: &str) -> Result<String, String> {
    let output = Command::new("osascript")
        .arg("-e")
        .arg(script)
        .output()
        .map_err(|e| format!("Failed to execute AppleScript: {}", e))?;

    if output.status.success() {
        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        Ok(stdout)
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        Err(format!("AppleScript error: {}", stderr))
    }
}

/// Detect which browser is currently active
pub fn detect_active_browser() -> Result<Option<Browser>, String> {
    #[cfg(target_os = "macos")]
    {
        let script = r#"tell application "System Events"
            return name of first application process whose frontmost is true
        end tell"#;

        let output = execute_applescript(script)?;
        let app_name = output.trim();

        let browser = match app_name {
            "Google Chrome" => Some(Browser::Chrome),
            "Safari" => Some(Browser::Safari),
            "Arc" => Some(Browser::Arc),
            "Firefox" => Some(Browser::Firefox),
            _ => None,
        };

        Ok(browser)
    }

    #[cfg(not(target_os = "macos"))]
    {
        Err("Browser automation only supported on macOS".to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_browser_names() {
        assert_eq!(Browser::Chrome.applescript_name(), "Google Chrome");
        assert_eq!(Browser::Safari.applescript_name(), "Safari");
        assert_eq!(Browser::Arc.applescript_name(), "Arc");
        assert_eq!(Browser::Firefox.applescript_name(), "Firefox");
    }
}
