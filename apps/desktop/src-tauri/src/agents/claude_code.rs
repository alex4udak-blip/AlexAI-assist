//! Claude Code CLI integration
//!
//! Provides functions to call Claude Code CLI and execute commands.

use serde::{Deserialize, Serialize};
use std::process::Command;

/// Safely truncate string to max chars (handles UTF-8 properly)
fn truncate_str(s: &str, max_chars: usize) -> &str {
    match s.char_indices().nth(max_chars) {
        Some((idx, _)) => &s[..idx],
        None => s,
    }
}

/// Dangerous command patterns that require confirmation
const DANGEROUS_PATTERNS: &[&str] = &[
    "rm -rf",
    "rm -r /",
    "sudo rm",
    "mkfs",
    "dd if=",
    "> /dev/",
    "chmod 000",
    "chmod 777",
    ":(){:|:&};:",  // fork bomb
    "mv /* ",
    "wget | sh",
    "curl | sh",
    ":(){ :|:& };:",
];

/// Response from Claude agent
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentResponse {
    /// Action to take: "command", "notify", "skip", "confirm"
    pub action: String,
    /// Shell command to execute (if action is "command")
    pub cmd: Option<String>,
    /// Explanation of the action
    pub reason: String,
    /// What to check after execution
    #[serde(default)]
    pub next_step: Option<String>,
}

/// System prompt for Claude agents
const SYSTEM_PROMPT: &str = r#"
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

/// Call Claude Code CLI with a prompt
pub async fn ask_claude(prompt: &str, claude_path: &str) -> Result<AgentResponse, String> {
    let full_prompt = format!("{}\n\nКОНТЕКСТ:\n{}", SYSTEM_PROMPT, prompt);
    let claude_path = claude_path.to_string(); // Clone for 'static lifetime

    println!("[Claude] Calling with prompt: {}...", truncate_str(prompt, 100));

    // Call Claude CLI
    let output = tokio::task::spawn_blocking(move || {
        Command::new(&claude_path)
            .arg("-p")
            .arg(&full_prompt)
            .output()
    })
    .await
    .map_err(|e| format!("Ошибка выполнения задачи: {}", e))?
    .map_err(|e| format!("Не удалось запустить Claude CLI: {}", e))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Ошибка Claude CLI: {}", stderr));
    }

    let response_text = String::from_utf8_lossy(&output.stdout).to_string();
    println!("[Claude] Raw response ({}): {}", response_text.len(), truncate_str(&response_text, 200));

    // Parse JSON response
    parse_agent_response(&response_text)
}

/// Parse Claude response to AgentResponse
fn parse_agent_response(text: &str) -> Result<AgentResponse, String> {
    // Try to extract JSON from response (may have markdown code blocks)
    let json_str = extract_json(text)?;

    serde_json::from_str(&json_str)
        .map_err(|e| format!("Не удалось распарсить JSON: {} - текст: {}", e, json_str))
}

/// Extract JSON from text (handles markdown code blocks)
fn extract_json(text: &str) -> Result<String, String> {
    let text = text.trim();

    // Try direct parse first
    if text.starts_with('{') {
        if let Some(end) = find_json_end(text) {
            return Ok(text[..=end].to_string());
        }
    }

    // Try to find JSON in code block
    if let Some(start) = text.find("```json") {
        let after_start = &text[start + 7..];
        if let Some(end) = after_start.find("```") {
            return Ok(after_start[..end].trim().to_string());
        }
    }

    // Try to find JSON in generic code block
    if let Some(start) = text.find("```") {
        let after_start = &text[start + 3..];
        // Skip language identifier if present
        let json_start = after_start.find('{').unwrap_or(0);
        if let Some(end) = after_start[json_start..].find("```") {
            let json_text = &after_start[json_start..json_start + end];
            return Ok(json_text.trim().to_string());
        }
    }

    // Try to find bare JSON object
    if let Some(start) = text.find('{') {
        if let Some(end) = find_json_end(&text[start..]) {
            return Ok(text[start..=start + end].to_string());
        }
    }

    Err(format!("JSON не найден в ответе: {}", truncate_str(text, 200)))
}

/// Find the closing brace of a JSON object
fn find_json_end(text: &str) -> Option<usize> {
    let mut depth = 0;
    let mut in_string = false;
    let mut escape_next = false;

    for (i, c) in text.char_indices() {
        if escape_next {
            escape_next = false;
            continue;
        }

        match c {
            '\\' if in_string => escape_next = true,
            '"' => in_string = !in_string,
            '{' if !in_string => depth += 1,
            '}' if !in_string => {
                depth -= 1;
                if depth == 0 {
                    return Some(i);
                }
            }
            _ => {}
        }
    }

    None
}

/// Check if command is potentially dangerous
fn is_dangerous_command(cmd: &str) -> Option<&'static str> {
    let cmd_lower = cmd.to_lowercase();
    for pattern in DANGEROUS_PATTERNS {
        if cmd_lower.contains(&pattern.to_lowercase()) {
            return Some(pattern);
        }
    }
    None
}

/// Execute a shell command with safety checks
pub async fn execute_command(cmd: &str) -> Result<String, String> {
    // Safety check: block dangerous commands
    if let Some(pattern) = is_dangerous_command(cmd) {
        return Err(format!(
            "Опасная команда заблокирована: обнаружен паттерн '{}'. Требуется подтверждение пользователя.",
            pattern
        ));
    }

    println!("[Execute] Running: {}", cmd);

    let output = tokio::task::spawn_blocking({
        let cmd = cmd.to_string();
        move || {
            Command::new("sh")
                .arg("-c")
                .arg(&cmd)
                .output()
        }
    })
    .await
    .map_err(|e| format!("Ошибка выполнения задачи: {}", e))?
    .map_err(|e| format!("Не удалось выполнить команду: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();

    if !output.status.success() {
        println!("[Execute] Command failed: {}", stderr);
        return Err(format!("Команда завершилась с ошибкой: {}\n{}", stderr, stdout));
    }

    println!("[Execute] Success: {}...", truncate_str(&stdout, 100));
    Ok(format!("{}\n{}", stdout, stderr))
}

/// Result of agent task execution
#[derive(Debug, Clone)]
pub struct AgentTaskResult {
    pub iterations: u32,
    pub final_action: String,
    pub reason: String,
    pub needs_notification: bool,
    pub needs_confirmation: bool,
    pub output: String,
}

/// Run agent task with iterative loop
pub async fn run_agent_task(
    initial_context: &str,
    max_iterations: u32,
    claude_path: &str,
) -> Result<AgentTaskResult, String> {
    let mut context = initial_context.to_string();
    let mut iteration = 0;
    let mut results = Vec::new();
    let mut needs_notification = false;
    let mut needs_confirmation = false;
    let mut final_action = String::new();
    let mut final_reason = String::new();

    println!("[Agent] Starting task with max {} iterations", max_iterations);

    while iteration < max_iterations {
        iteration += 1;
        println!("[Agent] Iteration {}/{}", iteration, max_iterations);

        // Ask Claude what to do
        let response = ask_claude(&context, claude_path).await?;
        results.push(format!("Iteration {}: {:?}", iteration, response));
        final_action = response.action.clone();
        final_reason = response.reason.clone();

        match response.action.as_str() {
            "skip" => {
                println!("[Agent] Skipping: {}", response.reason);
                break;
            }
            "notify" => {
                println!("[Agent] Notification: {}", response.reason);
                needs_notification = true;
                break;
            }
            "confirm" => {
                println!("[Agent] Needs confirmation: {}", response.reason);
                needs_confirmation = true;
                break;
            }
            "command" => {
                if let Some(cmd) = &response.cmd {
                    // Execute command
                    match execute_command(cmd).await {
                        Ok(output) => {
                            // Update context with result
                            context = format!(
                                "{}\n\nПредыдущее действие:\nКоманда: {}\nРезультат: {}\n\nЧто дальше?",
                                context, cmd, output
                            );
                        }
                        Err(e) => {
                            // Update context with error
                            context = format!(
                                "{}\n\nПредыдущее действие:\nКоманда: {}\nОшибка: {}\n\nКак исправить?",
                                context, cmd, e
                            );
                        }
                    }
                } else {
                    println!("[Agent] Command action but no cmd provided");
                    break;
                }
            }
            _ => {
                println!("[Agent] Unknown action: {}", response.action);
                break;
            }
        }

        // Check next_step if provided
        if let Some(next) = &response.next_step {
            context = format!("{}\n\nПроверь: {}", context, next);
        }
    }

    if iteration >= max_iterations {
        println!("[Agent] Reached max iterations");
    }

    Ok(AgentTaskResult {
        iterations: iteration,
        final_action,
        reason: final_reason,
        needs_notification,
        needs_confirmation,
        output: results.join("\n"),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_json_direct() {
        let text = r#"{"action": "skip", "reason": "test"}"#;
        let result = extract_json(text);
        assert!(result.is_ok());
    }

    #[test]
    fn test_extract_json_code_block() {
        let text = r#"Here is my response:
```json
{"action": "skip", "reason": "test"}
```
Done!"#;
        let result = extract_json(text);
        assert!(result.is_ok());
        assert!(result.unwrap().contains("skip"));
    }

    #[test]
    fn test_parse_agent_response() {
        let json = r#"{"action": "command", "cmd": "ls -la", "reason": "List files"}"#;
        let result = parse_agent_response(json);
        assert!(result.is_ok());
        let response = result.unwrap();
        assert_eq!(response.action, "command");
        assert_eq!(response.cmd, Some("ls -la".to_string()));
    }
}
