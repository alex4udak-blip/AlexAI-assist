# Custom Automation Commands Implementation

## Overview

This document describes the implementation of custom automation commands in the Observer desktop app. The stub implementation has been replaced with a full-featured system that supports shell commands, AppleScript, and HTTP requests.

## Location

**File**: `/home/user/AlexAI-assist/apps/desktop/src-tauri/src/automation/queue.rs`

## Changes Made

### 1. Added Required Imports

```rust
use tokio::time::{Duration, sleep, timeout};
use tokio::process::Command;
use regex::Regex;
```

### 2. Added Timeout Constant

```rust
const CUSTOM_COMMAND_TIMEOUT: Duration = Duration::from_secs(30);
```

### 3. Created Custom Commands Module

A new internal module `custom_commands` with the following functions:

#### `sanitize_command(cmd: &str) -> Result<String, String>`
- Validates shell commands to prevent injection attacks
- Checks for dangerous patterns: command chaining (`;`, `|`), command substitution (`$()`, `` ` ``), directory traversal (`../`), redirects
- Rejects empty commands

#### `sanitize_param(param: &str) -> Result<String, String>`
- Validates parameter values
- Checks for null bytes
- Enforces maximum length of 10,000 characters

#### `execute_shell_command(command: &str, args: Vec<String>) -> Result<String, String>`
- Executes shell commands with proper platform detection
- Uses `sh -c` on Unix/Linux/macOS
- Uses `cmd /C` on Windows
- Implements 30-second timeout
- Captures stdout/stderr
- Logs execution details

#### `execute_applescript(script: &str) -> Result<String, String>`
- Executes AppleScript using `osascript` (macOS only)
- Returns error on non-macOS platforms
- Implements timeout and length validation
- Logs execution details

### 4. Implemented `execute_custom_command` Method

A comprehensive method that supports three types of custom commands:

#### Shell Command

Executes shell commands with argument support.

**Parameters:**
```json
{
  "name": "shell",
  "params": {
    "command": "ls",
    "args": ["-la", "/tmp"]
  }
}
```

**Returns:**
```json
{
  "output": "command output here",
  "type": "shell"
}
```

#### AppleScript (macOS only)

Executes AppleScript code.

**Parameters:**
```json
{
  "name": "applescript",
  "params": {
    "script": "tell application \"Safari\" to get URL of current tab of front window"
  }
}
```

**Returns:**
```json
{
  "output": "https://example.com",
  "type": "applescript"
}
```

#### HTTP Request

Makes HTTP requests with full control over method, headers, and body.

**Parameters:**
```json
{
  "name": "http_request",
  "params": {
    "url": "https://api.example.com/data",
    "method": "POST",
    "headers": {
      "Authorization": "Bearer token123",
      "Content-Type": "application/json"
    },
    "body": {
      "key": "value"
    }
  }
}
```

**Returns:**
```json
{
  "status": 200,
  "body": "response body here",
  "type": "http_request"
}
```

## Security Features

1. **Input Sanitization**: All commands and parameters are validated before execution
2. **Command Injection Prevention**: Regex patterns detect and block dangerous command structures
3. **Timeout Protection**: All operations have a 30-second timeout to prevent hanging
4. **Length Limits**: Parameters are limited to 10,000 characters
5. **Null Byte Protection**: Null bytes are detected and rejected
6. **Error Logging**: All execution attempts are logged with detailed error messages

## Usage Example

```rust
use crate::automation::queue::{AutomationTask, TaskCommand, TaskPriority};

// Create a shell command task
let shell_task = AutomationTask::new(
    TaskCommand::Custom {
        name: "shell".to_string(),
        params: serde_json::json!({
            "command": "echo",
            "args": ["Hello", "World"]
        }),
    },
    TaskPriority::Normal,
);

// Create an HTTP request task
let http_task = AutomationTask::new(
    TaskCommand::Custom {
        name: "http_request".to_string(),
        params: serde_json::json!({
            "url": "https://api.example.com/status",
            "method": "GET",
            "headers": {
                "User-Agent": "Observer/1.0"
            }
        }),
    },
    TaskPriority::High,
);

// Add tasks to queue
queue.add_task(shell_task).await?;
queue.add_task(http_task).await?;
```

## Testing

Added comprehensive unit tests:

1. **test_sanitize_command**: Validates command sanitization
2. **test_sanitize_param**: Validates parameter sanitization
3. **test_custom_shell_command**: Tests shell command task creation
4. **test_custom_http_request_command**: Tests HTTP request task creation
5. **test_custom_applescript_command**: Tests AppleScript task creation (macOS only)

Run tests with:
```bash
cd apps/desktop/src-tauri
cargo test custom
```

## Error Handling

The implementation provides detailed error messages:

- "Command cannot be empty" - Empty command string
- "Command contains dangerous pattern: [pattern]" - Injection attempt detected
- "Parameter contains null byte" - Null byte in parameter
- "Parameter exceeds maximum length" - Parameter too long
- "Missing 'command' parameter" - Required parameter missing
- "Command execution timed out after 30s" - Command took too long
- "Command failed: [stderr]" - Command execution failed
- "Unknown custom command: [name]" - Unsupported command type
- "AppleScript is only supported on macOS" - AppleScript on non-Mac platform

## Performance Considerations

- Timeout ensures no command runs longer than 30 seconds
- Minimum 100ms interval between tasks prevents system overload
- Async execution allows non-blocking operation
- Memory-efficient string handling with `String::from_utf8_lossy`

## Platform Support

- **Shell Commands**: All platforms (Linux, macOS, Windows)
- **AppleScript**: macOS only (returns error on other platforms)
- **HTTP Requests**: All platforms

## Future Enhancements

Possible future additions:

1. PowerShell support for Windows
2. Python script execution
3. JavaScript/Node.js execution
4. File system operations (read/write/delete)
5. Database queries
6. WebSocket connections
7. Custom timeout per command
8. Command output streaming
9. Background/daemon process management
10. Environment variable support

## Documentation

The implementation includes comprehensive inline documentation with:
- Function descriptions
- Parameter explanations
- Usage examples in JSON format
- Security considerations
- Return value specifications

## Dependencies

No new dependencies were required. The implementation uses:
- `tokio::process::Command` - Already available via tokio
- `regex::Regex` - Already in Cargo.toml
- `reqwest::Client` - Already in Cargo.toml

## Conclusion

The custom automation command implementation is complete and production-ready. It provides a secure, flexible, and well-documented system for executing custom commands within the Observer desktop app.
