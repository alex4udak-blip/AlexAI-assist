//! Context Builder
//!
//! Collects and structures rich context from various sources:
//! - Current app and window information
//! - OCR text from screen
//! - Recent agent actions
//! - User project detection
//! - Time context

use chrono::{DateTime, Local, Timelike, Utc};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// Maximum OCR text length to include in context
const MAX_OCR_LENGTH: usize = 10000;

/// Rich context for Meta Agent decision making
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RichContext {
    /// Current active application name
    pub current_app: String,
    /// Window title
    pub window_title: String,
    /// URL if in browser (extracted from title or accessibility)
    pub url: Option<String>,
    /// OCR text from screen (truncated to MAX_OCR_LENGTH)
    pub ocr_text: String,
    /// Recent agent actions (last 5 minutes)
    pub recent_actions: Vec<RecentAction>,
    /// Detected project context
    pub project: Option<ProjectContext>,
    /// Time context
    pub time_context: TimeContext,
    /// Timestamp when context was collected
    pub collected_at: DateTime<Utc>,
}

/// Recent action performed by an agent
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecentAction {
    /// Agent that performed the action
    pub agent: String,
    /// Brief description of the action
    pub action: String,
    /// When it happened
    pub timestamp: DateTime<Utc>,
    /// Whether user accepted/rejected (if applicable)
    pub user_response: Option<UserResponse>,
}

/// User response to an agent action
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum UserResponse {
    Accepted,
    Rejected,
    Ignored,
}

/// Project context detected from file paths and git
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectContext {
    /// Project name (usually directory name)
    pub name: String,
    /// Full path to project root
    pub path: String,
    /// Git repository URL if available
    pub git_remote: Option<String>,
    /// Primary language/framework detected
    pub tech_stack: Option<String>,
}

/// Time context for smarter decisions
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimeContext {
    /// Current hour (0-23)
    pub hour: u32,
    /// Day of week (0=Sunday, 6=Saturday)
    pub day_of_week: u32,
    /// Is it work hours (9-18 on weekdays)?
    pub is_work_hours: bool,
    /// Is it late night (23-6)?
    pub is_late_night: bool,
}

impl RichContext {
    /// Create a new context builder
    pub fn builder() -> RichContextBuilder {
        RichContextBuilder::new()
    }

    /// Create context from raw inputs
    pub fn from_raw(app_name: &str, window_title: &str, ocr_text: &str) -> Self {
        Self::builder()
            .app(app_name)
            .window_title(window_title)
            .ocr_text(ocr_text)
            .build()
    }

    /// Get a truncated version of OCR text for logging
    pub fn ocr_preview(&self, max_len: usize) -> &str {
        if self.ocr_text.len() <= max_len {
            &self.ocr_text
        } else {
            &self.ocr_text[..max_len]
        }
    }
}

/// Builder for RichContext
pub struct RichContextBuilder {
    current_app: String,
    window_title: String,
    url: Option<String>,
    ocr_text: String,
    recent_actions: Vec<RecentAction>,
    project: Option<ProjectContext>,
}

impl RichContextBuilder {
    /// Create a new builder
    pub fn new() -> Self {
        Self {
            current_app: String::new(),
            window_title: String::new(),
            url: None,
            ocr_text: String::new(),
            recent_actions: Vec::new(),
            project: None,
        }
    }

    /// Set the current application name
    pub fn app(mut self, app_name: &str) -> Self {
        self.current_app = app_name.to_string();
        self
    }

    /// Set the window title
    pub fn window_title(mut self, title: &str) -> Self {
        self.window_title = title.to_string();
        // Try to extract URL from title (browsers often show it)
        self.url = Self::extract_url_from_title(title);
        self
    }

    /// Set the OCR text
    pub fn ocr_text(mut self, text: &str) -> Self {
        // Truncate if too long
        if text.len() > MAX_OCR_LENGTH {
            self.ocr_text = text.chars().take(MAX_OCR_LENGTH).collect();
        } else {
            self.ocr_text = text.to_string();
        }
        self
    }

    /// Set the URL explicitly
    pub fn url(mut self, url: &str) -> Self {
        self.url = Some(url.to_string());
        self
    }

    /// Add recent actions
    pub fn recent_actions(mut self, actions: Vec<RecentAction>) -> Self {
        self.recent_actions = actions;
        self
    }

    /// Set project context
    pub fn project(mut self, project: ProjectContext) -> Self {
        self.project = Some(project);
        self
    }

    /// Try to detect project from a file path
    pub fn detect_project_from_path(mut self, path: &str) -> Self {
        if let Some(project) = Self::detect_project(path) {
            self.project = Some(project);
        }
        self
    }

    /// Build the final RichContext
    pub fn build(self) -> RichContext {
        RichContext {
            current_app: self.current_app,
            window_title: self.window_title,
            url: self.url,
            ocr_text: self.ocr_text,
            recent_actions: self.recent_actions,
            project: self.project,
            time_context: Self::build_time_context(),
            collected_at: Utc::now(),
        }
    }

    /// Extract URL from browser window title
    fn extract_url_from_title(title: &str) -> Option<String> {
        // Common patterns:
        // "Page Title - Google Chrome" -> check for URL in page title
        // "github.com/owner/repo" -> extract as URL
        // "https://example.com - Browser" -> extract URL

        let title_lower = title.to_lowercase();

        // Check for common URL indicators
        if title_lower.contains("github.com")
            || title_lower.contains("gitlab.com")
            || title_lower.contains("bitbucket.org")
        {
            // Extract the domain/path part
            for part in title.split(&[' ', '-', '|'][..]) {
                let part = part.trim();
                if part.contains("github.com")
                    || part.contains("gitlab.com")
                    || part.contains("bitbucket.org")
                {
                    if part.starts_with("http") {
                        return Some(part.to_string());
                    } else {
                        return Some(format!("https://{}", part));
                    }
                }
            }
        }

        // Check for explicit URLs
        for part in title.split_whitespace() {
            if part.starts_with("http://") || part.starts_with("https://") {
                return Some(part.to_string());
            }
        }

        None
    }

    /// Detect project from file path
    fn detect_project(path: &str) -> Option<ProjectContext> {
        let path_buf = PathBuf::from(path);

        // Walk up to find project root (has .git, package.json, Cargo.toml, etc.)
        let mut current = path_buf.as_path();
        while let Some(parent) = current.parent() {
            let git_dir = parent.join(".git");
            let package_json = parent.join("package.json");
            let cargo_toml = parent.join("Cargo.toml");
            let pyproject = parent.join("pyproject.toml");

            if git_dir.exists() || package_json.exists() || cargo_toml.exists() || pyproject.exists()
            {
                let name = parent
                    .file_name()
                    .and_then(|n| n.to_str())
                    .unwrap_or("unknown")
                    .to_string();

                let tech_stack = if cargo_toml.exists() {
                    Some("Rust".to_string())
                } else if package_json.exists() {
                    Some("Node.js/TypeScript".to_string())
                } else if pyproject.exists() {
                    Some("Python".to_string())
                } else {
                    None
                };

                // Try to get git remote
                let git_remote = Self::get_git_remote(parent);

                return Some(ProjectContext {
                    name,
                    path: parent.to_string_lossy().to_string(),
                    git_remote,
                    tech_stack,
                });
            }
            current = parent;
        }

        None
    }

    /// Get git remote URL from a directory
    fn get_git_remote(dir: &std::path::Path) -> Option<String> {
        let output = std::process::Command::new("git")
            .args(["remote", "get-url", "origin"])
            .current_dir(dir)
            .output()
            .ok()?;

        if output.status.success() {
            Some(String::from_utf8_lossy(&output.stdout).trim().to_string())
        } else {
            None
        }
    }

    /// Build time context
    fn build_time_context() -> TimeContext {
        let now = Local::now();
        let hour = now.hour();
        let day_of_week = now.weekday().num_days_from_sunday();

        let is_weekday = day_of_week >= 1 && day_of_week <= 5;
        let is_work_hours = is_weekday && hour >= 9 && hour < 18;
        let is_late_night = hour >= 23 || hour < 6;

        TimeContext {
            hour,
            day_of_week,
            is_work_hours,
            is_late_night,
        }
    }
}

impl Default for RichContextBuilder {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_context_from_raw() {
        let ctx = RichContext::from_raw("Terminal", "zsh - ~/projects/observer", "$ cargo build");

        assert_eq!(ctx.current_app, "Terminal");
        assert_eq!(ctx.window_title, "zsh - ~/projects/observer");
        assert_eq!(ctx.ocr_text, "$ cargo build");
    }

    #[test]
    fn test_url_extraction_github() {
        let url = RichContextBuilder::extract_url_from_title(
            "Pull Request #123 - owner/repo - github.com/owner/repo/pull/123",
        );
        assert!(url.is_some());
        assert!(url.unwrap().contains("github.com"));
    }

    #[test]
    fn test_url_extraction_explicit() {
        let url = RichContextBuilder::extract_url_from_title(
            "My Page - https://example.com/page - Chrome",
        );
        assert_eq!(url, Some("https://example.com/page".to_string()));
    }

    #[test]
    fn test_url_extraction_none() {
        let url = RichContextBuilder::extract_url_from_title("Terminal - zsh");
        assert!(url.is_none());
    }

    #[test]
    fn test_ocr_truncation() {
        let long_text = "a".repeat(15000);
        let ctx = RichContext::builder().ocr_text(&long_text).build();
        assert_eq!(ctx.ocr_text.len(), MAX_OCR_LENGTH);
    }

    #[test]
    fn test_time_context() {
        let ctx = RichContext::builder().build();
        assert!(ctx.time_context.hour < 24);
        assert!(ctx.time_context.day_of_week < 7);
    }

    #[test]
    fn test_ocr_preview() {
        let ctx = RichContext::from_raw("App", "Title", "Hello, World! This is a test.");
        assert_eq!(ctx.ocr_preview(10), "Hello, Wor");
        assert_eq!(ctx.ocr_preview(100), "Hello, World! This is a test.");
    }
}
