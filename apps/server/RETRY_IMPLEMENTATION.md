# Retry Logic Implementation

## Overview
This document describes the retry logic and circuit breaker implementation added to external service calls in the Observer server.

## Files Modified

### 1. Dependencies
- **`requirements.txt`**: Added `tenacity>=8.2.0`
- **`pyproject.toml`**: Added `tenacity>=8.2.0`

### 2. Core Implementation
- **`/home/user/AlexAI-assist/apps/server/src/core/retry.py`** (NEW)
  - Retry decorator with exponential backoff
  - Circuit breaker pattern implementation
  - Retryable error detection

### 3. Service Updates
- **`/home/user/AlexAI-assist/apps/server/src/core/claude.py`**
  - Added retry logic to `complete()` method
  - Added circuit breaker protection for Claude API calls

- **`/home/user/AlexAI-assist/apps/server/src/services/agent_executor.py`**
  - Added retry logic to HTTP requests in `_make_http_request()` method
  - Added circuit breaker protection for agent HTTP actions

### 4. Tests
- **`/home/user/AlexAI-assist/apps/server/tests/test_retry.py`** (NEW)
  - Comprehensive test suite with 21 tests
  - Tests for retry logic, circuit breaker, and integration

## Features

### 1. Retry with Exponential Backoff

**Configuration:**
- Max attempts: 3
- Min wait: 1 second
- Max wait: 10 seconds
- Exponential multiplier: 1x (doubles each retry)

**Retryable Errors:**
- Network timeouts (`httpx.TimeoutException`)
- Connection errors (`httpx.ConnectError`, `httpx.NetworkError`)
- 5xx HTTP errors (500-599)
- 429 Too Many Requests
- 408 Request Timeout

**Non-Retryable Errors:**
- 4xx client errors (except 408, 429)
- Application logic errors
- Validation errors

### 2. Circuit Breaker Pattern

**States:**
- **CLOSED**: Normal operation, all requests allowed
- **OPEN**: Too many failures, requests blocked immediately
- **HALF_OPEN**: Testing recovery, limited requests allowed

**Configuration:**
- Failure threshold: 5 consecutive failures
- Recovery timeout: 60 seconds
- Success threshold: 2 successes (to transition from HALF_OPEN to CLOSED)

**State Transitions:**
```
CLOSED --[5 failures]--> OPEN
OPEN --[60 seconds]--> HALF_OPEN
HALF_OPEN --[2 successes]--> CLOSED
HALF_OPEN --[any failure]--> OPEN
```

**Benefits:**
- Prevents cascading failures
- Gives failing services time to recover
- Fails fast when service is known to be down
- Automatic recovery detection

### 3. Service-Specific Circuit Breakers

Each external service has its own circuit breaker state:
- `claude_api`: Claude API proxy calls
- `agent_http`: Agent HTTP action requests

This allows independent failure handling per service.

## Usage Examples

### Example 1: Using Retry Decorator

```python
from src.core.retry import retry_with_backoff

@retry_with_backoff(max_attempts=3, min_wait=1, max_wait=10)
async def my_external_call():
    # This will retry on transient errors
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        response.raise_for_status()
        return response.json()
```

### Example 2: Using Circuit Breaker

```python
from src.core.retry import with_circuit_breaker

@with_circuit_breaker(service_name="my_service")
async def my_service_call():
    # Circuit breaker will block calls if too many failures
    return await external_service.call()
```

### Example 3: Combined (Recommended)

```python
from src.core.retry import retry_with_backoff, with_circuit_breaker

@retry_with_backoff(max_attempts=3, min_wait=1, max_wait=10)
@with_circuit_breaker(service_name="my_service")
async def robust_external_call():
    # Combines retry logic with circuit breaker protection
    return await external_service.call()
```

### Example 4: Checking Circuit Breaker Status

```python
from src.core.retry import circuit_breaker

# Get circuit breaker stats
stats = circuit_breaker.get_stats("claude_api")
print(f"State: {stats['state']}")
print(f"Failures: {stats['failure_count']}")

# Manually reset circuit breaker
circuit_breaker.reset("claude_api")
```

## Logging

The retry logic provides detailed logging:

### Retry Attempts
```
WARNING - Retrying complete after TimeoutException('Request timeout')
         (attempt 2/3)
```

### Circuit Breaker State Changes
```
ERROR - Circuit breaker for claude_api: CLOSED -> OPEN (failures: 5)
INFO - Circuit breaker for claude_api: OPEN -> HALF_OPEN
INFO - Circuit breaker for claude_api: HALF_OPEN -> CLOSED
```

### Circuit Breaker Blocks
```
ERROR - Circuit breaker open for claude_api
```

## Monitoring

To monitor retry and circuit breaker behavior:

1. **Check logs** for retry attempts and circuit breaker state changes
2. **Use circuit_breaker.get_stats()** to get current state
3. **Track error rates** to identify services with issues
4. **Monitor recovery times** to optimize timeouts

## Testing

Run the comprehensive test suite:

```bash
cd /home/user/AlexAI-assist/apps/server
pytest tests/test_retry.py -v
```

**Test Coverage:**
- Retryable error detection (5 tests)
- Retry with exponential backoff (4 tests)
- Circuit breaker state machine (7 tests)
- Circuit breaker decorator (4 tests)
- Integration tests (1 test)

All 21 tests passing confirms:
- Retry logic works correctly
- Circuit breaker transitions properly
- Error detection is accurate
- Integration between retry and circuit breaker functions

## Configuration Recommendations

### For High-Traffic Services
```python
@retry_with_backoff(max_attempts=2, min_wait=0.5, max_wait=5)
@with_circuit_breaker(service_name="high_traffic_api")
```
- Fewer retries to fail fast
- Shorter wait times
- Circuit breaker protects from overload

### For Critical Services
```python
@retry_with_backoff(max_attempts=5, min_wait=2, max_wait=30)
@with_circuit_breaker(service_name="critical_api")
```
- More retries for better success rate
- Longer wait times for stability
- Circuit breaker prevents total failure

### For Background Jobs
```python
@retry_with_backoff(max_attempts=10, min_wait=5, max_wait=60)
@with_circuit_breaker(service_name="background_job")
```
- Many retries acceptable
- Longer wait times okay
- Circuit breaker prevents resource waste

## Production Considerations

1. **Timeout Configuration**: Ensure HTTP client timeouts are set appropriately
   - Claude API: 180 seconds (set in claude.py)
   - Agent HTTP: 30 seconds (set in agent_executor.py)

2. **Circuit Breaker Tuning**: Adjust thresholds based on production metrics
   - Monitor false positives (premature opening)
   - Monitor false negatives (late opening)

3. **Metrics**: Consider adding metrics for:
   - Retry success/failure rates
   - Circuit breaker state durations
   - Time to recovery

4. **Alerting**: Set up alerts for:
   - Circuit breakers stuck in OPEN state
   - High retry rates
   - Services with repeated failures

## Implementation Details

### Decorator Ordering
```python
@retry_with_backoff(...)      # Outer: handles retries
@with_circuit_breaker(...)    # Inner: checks circuit first
async def service_call():
    pass
```

This ordering ensures:
1. Circuit breaker check happens first (fast fail if open)
2. Retry logic wraps the circuit breaker call
3. Each retry attempt checks circuit state

### Error Handling Flow
```
1. Request → Circuit Breaker Check
2. If OPEN → Raise CircuitBreakerOpenError
3. If CLOSED/HALF_OPEN → Make Request
4. If Retryable Error → Record Failure → Retry
5. If Non-Retryable Error → Propagate Error
6. If Success → Record Success → Return Result
```

## Future Enhancements

Potential improvements:
1. **Metrics Export**: Export retry/circuit breaker metrics to Prometheus
2. **Adaptive Timeouts**: Adjust timeouts based on response times
3. **Bulkhead Pattern**: Limit concurrent requests per service
4. **Rate Limiting**: Add rate limiting alongside retry logic
5. **Distributed Circuit Breaker**: Use Redis for shared state across instances

## References

- Tenacity Documentation: https://tenacity.readthedocs.io/
- Circuit Breaker Pattern: https://martinfowler.com/bliki/CircuitBreaker.html
- Retry Strategies: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
