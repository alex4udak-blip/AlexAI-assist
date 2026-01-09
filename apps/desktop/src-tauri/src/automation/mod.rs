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

// Re-export commonly used types (allow unused for API stability)
#[allow(unused_imports)]
pub use queue::{AutomationQueue, TaskPriority, QueueStatus};
#[allow(unused_imports)]
pub use trust::TrustLevel;
#[allow(unused_imports)]
pub use input::{click_at, type_text, press_hotkey};
#[allow(unused_imports)]
pub use screen::capture_screenshot;
#[allow(unused_imports)]
pub use browser::{get_browser_url, navigate_to_url, Browser};
#[allow(unused_imports)]
pub use ocr::extract_text_from_image;

#[cfg(target_os = "macos")]
#[allow(unused_imports)]
pub use accessibility_ffi::{
    check_accessibility,
    request_accessibility,
    check_screen_recording,
    request_screen_recording,
};
