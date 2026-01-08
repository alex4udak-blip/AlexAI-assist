// Accessibility API wrapper for macOS
// This module provides access to the macOS Accessibility API
// to read information about the currently focused application and UI elements
//
// THREAD SAFETY NOTES:
// - All Core Foundation and Accessibility API calls in this module should be made from the main thread
// - Core Graphics window functions should also be called from the main thread
// - Functions in this module are marked with thread safety requirements

#[cfg(target_os = "macos")]
pub mod macos {
    use core_foundation::base::TCFType;
    use core_foundation::string::CFString;
    use core_graphics::display::CGWindowListCopyWindowInfo;
    use core_graphics::window::{kCGNullWindowID, kCGWindowListOptionOnScreenOnly};
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

    // External C function declarations for GCD (Grand Central Dispatch)
    #[link(name = "System", kind = "dylib")]
    extern "C" {
        fn dispatch_get_main_queue() -> *mut c_void;
        fn dispatch_sync_f(
            queue: *mut c_void,
            context: *mut c_void,
            work: unsafe extern "C" fn(*mut c_void),
        );
        fn pthread_main_np() -> i32;
    }

    /// Check if the current thread is the main thread
    ///
    /// # Safety
    /// This function calls into pthread APIs which are safe to call from any thread
    #[inline]
    fn is_main_thread() -> bool {
        unsafe { pthread_main_np() != 0 }
    }

    /// Assert that we're running on the main thread
    ///
    /// # Panics
    /// Panics if called from a non-main thread
    #[inline]
    fn assert_main_thread() {
        if !is_main_thread() {
            panic!("This function must be called from the main thread");
        }
    }

    /// Execute a closure on the main thread synchronously
    ///
    /// If already on the main thread, executes immediately.
    /// Otherwise, dispatches to main thread and waits for completion.
    ///
    /// # Safety
    /// Uses GCD (Grand Central Dispatch) FFI calls
    fn run_on_main_thread<F, R>(f: F) -> R
    where
        F: FnOnce() -> R + Send,
        R: Send,
    {
        if is_main_thread() {
            // Already on main thread, execute directly
            return f();
        }

        // Need to dispatch to main thread
        use std::mem::ManuallyDrop;

        struct Context<F, R> {
            func: ManuallyDrop<F>,
            result: ManuallyDrop<Option<R>>,
        }

        unsafe extern "C" fn trampoline<F, R>(ctx: *mut c_void)
        where
            F: FnOnce() -> R,
        {
            let ctx = &mut *(ctx as *mut Context<F, R>);
            let func = ManuallyDrop::take(&mut ctx.func);
            let result = func();
            ctx.result = ManuallyDrop::new(Some(result));
        }

        unsafe {
            let mut ctx = Context {
                func: ManuallyDrop::new(f),
                result: ManuallyDrop::new(None),
            };

            let main_queue = dispatch_get_main_queue();
            dispatch_sync_f(
                main_queue,
                &mut ctx as *mut _ as *mut c_void,
                trampoline::<F, R>,
            );

            ManuallyDrop::take(&mut ctx.result).unwrap()
        }
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

    /// Get information about the currently focused UI element (internal implementation)
    /// Returns (app_name, window_title) if successful
    ///
    /// # Thread Safety
    /// This function must be called from the main thread only.
    ///
    /// # Safety
    /// Uses unsafe FFI calls to Core Foundation and Accessibility APIs
    fn get_focused_element_info_impl() -> Option<(String, String)> {
        assert_main_thread();

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
                // Release if non-null but failed
                if !title_value.is_null() {
                    CFRelease(title_value);
                }
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
                    // Release if non-null but failed
                    if !win_title_value.is_null() {
                        CFRelease(win_title_value);
                    }
                    String::new()
                }
            } else {
                // Release if non-null but failed to get element
                if !focused_element.is_null() {
                    CFRelease(focused_element);
                }
                String::new()
            };

            CFRelease(focused_app);
            Some((app_name, window_title))
        }
    }

    /// Get information about the currently focused UI element
    /// Returns (app_name, window_title) if successful
    ///
    /// # Thread Safety
    /// This function is thread-safe. It can be called from any thread.
    /// If not on the main thread, it will automatically dispatch to the main thread.
    pub fn get_focused_element_info() -> Option<(String, String)> {
        run_on_main_thread(|| get_focused_element_info_impl())
    }

    /// Get currently selected text in the focused application (internal implementation)
    ///
    /// # Thread Safety
    /// This function must be called from the main thread only.
    ///
    /// # Safety
    /// Uses unsafe FFI calls to Core Foundation and Accessibility APIs
    fn get_selected_text_impl() -> Option<String> {
        assert_main_thread();

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
            } else if !selected_text.is_null() {
                // Release if non-null but failed
                CFRelease(selected_text);
            }

            None
        }
    }

    /// Get currently selected text in the focused application
    ///
    /// # Thread Safety
    /// This function is thread-safe. It can be called from any thread.
    /// If not on the main thread, it will automatically dispatch to the main thread.
    pub fn get_selected_text() -> Option<String> {
        run_on_main_thread(|| get_selected_text_impl())
    }

    /// Get the current URL from browser (if focused) (internal implementation)
    ///
    /// # Thread Safety
    /// This function must be called from the main thread only.
    ///
    /// # Safety
    /// Uses unsafe FFI calls to Core Foundation and Accessibility APIs
    fn get_browser_url_impl() -> Option<String> {
        assert_main_thread();

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
                // Release if non-null but failed
                if !title_value.is_null() {
                    CFRelease(title_value);
                }
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

    /// Get the current URL from browser (if focused)
    ///
    /// # Thread Safety
    /// This function is thread-safe. It can be called from any thread.
    /// If not on the main thread, it will automatically dispatch to the main thread.
    pub fn get_browser_url() -> Option<String> {
        run_on_main_thread(|| get_browser_url_impl())
    }

    /// Check if the app has accessibility permission
    ///
    /// # Thread Safety
    /// This function is thread-safe and can be called from any thread.
    /// AXIsProcessTrusted() is documented as thread-safe by Apple.
    ///
    /// # Safety
    /// Uses unsafe FFI call to Accessibility API
    pub fn has_accessibility_permission() -> bool {
        unsafe { AXIsProcessTrusted() }
    }

    /// Request accessibility permission from the user
    /// Opens System Preferences to the appropriate pane
    ///
    /// # Thread Safety
    /// This function is thread-safe and can be called from any thread.
    pub fn request_accessibility_permission() -> bool {
        use std::process::Command;

        // Open System Preferences to Privacy & Security > Accessibility
        let result = Command::new("open")
            .arg("x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility")
            .spawn();

        result.is_ok()
    }

    /// Get all visible windows using CGWindowListCopyWindowInfo (internal implementation)
    ///
    /// # Thread Safety
    /// This function must be called from the main thread only.
    ///
    /// # Safety
    /// Uses unsafe FFI calls to Core Graphics and Core Foundation APIs
    fn get_all_windows_impl() -> Vec<(String, String)> {
        assert_main_thread();

        unsafe {
            let window_list =
                CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID);

            if window_list.is_null() {
                return Vec::new();
            }

            let mut windows = Vec::new();
            let count = core_foundation::array::CFArray::<core_foundation::dictionary::CFDictionary>::wrap_under_get_rule(window_list as _).len();

            for i in 0..count {
                let array = core_foundation::array::CFArray::<
                    core_foundation::dictionary::CFDictionary,
                >::wrap_under_get_rule(window_list as _);
                if let Some(dict) = array.get(i as isize) {
                    // Get owner name (app name)
                    let owner_key = CFString::new("kCGWindowOwnerName");
                    let app_name = dict
                        .find(owner_key.as_concrete_TypeRef() as *const c_void)
                        .map(|v| {
                            let cf_str = CFString::wrap_under_get_rule(*v as _);
                            cf_str.to_string()
                        })
                        .unwrap_or_default();

                    // Get window name (title)
                    let name_key = CFString::new("kCGWindowName");
                    let window_title = dict
                        .find(name_key.as_concrete_TypeRef() as *const c_void)
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

    /// Get all visible windows using CGWindowListCopyWindowInfo
    ///
    /// # Thread Safety
    /// This function is thread-safe. It can be called from any thread.
    /// If not on the main thread, it will automatically dispatch to the main thread.
    pub fn get_all_windows() -> Vec<(String, String)> {
        run_on_main_thread(|| get_all_windows_impl())
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
