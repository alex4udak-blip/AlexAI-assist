//! DevOps Agent for Observer
//!
//! Handles terminal errors, automatic fixes, and dependency installation.

use super::AgentType;
use crate::agents::prompts;

/// Error types that the DevOps agent can recognize
#[derive(Debug, Clone, PartialEq)]
pub enum ErrorType {
    /// npm/node related errors
    NpmError,
    /// Cargo/Rust related errors
    CargoError,
    /// Python/pip related errors
    PythonError,
    /// Git related errors
    GitError,
    /// Docker related errors
    DockerError,
    /// Permission denied errors
    PermissionError,
    /// Command not found errors
    CommandNotFound,
    /// Module/package not found errors
    ModuleNotFound,
    /// Connection/network errors
    NetworkError,
    /// Build/compilation errors
    BuildError,
    /// Generic/unknown error
    Unknown,
}

impl ErrorType {
    /// Get error type name as string
    pub fn as_str(&self) -> &'static str {
        match self {
            ErrorType::NpmError => "npm",
            ErrorType::CargoError => "cargo",
            ErrorType::PythonError => "python",
            ErrorType::GitError => "git",
            ErrorType::DockerError => "docker",
            ErrorType::PermissionError => "permission",
            ErrorType::CommandNotFound => "command_not_found",
            ErrorType::ModuleNotFound => "module_not_found",
            ErrorType::NetworkError => "network",
            ErrorType::BuildError => "build",
            ErrorType::Unknown => "unknown",
        }
    }
}

/// Terminal application patterns
const TERMINAL_APPS: &[&str] = &[
    "Terminal",
    "iTerm",
    "iTerm2",
    "Warp",
    "Alacritty",
    "Hyper",
    "Kitty",
    "Konsole",
    "GNOME Terminal",
    "xterm",
    "rxvt",
    "urxvt",
    "st",
    "Tilix",
    "Terminator",
    "WezTerm",
    "foot",
    "Terminal.app",
    "PowerShell",
    "cmd.exe",
    "Windows Terminal",
];

/// Russian terminal names
const TERMINAL_APPS_RU: &[&str] = &["Терминал", "терминал"];

/// Error patterns for detection
const ERROR_PATTERNS: &[(&str, ErrorType)] = &[
    // npm/node errors
    ("npm ERR!", ErrorType::NpmError),
    ("npm error", ErrorType::NpmError),
    ("npm WARN", ErrorType::NpmError),
    ("ENOENT", ErrorType::NpmError),
    ("EACCES", ErrorType::NpmError),
    ("node:internal", ErrorType::NpmError),
    ("Cannot find module", ErrorType::NpmError),
    ("MODULE_NOT_FOUND", ErrorType::NpmError),
    ("SyntaxError:", ErrorType::NpmError),
    ("ReferenceError:", ErrorType::NpmError),
    ("TypeError:", ErrorType::NpmError),
    // Cargo/Rust errors
    ("cargo error", ErrorType::CargoError),
    ("error[E", ErrorType::CargoError),
    ("error: could not compile", ErrorType::CargoError),
    ("error: failed to compile", ErrorType::CargoError),
    ("cannot find crate", ErrorType::CargoError),
    ("unresolved import", ErrorType::CargoError),
    ("use of undeclared", ErrorType::CargoError),
    ("mismatched types", ErrorType::CargoError),
    ("borrow checker", ErrorType::CargoError),
    ("lifetime", ErrorType::CargoError),
    // Python errors
    ("ModuleNotFoundError", ErrorType::PythonError),
    ("ImportError", ErrorType::PythonError),
    ("pip error", ErrorType::PythonError),
    ("pip ERR", ErrorType::PythonError),
    ("SyntaxError: invalid syntax", ErrorType::PythonError),
    ("IndentationError", ErrorType::PythonError),
    ("NameError:", ErrorType::PythonError),
    ("AttributeError:", ErrorType::PythonError),
    ("KeyError:", ErrorType::PythonError),
    ("ValueError:", ErrorType::PythonError),
    ("FileNotFoundError:", ErrorType::PythonError),
    ("No module named", ErrorType::PythonError),
    ("Traceback (most recent call last)", ErrorType::PythonError),
    // Git errors
    ("fatal: not a git repository", ErrorType::GitError),
    ("fatal: remote origin already exists", ErrorType::GitError),
    ("error: failed to push", ErrorType::GitError),
    ("CONFLICT (content)", ErrorType::GitError),
    ("merge conflict", ErrorType::GitError),
    ("Your branch is behind", ErrorType::GitError),
    ("rejected", ErrorType::GitError),
    ("git: command not found", ErrorType::GitError),
    // Docker errors
    ("docker: Error", ErrorType::DockerError),
    (
        "Cannot connect to the Docker daemon",
        ErrorType::DockerError,
    ),
    ("Error response from daemon", ErrorType::DockerError),
    ("image not found", ErrorType::DockerError),
    ("container not found", ErrorType::DockerError),
    ("docker-compose", ErrorType::DockerError),
    // Permission errors
    ("Permission denied", ErrorType::PermissionError),
    ("EACCES:", ErrorType::PermissionError),
    ("Operation not permitted", ErrorType::PermissionError),
    ("access denied", ErrorType::PermissionError),
    // Command not found
    ("command not found", ErrorType::CommandNotFound),
    ("is not recognized as", ErrorType::CommandNotFound),
    ("not found:", ErrorType::CommandNotFound),
    ("zsh: command not found", ErrorType::CommandNotFound),
    ("bash: command not found", ErrorType::CommandNotFound),
    ("sh: command not found", ErrorType::CommandNotFound),
    // Module/dependency not found
    ("module not found", ErrorType::ModuleNotFound),
    ("package not found", ErrorType::ModuleNotFound),
    ("dependency not found", ErrorType::ModuleNotFound),
    ("Could not resolve", ErrorType::ModuleNotFound),
    ("Unable to resolve", ErrorType::ModuleNotFound),
    // Network errors
    ("Connection refused", ErrorType::NetworkError),
    ("ECONNREFUSED", ErrorType::NetworkError),
    ("ETIMEDOUT", ErrorType::NetworkError),
    ("Network is unreachable", ErrorType::NetworkError),
    ("getaddrinfo ENOTFOUND", ErrorType::NetworkError),
    ("socket hang up", ErrorType::NetworkError),
    ("ECONNRESET", ErrorType::NetworkError),
    // Build errors
    ("Build failed", ErrorType::BuildError),
    ("Compilation failed", ErrorType::BuildError),
    ("make: ***", ErrorType::BuildError),
    ("Error:", ErrorType::BuildError),
    ("error:", ErrorType::BuildError),
    ("Failed to compile", ErrorType::BuildError),
];

/// DevOps Agent for handling terminal errors and fixes
pub struct DevOpsAgent {
    system_prompt: String,
}

impl DevOpsAgent {
    /// Create a new DevOps agent
    pub fn new() -> Self {
        Self {
            system_prompt: prompts::load_devops_prompt(),
        }
    }

    /// Analyze error text and determine the error type
    pub fn analyze_error(&self, text: &str) -> Option<ErrorType> {
        let text_lower = text.to_lowercase();

        for (pattern, error_type) in ERROR_PATTERNS {
            if text_lower.contains(&pattern.to_lowercase()) {
                return Some(error_type.clone());
            }
        }

        // Check for generic error patterns
        if text_lower.contains("error")
            || text_lower.contains("failed")
            || text_lower.contains("exception")
        {
            return Some(ErrorType::Unknown);
        }

        None
    }

    /// Suggest a fix command based on the error type and context
    pub fn suggest_fix(&self, error_type: &ErrorType, context: &str) -> String {
        match error_type {
            ErrorType::NpmError => {
                // Try to extract package name if possible
                if context.contains("Cannot find module") || context.contains("MODULE_NOT_FOUND") {
                    if let Some(package) = Self::extract_npm_package(context) {
                        return format!("npm install {}", package);
                    }
                }
                "npm install".to_string()
            }
            ErrorType::CargoError => {
                if let Some(crate_name) = Self::extract_cargo_crate(context) {
                    return format!("cargo add {}", crate_name);
                }
                "cargo build".to_string()
            }
            ErrorType::PythonError => {
                if let Some(module) = Self::extract_python_module(context) {
                    return format!("pip install {}", module);
                }
                "pip install -r requirements.txt".to_string()
            }
            ErrorType::GitError => {
                if context.contains("not a git repository") {
                    return "git init".to_string();
                }
                if context.contains("Your branch is behind") {
                    return "git pull".to_string();
                }
                "git status".to_string()
            }
            ErrorType::DockerError => {
                if context.contains("Cannot connect to the Docker daemon") {
                    return "Запусти Docker Desktop или сервис docker".to_string();
                }
                "docker ps".to_string()
            }
            ErrorType::PermissionError => "chmod +x <script>".to_string(),
            ErrorType::CommandNotFound => {
                if let Some(cmd) = Self::extract_missing_command(context) {
                    return format!("Установи {}", cmd);
                }
                "Проверь PATH или установи нужную утилиту".to_string()
            }
            ErrorType::ModuleNotFound => "Установи недостающую зависимость".to_string(),
            ErrorType::NetworkError => {
                "Проверь сетевое подключение и доступность сервера".to_string()
            }
            ErrorType::BuildError => "Проверь логи сборки и исправь ошибки компиляции".to_string(),
            ErrorType::Unknown => "Анализирую ошибку...".to_string(),
        }
    }

    /// Check if the given app is a terminal application
    fn is_terminal_app(app_name: &str) -> bool {
        let app_lower = app_name.to_lowercase();

        // Check English terminal names
        for term in TERMINAL_APPS {
            if app_lower.contains(&term.to_lowercase()) {
                return true;
            }
        }

        // Check Russian terminal names
        for term in TERMINAL_APPS_RU {
            if app_name.contains(term) {
                return true;
            }
        }

        false
    }

    /// Check if the text contains error patterns
    fn contains_error_patterns(text: &str) -> bool {
        let text_lower = text.to_lowercase();

        for (pattern, _) in ERROR_PATTERNS {
            if text_lower.contains(&pattern.to_lowercase()) {
                return true;
            }
        }

        false
    }

    /// Extract npm package name from error text
    fn extract_npm_package(text: &str) -> Option<String> {
        // Pattern: Cannot find module 'package-name'
        if let Some(start) = text.find("Cannot find module '") {
            let after = &text[start + 20..];
            if let Some(end) = after.find('\'') {
                let module = &after[..end];
                // Skip relative paths
                if !module.starts_with('.') && !module.starts_with('/') {
                    // Extract base package name (before any /)
                    let package = module.split('/').next().unwrap_or(module);
                    return Some(package.to_string());
                }
            }
        }

        // Pattern: MODULE_NOT_FOUND ... 'package-name'
        if let Some(start) = text.find("MODULE_NOT_FOUND") {
            let after = &text[start..];
            if let Some(quote_start) = after.find('\'') {
                let after_quote = &after[quote_start + 1..];
                if let Some(quote_end) = after_quote.find('\'') {
                    let module = &after_quote[..quote_end];
                    if !module.starts_with('.') && !module.starts_with('/') {
                        let package = module.split('/').next().unwrap_or(module);
                        return Some(package.to_string());
                    }
                }
            }
        }

        None
    }

    /// Extract cargo crate name from error text
    fn extract_cargo_crate(text: &str) -> Option<String> {
        // Pattern: cannot find crate `crate_name`
        if let Some(start) = text.find("cannot find crate `") {
            let after = &text[start + 19..];
            if let Some(end) = after.find('`') {
                return Some(after[..end].to_string());
            }
        }

        // Pattern: use of undeclared crate or module `name`
        if let Some(start) = text.find("undeclared crate or module `") {
            let after = &text[start + 28..];
            if let Some(end) = after.find('`') {
                return Some(after[..end].to_string());
            }
        }

        None
    }

    /// Extract Python module name from error text
    fn extract_python_module(text: &str) -> Option<String> {
        // Pattern: No module named 'module_name'
        if let Some(start) = text.find("No module named '") {
            let after = &text[start + 17..];
            if let Some(end) = after.find('\'') {
                let module = &after[..end];
                // Get base module (before any .)
                let base = module.split('.').next().unwrap_or(module);
                return Some(base.to_string());
            }
        }

        // Pattern: ModuleNotFoundError: No module named 'X'
        if let Some(start) = text.find("ModuleNotFoundError: No module named '") {
            let after = &text[start + 38..];
            if let Some(end) = after.find('\'') {
                let module = &after[..end];
                let base = module.split('.').next().unwrap_or(module);
                return Some(base.to_string());
            }
        }

        None
    }

    /// Extract missing command name from error text
    fn extract_missing_command(text: &str) -> Option<String> {
        // Pattern: command not found: cmd
        if let Some(start) = text.find("command not found:") {
            let after = &text[start + 18..].trim();
            let cmd = after.split_whitespace().next()?;
            return Some(cmd.to_string());
        }

        // Pattern: zsh: command not found: cmd
        for shell in &["zsh:", "bash:", "sh:"] {
            if let Some(shell_start) = text.find(shell) {
                let after_shell = &text[shell_start + shell.len()..];
                if let Some(cnf_start) = after_shell.find("command not found:") {
                    let after = &after_shell[cnf_start + 18..].trim();
                    let cmd = after.split_whitespace().next()?;
                    return Some(cmd.to_string());
                }
            }
        }

        None
    }

    /// Get detailed error analysis
    pub fn get_error_details(&self, text: &str) -> Option<(ErrorType, String, String)> {
        if let Some(error_type) = self.analyze_error(text) {
            let suggested_fix = self.suggest_fix(&error_type, text);
            let description = match &error_type {
                ErrorType::NpmError => "Ошибка npm/Node.js".to_string(),
                ErrorType::CargoError => "Ошибка Cargo/Rust".to_string(),
                ErrorType::PythonError => "Ошибка Python/pip".to_string(),
                ErrorType::GitError => "Ошибка Git".to_string(),
                ErrorType::DockerError => "Ошибка Docker".to_string(),
                ErrorType::PermissionError => "Ошибка доступа".to_string(),
                ErrorType::CommandNotFound => "Команда не найдена".to_string(),
                ErrorType::ModuleNotFound => "Модуль не найден".to_string(),
                ErrorType::NetworkError => "Сетевая ошибка".to_string(),
                ErrorType::BuildError => "Ошибка сборки".to_string(),
                ErrorType::Unknown => "Неизвестная ошибка".to_string(),
            };
            return Some((error_type, description, suggested_fix));
        }
        None
    }
}

impl Default for DevOpsAgent {
    fn default() -> Self {
        Self::new()
    }
}

impl AgentType for DevOpsAgent {
    fn name(&self) -> &'static str {
        "DevOps"
    }

    fn system_prompt(&self) -> &str {
        &self.system_prompt
    }

    fn should_handle(&self, app_name: &str, text: &str) -> bool {
        // Must be a terminal application
        if !Self::is_terminal_app(app_name) {
            return false;
        }

        // Must contain error patterns
        Self::contains_error_patterns(text)
    }

    fn max_iterations(&self) -> u32 {
        5 // DevOps tasks usually need fewer iterations
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_terminal_app() {
        assert!(DevOpsAgent::is_terminal_app("Terminal"));
        assert!(DevOpsAgent::is_terminal_app("iTerm2"));
        assert!(DevOpsAgent::is_terminal_app("Warp"));
        assert!(DevOpsAgent::is_terminal_app("Alacritty"));
        assert!(DevOpsAgent::is_terminal_app("Терминал"));
        assert!(!DevOpsAgent::is_terminal_app("Safari"));
        assert!(!DevOpsAgent::is_terminal_app("VS Code"));
    }

    #[test]
    fn test_analyze_error_npm() {
        let agent = DevOpsAgent::new();

        let text = "npm ERR! missing dependency: lodash";
        assert_eq!(agent.analyze_error(text), Some(ErrorType::NpmError));

        let text = "Cannot find module 'express'";
        assert_eq!(agent.analyze_error(text), Some(ErrorType::NpmError));
    }

    #[test]
    fn test_analyze_error_python() {
        let agent = DevOpsAgent::new();

        let text = "ModuleNotFoundError: No module named 'requests'";
        assert_eq!(agent.analyze_error(text), Some(ErrorType::PythonError));

        let text = "ImportError: cannot import name 'Flask'";
        assert_eq!(agent.analyze_error(text), Some(ErrorType::PythonError));
    }

    #[test]
    fn test_analyze_error_cargo() {
        let agent = DevOpsAgent::new();

        let text = "error[E0432]: unresolved import `serde`";
        assert_eq!(agent.analyze_error(text), Some(ErrorType::CargoError));

        let text = "error: could not compile `my_project`";
        assert_eq!(agent.analyze_error(text), Some(ErrorType::CargoError));
    }

    #[test]
    fn test_analyze_error_git() {
        let agent = DevOpsAgent::new();

        let text = "fatal: not a git repository";
        assert_eq!(agent.analyze_error(text), Some(ErrorType::GitError));
    }

    #[test]
    fn test_analyze_error_permission() {
        let agent = DevOpsAgent::new();

        let text = "Permission denied: ./script.sh";
        assert_eq!(agent.analyze_error(text), Some(ErrorType::PermissionError));
    }

    #[test]
    fn test_analyze_error_command_not_found() {
        let agent = DevOpsAgent::new();

        let text = "zsh: command not found: node";
        assert_eq!(agent.analyze_error(text), Some(ErrorType::CommandNotFound));
    }

    #[test]
    fn test_should_handle() {
        let agent = DevOpsAgent::new();

        // Terminal with error - should handle
        assert!(agent.should_handle("Terminal", "npm ERR! missing dependency"));
        assert!(agent.should_handle("iTerm2", "ModuleNotFoundError: No module named 'flask'"));
        assert!(agent.should_handle("Warp", "error: could not compile"));

        // Terminal without error - should not handle
        assert!(!agent.should_handle("Terminal", "Build successful"));

        // Non-terminal with error - should not handle
        assert!(!agent.should_handle("Safari", "npm ERR! missing"));
        assert!(!agent.should_handle("VS Code", "error: something failed"));
    }

    #[test]
    fn test_suggest_fix_npm() {
        let agent = DevOpsAgent::new();

        let fix = agent.suggest_fix(&ErrorType::NpmError, "Cannot find module 'lodash'");
        assert_eq!(fix, "npm install lodash");

        let fix = agent.suggest_fix(&ErrorType::NpmError, "npm ERR! general error");
        assert_eq!(fix, "npm install");
    }

    #[test]
    fn test_suggest_fix_python() {
        let agent = DevOpsAgent::new();

        let fix = agent.suggest_fix(&ErrorType::PythonError, "No module named 'requests'");
        assert_eq!(fix, "pip install requests");
    }

    #[test]
    fn test_extract_npm_package() {
        let text = "Error: Cannot find module 'express'";
        assert_eq!(
            DevOpsAgent::extract_npm_package(text),
            Some("express".to_string())
        );

        let text = "Error: Cannot find module './local'";
        assert_eq!(DevOpsAgent::extract_npm_package(text), None);

        let text = "Error: Cannot find module '@types/node'";
        assert_eq!(
            DevOpsAgent::extract_npm_package(text),
            Some("@types".to_string())
        );
    }

    #[test]
    fn test_extract_python_module() {
        let text = "ModuleNotFoundError: No module named 'flask'";
        assert_eq!(
            DevOpsAgent::extract_python_module(text),
            Some("flask".to_string())
        );

        let text = "No module named 'sklearn.model_selection'";
        assert_eq!(
            DevOpsAgent::extract_python_module(text),
            Some("sklearn".to_string())
        );
    }

    #[test]
    fn test_extract_cargo_crate() {
        let text = "error: cannot find crate `tokio`";
        assert_eq!(
            DevOpsAgent::extract_cargo_crate(text),
            Some("tokio".to_string())
        );
    }

    #[test]
    fn test_extract_missing_command() {
        let text = "zsh: command not found: node";
        assert_eq!(
            DevOpsAgent::extract_missing_command(text),
            Some("node".to_string())
        );

        let text = "bash: command not found: python3";
        assert_eq!(
            DevOpsAgent::extract_missing_command(text),
            Some("python3".to_string())
        );
    }

    #[test]
    fn test_max_iterations() {
        let agent = DevOpsAgent::new();
        assert_eq!(agent.max_iterations(), 5);
    }

    #[test]
    fn test_get_error_details() {
        let agent = DevOpsAgent::new();

        let details = agent.get_error_details("npm ERR! missing dependency");
        assert!(details.is_some());
        let (error_type, desc, _fix) = details.unwrap();
        assert_eq!(error_type, ErrorType::NpmError);
        assert!(desc.contains("npm"));
    }
}
