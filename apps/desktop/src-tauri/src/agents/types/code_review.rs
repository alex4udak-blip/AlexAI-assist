//! Code Review Agent
//!
//! Handles automatic code review for Pull Requests and Merge Requests.
//! Integrates with GitHub, GitLab, and Bitbucket through gh CLI.

use super::AgentType;
use crate::agents::prompts;
use regex::Regex;
use std::process::Command;

/// Code Review Agent for automatic PR/MR analysis
pub struct CodeReviewAgent {
    system_prompt: String,
}

impl CodeReviewAgent {
    /// Create a new Code Review Agent
    pub fn new() -> Self {
        Self {
            system_prompt: prompts::load_code_review_prompt(),
        }
    }

    /// Get diff for a Pull Request using gh CLI
    ///
    /// # Arguments
    /// * `pr_url` - Full URL to the PR (e.g., https://github.com/owner/repo/pull/123)
    ///
    /// # Returns
    /// * `Ok(String)` - The diff content
    /// * `Err(String)` - Error message if failed
    pub fn get_pr_diff(pr_url: &str) -> Result<String, String> {
        // Extract owner/repo and PR number from URL
        let (repo, pr_number) = Self::parse_pr_url(pr_url)?;

        let output = Command::new("gh")
            .args(["pr", "diff", &pr_number, "-R", &repo])
            .output()
            .map_err(|e| format!("Failed to execute gh CLI: {}", e))?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(format!("gh pr diff failed: {}", stderr));
        }

        let diff = String::from_utf8_lossy(&output.stdout).to_string();
        if diff.is_empty() {
            return Err("PR diff is empty".to_string());
        }

        Ok(diff)
    }

    /// Generate a review comment for a specific issue
    ///
    /// # Arguments
    /// * `diff` - The diff content showing the change
    /// * `issue` - Description of the issue found
    ///
    /// # Returns
    /// A formatted review comment string
    pub fn generate_review_comment(diff: &str, issue: &str) -> String {
        // Extract file path and line number from diff if possible
        let (file_path, line_info) = Self::extract_location_from_diff(diff);

        let location = if let Some(path) = file_path {
            if let Some(line) = line_info {
                format!("**{}:{}**\n\n", path, line)
            } else {
                format!("**{}**\n\n", path)
            }
        } else {
            String::new()
        };

        format!(
            "{}**Issue:** {}\n\n**Context:**\n```diff\n{}\n```\n\n**Recommendation:** Please review and address this concern.",
            location,
            issue,
            Self::truncate_diff(diff, 500)
        )
    }

    /// Parse PR URL to extract repository and PR number
    fn parse_pr_url(url: &str) -> Result<(String, String), String> {
        // Handle GitHub URLs: https://github.com/owner/repo/pull/123
        let github_re = Regex::new(r"github\.com/([^/]+/[^/]+)/pull/(\d+)")
            .map_err(|e| format!("Regex error: {}", e))?;

        if let Some(caps) = github_re.captures(url) {
            let repo = caps.get(1).map(|m| m.as_str()).unwrap_or("");
            let pr_num = caps.get(2).map(|m| m.as_str()).unwrap_or("");
            return Ok((repo.to_string(), pr_num.to_string()));
        }

        // Handle GitLab URLs: https://gitlab.com/owner/repo/-/merge_requests/123
        let gitlab_re = Regex::new(r"gitlab\.com/([^/]+/[^/]+)/-/merge_requests/(\d+)")
            .map_err(|e| format!("Regex error: {}", e))?;

        if let Some(caps) = gitlab_re.captures(url) {
            let repo = caps.get(1).map(|m| m.as_str()).unwrap_or("");
            let mr_num = caps.get(2).map(|m| m.as_str()).unwrap_or("");
            return Ok((repo.to_string(), mr_num.to_string()));
        }

        // Handle Bitbucket URLs: https://bitbucket.org/owner/repo/pull-requests/123
        let bitbucket_re = Regex::new(r"bitbucket\.org/([^/]+/[^/]+)/pull-requests/(\d+)")
            .map_err(|e| format!("Regex error: {}", e))?;

        if let Some(caps) = bitbucket_re.captures(url) {
            let repo = caps.get(1).map(|m| m.as_str()).unwrap_or("");
            let pr_num = caps.get(2).map(|m| m.as_str()).unwrap_or("");
            return Ok((repo.to_string(), pr_num.to_string()));
        }

        Err(format!("Could not parse PR URL: {}", url))
    }

    /// Extract file path and line number from diff header
    fn extract_location_from_diff(diff: &str) -> (Option<String>, Option<u32>) {
        // Look for diff header: +++ b/path/to/file.rs
        let file_re = Regex::new(r"\+\+\+ b/(.+)").ok();
        let file_path = file_re
            .and_then(|re| re.captures(diff))
            .and_then(|caps| caps.get(1))
            .map(|m| m.as_str().to_string());

        // Look for line info: @@ -10,5 +12,7 @@
        let line_re = Regex::new(r"@@ -\d+,?\d* \+(\d+)").ok();
        let line_num = line_re
            .and_then(|re| re.captures(diff))
            .and_then(|caps| caps.get(1))
            .and_then(|m| m.as_str().parse::<u32>().ok());

        (file_path, line_num)
    }

    /// Truncate diff to max chars for readability
    fn truncate_diff(diff: &str, max_chars: usize) -> &str {
        match diff.char_indices().nth(max_chars) {
            Some((idx, _)) => &diff[..idx],
            None => diff,
        }
    }

    /// Check if URL matches GitHub PR pattern
    fn is_github_pr_url(url: &str) -> bool {
        let re = Regex::new(r"github\.com/[^/]+/[^/]+/pull/\d+").ok();
        re.map(|r| r.is_match(url)).unwrap_or(false)
    }

    /// Check if URL matches GitLab MR pattern
    fn is_gitlab_mr_url(url: &str) -> bool {
        let re = Regex::new(r"gitlab\.com/[^/]+/[^/]+/-/merge_requests/\d+").ok();
        re.map(|r| r.is_match(url)).unwrap_or(false)
    }

    /// Check if URL matches Bitbucket PR pattern
    fn is_bitbucket_pr_url(url: &str) -> bool {
        let re = Regex::new(r"bitbucket\.org/[^/]+/[^/]+/pull-requests/\d+").ok();
        re.map(|r| r.is_match(url)).unwrap_or(false)
    }

    /// Check if app name is a known browser
    fn is_browser(app_name: &str) -> bool {
        let browsers = [
            "Chrome", "Firefox", "Safari", "Edge", "Brave", "Opera", "Arc", "Vivaldi", "Chromium",
        ];
        let app_lower = app_name.to_lowercase();
        browsers
            .iter()
            .any(|b| app_lower.contains(&b.to_lowercase()))
    }
}

impl Default for CodeReviewAgent {
    fn default() -> Self {
        Self::new()
    }
}

impl AgentType for CodeReviewAgent {
    fn name(&self) -> &'static str {
        "Code Review"
    }

    fn system_prompt(&self) -> &str {
        &self.system_prompt
    }

    fn should_handle(&self, app_name: &str, text: &str) -> bool {
        let app_lower = app_name.to_lowercase();
        let text_lower = text.to_lowercase();

        // Check 1: app_name contains code hosting platforms
        let is_code_platform = app_lower.contains("github")
            || app_lower.contains("gitlab")
            || app_lower.contains("bitbucket");

        if is_code_platform {
            return true;
        }

        // Check 2: text contains PR/MR related keywords
        let pr_keywords = [
            "pull request",
            "merge request",
            "diff",
            "changed files",
            "files changed",
            "review changes",
            "code review",
            "commits ahead",
            "comparing changes",
        ];

        let has_pr_keywords = pr_keywords.iter().any(|kw| text_lower.contains(kw));
        if has_pr_keywords {
            return true;
        }

        // Check 3: Browser with PR/MR URL in text
        if Self::is_browser(app_name) {
            // Check if text contains a PR/MR URL
            if Self::is_github_pr_url(&text_lower)
                || Self::is_gitlab_mr_url(&text_lower)
                || Self::is_bitbucket_pr_url(&text_lower)
            {
                return true;
            }

            // Also check for URL patterns in window title (often shows repo/PR info)
            if text_lower.contains("/pull/") || text_lower.contains("/merge_requests/") {
                return true;
            }
        }

        false
    }

    fn max_iterations(&self) -> u32 {
        5 // Code review usually needs fewer iterations
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_should_handle_github_app() {
        let agent = CodeReviewAgent::new();
        assert!(agent.should_handle("GitHub Desktop", "some text"));
    }

    #[test]
    fn test_should_handle_gitlab_app() {
        let agent = CodeReviewAgent::new();
        assert!(agent.should_handle("GitLab", "project view"));
    }

    #[test]
    fn test_should_handle_bitbucket_app() {
        let agent = CodeReviewAgent::new();
        assert!(agent.should_handle("Bitbucket", "repository"));
    }

    #[test]
    fn test_should_handle_pr_keywords() {
        let agent = CodeReviewAgent::new();
        assert!(agent.should_handle("Terminal", "Pull Request #123 opened"));
        assert!(agent.should_handle("VS Code", "Merge Request: Add feature"));
        assert!(agent.should_handle("Slack", "Review the diff please"));
        assert!(agent.should_handle("Browser", "5 changed files in this PR"));
    }

    #[test]
    fn test_should_handle_browser_with_github_url() {
        let agent = CodeReviewAgent::new();
        assert!(agent.should_handle(
            "Google Chrome",
            "Fix bug #42 by user https://github.com/owner/repo/pull/123"
        ));
        assert!(agent.should_handle("Safari", "owner/repo/pull/456 - Safari"));
    }

    #[test]
    fn test_should_handle_browser_with_gitlab_url() {
        let agent = CodeReviewAgent::new();
        assert!(agent.should_handle(
            "Firefox",
            "https://gitlab.com/owner/repo/-/merge_requests/789"
        ));
    }

    #[test]
    fn test_should_not_handle_unrelated() {
        let agent = CodeReviewAgent::new();
        assert!(!agent.should_handle("Spotify", "Playing music"));
        assert!(!agent.should_handle("Calendar", "Meeting at 3pm"));
        assert!(!agent.should_handle("Notes", "Shopping list"));
    }

    #[test]
    fn test_parse_github_pr_url() {
        let result = CodeReviewAgent::parse_pr_url("https://github.com/owner/repo/pull/123");
        assert!(result.is_ok());
        let (repo, pr) = result.unwrap();
        assert_eq!(repo, "owner/repo");
        assert_eq!(pr, "123");
    }

    #[test]
    fn test_parse_gitlab_mr_url() {
        let result =
            CodeReviewAgent::parse_pr_url("https://gitlab.com/group/project/-/merge_requests/456");
        assert!(result.is_ok());
        let (repo, mr) = result.unwrap();
        assert_eq!(repo, "group/project");
        assert_eq!(mr, "456");
    }

    #[test]
    fn test_parse_bitbucket_pr_url() {
        let result =
            CodeReviewAgent::parse_pr_url("https://bitbucket.org/team/repo/pull-requests/789");
        assert!(result.is_ok());
        let (repo, pr) = result.unwrap();
        assert_eq!(repo, "team/repo");
        assert_eq!(pr, "789");
    }

    #[test]
    fn test_generate_review_comment() {
        let diff = r#"+++ b/src/main.rs
@@ -10,5 +12,7 @@
+ let password = "secret123";
"#;
        let issue = "Hardcoded password detected - security vulnerability";
        let comment = CodeReviewAgent::generate_review_comment(diff, issue);

        assert!(comment.contains("src/main.rs"));
        assert!(comment.contains("Hardcoded password"));
        assert!(comment.contains("Issue:"));
    }

    #[test]
    fn test_extract_location_from_diff() {
        let diff = r#"diff --git a/src/lib.rs b/src/lib.rs
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -25,6 +25,10 @@ impl Config {
"#;
        let (file, line) = CodeReviewAgent::extract_location_from_diff(diff);
        assert_eq!(file, Some("src/lib.rs".to_string()));
        assert_eq!(line, Some(25));
    }

    #[test]
    fn test_name() {
        let agent = CodeReviewAgent::new();
        assert_eq!(agent.name(), "Code Review");
    }

    #[test]
    fn test_system_prompt_not_empty() {
        let agent = CodeReviewAgent::new();
        assert!(!agent.system_prompt().is_empty());
        assert!(agent.system_prompt().contains("Code Review"));
    }

    #[test]
    fn test_max_iterations() {
        let agent = CodeReviewAgent::new();
        assert_eq!(agent.max_iterations(), 5);
    }
}
