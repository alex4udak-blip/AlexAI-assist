# Rate Limiting Middleware

## Overview

The rate limiting middleware protects the Observer API from abuse by limiting the number of requests per client within a time window. It uses a sliding window algorithm for accurate rate limiting and supports both Redis (distributed) and in-memory (single-instance) backends.

## Features

- **Sliding Window Algorithm**: More accurate than fixed windows, prevents burst attacks
- **Per-IP/Session Limiting**: Tracks requests by client IP address
- **Endpoint-Specific Limits**: Different limits for different endpoint types
- **Redis Backend**: Distributed rate limiting across multiple instances
- **In-Memory Fallback**: Automatic fallback if Redis is unavailable
- **Standard Headers**: Returns RFC-compliant rate limit headers
- **429 Responses**: Proper HTTP 429 Too Many Requests responses

## Configuration

### Rate Limits by Endpoint Type

| Endpoint Type | Limit | Window | Example Paths |
|--------------|-------|---------|---------------|
| Auth | 5 requests | 60 seconds | `/auth/*`, `/login`, `/register` |
| API | 100 requests | 60 seconds | `/api/v1/*` |
| WebSocket | 10 requests | 60 seconds | `/ws` |
| Default | 60 requests | 60 seconds | All other paths |

### Exempt Paths

The following paths are exempt from rate limiting:
- `/` (root)
- `/health`
- `/docs`
- `/openapi.json`
- `/redoc`

## Usage

### Automatic Integration

The rate limiter is automatically initialized during application startup:

```python
# In main.py
from src.api.middleware import RateLimiterMiddleware, get_rate_limiter

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize rate limiter
    rate_limiter = await get_rate_limiter()
    app.add_middleware(RateLimiterMiddleware, rate_limiter=rate_limiter)

    yield
```

### Customizing Limits

To customize rate limits, edit `RateLimitConfig` in `rate_limiter.py`:

```python
class RateLimitConfig:
    AUTH_LIMIT = 5      # Increase/decrease auth limit
    AUTH_WINDOW = 60    # Change time window

    API_LIMIT = 100
    API_WINDOW = 60

    # ... etc
```

## Response Headers

All non-exempt responses include rate limit headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704672000
```

- `X-RateLimit-Limit`: Maximum requests allowed in the window
- `X-RateLimit-Remaining`: Requests remaining in the current window
- `X-RateLimit-Reset`: Unix timestamp when the limit resets

## 429 Response Format

When rate limit is exceeded:

```json
{
  "detail": "Too many requests. Please try again later.",
  "retry_after": 45
}
```

HTTP Status: `429 Too Many Requests`

## Backend Selection

### Redis (Recommended for Production)

When Redis is available, the rate limiter uses it for distributed rate limiting:

```python
# Automatically uses Redis if available
rate_limiter = await get_rate_limiter()
```

**Advantages:**
- Works across multiple server instances
- Persistent across restarts
- More reliable for production

### In-Memory (Development/Fallback)

If Redis is unavailable, automatically falls back to in-memory:

```python
# Falls back automatically on Redis connection failure
rate_limiter = await get_rate_limiter()
```

**Limitations:**
- Per-instance only (not distributed)
- Lost on restart
- Not suitable for multi-instance deployments

## Client IP Detection

The middleware detects client IP in order of priority:

1. `X-Forwarded-For` header (for proxies/load balancers)
2. `X-Real-IP` header
3. Direct client IP from connection

This ensures accurate rate limiting behind reverse proxies.

## Algorithm: Sliding Window

The sliding window algorithm provides more accurate rate limiting than fixed windows:

```
Fixed Window (inaccurate):
[===5 req===][===5 req===]
            ^
    Burst of 10 at boundary

Sliding Window (accurate):
[===5===]
  [===5===]
    Max 5 in any 60s period
```

### How It Works

1. Store timestamp for each request
2. Remove timestamps older than window
3. Count remaining timestamps
4. Allow if count < limit

## Testing

Run tests:

```bash
pytest tests/api/middleware/test_rate_limiter.py -v
```

Test coverage includes:
- Basic rate limiting
- Sliding window behavior
- Different endpoint limits
- Redis fallback
- Header formatting
- Client IP detection

## Monitoring

Monitor rate limiting in logs:

```
WARNING: Rate limit exceeded for 192.168.1.1 on /api/v1/chat. Limit: 100/60s
```

## Security Considerations

1. **DDoS Protection**: Limits prevent resource exhaustion
2. **Brute Force Prevention**: Auth endpoints have strict limits
3. **IP Spoofing**: Uses X-Forwarded-For with caution
4. **Redis Security**: Use authenticated Redis in production

## Performance

- **Redis**: ~1ms per request (network + sorted set operations)
- **In-Memory**: ~0.01ms per request (dict lookups)
- **Memory Usage**: ~100 bytes per tracked IP per window

## Future Enhancements

- [ ] User-based rate limiting (in addition to IP)
- [ ] Configurable limits via environment variables
- [ ] Rate limit analytics dashboard
- [ ] Whitelist/blacklist support
- [ ] Dynamic limit adjustment based on load
