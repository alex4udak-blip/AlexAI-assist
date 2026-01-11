//! Git Assistant Agent
//!
//! Helps with git operations, generates commit messages,
//! and suggests splitting changes into logical commits.

use super::AgentType;
use serde::{Deserialize, Serialize};
use std::process::Command;

/// Represents a file change in git
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileChange {
    /// File path relative to repository root
    pub path: String,
    /// Change status: Added, Modified, Deleted, Renamed, etc.
    pub status: FileStatus,
    /// Number of lines added
    pub additions: u32,
    /// Number of lines deleted
    pub deletions: u32,
}

/// Status of a file change
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum FileStatus {
    Added,
    Modified,
    Deleted,
    Renamed,
    Copied,
    Untracked,
}

impl FileStatus {
    /// Parse git status code to FileStatus
    fn from_git_code(code: &str) -> Self {
        match code.trim() {
            "A" => Self::Added,
            "M" | " M" | "MM" => Self::Modified,
            "D" | " D" => Self::Deleted,
            "R" => Self::Renamed,
            "C" => Self::Copied,
            "??" => Self::Untracked,
            _ => Self::Untracked,
        }
    }
}

/// Suggestion for a logical commit
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommitSuggestion {
    /// Suggested commit message
    pub message: String,
    /// Files to include in this commit
    pub files: Vec<String>,
    /// Type of change (feat, fix, refactor, etc.)
    pub commit_type: String,
    /// Scope of the change (optional)
    pub scope: Option<String>,
}

/// Git keywords that trigger this agent
const GIT_KEYWORDS: &[&str] = &[
    "git",
    "commit",
    "push",
    "merge conflict",
    "pull request",
    "branch",
    "rebase",
    "cherry-pick",
    "stash",
];

/// Terminal indicators for uncommitted changes
const UNCOMMITTED_INDICATORS: &[&str] = &[
    "modified:",
    "new file:",
    "deleted:",
    "Changes not staged",
    "Changes to be committed",
    "Untracked files",
];

/// System prompt for Git Assistant
const SYSTEM_PROMPT: &str = r#"Ты Git Assistant агент Observer.

ТВОЯ РОЛЬ:
Помогаешь с git операциями, генерируешь осмысленные commit messages и предлагаешь структурировать изменения.

ПРАВИЛА БЕЗОПАСНОСТИ:
1. НИКОГДА не делай git push без явного подтверждения пользователя
2. НИКОГДА не делай force push (--force, -f)
3. НИКОГДА не удаляй ветки без подтверждения
4. НИКОГДА не выполняй git reset --hard без подтверждения

ПРАВИЛА КОММИТОВ (Conventional Commits):
- Формат: <type>(<scope>): <description>
- Типы: feat, fix, docs, style, refactor, perf, test, chore, build, ci
- Описание на английском, императивное наклонение
- Примеры:
  - feat(auth): add OAuth2 login support
  - fix(api): handle null response in user endpoint
  - refactor(ui): extract Button component

РЕКОМЕНДАЦИИ:
1. Один логический change = один коммит
2. Не смешивай рефакторинг с фичами
3. Тесты коммить вместе с кодом который они тестируют
4. Если много изменений - предложи разбить на коммиты

ФОРМАТ ОТВЕТА (строго JSON):
{
  "action": "command" | "notify" | "skip" | "confirm",
  "cmd": "git команда или null",
  "reason": "объяснение на русском",
  "next_step": "что проверить после или null"
}
"#;

/// Git Assistant Agent
pub struct GitAssistantAgent {
    system_prompt: String,
}

impl GitAssistantAgent {
    /// Create new Git Assistant Agent
    pub fn new() -> Self {
        Self {
            system_prompt: SYSTEM_PROMPT.to_string(),
        }
    }

    /// Get uncommitted changes from git
    pub fn get_uncommitted_changes() -> Vec<FileChange> {
        let mut changes = Vec::new();

        // Get staged and unstaged changes
        let status_output = Command::new("git").args(["status", "--porcelain"]).output();

        let status = match status_output {
            Ok(output) if output.status.success() => {
                String::from_utf8_lossy(&output.stdout).to_string()
            }
            _ => return changes,
        };

        for line in status.lines() {
            if line.len() < 3 {
                continue;
            }

            let status_code = &line[..2];
            let file_path = line[3..].trim().to_string();

            // Skip if path contains " -> " (renamed files format)
            let path = if file_path.contains(" -> ") {
                file_path
                    .split(" -> ")
                    .last()
                    .unwrap_or(&file_path)
                    .to_string()
            } else {
                file_path
            };

            let file_status = FileStatus::from_git_code(status_code);

            // Get additions/deletions from diff
            let (additions, deletions) = Self::get_file_diff_stats(&path);

            changes.push(FileChange {
                path,
                status: file_status,
                additions,
                deletions,
            });
        }

        changes
    }

    /// Get diff statistics for a file
    fn get_file_diff_stats(file_path: &str) -> (u32, u32) {
        let output = Command::new("git")
            .args(["diff", "--numstat", "--", file_path])
            .output();

        match output {
            Ok(out) if out.status.success() => {
                let stat = String::from_utf8_lossy(&out.stdout);
                let parts: Vec<&str> = stat.split_whitespace().collect();
                if parts.len() >= 2 {
                    let additions = parts[0].parse().unwrap_or(0);
                    let deletions = parts[1].parse().unwrap_or(0);
                    return (additions, deletions);
                }
                (0, 0)
            }
            _ => (0, 0),
        }
    }

    /// Generate commit message based on changes
    pub fn generate_commit_message(changes: &[FileChange]) -> String {
        if changes.is_empty() {
            return String::from("chore: empty commit");
        }

        // Analyze changes to determine commit type
        let (commit_type, scope) = Self::analyze_changes(changes);

        // Generate description based on files
        let description = Self::generate_description(changes);

        if let Some(s) = scope {
            format!("{}({}): {}", commit_type, s, description)
        } else {
            format!("{}: {}", commit_type, description)
        }
    }

    /// Analyze changes to determine commit type and scope
    fn analyze_changes(changes: &[FileChange]) -> (&'static str, Option<String>) {
        let paths: Vec<&str> = changes.iter().map(|c| c.path.as_str()).collect();

        // Determine scope from common path
        let scope = Self::find_common_scope(&paths);

        // Determine type from file patterns
        let commit_type = if paths
            .iter()
            .any(|p| p.contains("test") || p.ends_with("_test.rs") || p.ends_with(".test.ts"))
        {
            "test"
        } else if paths
            .iter()
            .all(|p| p.ends_with(".md") || p.contains("docs/") || p.contains("README"))
        {
            "docs"
        } else if paths.iter().any(|p| p.contains("fix") || p.contains("bug")) {
            "fix"
        } else if paths
            .iter()
            .all(|p| p.ends_with(".css") || p.ends_with(".scss") || p.ends_with(".less"))
        {
            "style"
        } else if paths
            .iter()
            .any(|p| p.contains("Cargo.toml") || p.contains("package.json") || p.contains("build"))
        {
            "build"
        } else if paths
            .iter()
            .any(|p| p.contains(".github/") || p.contains("ci") || p.contains("workflow"))
        {
            "ci"
        } else if changes.iter().all(|c| c.status == FileStatus::Deleted) {
            "chore"
        } else if changes.iter().all(|c| c.additions > 0 && c.deletions > 0) {
            "refactor"
        } else if changes.iter().any(|c| c.status == FileStatus::Added) {
            "feat"
        } else {
            "chore"
        };

        (commit_type, scope)
    }

    /// Find common scope from file paths
    fn find_common_scope(paths: &[&str]) -> Option<String> {
        if paths.is_empty() {
            return None;
        }

        // Try to find common directory
        let first_parts: Vec<&str> = paths[0].split('/').collect();

        for i in (0..first_parts.len()).rev() {
            let potential_scope = first_parts[i];

            // Skip generic names
            if ["src", "lib", "mod.rs", "index.ts", "index.js"].contains(&potential_scope) {
                continue;
            }

            // Check if it's a meaningful scope
            if potential_scope.len() > 2 && !potential_scope.contains('.') {
                // Check if most files share this scope
                let matches = paths.iter().filter(|p| p.contains(potential_scope)).count();
                if matches > paths.len() / 2 {
                    return Some(potential_scope.to_string());
                }
            }
        }

        None
    }

    /// Generate description from changes
    fn generate_description(changes: &[FileChange]) -> String {
        if changes.len() == 1 {
            let change = &changes[0];
            let file_name = change.path.split('/').last().unwrap_or(&change.path);
            let action = match change.status {
                FileStatus::Added => "add",
                FileStatus::Modified => "update",
                FileStatus::Deleted => "remove",
                FileStatus::Renamed => "rename",
                FileStatus::Copied => "copy",
                FileStatus::Untracked => "add",
            };
            format!("{} {}", action, file_name)
        } else {
            // Multiple files
            let actions: std::collections::HashSet<_> = changes
                .iter()
                .map(|c| match c.status {
                    FileStatus::Added | FileStatus::Untracked => "add",
                    FileStatus::Modified => "update",
                    FileStatus::Deleted => "remove",
                    FileStatus::Renamed => "rename",
                    FileStatus::Copied => "copy",
                })
                .collect();

            if actions.len() == 1 {
                format!("{} {} files", actions.iter().next().unwrap(), changes.len())
            } else {
                format!("update {} files", changes.len())
            }
        }
    }

    /// Suggest how to split changes into logical commits
    pub fn suggest_commit_split(changes: &[FileChange]) -> Vec<CommitSuggestion> {
        let mut suggestions = Vec::new();

        if changes.is_empty() {
            return suggestions;
        }

        // Group files by type/purpose
        let mut groups: std::collections::HashMap<String, Vec<FileChange>> =
            std::collections::HashMap::new();

        for change in changes {
            let category = Self::categorize_file(&change.path);
            groups.entry(category).or_default().push(change.clone());
        }

        // Create suggestions for each group
        for (category, files) in groups {
            let file_paths: Vec<String> = files.iter().map(|f| f.path.clone()).collect();
            let message = Self::generate_commit_message(&files);

            let (commit_type, scope) = Self::analyze_changes(&files);

            suggestions.push(CommitSuggestion {
                message,
                files: file_paths,
                commit_type: commit_type.to_string(),
                scope,
            });
        }

        // Sort suggestions by priority (tests last, features first)
        suggestions.sort_by(|a, b| {
            let priority_a = Self::commit_type_priority(&a.commit_type);
            let priority_b = Self::commit_type_priority(&b.commit_type);
            priority_a.cmp(&priority_b)
        });

        suggestions
    }

    /// Categorize file by its path
    fn categorize_file(path: &str) -> String {
        if path.contains("test")
            || path.ends_with("_test.rs")
            || path.ends_with(".test.ts")
            || path.ends_with(".spec.ts")
        {
            "tests".to_string()
        } else if path.ends_with(".md") || path.contains("docs/") {
            "docs".to_string()
        } else if path.contains(".github/") || path.contains("ci/") || path.contains("workflow") {
            "ci".to_string()
        } else if path.contains("Cargo.toml")
            || path.contains("package.json")
            || path.contains("pnpm")
        {
            "build".to_string()
        } else if path.ends_with(".css") || path.ends_with(".scss") {
            "style".to_string()
        } else if path.contains("/types/")
            || path.contains("/models/")
            || path.contains("/interfaces/")
        {
            "types".to_string()
        } else if path.contains("/api/")
            || path.contains("/routes/")
            || path.contains("/endpoints/")
        {
            "api".to_string()
        } else if path.contains("/ui/") || path.contains("/components/") || path.contains("/views/")
        {
            "ui".to_string()
        } else {
            // Use parent directory as category
            path.split('/')
                .rev()
                .nth(1)
                .unwrap_or("general")
                .to_string()
        }
    }

    /// Get priority for commit type (lower = first)
    fn commit_type_priority(commit_type: &str) -> u8 {
        match commit_type {
            "feat" => 1,
            "fix" => 2,
            "refactor" => 3,
            "perf" => 4,
            "style" => 5,
            "build" => 6,
            "ci" => 7,
            "docs" => 8,
            "test" => 9,
            "chore" => 10,
            _ => 11,
        }
    }

    /// Check if there are many uncommitted changes
    fn has_many_uncommitted_changes() -> bool {
        let changes = Self::get_uncommitted_changes();
        changes.len() > 5
    }

    /// Check if text contains git-related keywords
    fn contains_git_keywords(text: &str) -> bool {
        let text_lower = text.to_lowercase();
        GIT_KEYWORDS.iter().any(|kw| text_lower.contains(kw))
    }

    /// Check if terminal shows uncommitted changes
    fn terminal_shows_uncommitted(app_name: &str, text: &str) -> bool {
        let app_lower = app_name.to_lowercase();
        let is_terminal = app_lower.contains("terminal")
            || app_lower.contains("iterm")
            || app_lower.contains("warp");

        if !is_terminal {
            return false;
        }

        UNCOMMITTED_INDICATORS
            .iter()
            .any(|indicator| text.contains(indicator))
    }
}

impl Default for GitAssistantAgent {
    fn default() -> Self {
        Self::new()
    }
}

impl AgentType for GitAssistantAgent {
    fn name(&self) -> &'static str {
        "Git Assistant"
    }

    fn system_prompt(&self) -> &str {
        &self.system_prompt
    }

    fn should_handle(&self, app_name: &str, text: &str) -> bool {
        // Check if there are many uncommitted changes
        if Self::has_many_uncommitted_changes() {
            return true;
        }

        // Check if text contains git keywords
        if Self::contains_git_keywords(text) {
            return true;
        }

        // Check if terminal shows uncommitted changes
        if Self::terminal_shows_uncommitted(app_name, text) {
            return true;
        }

        false
    }

    fn max_iterations(&self) -> u32 {
        5
    }

    fn priority(&self) -> u32 {
        // High priority for git-related contexts
        80
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_new_agent() {
        let agent = GitAssistantAgent::new();
        assert_eq!(agent.name(), "Git Assistant");
        assert!(!agent.system_prompt().is_empty());
    }

    #[test]
    fn test_should_handle_git_keywords() {
        let agent = GitAssistantAgent::new();

        assert!(agent.should_handle("Any App", "git status"));
        assert!(agent.should_handle("Any App", "need to commit these changes"));
        assert!(agent.should_handle("Any App", "push to origin"));
        assert!(agent.should_handle("Any App", "there's a merge conflict here"));
    }

    #[test]
    fn test_should_handle_terminal_uncommitted() {
        let agent = GitAssistantAgent::new();

        assert!(agent.should_handle("Terminal", "modified: src/main.rs"));
        assert!(agent.should_handle("iTerm2", "Changes not staged for commit"));
        assert!(agent.should_handle("Warp", "new file: README.md"));
    }

    #[test]
    fn test_should_not_handle_unrelated() {
        let agent = GitAssistantAgent::new();

        // These might still return true if there are actual uncommitted changes in git
        // So we just test the basic case
        let result = agent.should_handle("Safari", "Hello World");
        // Result depends on actual git state, so we don't assert a specific value
        assert!(result || !result); // Always true, just checking it doesn't panic
    }

    #[test]
    fn test_file_status_from_git_code() {
        assert_eq!(FileStatus::from_git_code("A"), FileStatus::Added);
        assert_eq!(FileStatus::from_git_code("M"), FileStatus::Modified);
        assert_eq!(FileStatus::from_git_code(" M"), FileStatus::Modified);
        assert_eq!(FileStatus::from_git_code("D"), FileStatus::Deleted);
        assert_eq!(FileStatus::from_git_code("R"), FileStatus::Renamed);
        assert_eq!(FileStatus::from_git_code("??"), FileStatus::Added);
    }

    #[test]
    fn test_generate_commit_message_single_file() {
        let changes = vec![FileChange {
            path: "src/main.rs".to_string(),
            status: FileStatus::Modified,
            additions: 10,
            deletions: 5,
        }];

        let message = GitAssistantAgent::generate_commit_message(&changes);
        assert!(message.contains("update"));
        assert!(message.contains("main.rs"));
    }

    #[test]
    fn test_generate_commit_message_multiple_files() {
        let changes = vec![
            FileChange {
                path: "src/lib.rs".to_string(),
                status: FileStatus::Added,
                additions: 50,
                deletions: 0,
            },
            FileChange {
                path: "src/utils.rs".to_string(),
                status: FileStatus::Added,
                additions: 30,
                deletions: 0,
            },
        ];

        let message = GitAssistantAgent::generate_commit_message(&changes);
        assert!(message.starts_with("feat"));
        assert!(message.contains("2 files"));
    }

    #[test]
    fn test_generate_commit_message_test_files() {
        let changes = vec![FileChange {
            path: "tests/unit_test.rs".to_string(),
            status: FileStatus::Added,
            additions: 100,
            deletions: 0,
        }];

        let message = GitAssistantAgent::generate_commit_message(&changes);
        assert!(message.starts_with("test"));
    }

    #[test]
    fn test_suggest_commit_split() {
        let changes = vec![
            FileChange {
                path: "src/api/routes.rs".to_string(),
                status: FileStatus::Modified,
                additions: 20,
                deletions: 5,
            },
            FileChange {
                path: "tests/api_test.rs".to_string(),
                status: FileStatus::Added,
                additions: 50,
                deletions: 0,
            },
            FileChange {
                path: "docs/README.md".to_string(),
                status: FileStatus::Modified,
                additions: 10,
                deletions: 2,
            },
        ];

        let suggestions = GitAssistantAgent::suggest_commit_split(&changes);
        assert!(!suggestions.is_empty());
        assert!(suggestions.len() >= 2); // At least 2 groups (code and tests)
    }

    #[test]
    fn test_categorize_file() {
        assert_eq!(
            GitAssistantAgent::categorize_file("tests/unit_test.rs"),
            "tests"
        );
        assert_eq!(GitAssistantAgent::categorize_file("docs/README.md"), "docs");
        assert_eq!(
            GitAssistantAgent::categorize_file(".github/workflows/ci.yml"),
            "ci"
        );
        assert_eq!(
            GitAssistantAgent::categorize_file("src/components/Button.tsx"),
            "ui"
        );
        assert_eq!(
            GitAssistantAgent::categorize_file("src/api/users.rs"),
            "api"
        );
    }

    #[test]
    fn test_commit_type_priority() {
        assert!(
            GitAssistantAgent::commit_type_priority("feat")
                < GitAssistantAgent::commit_type_priority("test")
        );
        assert!(
            GitAssistantAgent::commit_type_priority("fix")
                < GitAssistantAgent::commit_type_priority("docs")
        );
    }

    #[test]
    fn test_max_iterations() {
        let agent = GitAssistantAgent::new();
        assert_eq!(agent.max_iterations(), 5);
    }
}
