# Rate Limiting Quick Start Guide

## What Was Added

Rate limiting middleware has been added to protect the FastAPI server from abuse. It automatically limits requests per IP address with different limits for different endpoint types.

## Quick Start

### 1. Start the Server (Rate Limiting Active)

```bash
cd /home/user/AlexAI-assist/apps/server
uvicorn src.main:app --reload
```

Rate limiting is **automatically active** - no additional configuration needed!

### 2. Verify It's Working

```bash
# Check startup logs
# You should see: "Rate limiter initialized"

# Make a test request
curl -i http://localhost:8000/api/v1/events

# Look for these headers:
# X-RateLimit-Limit: 100
# X-RateLimit-Remaining: 99
# X-RateLimit-Reset: 1704672000
```

### 3. Test Rate Limiting

```bash
# Quickly make 105 requests to exceed the limit
for i in {1..105}; do
  echo "Request $i"
  curl http://localhost:8000/api/v1/events
done

# Requests 101-105 will return:
# HTTP 429 Too Many Requests
# {"detail": "Too many requests. Please try again later.", "retry_after": 45}
```

## Current Limits

| Endpoint | Limit | Window | Example |
|----------|-------|--------|---------|
| Auth | 5 req | 60 sec | `/auth/login` |
| API | 100 req | 60 sec | `/api/v1/events` |
| WebSocket | 10 req | 60 sec | `/ws` |
| Other | 60 req | 60 sec | Other endpoints |

**Exempt paths**: `/`, `/health`, `/docs`, `/openapi.json`, `/redoc`

## Customization

### Change Limits

Edit `/home/user/AlexAI-assist/apps/server/src/api/middleware/rate_limiter.py`:

```python
class RateLimitConfig:
    AUTH_LIMIT = 10     # Change from 5 to 10
    API_LIMIT = 200     # Change from 100 to 200
    # etc...
```

### Use Redis (Production)

For distributed rate limiting across multiple servers:

1. Ensure Redis is running:
   ```bash
   docker-compose up -d redis
   ```

2. Set REDIS_URL in `.env`:
   ```bash
   REDIS_URL=redis://localhost:6379/0
   ```

3. Restart server - Redis will be auto-detected

## Testing

Run the test suite:

```bash
cd /home/user/AlexAI-assist/apps/server
pytest tests/api/middleware/test_rate_limiter.py -v
```

## Monitoring

Watch for rate limit violations:

```bash
# Server logs
tail -f logs/server.log | grep "Rate limit exceeded"

# Example output:
# WARNING: Rate limit exceeded for 192.168.1.100 on /api/v1/chat. Limit: 100/60s
```

## Documentation

- **Technical Details**: `/home/user/AlexAI-assist/apps/server/src/api/middleware/README.md`
- **Usage Examples**: `/home/user/AlexAI-assist/apps/server/src/api/middleware/USAGE.md`
- **Implementation Summary**: `/home/user/AlexAI-assist/RATE_LIMITER_IMPLEMENTATION.md`

## Troubleshooting

### All requests return 429

**Solution**: Limits might be too low. Temporarily increase in `RateLimitConfig`.

### Rate limiting not working

**Solution**: Check that middleware is initialized:
```bash
grep "Rate limiter initialized" logs/server.log
```

### Different instances have different counts

**Solution**: Use Redis for distributed rate limiting (see "Use Redis" above).

## Files Modified/Created

```
apps/server/
├── src/
│   ├── api/
│   │   └── middleware/          # NEW
│   │       ├── __init__.py
│   │       ├── rate_limiter.py
│   │       ├── README.md
│   │       └── USAGE.md
│   └── main.py                  # MODIFIED (lines 11, 40-42)
└── tests/
    └── api/
        └── middleware/          # NEW
            ├── __init__.py
            └── test_rate_limiter.py
```

## Next Steps

1. Start server and verify rate limiting works
2. Adjust limits based on your needs
3. Set up Redis for production
4. Monitor logs for rate limit violations
5. Tune limits based on actual usage patterns

## Summary

Rate limiting is now active on all routes with:
- Sliding window algorithm for accuracy
- Different limits for different endpoint types
- Automatic Redis/in-memory backend selection
- Standard rate limit headers
- Proper 429 error responses

No code changes needed in your route handlers - everything works automatically!
