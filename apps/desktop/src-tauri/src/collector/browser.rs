use serde::{Deserialize, Serialize};
use std::process::Command;

/// Represents information about a browser tab
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BrowserTab {
    /// Browser name (Chrome, Safari, Firefox, etc.)
    pub browser: String,
    /// Current URL of the tab
    pub url: String,
    /// Title of the tab
    pub title: String,
    /// Visible text content (optional, may require additional scraping)
    pub visible_text: Option<String>,
}

/// Represents the current state of all browsers
#[allow(dead_code)]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BrowserState {
    /// Currently active browser name
    pub active_browser: Option<String>,
    /// Currently active tab
    pub active_tab: Option<BrowserTab>,
    /// All open tabs across browsers
    pub all_tabs: Vec<BrowserTab>,
}

/// Browser monitor for macOS
#[allow(dead_code)]
pub struct BrowserMonitor;

impl BrowserMonitor {
    /// Create a new BrowserMonitor instance
    pub fn new() -> Self {
        Self
    }

    /// Get the active tab from a specific browser application
    pub fn get_active_tab(&self, app_name: &str) -> Option<BrowserTab> {
        let normalized_name = app_name.to_lowercase();

        if normalized_name.contains("chrome") && !normalized_name.contains("arc") {
            self.get_chrome_active_tab()
        } else if normalized_name.contains("safari") {
            self.get_safari_active_tab()
        } else if normalized_name.contains("firefox") {
            self.get_firefox_active_tab()
        } else if normalized_name.contains("edge") {
            self.get_edge_active_tab()
        } else if normalized_name.contains("arc") {
            self.get_arc_active_tab()
        } else if normalized_name.contains("brave") {
            self.get_brave_active_tab()
        } else {
            None
        }
    }

    /// Get active tab from Google Chrome
    pub fn get_chrome_active_tab(&self) -> Option<BrowserTab> {
        let script = r#"
            tell application "Google Chrome"
                if (count of windows) > 0 then
                    set activeTab to active tab of front window
                    return URL of activeTab & "|||" & title of activeTab
                end if
            end tell
        "#;

        self.run_applescript_tab(script, "Chrome")
    }

    /// Get active tab from Safari
    pub fn get_safari_active_tab(&self) -> Option<BrowserTab> {
        let script = r#"
            tell application "Safari"
                if (count of windows) > 0 then
                    set currentTab to current tab of front window
                    return URL of currentTab & "|||" & name of currentTab
                end if
            end tell
        "#;

        self.run_applescript_tab(script, "Safari")
    }

    /// Get active tab from Firefox
    pub fn get_firefox_active_tab(&self) -> Option<BrowserTab> {
        let script = r#"
            tell application "Firefox"
                if (count of windows) > 0 then
                    tell front window
                        set currentTab to active tab
                        return URL of currentTab & "|||" & name of currentTab
                    end tell
                end if
            end tell
        "#;

        self.run_applescript_tab(script, "Firefox")
    }

    /// Get active tab from Microsoft Edge
    pub fn get_edge_active_tab(&self) -> Option<BrowserTab> {
        let script = r#"
            tell application "Microsoft Edge"
                if (count of windows) > 0 then
                    set activeTab to active tab of front window
                    return URL of activeTab & "|||" & title of activeTab
                end if
            end tell
        "#;

        self.run_applescript_tab(script, "Edge")
    }

    /// Get active tab from Arc Browser
    pub fn get_arc_active_tab(&self) -> Option<BrowserTab> {
        let script = r#"
            tell application "Arc"
                if (count of windows) > 0 then
                    set activeTab to active tab of front window
                    return URL of activeTab & "|||" & title of activeTab
                end if
            end tell
        "#;

        self.run_applescript_tab(script, "Arc")
    }

    /// Get active tab from Brave Browser
    pub fn get_brave_active_tab(&self) -> Option<BrowserTab> {
        let script = r#"
            tell application "Brave Browser"
                if (count of windows) > 0 then
                    set activeTab to active tab of front window
                    return URL of activeTab & "|||" & title of activeTab
                end if
            end tell
        "#;

        self.run_applescript_tab(script, "Brave")
    }

    /// Helper function to run AppleScript NATIVELY and parse tab information
    /// Uses NSAppleScript directly so macOS prompts for Automation permissions for Observer itself
    fn run_applescript_tab(&self, script: &str, browser_name: &str) -> Option<BrowserTab> {
        #[cfg(target_os = "macos")]
        {
            use objc::runtime::{Class, Object};
            use objc::{msg_send, sel, sel_impl};
            use std::ffi::{CStr, CString};

            unsafe {
                // Get NSAppleScript class
                let ns_applescript_class = Class::get("NSAppleScript")?;
                let ns_string_class = Class::get("NSString")?;

                // Create NSString from script
                let script_cstr = CString::new(script).ok()?;
                let source: *mut Object =
                    msg_send![ns_string_class, stringWithUTF8String: script_cstr.as_ptr()];
                if source.is_null() {
                    println!("[Browser] {} failed to create NSString", browser_name);
                    return None;
                }

                // Create NSAppleScript
                let script_obj: *mut Object = msg_send![ns_applescript_class, alloc];
                let script_obj: *mut Object = msg_send![script_obj, initWithSource: source];
                if script_obj.is_null() {
                    println!("[Browser] {} failed to create NSAppleScript", browser_name);
                    return None;
                }

                // Execute script
                let mut error: *mut Object = std::ptr::null_mut();
                let result: *mut Object = msg_send![script_obj, executeAndReturnError: &mut error];

                // Release script object
                let _: () = msg_send![script_obj, release];

                if result.is_null() {
                    if !error.is_null() {
                        let error_key: *mut Object = msg_send![ns_string_class, stringWithUTF8String: CString::new("NSAppleScriptErrorMessage").unwrap().as_ptr()];
                        let error_desc: *mut Object = msg_send![error, objectForKey: error_key];
                        if !error_desc.is_null() {
                            let c_str: *const i8 = msg_send![error_desc, UTF8String];
                            if !c_str.is_null() {
                                let error_msg = CStr::from_ptr(c_str).to_string_lossy();
                                println!(
                                    "[Browser] {} AppleScript error: {}",
                                    browser_name, error_msg
                                );
                            }
                        }
                    }
                    return None;
                }

                // Get string value from result
                let string_value: *mut Object = msg_send![result, stringValue];
                if string_value.is_null() {
                    println!("[Browser] {} result has no stringValue", browser_name);
                    return None;
                }

                let c_str: *const i8 = msg_send![string_value, UTF8String];
                if c_str.is_null() {
                    println!("[Browser] {} UTF8String is null", browser_name);
                    return None;
                }

                let output_str = CStr::from_ptr(c_str).to_string_lossy().trim().to_string();
                println!("[Browser] {} returned: {}", browser_name, output_str);

                if output_str.is_empty() {
                    return None;
                }

                // Parse the output format: "URL|||Title"
                let parts: Vec<&str> = output_str.split("|||").collect();
                if parts.len() == 2 {
                    Some(BrowserTab {
                        browser: browser_name.to_string(),
                        url: parts[0].to_string(),
                        title: parts[1].to_string(),
                        visible_text: None,
                    })
                } else {
                    println!("[Browser] {} unexpected format: {}", browser_name, output_str);
                    None
                }
            }
        }

        #[cfg(not(target_os = "macos"))]
        {
            let _ = (script, browser_name);
            None
        }
    }

    /// Get all open tabs from a specific browser
    pub fn get_all_tabs(&self, browser: &str) -> Vec<BrowserTab> {
        let script = match browser.to_lowercase().as_str() {
            "chrome" => r#"
                tell application "Google Chrome"
                    set tabList to {}
                    repeat with w in windows
                        repeat with t in tabs of w
                            set end of tabList to (URL of t & "|||" & title of t)
                        end repeat
                    end repeat
                    return tabList
                end tell
            "#,
            "safari" => r#"
                tell application "Safari"
                    set tabList to {}
                    repeat with w in windows
                        repeat with t in tabs of w
                            set end of tabList to (URL of t & "|||" & name of t)
                        end repeat
                    end repeat
                    return tabList
                end tell
            "#,
            "firefox" => r#"
                tell application "Firefox"
                    set tabList to {}
                    repeat with w in windows
                        repeat with t in tabs of w
                            set end of tabList to (URL of t & "|||" & name of t)
                        end repeat
                    end repeat
                    return tabList
                end tell
            "#,
            "edge" => r#"
                tell application "Microsoft Edge"
                    set tabList to {}
                    repeat with w in windows
                        repeat with t in tabs of w
                            set end of tabList to (URL of t & "|||" & title of t)
                        end repeat
                    end repeat
                    return tabList
                end tell
            "#,
            "arc" => r#"
                tell application "Arc"
                    set tabList to {}
                    repeat with w in windows
                        repeat with t in tabs of w
                            set end of tabList to (URL of t & "|||" & title of t)
                        end repeat
                    end repeat
                    return tabList
                end tell
            "#,
            "brave" => r#"
                tell application "Brave Browser"
                    set tabList to {}
                    repeat with w in windows
                        repeat with t in tabs of w
                            set end of tabList to (URL of t & "|||" & title of t)
                        end repeat
                    end repeat
                    return tabList
                end tell
            "#,
            _ => return vec![],
        };

        let output = Command::new("osascript")
            .arg("-e")
            .arg(script)
            .output();

        match output {
            Ok(result) => {
                if result.status.success() {
                    let output_str = String::from_utf8_lossy(&result.stdout).trim().to_string();

                    if output_str.is_empty() {
                        return vec![];
                    }

                    // Parse the output - AppleScript returns comma-separated list
                    output_str
                        .split(", ")
                        .filter_map(|item| {
                            let parts: Vec<&str> = item.split("|||").collect();
                            if parts.len() == 2 {
                                Some(BrowserTab {
                                    browser: browser.to_string(),
                                    url: parts[0].to_string(),
                                    title: parts[1].to_string(),
                                    visible_text: None,
                                })
                            } else {
                                None
                            }
                        })
                        .collect()
                } else {
                    vec![]
                }
            }
            Err(_) => vec![],
        }
    }

    /// Get the current browser state with active browser and all tabs
    pub fn get_browser_state(&self, active_app: Option<&str>) -> BrowserState {
        let active_browser = active_app.map(|s| s.to_string());
        let active_tab = active_app.and_then(|app| self.get_active_tab(app));

        // Collect all tabs from known browsers
        let browsers = vec!["Chrome", "Safari", "Firefox", "Edge", "Arc", "Brave"];
        let mut all_tabs = Vec::new();

        for browser in browsers {
            let tabs = self.get_all_tabs(browser);
            all_tabs.extend(tabs);
        }

        BrowserState {
            active_browser,
            active_tab,
            all_tabs,
        }
    }

    /// Check if a browser is running
    pub fn is_browser_running(&self, browser_name: &str) -> bool {
        let script = format!(
            r#"
                tell application "System Events"
                    return exists (processes where name is "{}")
                end tell
            "#,
            browser_name
        );

        let output = Command::new("osascript")
            .arg("-e")
            .arg(&script)
            .output();

        match output {
            Ok(result) => {
                if result.status.success() {
                    let output_str = String::from_utf8_lossy(&result.stdout).trim().to_string();
                    output_str == "true"
                } else {
                    false
                }
            }
            Err(_) => false,
        }
    }

    /// Get list of currently running browsers
    pub fn get_running_browsers(&self) -> Vec<String> {
        let browser_names = vec![
            "Google Chrome",
            "Safari",
            "Firefox",
            "Microsoft Edge",
            "Arc",
            "Brave Browser",
        ];

        browser_names
            .into_iter()
            .filter(|&browser| self.is_browser_running(browser))
            .map(|s| s.to_string())
            .collect()
    }
}

impl Default for BrowserMonitor {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_browser_monitor_creation() {
        let monitor = BrowserMonitor::new();
        assert!(true); // Just ensure it can be created
    }

    #[test]
    fn test_browser_state_creation() {
        let state = BrowserState {
            active_browser: Some("Chrome".to_string()),
            active_tab: None,
            all_tabs: vec![],
        };
        assert_eq!(state.active_browser, Some("Chrome".to_string()));
    }

    #[test]
    fn test_browser_tab_creation() {
        let tab = BrowserTab {
            browser: "Chrome".to_string(),
            url: "https://example.com".to_string(),
            title: "Example".to_string(),
            visible_text: None,
        };
        assert_eq!(tab.browser, "Chrome");
        assert_eq!(tab.url, "https://example.com");
    }
}
