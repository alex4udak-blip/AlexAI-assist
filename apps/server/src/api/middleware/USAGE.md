# Rate Limiter Usage Examples

## Basic Usage

The rate limiter is automatically applied to all routes. No code changes needed in your route handlers.

### Example Route (Automatically Rate Limited)

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/api/v1/users")
async def get_users():
    """This endpoint is automatically rate limited to 100 req/60s."""
    return {"users": [...]}
```

### Response with Rate Limit Headers

```bash
$ curl -i http://localhost:8000/api/v1/users

HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1704672000
Content-Type: application/json

{"users": [...]}
```

## Handling Rate Limit Errors

### Client-Side Example (JavaScript/TypeScript)

```typescript
async function makeRequest(url: string) {
  const response = await fetch(url);

  if (response.status === 429) {
    const data = await response.json();
    const retryAfter = data.retry_after;

    console.log(`Rate limited. Retry after ${retryAfter} seconds`);

    // Wait and retry
    await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
    return makeRequest(url);
  }

  return response.json();
}
```

### Client-Side with Headers

```typescript
async function makeRequestWithBackoff(url: string) {
  const response = await fetch(url);

  // Check remaining requests
  const remaining = parseInt(response.headers.get('X-RateLimit-Remaining') || '0');

  if (remaining < 10) {
    console.warn(`Low rate limit remaining: ${remaining}`);
  }

  if (response.status === 429) {
    const reset = parseInt(response.headers.get('X-RateLimit-Reset') || '0');
    const now = Math.floor(Date.now() / 1000);
    const waitTime = reset - now;

    throw new Error(`Rate limited. Try again in ${waitTime} seconds`);
  }

  return response.json();
}
```

## Testing Rate Limits

### Manual Testing

```bash
# Test API endpoint (100 req/60s limit)
for i in {1..105}; do
  echo "Request $i"
  curl -s http://localhost:8000/api/v1/test | jq .
done
# Requests 101-105 will receive 429 errors

# Test auth endpoint (5 req/60s limit)
for i in {1..7}; do
  echo "Request $i"
  curl -s http://localhost:8000/auth/login | jq .
done
# Requests 6-7 will receive 429 errors
```

### With Different IPs

```bash
# Simulate different clients
curl -H "X-Forwarded-For: 192.168.1.1" http://localhost:8000/api/v1/test
curl -H "X-Forwarded-For: 192.168.1.2" http://localhost:8000/api/v1/test
# Each IP has independent rate limits
```

## Custom Rate Limiting for Specific Routes

If you need custom rate limiting for specific endpoints, you can use dependencies:

```python
from fastapi import APIRouter, Depends, HTTPException
from src.api.middleware.rate_limiter import RateLimiter, get_rate_limiter

router = APIRouter()

async def check_custom_limit(
    request: Request,
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
):
    """Custom rate limit: 10 requests per 5 seconds."""
    client_id = request.client.host
    is_allowed, info = await rate_limiter.is_allowed(
        f"custom:{client_id}:{request.url.path}",
        limit=10,
        window=5,
    )

    if not is_allowed:
        raise HTTPException(
            status_code=429,
            detail="Custom rate limit exceeded",
        )

@router.post("/api/v1/expensive-operation", dependencies=[Depends(check_custom_limit)])
async def expensive_operation():
    """This endpoint has a custom stricter limit."""
    return {"status": "processing"}
```

## Monitoring Rate Limits

### Check Logs

```bash
# Server logs show rate limit violations
tail -f logs/server.log | grep "Rate limit exceeded"

# Example output:
# WARNING: Rate limit exceeded for 192.168.1.100 on /api/v1/chat. Limit: 100/60s
```

### Prometheus Metrics (Future Enhancement)

```python
# Future: Export metrics for monitoring
rate_limit_exceeded_total{endpoint="/api/v1/chat"} 15
rate_limit_requests_total{endpoint="/api/v1/chat"} 1050
```

## Production Considerations

### 1. Behind Load Balancer / Reverse Proxy

Ensure proper IP forwarding:

```nginx
# Nginx configuration
location / {
    proxy_pass http://backend;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### 2. Redis Configuration

Use authenticated Redis in production:

```bash
# .env
REDIS_URL=redis://:password@redis:6379/0
```

### 3. Adjust Limits for Production

```python
# In rate_limiter.py - adjust based on your needs
class RateLimitConfig:
    # More restrictive for production
    AUTH_LIMIT = 3  # 3 login attempts per minute
    AUTH_WINDOW = 60

    # Higher for high-traffic APIs
    API_LIMIT = 1000  # 1000 req/min for paid users
    API_WINDOW = 60
```

### 4. Whitelist Trusted IPs

Add whitelisting for internal services:

```python
def _is_exempt(self, path: str, client_id: str) -> bool:
    """Check if path or client is exempt from rate limiting."""
    # Existing path exemptions
    exempt_paths = ["/", "/health", "/docs", "/openapi.json", "/redoc"]
    if path in exempt_paths:
        return True

    # Whitelist internal IPs
    trusted_ips = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
    # Check if client_id in trusted_ips
    return False
```

## Troubleshooting

### Issue: All requests get 429

**Cause**: Rate limit too low or Redis issue

**Solution**:
```bash
# Check Redis connection
redis-cli ping

# Check logs for errors
tail -f logs/server.log | grep -i redis

# Temporarily increase limits for testing
# Edit rate_limiter.py RateLimitConfig values
```

### Issue: Rate limits not working

**Cause**: Middleware not initialized

**Solution**:
```python
# Verify in main.py lifespan function
rate_limiter = await get_rate_limiter()
app.add_middleware(RateLimiterMiddleware, rate_limiter=rate_limiter)
```

### Issue: Different instances have different limits

**Cause**: Using in-memory backend without Redis

**Solution**:
```bash
# Ensure Redis is running and configured
docker-compose up -d redis

# Verify REDIS_URL in .env
echo $REDIS_URL
```

## Performance Tips

1. **Use Redis in Production**: In-memory is only for single-instance dev
2. **Monitor Redis Performance**: Keep latency low for rate limiting
3. **Adjust Window Size**: Shorter windows = more memory, longer windows = less precise
4. **Clean Old Data**: Redis automatically expires old sorted set entries
