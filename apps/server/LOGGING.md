# Logging System Documentation

## Overview

The Observer server now has a comprehensive structured logging system with request tracing, security event logging, and sensitive data filtering.

## Features

### 1. Structured Logging
- **Format**: Human-readable in development, JSON in production
- **Request ID**: Every request gets a unique ID for tracing
- **Event Types**: Categorized events for easy filtering
- **Stack Traces**: Full error stack traces for debugging

### 2. Security Event Logging
- Session validation failures
- SQL injection attempts
- SSRF attack attempts
- Invalid authentication attempts

### 3. Sensitive Data Filtering
Automatically filters sensitive data from logs:
- Passwords
- API keys and tokens
- Secret keys
- OAuth tokens
- Authorization headers

### 4. Request ID Tracing
- Generated automatically for each request
- Can be provided via `X-Request-ID` header
- Included in response headers
- Used throughout the request lifecycle

## Configuration

### Environment Variables

```bash
# Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
DEBUG=true  # Sets to DEBUG, otherwise INFO

# Set environment for JSON logs in production
ENVIRONMENT=production  # Enables JSON logging
```

### Log Levels

- **DEBUG**: Detailed diagnostic information (cache hits, detailed operations)
- **INFO**: General informational messages (requests, successful operations)
- **WARNING**: Warning messages (non-critical issues, deprecated features)
- **ERROR**: Error messages with stack traces
- **CRITICAL**: Critical errors requiring immediate attention

## Usage Examples

### Basic Logging

```python
from src.core.logging import get_logger

logger = get_logger(__name__)

# Simple log
logger.info("Operation completed")

# With context
logger.info(
    "User logged in",
    extra={
        "event_type": "authentication",
        "user_id": user_id,
    },
)
```

### Error Logging

```python
from src.core.logging import get_logger, log_error

logger = get_logger(__name__)

try:
    # Some operation
    result = await dangerous_operation()
except Exception as e:
    log_error(
        logger,
        "Operation failed",
        error=e,
        extra={
            "event_type": "operation_error",
            "operation": "dangerous_operation",
        },
    )
```

### Security Event Logging

```python
from src.core.logging import get_logger, log_security_event

logger = get_logger(__name__)

log_security_event(
    logger,
    "Invalid login attempt",
    details={
        "username": username,
        "ip_address": client_ip,
    },
    level="WARNING",  # or "ERROR" for critical events
)
```

### Request ID Context

```python
from src.core.logging import get_request_id, set_request_id

# Get current request ID
request_id = get_request_id()

# Set request ID (usually done by middleware)
set_request_id("custom-request-id")
```

## Log Format

### Development (Human-Readable)

```
2026-01-07 12:00:00,000 | INFO     | abc-123-def | src.api.routes.chat:chat:85 | Chat messages saved
```

Format: `timestamp | level | request_id | module:function:line | message`

### Production (JSON)

```json
{
  "timestamp": "2026-01-07T12:00:00.000Z",
  "level": "INFO",
  "logger": "src.api.routes.chat",
  "message": "Chat messages saved",
  "module": "chat",
  "function": "chat",
  "line": 85,
  "request_id": "abc-123-def",
  "event_type": "chat_saved",
  "session_id": "default",
  "message_count": 2
}
```

## Event Types

Common event types for filtering and monitoring:

- `request_started` - HTTP request initiated
- `request_completed` - HTTP request completed successfully
- `request_failed` - HTTP request failed
- `security` - Security-related events
- `authentication` - Authentication events
- `authorization` - Authorization events
- `db_error` - Database errors
- `redis_connection_error` - Redis connection issues
- `cache_hit` / `cache_miss` - Cache operations
- `agent_execution_started` / `agent_execution_completed` - Agent operations
- `claude_response` / `claude_error` - Claude API interactions
- `memory_processed` / `memory_processing_error` - Memory system operations

## Monitoring Recommendations

### Production Monitoring Queries

#### Error Rate
```bash
# Count errors in last hour
grep '"level":"ERROR"' app.log | grep "$(date -u +%Y-%m-%d)" | wc -l
```

#### Security Events
```bash
# Monitor security events
grep '"event_type":"security"' app.log | tail -f
```

#### Request Performance
```bash
# Find slow requests (>1000ms)
grep '"event_type":"request_completed"' app.log | \
  jq 'select(.duration_ms > 1000)'
```

#### Request Tracing
```bash
# Trace all logs for a specific request
grep '"request_id":"abc-123-def"' app.log | jq '.'
```

## Files Modified

1. **`src/core/logging.py`** - Core logging configuration
2. **`src/api/middleware/request_logging.py`** - Request logging middleware
3. **`src/main.py`** - Application setup with logging
4. **`src/core/security.py`** - Security event logging
5. **`src/api/routes/chat.py`** - Chat route logging
6. **`src/services/agent_executor.py`** - Agent execution logging

## Best Practices

1. **Always use structured extra data**: Include relevant context in the `extra` parameter
2. **Use appropriate log levels**: Don't log INFO messages in tight loops
3. **Never log sensitive data**: Passwords, tokens, etc. (filtered automatically but still avoid)
4. **Include event_type**: Makes filtering and monitoring easier
5. **Log errors with context**: Use `log_error()` to include stack traces
6. **Use request IDs**: Makes distributed tracing possible

## Testing Logging

```python
# Test that logging works
import pytest
from src.core.logging import setup_logging, get_logger

def test_logging():
    setup_logging(level="INFO")
    logger = get_logger(__name__)

    logger.info("Test message")
    # Check logs
```

## Troubleshooting

### Logs not appearing
- Check log level configuration
- Verify logger is properly initialized with `get_logger(__name__)`
- Check if log level is high enough for message

### Sensitive data in logs
- Update `SENSITIVE_KEYS` in `src/core/logging.py`
- Avoid logging raw request/response bodies
- Use truncation for URLs and large payloads

### Request ID not showing
- Ensure `RequestLoggingMiddleware` is properly installed
- Check that request passes through middleware
- Verify request_id is set in context

## Future Improvements

- [ ] Integrate with external logging services (Datadog, CloudWatch, etc.)
- [ ] Add log aggregation and search
- [ ] Implement log rotation for file-based logging
- [ ] Add performance metrics logging
- [ ] Create alerting based on error patterns
- [ ] Add distributed tracing with OpenTelemetry
