/// FFI bindings for macOS accessibility and screen recording APIs
/// Uses ApplicationServices and CoreGraphics frameworks

use core_foundation::base::{CFTypeRef, TCFType};
use core_foundation::boolean::CFBoolean;
use core_foundation::dictionary::CFDictionary;
use core_foundation::string::CFString;

// External C functions from ApplicationServices framework
#[link(name = "ApplicationServices", kind = "framework")]
extern "C" {
    /// Check if the process is trusted for accessibility
    fn AXIsProcessTrusted() -> bool;

    /// Check if the process is trusted with options (can show prompt)
    fn AXIsProcessTrustedWithOptions(options: CFTypeRef) -> bool;
}

// External C functions from CoreGraphics framework
#[link(name = "CoreGraphics", kind = "framework")]
extern "C" {
    /// Check if screen capture access is available
    fn CGPreflightScreenCaptureAccess() -> bool;

    /// Request screen capture access (shows system dialog)
    fn CGRequestScreenCaptureAccess() -> bool;
}

/// Check if the app has accessibility permissions without prompting
pub fn check_accessibility() -> bool {
    unsafe { AXIsProcessTrusted() }
}

/// Request accessibility permissions (shows system dialog if not trusted)
pub fn request_accessibility() -> bool {
    unsafe {
        // Create options dictionary with prompt key
        let prompt_key = CFString::from_static_string("AXTrustedCheckOptionPrompt");
        let prompt_value = CFBoolean::true_value();

        // Create pairs array for new CFDictionary API
        let pairs = [(prompt_key, prompt_value)];
        let options = CFDictionary::from_CFType_pairs(&pairs);

        AXIsProcessTrustedWithOptions(options.as_CFTypeRef())
    }
}

/// Check if the app has screen recording permissions without prompting
pub fn check_screen_recording() -> bool {
    unsafe { CGPreflightScreenCaptureAccess() }
}

/// Request screen recording permissions (shows system dialog)
pub fn request_screen_recording() -> bool {
    unsafe { CGRequestScreenCaptureAccess() }
}

/// Check all required permissions for automation
pub fn check_all_permissions() -> (bool, bool) {
    (check_accessibility(), check_screen_recording())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_check_accessibility() {
        // Should not panic
        let _ = check_accessibility();
    }

    #[test]
    fn test_check_screen_recording() {
        // Should not panic
        let _ = check_screen_recording();
    }
}
