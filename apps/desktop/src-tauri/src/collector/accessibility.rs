// Accessibility API wrapper for macOS
// This module provides access to the macOS Accessibility API
// to read information about the currently focused application and UI elements

#[cfg(target_os = "macos")]
pub mod macos {
    use core_foundation::base::{CFType, TCFType};
    use core_foundation::boolean::CFBoolean;
    use core_foundation::string::CFString;
    use core_graphics::display::CGWindowListCopyWindowInfo;
    use core_graphics::window::{
        kCGNullWindowID, kCGWindowListOptionOnScreenOnly, kCGWindowName, kCGWindowOwnerName,
    };
    use std::ffi::c_void;

    // External C function declarations for Accessibility API
    #[link(name = "ApplicationServices", kind = "framework")]
    extern "C" {
        fn AXIsProcessTrusted() -> bool;
        fn AXUIElementCreateSystemWide() -> *mut c_void;
        fn AXUIElementCopyAttributeValue(
            element: *mut c_void,
            attribute: *const c_void,
            value: *mut *mut c_void,
        ) -> i32;
        fn CFRelease(cf: *mut c_void);
    }

    // AX error codes
    const K_AX_ERROR_SUCCESS: i32 = 0;

    // AX attribute names
    const K_AX_FOCUSED_APPLICATION_ATTRIBUTE: &str = "AXFocusedApplication";
    const K_AX_TITLE_ATTRIBUTE: &str = "AXTitle";
    const K_AX_FOCUSED_UI_ELEMENT_ATTRIBUTE: &str = "AXFocusedUIElement";
    const K_AX_SELECTED_TEXT_ATTRIBUTE: &str = "AXSelectedText";
    const K_AX_VALUE_ATTRIBUTE: &str = "AXValue";
    const K_AX_ROLE_ATTRIBUTE: &str = "AXRole";

    /// Get information about the currently focused UI element
    /// Returns (app_name, window_title) if successful
    pub fn get_focused_element_info() -> Option<(String, String)> {
        unsafe {
            let system_wide = AXUIElementCreateSystemWide();
            if system_wide.is_null() {
                return None;
            }

            // Get focused application
            let attr_name = CFString::new(K_AX_FOCUSED_APPLICATION_ATTRIBUTE);
            let mut focused_app: *mut c_void = std::ptr::null_mut();

            let result = AXUIElementCopyAttributeValue(
                system_wide,
                attr_name.as_concrete_TypeRef() as *const c_void,
                &mut focused_app,
            );

            CFRelease(system_wide);

            if result != K_AX_ERROR_SUCCESS || focused_app.is_null() {
                return None;
            }

            // Get app title
            let title_attr = CFString::new(K_AX_TITLE_ATTRIBUTE);
            let mut title_value: *mut c_void = std::ptr::null_mut();

            let title_result = AXUIElementCopyAttributeValue(
                focused_app,
                title_attr.as_concrete_TypeRef() as *const c_void,
                &mut title_value,
            );

            let app_name = if title_result == K_AX_ERROR_SUCCESS && !title_value.is_null() {
                let cf_string = CFString::wrap_under_create_rule(title_value as _);
                let name = cf_string.to_string();
                name
            } else {
                "Unknown".to_string()
            };

            // Get focused window/UI element
            let focused_attr = CFString::new(K_AX_FOCUSED_UI_ELEMENT_ATTRIBUTE);
            let mut focused_element: *mut c_void = std::ptr::null_mut();

            let element_result = AXUIElementCopyAttributeValue(
                focused_app,
                focused_attr.as_concrete_TypeRef() as *const c_void,
                &mut focused_element,
            );

            CFRelease(focused_app);

            let window_title = if element_result == K_AX_ERROR_SUCCESS && !focused_element.is_null()
            {
                // Try to get title of focused element
                let win_title_attr = CFString::new(K_AX_TITLE_ATTRIBUTE);
                let mut win_title_value: *mut c_void = std::ptr::null_mut();

                let win_result = AXUIElementCopyAttributeValue(
                    focused_element,
                    win_title_attr.as_concrete_TypeRef() as *const c_void,
                    &mut win_title_value,
                );

                CFRelease(focused_element);

                if win_result == K_AX_ERROR_SUCCESS && !win_title_value.is_null() {
                    let cf_string = CFString::wrap_under_create_rule(win_title_value as _);
                    cf_string.to_string()
                } else {
                    String::new()
                }
            } else {
                String::new()
            };

            Some((app_name, window_title))
        }
    }

    /// Get currently selected text in the focused application
    pub fn get_selected_text() -> Option<String> {
        unsafe {
            let system_wide = AXUIElementCreateSystemWide();
            if system_wide.is_null() {
                return None;
            }

            // Get focused application
            let attr_name = CFString::new(K_AX_FOCUSED_APPLICATION_ATTRIBUTE);
            let mut focused_app: *mut c_void = std::ptr::null_mut();

            let result = AXUIElementCopyAttributeValue(
                system_wide,
                attr_name.as_concrete_TypeRef() as *const c_void,
                &mut focused_app,
            );

            CFRelease(system_wide);

            if result != K_AX_ERROR_SUCCESS || focused_app.is_null() {
                return None;
            }

            // Get focused UI element
            let focused_attr = CFString::new(K_AX_FOCUSED_UI_ELEMENT_ATTRIBUTE);
            let mut focused_element: *mut c_void = std::ptr::null_mut();

            let element_result = AXUIElementCopyAttributeValue(
                focused_app,
                focused_attr.as_concrete_TypeRef() as *const c_void,
                &mut focused_element,
            );

            CFRelease(focused_app);

            if element_result != K_AX_ERROR_SUCCESS || focused_element.is_null() {
                return None;
            }

            // Get selected text
            let selected_text_attr = CFString::new(K_AX_SELECTED_TEXT_ATTRIBUTE);
            let mut selected_text: *mut c_void = std::ptr::null_mut();

            let text_result = AXUIElementCopyAttributeValue(
                focused_element,
                selected_text_attr.as_concrete_TypeRef() as *const c_void,
                &mut selected_text,
            );

            CFRelease(focused_element);

            if text_result == K_AX_ERROR_SUCCESS && !selected_text.is_null() {
                let cf_string = CFString::wrap_under_create_rule(selected_text as _);
                let text = cf_string.to_string();
                if !text.is_empty() {
                    return Some(text);
                }
            }

            None
        }
    }

    /// Get the current URL from browser (if focused)
    pub fn get_browser_url() -> Option<String> {
        unsafe {
            let system_wide = AXUIElementCreateSystemWide();
            if system_wide.is_null() {
                return None;
            }

            // Get focused application
            let attr_name = CFString::new(K_AX_FOCUSED_APPLICATION_ATTRIBUTE);
            let mut focused_app: *mut c_void = std::ptr::null_mut();

            let result = AXUIElementCopyAttributeValue(
                system_wide,
                attr_name.as_concrete_TypeRef() as *const c_void,
                &mut focused_app,
            );

            CFRelease(system_wide);

            if result != K_AX_ERROR_SUCCESS || focused_app.is_null() {
                return None;
            }

            // Get app name to check if it's a browser
            let title_attr = CFString::new(K_AX_TITLE_ATTRIBUTE);
            let mut title_value: *mut c_void = std::ptr::null_mut();

            let title_result = AXUIElementCopyAttributeValue(
                focused_app,
                title_attr.as_concrete_TypeRef() as *const c_void,
                &mut title_value,
            );

            let app_name = if title_result == K_AX_ERROR_SUCCESS && !title_value.is_null() {
                let cf_string = CFString::wrap_under_create_rule(title_value as _);
                cf_string.to_string().to_lowercase()
            } else {
                CFRelease(focused_app);
                return None;
            };

            // Check if it's a browser
            let is_browser = app_name.contains("chrome")
                || app_name.contains("safari")
                || app_name.contains("firefox")
                || app_name.contains("edge")
                || app_name.contains("arc")
                || app_name.contains("brave");

            if !is_browser {
                CFRelease(focused_app);
                return None;
            }

            // Try to get URL from address bar (AXValue of text field)
            // This is browser-specific and may not work for all browsers
            // For a full implementation, you'd need to navigate the accessibility tree

            CFRelease(focused_app);
            None // URL extraction is complex and browser-specific
        }
    }

    /// Check if the app has accessibility permission
    pub fn has_accessibility_permission() -> bool {
        unsafe { AXIsProcessTrusted() }
    }

    /// Request accessibility permission from the user
    /// Opens System Preferences to the appropriate pane
    pub fn request_accessibility_permission() -> bool {
        use std::process::Command;

        // Open System Preferences to Privacy & Security > Accessibility
        let result = Command::new("open")
            .arg("x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility")
            .spawn();

        result.is_ok()
    }

    /// Get all visible windows using CGWindowListCopyWindowInfo
    pub fn get_all_windows() -> Vec<(String, String)> {
        unsafe {
            let window_list = CGWindowListCopyWindowInfo(
                kCGWindowListOptionOnScreenOnly,
                kCGNullWindowID,
            );

            if window_list.is_null() {
                return Vec::new();
            }

            let mut windows = Vec::new();
            let count = core_foundation::array::CFArray::<core_foundation::dictionary::CFDictionary>::wrap_under_get_rule(window_list as _).len();

            for i in 0..count {
                let array = core_foundation::array::CFArray::<core_foundation::dictionary::CFDictionary>::wrap_under_get_rule(window_list as _);
                if let Some(dict) = array.get(i as isize) {
                    // Get owner name (app name)
                    let owner_key = CFString::new("kCGWindowOwnerName");
                    let app_name = dict.find(owner_key.as_concrete_TypeRef() as *const c_void)
                        .map(|v| {
                            let cf_str = CFString::wrap_under_get_rule(*v as _);
                            cf_str.to_string()
                        })
                        .unwrap_or_default();

                    // Get window name (title)
                    let name_key = CFString::new("kCGWindowName");
                    let window_title = dict.find(name_key.as_concrete_TypeRef() as *const c_void)
                        .map(|v| {
                            let cf_str = CFString::wrap_under_get_rule(*v as _);
                            cf_str.to_string()
                        })
                        .unwrap_or_default();

                    if !app_name.is_empty() {
                        windows.push((app_name, window_title));
                    }
                }
            }

            CFRelease(window_list as *mut c_void);
            windows
        }
    }
}

#[cfg(not(target_os = "macos"))]
pub mod macos {
    /// Get information about the currently focused UI element
    pub fn get_focused_element_info() -> Option<(String, String)> {
        None
    }

    /// Get currently selected text in the focused application
    pub fn get_selected_text() -> Option<String> {
        None
    }

    /// Get the current URL from browser (if focused)
    pub fn get_browser_url() -> Option<String> {
        None
    }

    /// Check if the app has accessibility permission
    pub fn has_accessibility_permission() -> bool {
        true
    }

    /// Request accessibility permission from the user
    pub fn request_accessibility_permission() -> bool {
        true
    }

    /// Get all visible windows
    pub fn get_all_windows() -> Vec<(String, String)> {
        Vec::new()
    }
}
