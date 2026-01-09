/// Permission management module for macOS system permissions
/// Handles accessibility and screen recording permissions

use serde::{Serialize, Deserialize};

#[cfg(target_os = "macos")]
use crate::automation::accessibility_ffi;

/// Permission types
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum PermissionType {
    Accessibility,
    ScreenRecording,
}

/// Permission status
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PermissionStatus {
    pub permission_type: PermissionType,
    pub granted: bool,
    pub can_request: bool,
}

/// All permissions status
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AllPermissions {
    pub accessibility: bool,
    pub screen_recording: bool,
    pub all_granted: bool,
}

/// Check specific permission
pub fn check_permission(permission: PermissionType) -> PermissionStatus {
    #[cfg(target_os = "macos")]
    {
        let granted = match permission {
            PermissionType::Accessibility => accessibility_ffi::check_accessibility(),
            PermissionType::ScreenRecording => accessibility_ffi::check_screen_recording(),
        };

        PermissionStatus {
            permission_type: permission,
            granted,
            can_request: true,
        }
    }

    #[cfg(not(target_os = "macos"))]
    {
        PermissionStatus {
            permission_type: permission,
            granted: false,
            can_request: false,
        }
    }
}

/// Check all required permissions
pub fn check_all_permissions() -> AllPermissions {
    #[cfg(target_os = "macos")]
    {
        let (accessibility, screen_recording) = accessibility_ffi::check_all_permissions();

        AllPermissions {
            accessibility,
            screen_recording,
            all_granted: accessibility && screen_recording,
        }
    }

    #[cfg(not(target_os = "macos"))]
    {
        AllPermissions {
            accessibility: false,
            screen_recording: false,
            all_granted: false,
        }
    }
}

/// Request specific permission
pub fn request_permission(permission: PermissionType) -> Result<bool, String> {
    #[cfg(target_os = "macos")]
    {
        let granted = match permission {
            PermissionType::Accessibility => accessibility_ffi::request_accessibility(),
            PermissionType::ScreenRecording => accessibility_ffi::request_screen_recording(),
        };

        Ok(granted)
    }

    #[cfg(not(target_os = "macos"))]
    {
        Err("Permissions only supported on macOS".to_string())
    }
}

/// Open system settings for specific permission
pub fn open_permission_settings(permission: PermissionType) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        let url = match permission {
            PermissionType::Accessibility => {
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
            }
            PermissionType::ScreenRecording => {
                "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
            }
        };

        std::process::Command::new("open")
            .arg(url)
            .spawn()
            .map_err(|e| format!("Failed to open settings: {}", e))?;

        Ok(())
    }

    #[cfg(not(target_os = "macos"))]
    {
        Err("Settings only supported on macOS".to_string())
    }
}

/// Get permission description for user
pub fn get_permission_description(permission: PermissionType) -> &'static str {
    match permission {
        PermissionType::Accessibility => {
            "Accessibility permission allows Observer to monitor your computer activity \
            and control keyboard/mouse for automation."
        }
        PermissionType::ScreenRecording => {
            "Screen Recording permission allows Observer to capture screenshots \
            for visual automation and OCR."
        }
    }
}

/// Check if permission is required for specific feature
pub fn is_permission_required_for_feature(
    permission: PermissionType,
    feature: &str,
) -> bool {
    match (permission, feature) {
        (PermissionType::Accessibility, "input") => true,
        (PermissionType::Accessibility, "focus_tracking") => true,
        (PermissionType::Accessibility, "browser_control") => true,
        (PermissionType::ScreenRecording, "screenshot") => true,
        (PermissionType::ScreenRecording, "ocr") => true,
        _ => false,
    }
}

/// Permission manager
pub struct PermissionManager {
    last_check: std::sync::RwLock<std::time::Instant>,
    cache_duration: std::time::Duration,
    cached_permissions: std::sync::RwLock<Option<AllPermissions>>,
}

impl PermissionManager {
    /// Create new permission manager
    pub fn new() -> Self {
        Self {
            last_check: std::sync::RwLock::new(std::time::Instant::now()),
            cache_duration: std::time::Duration::from_secs(5),
            cached_permissions: std::sync::RwLock::new(None),
        }
    }

    /// Check all permissions with caching
    pub fn check_all(&self) -> AllPermissions {
        let now = std::time::Instant::now();
        let last_check = *self.last_check.read().unwrap();

        // Return cached if still valid
        if now.duration_since(last_check) < self.cache_duration {
            if let Some(cached) = self.cached_permissions.read().unwrap().as_ref() {
                return cached.clone();
            }
        }

        // Check permissions
        let permissions = check_all_permissions();

        // Update cache
        {
            let mut last = self.last_check.write().unwrap();
            *last = now;
        }
        {
            let mut cached = self.cached_permissions.write().unwrap();
            *cached = Some(permissions.clone());
        }

        permissions
    }

    /// Invalidate cache
    pub fn invalidate_cache(&self) {
        let mut cached = self.cached_permissions.write().unwrap();
        *cached = None;
    }
}

impl Default for PermissionManager {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_permission_description() {
        let desc = get_permission_description(PermissionType::Accessibility);
        assert!(!desc.is_empty());
    }

    #[test]
    fn test_is_permission_required() {
        assert!(is_permission_required_for_feature(
            PermissionType::Accessibility,
            "input"
        ));
        assert!(is_permission_required_for_feature(
            PermissionType::ScreenRecording,
            "screenshot"
        ));
        assert!(!is_permission_required_for_feature(
            PermissionType::ScreenRecording,
            "input"
        ));
    }

    #[test]
    fn test_permission_manager() {
        let manager = PermissionManager::new();
        let _ = manager.check_all();
        manager.invalidate_cache();
    }
}
