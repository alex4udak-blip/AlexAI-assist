use chrono::{DateTime, Duration, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use uuid::Uuid;

#[cfg(target_os = "macos")]
use core_graphics::display::CGMainDisplayID;
#[cfg(target_os = "macos")]
use image::{DynamicImage, ImageBuffer, Rgb};

/// Configuration for screenshot capture behavior
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScreenshotConfig {
    /// Minimum seconds between screenshot captures
    pub min_interval_seconds: u64,
    /// JPEG quality (0-100)
    pub jpeg_quality: u8,
    /// Scale factor for compression (0.0-1.0)
    pub scale_factor: f32,
    /// Number of days to keep screenshots before auto-deletion
    pub retention_days: i64,
    /// Base directory for screenshot storage
    pub storage_path: PathBuf,
    /// Perceptual hash similarity threshold (0-100, higher = more similar)
    pub similarity_threshold: u8,
}

impl Default for ScreenshotConfig {
    fn default() -> Self {
        let home = dirs::home_dir().expect("Unable to determine home directory");
        Self {
            min_interval_seconds: 5,
            jpeg_quality: 60,
            scale_factor: 0.5,
            retention_days: 7,
            storage_path: home
                .join("Library")
                .join("Application Support")
                .join("observer")
                .join("screenshots"),
            similarity_threshold: 90,
        }
    }
}

/// Represents a captured screenshot with metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Screenshot {
    pub id: String,
    pub timestamp: DateTime<Utc>,
    pub app_name: String,
    pub window_title: String,
    pub path: PathBuf,
    pub size_bytes: u64,
    #[serde(skip)]
    pub hash: Option<u64>,
}

/// Statistics about screenshot collection
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScreenshotStats {
    pub total_screenshots: usize,
    pub total_size_bytes: u64,
    pub oldest_screenshot: Option<DateTime<Utc>>,
    pub newest_screenshot: Option<DateTime<Utc>>,
    pub screenshots_by_date: HashMap<String, usize>,
}

/// Manager for capturing and managing screenshots
pub struct ScreenshotManager {
    config: ScreenshotConfig,
    last_capture_time: Option<DateTime<Utc>>,
    last_hash: Option<u64>,
}

impl ScreenshotManager {
    /// Create a new ScreenshotManager with the given configuration
    pub fn new(config: ScreenshotConfig) -> Self {
        // Ensure storage directory exists
        if let Err(e) = fs::create_dir_all(&config.storage_path) {
            eprintln!("Failed to create screenshot directory: {}", e);
        }

        Self {
            config,
            last_capture_time: None,
            last_hash: None,
        }
    }

    /// Attempt to capture a screenshot, only if conditions are met
    /// Returns Some(Screenshot) if capture was successful, None otherwise
    pub async fn maybe_capture(
        &mut self,
        app_name: String,
        window_title: String,
    ) -> Option<Screenshot> {
        // Check minimum interval
        if let Some(last_time) = self.last_capture_time {
            let elapsed = Utc::now().signed_duration_since(last_time);
            if elapsed.num_seconds() < self.config.min_interval_seconds as i64 {
                return None;
            }
        }

        // Capture screen
        #[cfg(target_os = "macos")]
        let image = self.capture_screen()?;

        #[cfg(not(target_os = "macos"))]
        {
            eprintln!("Screenshot capture is only supported on macOS");
            return None;
        }

        #[cfg(target_os = "macos")]
        {
            // Compute perceptual hash
            let hash = self.compute_image_hash(&image);

            // Check if content has changed
            if let Some(last_hash) = self.last_hash {
                let similarity = self.hash_similarity(last_hash, hash);
                if similarity >= self.config.similarity_threshold {
                    // Content hasn't changed significantly
                    return None;
                }
            }

            // Save screenshot
            let screenshot = self.save_screenshot(image, app_name, window_title, hash)?;

            // Update tracking
            self.last_capture_time = Some(screenshot.timestamp);
            self.last_hash = Some(hash);

            Some(screenshot)
        }
    }

    /// Capture the screen using macOS Core Graphics
    #[cfg(target_os = "macos")]
    fn capture_screen(&self) -> Option<DynamicImage> {
        use core_graphics::display::CGDisplay;

        unsafe {
            // Get main display
            let display_id = CGMainDisplayID();
            let display = CGDisplay::new(display_id);

            // Capture display image
            let cg_image = display.image()?;

            // Convert CGImage to DynamicImage
            self.cgimage_to_dynamic_image(&cg_image)
        }
    }

    /// Convert CGImage to DynamicImage using CGBitmapContext
    #[cfg(target_os = "macos")]
    fn cgimage_to_dynamic_image(
        &self,
        cg_image: &core_graphics::image::CGImage,
    ) -> Option<DynamicImage> {
        use core_graphics::context::CGContext;
        use core_graphics::color_space::CGColorSpace;

        let width = cg_image.width();
        let height = cg_image.height();

        // Create a buffer to hold the pixel data (RGBA format)
        let bytes_per_row = width * 4;
        let mut buffer: Vec<u8> = vec![0; height * bytes_per_row];

        // Create a bitmap context to render the image
        let color_space = CGColorSpace::create_device_rgb();
        let context = CGContext::create_bitmap_context(
            Some(buffer.as_mut_ptr() as *mut _),
            width,
            height,
            8,                  // bits per component
            bytes_per_row,
            &color_space,
            core_graphics::base::kCGImageAlphaPremultipliedLast, // RGBA
        );

        // Draw the CGImage into the context
        let rect = core_graphics::geometry::CGRect::new(
            &core_graphics::geometry::CGPoint::new(0.0, 0.0),
            &core_graphics::geometry::CGSize::new(width as f64, height as f64),
        );
        context.draw_image(rect, cg_image);

        // Create image buffer from RGBA data
        let mut img_buffer = ImageBuffer::<Rgb<u8>, Vec<u8>>::new(width as u32, height as u32);

        for y in 0..height {
            for x in 0..width {
                let offset = y * bytes_per_row + x * 4;
                if offset + 3 <= buffer.len() {
                    // RGBA format
                    let r = buffer[offset];
                    let g = buffer[offset + 1];
                    let b = buffer[offset + 2];
                    img_buffer.put_pixel(x as u32, y as u32, Rgb([r, g, b]));
                }
            }
        }

        // Scale down if needed
        let scaled_image = if self.config.scale_factor < 1.0 {
            let new_width = ((width as f32) * self.config.scale_factor) as u32;
            let new_height = ((height as f32) * self.config.scale_factor) as u32;
            DynamicImage::ImageRgb8(img_buffer).resize(
                new_width,
                new_height,
                image::imageops::FilterType::Lanczos3,
            )
        } else {
            DynamicImage::ImageRgb8(img_buffer)
        };

        Some(scaled_image)
    }

    /// Compute a perceptual hash of the image for similarity comparison
    fn compute_image_hash(&self, image: &DynamicImage) -> u64 {
        use image::imageops::FilterType;

        // Resize to 8x8 for hash computation
        let small = image.resize_exact(8, 8, FilterType::Lanczos3);
        let gray = small.to_luma8();

        // Calculate average pixel value
        let mut sum: u32 = 0;
        for pixel in gray.pixels() {
            sum += pixel[0] as u32;
        }
        let avg = sum / 64;

        // Build hash
        let mut hash: u64 = 0;
        for (i, pixel) in gray.pixels().enumerate() {
            if pixel[0] as u32 > avg {
                hash |= 1 << i;
            }
        }

        hash
    }

    /// Calculate similarity between two hashes (0-100, higher = more similar)
    fn hash_similarity(&self, hash1: u64, hash2: u64) -> u8 {
        let diff = (hash1 ^ hash2).count_ones();
        let max_diff = 64;
        let similarity = ((max_diff - diff) as f32 / max_diff as f32 * 100.0) as u8;
        similarity
    }

    /// Save screenshot to disk as JPEG
    #[cfg(target_os = "macos")]
    fn save_screenshot(
        &self,
        image: DynamicImage,
        app_name: String,
        window_title: String,
        hash: u64,
    ) -> Option<Screenshot> {

        // Create date-based subdirectory
        let now = Utc::now();
        let date_str = now.format("%Y-%m-%d").to_string();
        let date_dir = self.config.storage_path.join(&date_str);

        if let Err(e) = fs::create_dir_all(&date_dir) {
            eprintln!("Failed to create date directory: {}", e);
            return None;
        }

        // Generate filename
        let id = Uuid::new_v4().to_string();
        let filename = format!("{}_{}.jpg", now.format("%H%M%S"), &id[..8]);
        let filepath = date_dir.join(&filename);

        // Save as JPEG
        let mut buffer = Vec::new();
        {
            let mut encoder = image::codecs::jpeg::JpegEncoder::new_with_quality(
                &mut buffer,
                self.config.jpeg_quality,
            );
            if let Err(e) = encoder.encode_image(&image) {
                eprintln!("Failed to encode JPEG: {}", e);
                return None;
            }
        }

        if let Err(e) = fs::write(&filepath, &buffer) {
            eprintln!("Failed to write screenshot file: {}", e);
            return None;
        }

        let size_bytes = buffer.len() as u64;

        Some(Screenshot {
            id,
            timestamp: now,
            app_name,
            window_title,
            path: filepath,
            size_bytes,
            hash: Some(hash),
        })
    }

    /// Delete screenshots older than the retention period
    pub async fn cleanup_old_screenshots(&self) -> Result<usize, std::io::Error> {
        let cutoff_date = Utc::now() - Duration::days(self.config.retention_days);
        let mut deleted_count = 0;

        // Iterate through date directories
        let entries = fs::read_dir(&self.config.storage_path)?;

        for entry in entries {
            let entry = entry?;
            let path = entry.path();

            if path.is_dir() {
                // Check if directory name is a date
                if let Some(dirname) = path.file_name().and_then(|n| n.to_str()) {
                    // Try to parse as date
                    if let Ok(dir_date) = chrono::NaiveDate::parse_from_str(dirname, "%Y-%m-%d") {
                        // Safely convert to datetime, skip if fails
                        let Some(naive_dt) = dir_date.and_hms_opt(0, 0, 0) else {
                            continue;
                        };
                        let chrono::LocalResult::Single(dir_datetime) = naive_dt.and_local_timezone(Utc) else {
                            continue;
                        };

                        if dir_datetime < cutoff_date {
                            // Delete entire directory
                            match fs::remove_dir_all(&path) {
                                Ok(_) => {
                                    deleted_count += 1;
                                }
                                Err(e) => {
                                    eprintln!("Failed to delete directory {:?}: {}", path, e);
                                }
                            }
                        }
                    }
                }
            }
        }

        Ok(deleted_count)
    }

    /// Get statistics about stored screenshots
    pub fn get_stats(&self) -> ScreenshotStats {
        let mut stats = ScreenshotStats {
            total_screenshots: 0,
            total_size_bytes: 0,
            oldest_screenshot: None,
            newest_screenshot: None,
            screenshots_by_date: HashMap::new(),
        };

        // Iterate through all screenshot files
        if let Ok(entries) = fs::read_dir(&self.config.storage_path) {
            for entry in entries.flatten() {
                let path = entry.path();

                if path.is_dir() {
                    if let Some(dirname) = path.file_name().and_then(|n| n.to_str()) {
                        if let Ok(_) = chrono::NaiveDate::parse_from_str(dirname, "%Y-%m-%d") {
                            // Count files in this date directory
                            let mut count = 0;
                            if let Ok(files) = fs::read_dir(&path) {
                                for file in files.flatten() {
                                    if file.path().extension().and_then(|s| s.to_str()) == Some("jpg") {
                                        count += 1;
                                        stats.total_screenshots += 1;

                                        // Get file size
                                        if let Ok(metadata) = file.metadata() {
                                            stats.total_size_bytes += metadata.len();
                                        }

                                        // Parse timestamp from filename
                                        if let Some(filename) = file.file_name().to_str() {
                                            if let Some(date_time_str) = self.parse_filename_timestamp(dirname, filename) {
                                                if let Ok(dt) = DateTime::parse_from_rfc3339(&date_time_str) {
                                                    let utc_dt = dt.with_timezone(&Utc);

                                                    if stats.oldest_screenshot.is_none() || Some(utc_dt) < stats.oldest_screenshot {
                                                        stats.oldest_screenshot = Some(utc_dt);
                                                    }
                                                    if stats.newest_screenshot.is_none() || Some(utc_dt) > stats.newest_screenshot {
                                                        stats.newest_screenshot = Some(utc_dt);
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                            stats.screenshots_by_date.insert(dirname.to_string(), count);
                        }
                    }
                }
            }
        }

        stats
    }

    /// Helper to parse timestamp from filename
    fn parse_filename_timestamp(&self, date: &str, filename: &str) -> Option<String> {
        // Filename format: HHMMSS_uuid.jpg
        let parts: Vec<&str> = filename.split('_').collect();
        if parts.len() >= 1 {
            let time_str = parts[0];
            if time_str.len() == 6 {
                let hour = &time_str[0..2];
                let minute = &time_str[2..4];
                let second = &time_str[4..6];
                return Some(format!("{}T{}:{}:{}Z", date, hour, minute, second));
            }
        }
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hash_similarity() {
        let config = ScreenshotConfig::default();
        let manager = ScreenshotManager::new(config);

        // Identical hashes should be 100% similar
        let hash1: u64 = 0b1010101010101010;
        assert_eq!(manager.hash_similarity(hash1, hash1), 100);

        // Completely different hashes
        let hash2: u64 = !hash1;
        assert_eq!(manager.hash_similarity(hash1, hash2), 0);

        // One bit different
        let hash3: u64 = hash1 ^ 0b1;
        let similarity = manager.hash_similarity(hash1, hash3);
        assert!(similarity > 95);
    }

    #[test]
    fn test_config_default() {
        let config = ScreenshotConfig::default();
        assert_eq!(config.min_interval_seconds, 5);
        assert_eq!(config.jpeg_quality, 60);
        assert_eq!(config.scale_factor, 0.5);
        assert_eq!(config.retention_days, 7);
        assert_eq!(config.similarity_threshold, 90);
    }

    #[test]
    fn test_parse_filename_timestamp() {
        let config = ScreenshotConfig::default();
        let manager = ScreenshotManager::new(config);

        let result = manager.parse_filename_timestamp("2026-01-08", "143025_abc123def.jpg");
        assert_eq!(result, Some("2026-01-08T14:30:25Z".to_string()));
    }
}
