//! Architect Agent
//!
//! Responsible for:
//! - Project architecture verification
//! - File structure analysis
//! - Code organization suggestions

use super::AgentType;
use crate::agents::prompts;
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;

/// IDE applications that the Architect Agent monitors
const IDE_APPS: &[&str] = &[
    "Code", // VS Code
    "Visual Studio Code",
    "Cursor",         // Cursor IDE
    "Xcode",          // Apple Xcode
    "IntelliJ",       // JetBrains IntelliJ IDEA
    "WebStorm",       // JetBrains WebStorm
    "PyCharm",        // JetBrains PyCharm
    "RustRover",      // JetBrains RustRover
    "CLion",          // JetBrains CLion
    "GoLand",         // JetBrains GoLand
    "Android Studio", // Google Android Studio
    "Sublime",        // Sublime Text
    "Atom",           // Atom (deprecated but still used)
    "Neovim",         // Neovim
    "Vim",            // Vim
    "Emacs",          // Emacs
    "Nova",           // Panic Nova (macOS)
    "Zed",            // Zed editor
];

/// Patterns indicating file/module creation
const CREATE_PATTERNS: &[&str] = &[
    "new file",
    "create",
    "mkdir",
    "touch",
    "add file",
    "adding",
    "created",
    "new module",
    "new component",
    "generate",
    "scaffold",
    "init",
    "initialize",
];

/// Architect Agent for project structure analysis
pub struct ArchitectAgent {
    /// System prompt for this agent
    system_prompt: String,
    /// Compiled regex patterns for detection
    create_patterns: Vec<Regex>,
}

impl ArchitectAgent {
    /// Create a new ArchitectAgent with default system prompt
    pub fn new() -> Self {
        let create_patterns = CREATE_PATTERNS
            .iter()
            .filter_map(|p| Regex::new(&format!(r"(?i){}", regex::escape(p))).ok())
            .collect();

        Self {
            system_prompt: prompts::load_architect_prompt(),
            create_patterns,
        }
    }

    /// Create ArchitectAgent with custom system prompt
    pub fn with_system_prompt(system_prompt: String) -> Self {
        let create_patterns = CREATE_PATTERNS
            .iter()
            .filter_map(|p| Regex::new(&format!(r"(?i){}", regex::escape(p))).ok())
            .collect();

        Self {
            system_prompt,
            create_patterns,
        }
    }

    /// Check if the text contains file/module creation patterns
    fn contains_create_pattern(&self, text: &str) -> bool {
        self.create_patterns.iter().any(|p| p.is_match(text))
    }

    /// Check if the app is an IDE
    fn is_ide_app(app_name: &str) -> bool {
        IDE_APPS
            .iter()
            .any(|ide| app_name.to_lowercase().contains(&ide.to_lowercase()))
    }

    /// Analyze project structure at the given path
    pub fn analyze_project_structure(&self, path: &str) -> ProjectStructure {
        let path = Path::new(path);

        if !path.exists() || !path.is_dir() {
            return ProjectStructure::default();
        }

        let mut structure = ProjectStructure {
            root_path: path.to_string_lossy().to_string(),
            project_type: Self::detect_project_type(path),
            modules: Vec::new(),
            config_files: Vec::new(),
            entry_points: Vec::new(),
            file_count: 0,
            line_count: 0,
        };

        // Scan directory structure
        if let Ok(entries) = std::fs::read_dir(path) {
            for entry in entries.flatten() {
                let entry_path = entry.path();
                let file_name = entry.file_name().to_string_lossy().to_string();

                if entry_path.is_file() {
                    structure.file_count += 1;

                    // Detect config files
                    if Self::is_config_file(&file_name) {
                        structure.config_files.push(file_name.clone());
                    }

                    // Detect entry points
                    if Self::is_entry_point(&file_name) {
                        structure.entry_points.push(file_name.clone());
                    }
                } else if entry_path.is_dir() && !file_name.starts_with('.') {
                    // Analyze module
                    if let Some(module_info) = self.analyze_module(&entry_path, &file_name) {
                        structure.modules.push(module_info);
                    }
                }
            }
        }

        structure
    }

    /// Analyze a module/directory
    fn analyze_module(&self, path: &Path, name: &str) -> Option<ModuleInfo> {
        let mut module = ModuleInfo {
            name: name.to_string(),
            path: path.to_string_lossy().to_string(),
            file_count: 0,
            children: Vec::new(),
            has_docs: false,
            has_tests: false,
        };

        if let Ok(entries) = std::fs::read_dir(path) {
            for entry in entries.flatten() {
                let entry_path = entry.path();
                let file_name = entry.file_name().to_string_lossy().to_string();

                if entry_path.is_file() {
                    module.file_count += 1;

                    // Check for docs
                    if file_name == "README.md" || file_name.ends_with(".md") {
                        module.has_docs = true;
                    }

                    // Check for tests
                    if file_name.contains("test") || file_name.contains("spec") {
                        module.has_tests = true;
                    }
                } else if entry_path.is_dir() && !file_name.starts_with('.') {
                    module.children.push(file_name.clone());

                    // Check for tests directory
                    if file_name == "tests" || file_name == "__tests__" || file_name == "test" {
                        module.has_tests = true;
                    }
                }
            }
        }

        Some(module)
    }

    /// Detect project type based on config files
    fn detect_project_type(path: &Path) -> ProjectType {
        let markers = [
            ("Cargo.toml", ProjectType::Rust),
            ("package.json", ProjectType::TypeScript), // Could also be JS
            ("pyproject.toml", ProjectType::Python),
            ("setup.py", ProjectType::Python),
            ("go.mod", ProjectType::Go),
            ("Package.swift", ProjectType::Swift),
            ("tsconfig.json", ProjectType::TypeScript),
        ];

        let mut detected_types = Vec::new();

        for (marker, project_type) in markers {
            if path.join(marker).exists() {
                detected_types.push(project_type);
            }
        }

        match detected_types.len() {
            0 => ProjectType::Unknown,
            1 => detected_types.into_iter().next().unwrap(),
            _ => ProjectType::Mixed,
        }
    }

    /// Check if file is a config file
    fn is_config_file(name: &str) -> bool {
        let config_patterns = [
            "Cargo.toml",
            "package.json",
            "tsconfig.json",
            "pyproject.toml",
            "go.mod",
            ".env",
            ".gitignore",
            "Dockerfile",
            "docker-compose",
            "Makefile",
            "CMakeLists.txt",
            ".eslintrc",
            ".prettierrc",
            "jest.config",
            "vitest.config",
            "vite.config",
            "webpack.config",
            "tauri.conf.json",
            "next.config",
            "nuxt.config",
        ];

        config_patterns.iter().any(|p| name.contains(p))
    }

    /// Check if file is an entry point
    fn is_entry_point(name: &str) -> bool {
        let entry_patterns = [
            "main.rs",
            "lib.rs",
            "mod.rs",
            "index.ts",
            "index.js",
            "main.ts",
            "main.js",
            "app.ts",
            "app.js",
            "App.tsx",
            "App.jsx",
            "__init__.py",
            "main.py",
            "app.py",
            "main.go",
            "cmd/",
            "main.swift",
            "App.swift",
        ];

        entry_patterns
            .iter()
            .any(|p| name == *p || name.starts_with(p))
    }

    /// Check file conventions and return suggestions
    pub fn check_conventions(&self, file_path: &str) -> Vec<Suggestion> {
        let path = Path::new(file_path);
        let mut suggestions = Vec::new();

        if !path.exists() {
            return suggestions;
        }

        let file_name = path
            .file_name()
            .map(|n| n.to_string_lossy().to_string())
            .unwrap_or_default();

        let extension = path
            .extension()
            .map(|e| e.to_string_lossy().to_string())
            .unwrap_or_default();

        // Check naming conventions
        suggestions.extend(self.check_naming_conventions(&file_name, &extension));

        // Check location conventions
        suggestions.extend(self.check_location_conventions(path, &extension));

        // Check for missing documentation
        suggestions.extend(self.check_documentation(path, &extension));

        // Check for missing tests
        suggestions.extend(self.check_tests(path, &extension));

        suggestions
    }

    /// Check naming conventions
    fn check_naming_conventions(&self, file_name: &str, extension: &str) -> Vec<Suggestion> {
        let mut suggestions = Vec::new();

        match extension {
            "rs" => {
                // Rust files should be snake_case
                if file_name.chars().any(|c| c.is_uppercase()) && file_name != "Cargo.toml" {
                    suggestions.push(Suggestion {
                        suggestion_type: SuggestionType::NamingConvention,
                        file_path: file_name.to_string(),
                        description: "Rust files should use snake_case naming".to_string(),
                        severity: Severity::Warning,
                        proposed_fix: Some(file_name.to_lowercase()),
                    });
                }
            }
            "ts" | "tsx" | "js" | "jsx" => {
                // React components should be PascalCase
                if extension.ends_with("x")
                    && !file_name.chars().next().is_some_and(|c| c.is_uppercase())
                {
                    if !file_name.starts_with("index") && !file_name.starts_with("use") {
                        suggestions.push(Suggestion {
                            suggestion_type: SuggestionType::NamingConvention,
                            file_path: file_name.to_string(),
                            description: "React component files should use PascalCase".to_string(),
                            severity: Severity::Info,
                            proposed_fix: None,
                        });
                    }
                }
            }
            "py" => {
                // Python files should be snake_case
                if file_name.chars().any(|c| c.is_uppercase()) {
                    suggestions.push(Suggestion {
                        suggestion_type: SuggestionType::NamingConvention,
                        file_path: file_name.to_string(),
                        description: "Python files should use snake_case naming".to_string(),
                        severity: Severity::Warning,
                        proposed_fix: Some(file_name.to_lowercase()),
                    });
                }
            }
            _ => {}
        }

        suggestions
    }

    /// Check location conventions
    fn check_location_conventions(&self, path: &Path, extension: &str) -> Vec<Suggestion> {
        let mut suggestions = Vec::new();
        let path_str = path.to_string_lossy().to_string();

        // Test files should be in appropriate locations
        let file_name = path
            .file_name()
            .map(|n| n.to_string_lossy().to_string())
            .unwrap_or_default();

        if file_name.contains("test") || file_name.contains("spec") {
            let in_test_dir = path_str.contains("/tests/")
                || path_str.contains("/__tests__/")
                || path_str.contains("/test/");

            if !in_test_dir && !path_str.contains(".test.") && !path_str.contains(".spec.") {
                suggestions.push(Suggestion {
                    suggestion_type: SuggestionType::WrongLocation,
                    file_path: path_str.clone(),
                    description:
                        "Test files should be in tests/ directory or use .test/.spec suffix"
                            .to_string(),
                    severity: Severity::Info,
                    proposed_fix: None,
                });
            }
        }

        // Type definitions should be in types/ or @types/
        if extension == "d.ts" {
            if !path_str.contains("/types/") && !path_str.contains("/@types/") {
                suggestions.push(Suggestion {
                    suggestion_type: SuggestionType::WrongLocation,
                    file_path: path_str,
                    description: "TypeScript declaration files should be in types/ directory"
                        .to_string(),
                    severity: Severity::Hint,
                    proposed_fix: None,
                });
            }
        }

        suggestions
    }

    /// Check for missing documentation
    fn check_documentation(&self, path: &Path, extension: &str) -> Vec<Suggestion> {
        let mut suggestions = Vec::new();

        // Check if this looks like a module directory
        if path.is_dir() {
            let has_readme = path.join("README.md").exists();
            let file_count = std::fs::read_dir(path)
                .map(|entries| entries.count())
                .unwrap_or(0);

            // Modules with more than 3 files should have docs
            if !has_readme && file_count > 3 {
                suggestions.push(Suggestion {
                    suggestion_type: SuggestionType::MissingDocs,
                    file_path: path.to_string_lossy().to_string(),
                    description: "Module has multiple files but no README.md".to_string(),
                    severity: Severity::Hint,
                    proposed_fix: Some("Add README.md with module description".to_string()),
                });
            }
        }

        // Check for module files without doc comments
        let module_files = ["mod.rs", "lib.rs", "index.ts", "index.js", "__init__.py"];
        let file_name = path
            .file_name()
            .map(|n| n.to_string_lossy().to_string())
            .unwrap_or_default();

        if module_files.contains(&file_name.as_str()) {
            if let Ok(content) = std::fs::read_to_string(path) {
                let has_doc_comment = match extension {
                    "rs" => content.starts_with("//!") || content.contains("\n//!"),
                    "ts" | "js" => content.starts_with("/**") || content.starts_with("//"),
                    "py" => content.starts_with("\"\"\"") || content.starts_with("'''"),
                    _ => true,
                };

                if !has_doc_comment && content.len() > 100 {
                    suggestions.push(Suggestion {
                        suggestion_type: SuggestionType::MissingDocs,
                        file_path: path.to_string_lossy().to_string(),
                        description: "Module file lacks documentation comment".to_string(),
                        severity: Severity::Info,
                        proposed_fix: Some("Add module-level documentation".to_string()),
                    });
                }
            }
        }

        suggestions
    }

    /// Check for missing tests
    fn check_tests(&self, path: &Path, extension: &str) -> Vec<Suggestion> {
        let mut suggestions = Vec::new();

        // Skip if this is already a test file
        let file_name = path
            .file_name()
            .map(|n| n.to_string_lossy().to_string())
            .unwrap_or_default();

        if file_name.contains("test") || file_name.contains("spec") {
            return suggestions;
        }

        // Check for corresponding test file
        let test_exists = match extension {
            "rs" => {
                // Rust: check for mod tests in file or tests/ directory
                if let Ok(content) = std::fs::read_to_string(path) {
                    content.contains("#[cfg(test)]") || content.contains("mod tests")
                } else {
                    false
                }
            }
            "ts" | "js" | "tsx" | "jsx" => {
                // TypeScript/JavaScript: check for .test.ts or .spec.ts
                let parent = path.parent();
                let stem = path
                    .file_stem()
                    .map(|s| s.to_string_lossy().to_string())
                    .unwrap_or_default();

                if let Some(parent) = parent {
                    parent.join(format!("{}.test.{}", stem, extension)).exists()
                        || parent.join(format!("{}.spec.{}", stem, extension)).exists()
                        || parent.join("__tests__").join(&file_name).exists()
                } else {
                    false
                }
            }
            "py" => {
                // Python: check for test_*.py or *_test.py
                let parent = path.parent();
                let stem = path
                    .file_stem()
                    .map(|s| s.to_string_lossy().to_string())
                    .unwrap_or_default();

                if let Some(parent) = parent {
                    parent.join(format!("test_{}.py", stem)).exists()
                        || parent.join(format!("{}_test.py", stem)).exists()
                        || parent
                            .join("tests")
                            .join(format!("test_{}.py", stem))
                            .exists()
                } else {
                    false
                }
            }
            _ => true, // Skip other extensions
        };

        // Only suggest for substantial files
        if !test_exists {
            if let Ok(content) = std::fs::read_to_string(path) {
                let line_count = content.lines().count();
                if line_count > 50 {
                    suggestions.push(Suggestion {
                        suggestion_type: SuggestionType::MissingTests,
                        file_path: path.to_string_lossy().to_string(),
                        description: format!(
                            "File has {} lines but no corresponding tests",
                            line_count
                        ),
                        severity: Severity::Warning,
                        proposed_fix: Some("Add unit tests for this module".to_string()),
                    });
                }
            }
        }

        suggestions
    }

    /// Get all suggestions for a project
    pub fn analyze_project(&self, root_path: &str) -> ArchitectAnalysis {
        let structure = self.analyze_project_structure(root_path);
        let mut all_suggestions = Vec::new();
        let mut module_analysis = HashMap::new();

        // Analyze each module
        for module in &structure.modules {
            let suggestions = self.check_conventions(&module.path);
            if !suggestions.is_empty() {
                module_analysis.insert(module.name.clone(), suggestions.clone());
                all_suggestions.extend(suggestions);
            }
        }

        ArchitectAnalysis {
            structure,
            suggestions: all_suggestions,
            module_analysis,
        }
    }
}

impl Default for ArchitectAgent {
    fn default() -> Self {
        Self::new()
    }
}

impl AgentType for ArchitectAgent {
    fn name(&self) -> &'static str {
        "Architect"
    }

    fn system_prompt(&self) -> &str {
        &self.system_prompt
    }

    fn should_handle(&self, app_name: &str, text: &str) -> bool {
        // Check if working in IDE
        if Self::is_ide_app(app_name) {
            // Check for file/module creation patterns
            if self.contains_create_pattern(text) {
                return true;
            }
        }

        // Also trigger on explicit architecture keywords
        let architecture_keywords = [
            "refactor",
            "reorganize",
            "restructure",
            "architecture",
            "module structure",
        ];

        architecture_keywords
            .iter()
            .any(|kw| text.to_lowercase().contains(kw))
    }

    fn max_iterations(&self) -> u32 {
        5 // Architecture analysis usually needs fewer iterations
    }

    fn priority(&self) -> u32 {
        50 // Medium-high priority for architecture decisions
    }
}

/// Full project analysis result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArchitectAnalysis {
    /// Project structure
    pub structure: ProjectStructure,
    /// All suggestions
    pub suggestions: Vec<Suggestion>,
    /// Suggestions grouped by module
    pub module_analysis: HashMap<String, Vec<Suggestion>>,
}

/// Project structure information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectStructure {
    /// Project root path
    pub root_path: String,
    /// Detected project type
    pub project_type: ProjectType,
    /// List of modules/directories
    pub modules: Vec<ModuleInfo>,
    /// Configuration files found
    pub config_files: Vec<String>,
    /// Entry points
    pub entry_points: Vec<String>,
    /// Total file count
    pub file_count: usize,
    /// Total line count (estimated)
    pub line_count: usize,
}

impl Default for ProjectStructure {
    fn default() -> Self {
        Self {
            root_path: String::new(),
            project_type: ProjectType::Unknown,
            modules: Vec::new(),
            config_files: Vec::new(),
            entry_points: Vec::new(),
            file_count: 0,
            line_count: 0,
        }
    }
}

/// Type of project
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ProjectType {
    Rust,
    TypeScript,
    JavaScript,
    Python,
    Go,
    Swift,
    Mixed,
    Unknown,
}

/// Information about a module/directory
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModuleInfo {
    /// Module name
    pub name: String,
    /// Path relative to project root
    pub path: String,
    /// Number of files
    pub file_count: usize,
    /// Child modules
    pub children: Vec<String>,
    /// Has documentation
    pub has_docs: bool,
    /// Has tests
    pub has_tests: bool,
}

/// Suggestion for code improvement
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Suggestion {
    /// Type of suggestion
    pub suggestion_type: SuggestionType,
    /// File path this suggestion applies to
    pub file_path: String,
    /// Description of the suggestion
    pub description: String,
    /// Severity level
    pub severity: Severity,
    /// Proposed fix (if available)
    pub proposed_fix: Option<String>,
}

/// Types of suggestions
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SuggestionType {
    /// File is in wrong directory
    WrongLocation,
    /// Missing documentation
    MissingDocs,
    /// Naming convention violation
    NamingConvention,
    /// Missing tests
    MissingTests,
    /// Circular dependency detected
    CircularDependency,
    /// File too large
    FileTooLarge,
    /// Missing module export
    MissingExport,
    /// Unused code
    UnusedCode,
    /// Architecture violation
    ArchitectureViolation,
}

/// Severity levels for suggestions
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
pub enum Severity {
    /// Just a hint
    Hint,
    /// Informational
    Info,
    /// Warning - should be addressed
    Warning,
    /// Error - must be addressed
    Error,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_architect_agent_creation() {
        let agent = ArchitectAgent::new();
        assert_eq!(agent.name(), "Architect");
        assert!(!agent.system_prompt().is_empty());
    }

    #[test]
    fn test_should_handle_ide_with_create() {
        let agent = ArchitectAgent::new();
        assert!(agent.should_handle("Visual Studio Code", "Creating new file..."));
        assert!(agent.should_handle("Cursor", "mkdir src/components"));
        assert!(agent.should_handle("IntelliJ IDEA", "New module created"));
    }

    #[test]
    fn test_should_not_handle_non_ide() {
        let agent = ArchitectAgent::new();
        assert!(!agent.should_handle("Safari", "Creating new file"));
        assert!(!agent.should_handle("Chrome", "mkdir test"));
    }

    #[test]
    fn test_should_handle_architecture_keywords() {
        let agent = ArchitectAgent::new();
        assert!(agent.should_handle("Terminal", "refactor the module structure"));
        assert!(agent.should_handle("Any App", "architecture review needed"));
    }

    #[test]
    fn test_is_ide_app() {
        assert!(ArchitectAgent::is_ide_app("Visual Studio Code"));
        assert!(ArchitectAgent::is_ide_app("code"));
        assert!(ArchitectAgent::is_ide_app("Cursor"));
        assert!(ArchitectAgent::is_ide_app("Xcode"));
        assert!(ArchitectAgent::is_ide_app("IntelliJ IDEA"));
        assert!(!ArchitectAgent::is_ide_app("Safari"));
        assert!(!ArchitectAgent::is_ide_app("Chrome"));
    }

    #[test]
    fn test_contains_create_pattern() {
        let agent = ArchitectAgent::new();
        assert!(agent.contains_create_pattern("new file created"));
        assert!(agent.contains_create_pattern("mkdir src/test"));
        assert!(agent.contains_create_pattern("Creating component..."));
        assert!(!agent.contains_create_pattern("editing file"));
    }

    #[test]
    fn test_project_structure_default() {
        let structure = ProjectStructure::default();
        assert!(structure.root_path.is_empty());
        assert!(matches!(structure.project_type, ProjectType::Unknown));
        assert!(structure.modules.is_empty());
    }

    #[test]
    fn test_severity_ordering() {
        assert!(Severity::Hint < Severity::Info);
        assert!(Severity::Info < Severity::Warning);
        assert!(Severity::Warning < Severity::Error);
    }

    #[test]
    fn test_naming_conventions_rust() {
        let agent = ArchitectAgent::new();
        let suggestions = agent.check_naming_conventions("MyFile.rs", "rs");
        assert!(!suggestions.is_empty());
        assert!(matches!(
            suggestions[0].suggestion_type,
            SuggestionType::NamingConvention
        ));
    }

    #[test]
    fn test_naming_conventions_rust_valid() {
        let agent = ArchitectAgent::new();
        let suggestions = agent.check_naming_conventions("my_file.rs", "rs");
        assert!(suggestions.is_empty());
    }
}
