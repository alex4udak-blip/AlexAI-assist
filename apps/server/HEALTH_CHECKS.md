# Health Check System

## Overview
Comprehensive health check system for the Observer API server with monitoring for critical services and system resources.

## Endpoints

### `/health` - Comprehensive Health Check
Full health check with detailed status for all services and system resources.

**Response Status Codes:**
- `200 OK` - All services healthy or degraded (still operational)
- `503 Service Unavailable` - One or more critical services unhealthy

**Response Example:**
```json
{
  "status": "healthy",
  "timestamp": 1704672000.0,
  "response_time_ms": 45.23,
  "checks": {
    "database": {
      "status": "healthy",
      "latency_ms": 12.5
    },
    "redis": {
      "status": "degraded",
      "error": "Redis unavailable",
      "note": "Using in-memory fallback for rate limiting"
    },
    "memory": {
      "status": "healthy",
      "percent_used": 65.4,
      "available_mb": 2048.5,
      "total_mb": 8192.0
    },
    "disk": {
      "status": "healthy",
      "percent_used": 42.1,
      "available_gb": 45.6,
      "total_gb": 100.0
    }
  }
}
```

**Features:**
- Concurrent execution of all checks for speed
- Database connection with 5-second timeout
- Redis connection with graceful degradation (optional service)
- Memory usage monitoring (degraded >80%, unhealthy >90%)
- Disk space monitoring (degraded >80%, unhealthy >90%)
- Fast response time (<100ms typical)

### `/ready` - Kubernetes Readiness Check
Lightweight check for Kubernetes readiness probes. Focuses only on critical dependencies.

**Response Status Codes:**
- `200 OK` - Service ready to accept traffic
- `503 Service Unavailable` - Service not ready

**Response Example:**
```json
{
  "status": "ready",
  "timestamp": 1704672000.0
}
```

**Features:**
- Very fast (<50ms typical)
- Only checks database connectivity
- 3-second timeout for quick response
- No rate limiting (exempt from rate limiter)

## Status Levels

### healthy
Service is operating normally with no issues.

### degraded
Service is operational but experiencing non-critical issues:
- Redis unavailable (fallback to in-memory rate limiting)
- High memory usage (80-90%)
- High disk usage (80-90%)

### unhealthy
Critical service failure:
- Database connection failed
- Memory usage >90%
- Disk space >90%

## Kubernetes Configuration

### Liveness Probe
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 30
  timeoutSeconds: 10
  failureThreshold: 3
```

### Readiness Probe
```yaml
readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 2
```

## Monitoring Integration

### Prometheus
Health check metrics can be scraped from the `/health` endpoint:
- `observer_health_status` - Overall health status (0=unhealthy, 1=degraded, 2=healthy)
- `observer_database_latency_ms` - Database response time
- `observer_redis_latency_ms` - Redis response time
- `observer_memory_percent` - Memory usage percentage
- `observer_disk_percent` - Disk usage percentage

### Alerting Rules

**Critical Alerts:**
- Database connection failed (trigger immediately)
- Memory usage >90% (trigger after 5 minutes)
- Disk space >90% (trigger after 5 minutes)

**Warning Alerts:**
- Redis unavailable (informational)
- Memory usage >80% (trigger after 15 minutes)
- Disk space >80% (trigger after 15 minutes)

## Performance

### Response Times
- `/ready`: <50ms typical, <3s max
- `/health`: <100ms typical, <10s max

### Resource Impact
- Minimal CPU usage (<1% during check)
- No database transactions or locks
- Concurrent execution prevents blocking
- No impact on application performance

## Rate Limiting

Both `/health` and `/ready` endpoints are exempt from rate limiting to ensure:
- Kubernetes probes don't get rate limited
- Monitoring systems can poll frequently
- No false positives from rate limit blocks

## Dependencies

- `psutil>=5.9.0` - System metrics (memory, disk)
- `redis>=5.0.0` - Redis connectivity check
- `sqlalchemy[asyncio]>=2.0.25` - Database connectivity check

## Implementation Details

### Fast Execution
All checks run concurrently using `asyncio.gather()` for maximum speed:
- Database check: async with timeout
- Redis check: async with timeout and connection pool
- Memory check: sync wrapped in `asyncio.to_thread()`
- Disk check: sync wrapped in `asyncio.to_thread()`

### Error Handling
- Database timeout → unhealthy status
- Redis timeout → degraded status (fallback available)
- System metrics error → unknown status (non-blocking)
- All errors logged for debugging

### Status Determination
```python
if any_critical_unhealthy:
    return 503 SERVICE_UNAVAILABLE
elif any_critical_degraded:
    return 200 OK  # Still operational
else:
    return 200 OK  # All healthy
```

Critical services: Database, Memory, Disk
Optional services: Redis (degraded is acceptable)

## Testing

Run health check tests:
```bash
cd apps/server
pytest tests/test_api.py::TestHealthEndpoints -v
```

Test coverage:
- Comprehensive health check structure
- Response time validation
- Status code correctness
- Readiness check speed
- Individual check validation

## Troubleshooting

### Health Check Slow
- Check database connection pool status
- Verify Redis connectivity
- Review system resource usage
- Check network latency

### False Positives
- Adjust timeout values if needed
- Review threshold percentages
- Check for transient issues

### Kubernetes Pod Not Ready
1. Check `/ready` endpoint manually
2. Verify database is accessible
3. Review pod logs for errors
4. Ensure sufficient startup time
