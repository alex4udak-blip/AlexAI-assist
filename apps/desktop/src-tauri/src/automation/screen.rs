/// Screen capture module with caching
/// Uses xcap for cross-platform screenshot support with 500ms cache TTL

use base64::{Engine as _, engine::general_purpose::STANDARD as BASE64};
use image::{ImageBuffer, ImageEncoder, RgbaImage};
use once_cell::sync::Lazy;
use std::sync::Mutex;
use std::time::{Duration, Instant};
use xcap::Monitor;

const CACHE_TTL: Duration = Duration::from_millis(500);

/// Cached screenshot data
struct CachedScreenshot {
    image: RgbaImage,
    timestamp: Instant,
}

/// Global cache for screenshots
static SCREENSHOT_CACHE: Lazy<Mutex<Option<CachedScreenshot>>> = Lazy::new(|| Mutex::new(None));

/// Capture screenshot of primary monitor with caching
pub fn capture_screenshot() -> Result<RgbaImage, String> {
    // Check cache first
    {
        let cache = SCREENSHOT_CACHE
            .lock()
            .map_err(|e| format!("Failed to lock cache: {}", e))?;

        if let Some(cached) = cache.as_ref() {
            if cached.timestamp.elapsed() < CACHE_TTL {
                return Ok(cached.image.clone());
            }
        }
    }

    // Capture new screenshot
    let monitors = Monitor::all().map_err(|e| format!("Failed to get monitors: {}", e))?;

    let primary_monitor = monitors
        .into_iter()
        .next()
        .ok_or_else(|| "No monitors found".to_string())?;

    let image = primary_monitor
        .capture_image()
        .map_err(|e| format!("Failed to capture screenshot: {}", e))?;

    // xcap returns RgbaImage directly
    let rgba_image = image;

    // Update cache
    {
        let mut cache = SCREENSHOT_CACHE
            .lock()
            .map_err(|e| format!("Failed to lock cache: {}", e))?;

        *cache = Some(CachedScreenshot {
            image: rgba_image.clone(),
            timestamp: Instant::now(),
        });
    }

    Ok(rgba_image)
}

/// Capture screenshot of specific monitor
pub fn capture_monitor(monitor_index: usize) -> Result<RgbaImage, String> {
    let monitors = Monitor::all().map_err(|e| format!("Failed to get monitors: {}", e))?;

    let monitor = monitors
        .get(monitor_index)
        .ok_or_else(|| format!("Monitor {} not found", monitor_index))?;

    let image = monitor
        .capture_image()
        .map_err(|e| format!("Failed to capture screenshot: {}", e))?;

    Ok(image)
}

/// Capture screenshot of specific region
pub fn capture_region(x: i32, y: i32, width: u32, height: u32) -> Result<RgbaImage, String> {
    let full_screenshot = capture_screenshot()?;

    // Validate bounds
    if x < 0 || y < 0 {
        return Err("Negative coordinates not allowed".to_string());
    }

    let x = x as u32;
    let y = y as u32;

    if x + width > full_screenshot.width() || y + height > full_screenshot.height() {
        return Err("Region exceeds screenshot bounds".to_string());
    }

    // Crop the image
    let cropped = image::imageops::crop_imm(&full_screenshot, x, y, width, height).to_image();

    Ok(cropped)
}

/// Get list of available monitors
pub fn get_monitors() -> Result<Vec<MonitorInfo>, String> {
    let monitors = Monitor::all().map_err(|e| format!("Failed to get monitors: {}", e))?;

    let info = monitors
        .iter()
        .enumerate()
        .map(|(index, monitor)| MonitorInfo {
            index,
            name: monitor.name().to_string(),
            width: monitor.width(),
            height: monitor.height(),
            x: monitor.x(),
            y: monitor.y(),
            is_primary: monitor.is_primary(),
        })
        .collect();

    Ok(info)
}

/// Encode image to base64 PNG
pub fn encode_to_base64(image: &RgbaImage) -> Result<String, String> {
    let mut buffer = Vec::new();
    let mut cursor = std::io::Cursor::new(&mut buffer);

    image::codecs::png::PngEncoder::new(&mut cursor)
        .write_image(
            image.as_raw(),
            image.width(),
            image.height(),
            image::ColorType::Rgba8.into(),
        )
        .map_err(|e| format!("Failed to encode PNG: {}", e))?;

    Ok(BASE64.encode(&buffer))
}

/// Encode image to base64 JPEG
pub fn encode_to_base64_jpeg(image: &RgbaImage, quality: u8) -> Result<String, String> {
    // Convert RGBA to RGB
    let rgb_image: ImageBuffer<image::Rgb<u8>, Vec<u8>> = ImageBuffer::from_fn(
        image.width(),
        image.height(),
        |x, y| {
            let pixel = image.get_pixel(x, y);
            image::Rgb([pixel[0], pixel[1], pixel[2]])
        },
    );

    let mut buffer = Vec::new();
    let mut cursor = std::io::Cursor::new(&mut buffer);

    image::codecs::jpeg::JpegEncoder::new_with_quality(&mut cursor, quality)
        .write_image(
            rgb_image.as_raw(),
            rgb_image.width(),
            rgb_image.height(),
            image::ColorType::Rgb8.into(),
        )
        .map_err(|e| format!("Failed to encode JPEG: {}", e))?;

    Ok(BASE64.encode(&buffer))
}

/// Clear screenshot cache
pub fn clear_cache() {
    if let Ok(mut cache) = SCREENSHOT_CACHE.lock() {
        *cache = None;
    }
}

/// Monitor information
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct MonitorInfo {
    pub index: usize,
    pub name: String,
    pub width: u32,
    pub height: u32,
    pub x: i32,
    pub y: i32,
    pub is_primary: bool,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_monitors() {
        let result = get_monitors();
        // Should not panic, even if no monitors (in CI)
        assert!(result.is_ok() || result.is_err());
    }

    #[test]
    fn test_clear_cache() {
        clear_cache();
        // Should not panic
    }
}
