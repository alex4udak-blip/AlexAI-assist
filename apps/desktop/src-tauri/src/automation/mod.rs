/// Main automation module for Observer desktop app
/// Provides macOS automation capabilities including input control, screen capture,
/// browser automation, and task queue management

#[cfg(target_os = "macos")]
pub mod accessibility_ffi;

pub mod input;
pub mod screen;
pub mod browser;
pub mod queue;
pub mod trust;
pub mod ocr;
pub mod sync;

// Re-export commonly used types
pub use queue::{AutomationQueue, TaskPriority, QueueStatus};
pub use trust::TrustLevel;
pub use input::{click_at, type_text, press_hotkey};
pub use screen::capture_screenshot;
pub use browser::{get_browser_url, navigate_to_url, Browser};
pub use ocr::extract_text_from_image;

#[cfg(target_os = "macos")]
pub use accessibility_ffi::{
    check_accessibility,
    request_accessibility,
    check_screen_recording,
    request_screen_recording,
};
