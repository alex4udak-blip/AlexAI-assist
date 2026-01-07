# Rate Limiting Flow Diagram

## Request Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      Incoming Request                            │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              RateLimiterMiddleware.dispatch()                    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                   ┌────────────────────────┐
                   │   Is path exempt?      │
                   │   (/, /health, /docs)  │
                   └────────┬───────────────┘
                            │
              ┌─────────────┴─────────────┐
              │ YES                    NO │
              ▼                           ▼
        ┌──────────┐         ┌────────────────────────┐
        │  ALLOW   │         │ Get client identifier  │
        │  (skip)  │         │ (IP from headers)      │
        └──────────┘         └────────┬───────────────┘
                                      │
                                      ▼
                         ┌────────────────────────────┐
                         │  Get rate limit params     │
                         │  based on endpoint type    │
                         │  (/api=100, /auth=5, etc)  │
                         └────────┬───────────────────┘
                                  │
                                  ▼
                         ┌────────────────────────────┐
                         │   Build rate limit key     │
                         │   "IP:path"                │
                         └────────┬───────────────────┘
                                  │
                                  ▼
                         ┌────────────────────────────┐
                         │  RateLimiter.is_allowed()  │
                         └────────┬───────────────────┘
                                  │
                 ┌────────────────┴────────────────┐
                 │                                 │
                 ▼                                 ▼
        ┌─────────────────┐              ┌─────────────────┐
        │  Redis available?│              │  Redis available?│
        └────────┬─────────┘              └────────┬─────────┘
                 │                                  │
        ┌────────┴─────────┐              ┌────────┴─────────┐
        │ YES           NO │              │ YES           NO │
        ▼                  ▼              ▼                  ▼
   ┌─────────┐      ┌──────────┐   ┌─────────┐      ┌──────────┐
   │  Redis  │      │ In-Memory│   │  Redis  │      │ In-Memory│
   │  Check  │      │  Check   │   │  Check  │      │  Check   │
   └────┬────┘      └─────┬────┘   └────┬────┘      └─────┬────┘
        │                 │              │                 │
        └────────┬────────┘              └────────┬────────┘
                 │                                │
                 ▼                                ▼
        ┌──────────────────┐            ┌──────────────────┐
        │   Count < Limit? │            │   Count >= Limit?│
        └────────┬─────────┘            └────────┬─────────┘
                 │                                │
            YES  │                            YES │
                 ▼                                ▼
        ┌──────────────────┐            ┌──────────────────┐
        │  Add timestamp   │            │  DON'T add       │
        │  Process request │            │  Return 429      │
        └────────┬─────────┘            └────────┬─────────┘
                 │                                │
                 ▼                                ▼
        ┌──────────────────┐            ┌──────────────────┐
        │  Add headers:    │            │  Return JSON:    │
        │  X-RateLimit-*   │            │  {"detail": ".."}│
        └────────┬─────────┘            │  retry_after: N  │
                 │                      └──────────────────┘
                 ▼
        ┌──────────────────┐
        │   200 Response   │
        └──────────────────┘
```

## Sliding Window Algorithm

```
Time Window: 60 seconds
Limit: 5 requests

Current Time: t
Window Start: t - 60s

Timeline:
─────────────────────────────────────────────────────────────>
                    Window (60s)
              ├────────────────────┤
              │                    │
        Remove│  Count these  │    │ Current
         old  │  timestamps  │    │  time
         data │              │    │
              │  ●  ●  ●  ●  │    │ ●
              │              │    │
         t-60s│              │    │ t
              └──────────────┘    │
                                  │
                        Add new timestamp if count < limit

Process:
1. Remove all timestamps < (t - 60s)
2. Count remaining timestamps
3. If count < 5: ALLOW and add timestamp
4. If count >= 5: DENY (429)
```

## Redis Data Structure

```
Key: "rate_limit:192.168.1.1:/api/v1/chat"

Value: Sorted Set (ZSET)
┌──────────────────────────────────┐
│ Score (timestamp)  │   Member    │
├────────────────────┼─────────────┤
│  1704672001.123   │ "1704672001"│
│  1704672002.456   │ "1704672002"│
│  1704672003.789   │ "1704672003"│
│  1704672004.012   │ "1704672004"│
│  1704672005.345   │ "1704672005"│
└──────────────────────────────────┘

Operations (atomic via pipeline):
1. ZREMRANGEBYSCORE key 0 (t-60)   # Remove old
2. ZCARD key                        # Count
3. ZADD key t t                     # Add new
4. EXPIRE key 70                    # Auto-cleanup

TTL: Window + 10s buffer
```

## Endpoint Type Detection

```
Request Path
      │
      ▼
┌──────────────────────┐
│  Path matching       │
└───────┬──────────────┘
        │
        ├─ "/auth/*" ────────────> AUTH (5 req/60s)
        │
        ├─ "/ws" ────────────────> WEBSOCKET (10 req/60s)
        │
        ├─ "/api/v1/*" ──────────> API (100 req/60s)
        │
        └─ Others ───────────────> DEFAULT (60 req/60s)
```

## Client IP Detection

```
Request Headers
      │
      ▼
┌──────────────────────────────┐
│ X-Forwarded-For exists?      │
└───────┬──────────────────────┘
        │
    ┌───┴───┐
    │  YES  │
    └───┬───┘
        │
        ▼
┌──────────────────────────────┐
│ Use first IP from            │
│ X-Forwarded-For              │
│ (split by comma)             │
└──────────────────────────────┘
        │
        │  NO
        ▼
┌──────────────────────────────┐
│ X-Real-IP exists?            │
└───────┬──────────────────────┘
        │
    ┌───┴───┐
    │  YES  │
    └───┬───┘
        │
        ▼
┌──────────────────────────────┐
│ Use X-Real-IP                │
└──────────────────────────────┘
        │
        │  NO
        ▼
┌──────────────────────────────┐
│ Use request.client.host      │
│ (direct connection IP)       │
└──────────────────────────────┘
```

## Error Response Flow

```
┌──────────────────────────────┐
│  Rate Limit Exceeded         │
│  (count >= limit)            │
└───────────┬──────────────────┘
            │
            ▼
┌──────────────────────────────┐
│  Calculate retry_after       │
│  = reset_time - current_time │
└───────────┬──────────────────┘
            │
            ▼
┌──────────────────────────────┐
│  Build JSON Response:        │
│  {                           │
│    "detail": "Too many...",  │
│    "retry_after": 45         │
│  }                           │
└───────────┬──────────────────┘
            │
            ▼
┌──────────────────────────────┐
│  Add Headers:                │
│  X-RateLimit-Limit: 100      │
│  X-RateLimit-Remaining: 0    │
│  X-RateLimit-Reset: ...      │
└───────────┬──────────────────┘
            │
            ▼
┌──────────────────────────────┐
│  Return HTTP 429             │
└──────────────────────────────┘
```

## Backend Selection Flow

```
Application Startup
        │
        ▼
┌───────────────────────┐
│  get_rate_limiter()   │
└───────┬───────────────┘
        │
        ▼
┌───────────────────────┐
│  Try Redis connect    │
└───────┬───────────────┘
        │
    ┌───┴────┐
    │SUCCESS │
    └───┬────┘
        │
        ▼
┌───────────────────────┐      ┌────────────────────┐
│  Use Redis backend    │      │  Use in-memory     │
│  (distributed)        │<─NO──│  Redis available?  │
└───────────────────────┘      └────────┬───────────┘
        │                               │
        │                           YES │
        └───────────┬───────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  RateLimiter instance │
        └───────────────────────┘
```

## Complete Integration

```
main.py
   │
   ├─ Import RateLimiterMiddleware, get_rate_limiter
   │
   ├─ lifespan():
   │     │
   │     ├─ rate_limiter = await get_rate_limiter()
   │     │     │
   │     │     └─> Connects to Redis or uses in-memory
   │     │
   │     └─ app.add_middleware(RateLimiterMiddleware, ...)
   │           │
   │           └─> Applies to ALL routes
   │
   └─ All routes automatically protected:
         │
         ├─ /api/v1/events  (100 req/60s)
         ├─ /api/v1/chat    (100 req/60s)
         ├─ /api/v1/memory  (100 req/60s)
         ├─ /api/v1/agents  (100 req/60s)
         └─ ... all others
```
