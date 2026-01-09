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

#[cfg(target_os = "windows")]
pub fn get_active_window() -> (Option<String>, Option<String>) {
    use windows::Win32::Foundation::HWND;
    use windows::Win32::System::ProcessStatus::GetModuleBaseNameW;
    use windows::Win32::System::Threading::{OpenProcess, PROCESS_QUERY_INFORMATION, PROCESS_VM_READ};
    use windows::Win32::UI::WindowsAndMessaging::{GetForegroundWindow, GetWindowTextW, GetWindowThreadProcessId};

    unsafe {
        // Get the foreground window
        let hwnd: HWND = GetForegroundWindow();
        if hwnd.0 == 0 {
            return (None, None);
        }

        // Get window title
        let mut title_buf = [0u16; 512];
        let title_len = GetWindowTextW(hwnd, &mut title_buf);
        let window_title = if title_len > 0 {
            String::from_utf16_lossy(&title_buf[..title_len as usize])
        } else {
            String::new()
        };

        // Get process ID and name
        let mut process_id: u32 = 0;
        GetWindowThreadProcessId(hwnd, Some(&mut process_id));

        let app_name = if process_id != 0 {
            let process_handle = OpenProcess(
                PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                false,
                process_id,
            );

            if let Ok(handle) = process_handle {
                let mut name_buf = [0u16; 512];
                let name_len = GetModuleBaseNameW(handle, None, &mut name_buf);
                if name_len > 0 {
                    let full_name = String::from_utf16_lossy(&name_buf[..name_len as usize]);
                    // Remove .exe extension if present
                    Some(full_name.trim_end_matches(".exe").to_string())
                } else {
                    None
                }
            } else {
                None
            }
        } else {
            None
        };

        let title = if !window_title.is_empty() {
            Some(window_title)
        } else {
            None
        };

        (app_name, title)
    }
}

#[cfg(target_os = "linux")]
pub fn get_active_window() -> (Option<String>, Option<String>) {
    use std::ffi::CString;
    use std::ptr;
    use x11::xlib::*;

    unsafe {
        // Open X11 display
        let display = XOpenDisplay(ptr::null());
        if display.is_null() {
            // Fallback to command-line tools if X11 is not available
            return get_active_window_fallback();
        }

        // Get the root window
        let root = XDefaultRootWindow(display);

        // Get _NET_ACTIVE_WINDOW property
        let net_active_window = XInternAtom(
            display,
            CString::new("_NET_ACTIVE_WINDOW").unwrap().as_ptr(),
            0,
        );

        let mut actual_type: Atom = 0;
        let mut actual_format: i32 = 0;
        let mut nitems: u64 = 0;
        let mut bytes_after: u64 = 0;
        let mut prop: *mut u8 = ptr::null_mut();

        let status = XGetWindowProperty(
            display,
            root,
            net_active_window,
            0,
            1,
            0,
            XA_WINDOW,
            &mut actual_type,
            &mut actual_format,
            &mut nitems,
            &mut bytes_after,
            &mut prop,
        );

        if status != 0 || prop.is_null() {
            XCloseDisplay(display);
            return (None, None);
        }

        let active_window = *(prop as *const Window);
        XFree(prop as *mut _);

        // Get window title (_NET_WM_NAME or WM_NAME)
        let net_wm_name = XInternAtom(
            display,
            CString::new("_NET_WM_NAME").unwrap().as_ptr(),
            0,
        );
        let utf8_string = XInternAtom(
            display,
            CString::new("UTF8_STRING").unwrap().as_ptr(),
            0,
        );

        let mut title_prop: *mut u8 = ptr::null_mut();
        let status = XGetWindowProperty(
            display,
            active_window,
            net_wm_name,
            0,
            1024,
            0,
            utf8_string,
            &mut actual_type,
            &mut actual_format,
            &mut nitems,
            &mut bytes_after,
            &mut title_prop,
        );

        let window_title = if status == 0 && !title_prop.is_null() {
            let title_slice = std::slice::from_raw_parts(title_prop, nitems as usize);
            let title = String::from_utf8_lossy(title_slice).to_string();
            XFree(title_prop as *mut _);
            if !title.is_empty() {
                Some(title)
            } else {
                None
            }
        } else {
            None
        };

        // Get window class (WM_CLASS for app name)
        let mut class_prop: *mut u8 = ptr::null_mut();
        let status = XGetWindowProperty(
            display,
            active_window,
            XA_WM_CLASS,
            0,
            1024,
            0,
            XA_STRING,
            &mut actual_type,
            &mut actual_format,
            &mut nitems,
            &mut bytes_after,
            &mut class_prop,
        );

        let app_name = if status == 0 && !class_prop.is_null() {
            let class_slice = std::slice::from_raw_parts(class_prop, nitems as usize);
            // WM_CLASS contains two null-terminated strings: instance and class
            // We want the class name (second string)
            let class_str = String::from_utf8_lossy(class_slice);
            let parts: Vec<&str> = class_str.split('\0').collect();
            let app = if parts.len() > 1 && !parts[1].is_empty() {
                Some(parts[1].to_string())
            } else if !parts[0].is_empty() {
                Some(parts[0].to_string())
            } else {
                None
            };
            XFree(class_prop as *mut _);
            app
        } else {
            None
        };

        XCloseDisplay(display);
        (app_name, window_title)
    }
}

#[cfg(target_os = "linux")]
fn get_active_window_fallback() -> (Option<String>, Option<String>) {
    use std::process::Command;

    // Try xdotool first
    if let Ok(output) = Command::new("xdotool")
        .args(["getactivewindow", "getwindowname"])
        .output()
    {
        if output.status.success() {
            let title = String::from_utf8_lossy(&output.stdout)
                .trim()
                .to_string();

            // Get window class for app name
            if let Ok(class_output) = Command::new("xdotool")
                .args(["getactivewindow", "getwindowclassname"])
                .output()
            {
                if class_output.status.success() {
                    let app_name = String::from_utf8_lossy(&class_output.stdout)
                        .trim()
                        .to_string();
                    return (
                        if !app_name.is_empty() { Some(app_name) } else { None },
                        if !title.is_empty() { Some(title) } else { None },
                    );
                }
            }

            return (None, if !title.is_empty() { Some(title) } else { None });
        }
    }

    // Try wmctrl as fallback
    if let Ok(output) = Command::new("wmctrl")
        .args(["-l", "-p"])
        .output()
    {
        if output.status.success() {
            let stdout = String::from_utf8_lossy(&output.stdout);
            // wmctrl output format: window_id desktop pid machine title
            // We need to find the active window - this is a simplified approach
            if let Some(line) = stdout.lines().next() {
                let parts: Vec<&str> = line.split_whitespace().collect();
                if parts.len() >= 5 {
                    let title = parts[4..].join(" ");
                    return (None, Some(title));
                }
            }
        }
    }

    (None, None)
}

#[cfg(all(not(target_os = "macos"), not(target_os = "windows"), not(target_os = "linux")))]
pub fn get_active_window() -> (Option<String>, Option<String>) {
    // Unsupported platform
    (None, None)
}

#[allow(dead_code)]
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
