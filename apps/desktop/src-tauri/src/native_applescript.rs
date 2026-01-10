//! Native AppleScript execution via NSAppleScript
//! This ensures Automation permissions are requested for Observer itself,
//! not for a separate osascript process.

#[cfg(target_os = "macos")]
use objc::runtime::{Class, Object};
#[cfg(target_os = "macos")]
use objc::{msg_send, sel, sel_impl};
#[cfg(target_os = "macos")]
use std::ffi::{CStr, CString};

/// Execute AppleScript natively using NSAppleScript
/// Returns the result as a String, or None if execution failed
#[cfg(target_os = "macos")]
pub fn execute(script: &str) -> Option<String> {
    unsafe {
        // Get NSAppleScript class
        let ns_applescript_class = Class::get("NSAppleScript")?;
        let ns_string_class = Class::get("NSString")?;

        // Create NSString from script
        let script_cstr = CString::new(script).ok()?;
        let source: *mut Object =
            msg_send![ns_string_class, stringWithUTF8String: script_cstr.as_ptr()];

        if source.is_null() {
            eprintln!("[NativeAppleScript] Failed to create NSString from script");
            return None;
        }

        // Create NSAppleScript instance
        let script_obj: *mut Object = msg_send![ns_applescript_class, alloc];
        let script_obj: *mut Object = msg_send![script_obj, initWithSource: source];

        if script_obj.is_null() {
            eprintln!("[NativeAppleScript] Failed to create NSAppleScript");
            return None;
        }

        // Execute the script
        let mut error: *mut Object = std::ptr::null_mut();
        let result: *mut Object = msg_send![script_obj, executeAndReturnError: &mut error];

        // Release script object
        let _: () = msg_send![script_obj, release];

        // Check for errors
        if !error.is_null() {
            let error_key: *mut Object = msg_send![
                ns_string_class,
                stringWithUTF8String: CString::new("NSAppleScriptErrorMessage").unwrap().as_ptr()
            ];
            let error_desc: *mut Object = msg_send![error, objectForKey: error_key];
            if !error_desc.is_null() {
                let error_str: *const i8 = msg_send![error_desc, UTF8String];
                if !error_str.is_null() {
                    let error_msg = CStr::from_ptr(error_str).to_string_lossy();
                    eprintln!("[NativeAppleScript] Error: {}", error_msg);
                }
            }
            return None;
        }

        if result.is_null() {
            return Some(String::new());
        }

        // Get string value from result
        let string_value: *mut Object = msg_send![result, stringValue];
        if string_value.is_null() {
            return Some(String::new());
        }

        let c_str: *const i8 = msg_send![string_value, UTF8String];
        if c_str.is_null() {
            return Some(String::new());
        }

        Some(
            CStr::from_ptr(c_str)
                .to_string_lossy()
                .trim()
                .to_string(),
        )
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
