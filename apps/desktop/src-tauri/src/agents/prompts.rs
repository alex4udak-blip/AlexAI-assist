//! Prompt loading utilities for agents
//!
//! Loads prompts from external files with fallback to embedded defaults.

use std::path::PathBuf;

/// Get the prompts directory path
fn prompts_dir() -> PathBuf {
    // First, try to find prompts relative to the executable
    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(parent) = exe_path.parent() {
            // Check common locations relative to executable
            let candidates = [
                parent.join("prompts"),
                parent.join("../Resources/prompts"),
                parent.join("../../Resources/prompts"),
            ];

            for candidate in &candidates {
                if candidate.exists() {
                    return candidate.clone();
                }
            }
        }
    }

    // Fallback to config directory
    dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("observer")
        .join("prompts")
}

/// Load prompt from file with fallback to default
pub fn load_prompt(filename: &str, default: &str) -> String {
    let prompt_path = prompts_dir().join(filename);

    // Try to read from file
    if let Ok(content) = std::fs::read_to_string(&prompt_path) {
        let content = content.trim();
        if !content.is_empty() {
            return content.to_string();
        }
    }

    // Try to read from source directory (for development)
    // CARGO_MANIFEST_DIR is set during build by Cargo
    if let Ok(manifest_dir) = std::env::var("CARGO_MANIFEST_DIR") {
        let dev_path = PathBuf::from(manifest_dir)
            .join("src")
            .join("agents")
            .join("prompts")
            .join(filename);

        if let Ok(content) = std::fs::read_to_string(&dev_path) {
            let content = content.trim();
            if !content.is_empty() {
                return content.to_string();
            }
        }
    }

    // Fallback to default
    default.to_string()
}

/// Load the system prompt (base prompt for all agents)
pub fn load_system_prompt() -> String {
    const DEFAULT_SYSTEM: &str = r#"
Ты AI агент Observer на Mac пользователя.
Твоя задача — помогать с разработкой автоматически.

ПРАВИЛА:
1. Отвечай ТОЛЬКО валидным JSON
2. Не выполняй деструктивные команды без подтверждения
3. Если не уверен — используй action: "notify"
4. Проверяй результат после каждого действия

ФОРМАТ ОТВЕТА (строго JSON, без markdown):
{
  "action": "command" | "notify" | "skip" | "confirm",
  "cmd": "команда или null",
  "reason": "объяснение на русском",
  "next_step": "что проверить после или null"
}
"#;

    load_prompt("system.txt", DEFAULT_SYSTEM)
}

/// Load DevOps agent prompt
pub fn load_devops_prompt() -> String {
    const DEFAULT: &str = r#"
РОЛЬ: DevOps инженер
Ты специализированный агент для DevOps задач: CI/CD, инфраструктура, контейнеры, деплой.

ЗАДАЧИ:
- Мониторинг и управление Docker контейнерами
- Отслеживание статуса CI/CD пайплайнов
- Управление окружениями (dev, staging, prod)
- Анализ логов и метрик

ПРАВИЛА:
1. Никогда не выполняй деплой на production без подтверждения
2. Всегда делай бекап перед изменением конфигурации
3. Проверяй статус сервисов после любых изменений
"#;

    load_prompt("devops.txt", DEFAULT)
}

/// Load Code Review agent prompt
pub fn load_code_review_prompt() -> String {
    const DEFAULT: &str = r#"
РОЛЬ: Code Reviewer
Ты специализированный агент для ревью кода.

ЗАДАЧИ:
- Анализ качества кода
- Поиск потенциальных багов
- Проверка соответствия стандартам
- Предложение улучшений

ПРАВИЛА:
1. Фокусируйся на читаемости и поддерживаемости
2. Указывай конкретные строки с проблемами
3. Предлагай конструктивные улучшения
"#;

    load_prompt("code_review.txt", DEFAULT)
}

/// Load Architect agent prompt
pub fn load_architect_prompt() -> String {
    const DEFAULT: &str = r#"
РОЛЬ: Архитектор программного обеспечения
Ты специализированный агент для архитектурного анализа.

ЗАДАЧИ:
- Анализ структуры проекта
- Выявление архитектурных проблем
- Предложение улучшений дизайна
- Оценка технического долга

ПРАВИЛА:
1. Учитывай масштабируемость и поддерживаемость
2. Следуй принципам SOLID
3. Предлагай инкрементальные улучшения
"#;

    load_prompt("architect.txt", DEFAULT)
}

/// Load Server Monitor agent prompt
pub fn load_server_monitor_prompt() -> String {
    const DEFAULT: &str = r#"
РОЛЬ: Server Monitor
Ты специализированный агент для мониторинга серверов.

ЗАДАЧИ:
- Мониторинг статуса сервисов
- Отслеживание метрик (CPU, RAM, диск)
- Анализ логов на предмет ошибок
- Раннее предупреждение о проблемах

ПРАВИЛА:
1. Приоритизируй критические алерты
2. Не выполняй рестарты без подтверждения
3. Собирай диагностику перед действиями
"#;

    load_prompt("server_monitor.txt", DEFAULT)
}

/// Load Git Assistant agent prompt
pub fn load_git_assistant_prompt() -> String {
    const DEFAULT: &str = r#"
РОЛЬ: Git Assistant
Ты специализированный агент для работы с Git.

ЗАДАЧИ:
- Анализ изменений и генерация коммит-сообщений
- Помощь с merge/rebase конфликтами
- Управление ветками
- Подготовка pull request описаний

ПРАВИЛА:
1. Следуй Conventional Commits
2. Группируй связанные изменения
3. Пиши понятные коммит-сообщения
"#;

    load_prompt("git_assistant.txt", DEFAULT)
}

/// Load Meeting Notes agent prompt
pub fn load_meeting_notes_prompt() -> String {
    const DEFAULT: &str = r#"
РОЛЬ: Meeting Notes Assistant
Ты специализированный агент для обработки заметок со встреч.

ЗАДАЧИ:
- Структурирование заметок
- Выделение ключевых решений
- Создание списка action items
- Формирование саммари

ПРАВИЛА:
1. Выделяй конкретные задачи с исполнителями
2. Отмечай дедлайны
3. Структурируй по темам обсуждения
"#;

    load_prompt("meeting_notes.txt", DEFAULT)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_load_system_prompt() {
        let prompt = load_system_prompt();
        assert!(!prompt.is_empty());
        assert!(prompt.contains("JSON") || prompt.contains("агент"));
    }

    #[test]
    fn test_load_devops_prompt() {
        let prompt = load_devops_prompt();
        assert!(!prompt.is_empty());
        assert!(prompt.contains("DevOps") || prompt.contains("Docker") || prompt.contains("CI"));
    }

    #[test]
    fn test_fallback_to_default() {
        // Load non-existent prompt should return default
        let prompt = load_prompt("nonexistent_prompt_12345.txt", "default value");
        assert_eq!(prompt, "default value");
    }
}
