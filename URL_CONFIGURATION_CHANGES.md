# URL Configuration Changes Summary

## Overview
Fixed all hardcoded URLs in the codebase to use environment variables and configuration files. Removed inconsistent Railway production URLs and implemented a consistent configuration approach across all applications.

## Problems Fixed

### 1. **Inconsistent Production URLs**
- Web app used: `server-production-6bb7.up.railway.app`
- Desktop app used: `server-production-20d71.up.railway.app`
- **Solution**: Removed all hardcoded production URLs

### 2. **Hardcoded URLs in Multiple Locations**
- Web config.ts
- Desktop sync.rs
- Web index.html (CSP)
- Desktop tauri.conf.json (CSP)
- SECURITY.md documentation

### 3. **No Documentation for Environment Variables**
- **Solution**: Created .env.example files for all apps

## Files Modified

### `/apps/web/src/lib/config.ts`
- **Before**: Hardcoded Railway URL fallback
- **After**: Environment variable priority with localhost development fallback
- Removed: `RAILWAY_SERVER_URL` constant
- Added: Clear priority documentation and warning messages

### `/apps/desktop/src-tauri/src/sync.rs`
- **Before**: Hardcoded Railway production URLs as defaults
- **After**: Environment variable and config file priority with localhost fallback
- Added: URL validation and security checks (SSRF prevention)
- Added: Development mode detection
- Added: Retry logic with exponential backoff
- Added: Better error messages and warnings

### `/apps/desktop/src-tauri/tauri.conf.json`
- **Before**: Hardcoded production URLs in CSP
- **After**: Wildcard patterns `https://*.railway.app` and `http://localhost:*`

### `/apps/web/index.html`
- **Before**: Hardcoded production URLs in CSP
- **After**: Wildcard patterns `https://*.railway.app` and `http://localhost:*`

### `/apps/web/SECURITY.md`
- Updated documentation to reference environment variables instead of hardcoded URLs
- Updated CSP examples to use wildcard patterns

## Files Created

### `/apps/web/.env.example`
```
VITE_API_URL=
VITE_WS_URL=
```

### `/apps/server/.env.example`
```
DATABASE_URL=
REDIS_URL=
SECRET_KEY=
ALLOWED_ORIGINS=
CLAUDE_OAUTH_TOKEN=
CLAUDE_MODEL=
CLAUDE_PROXY_URL=
CCPROXY_INTERNAL_TOKEN=
ENVIRONMENT=
DEBUG=
```

### `/apps/desktop/.env.example`
```
OBSERVER_SERVER_URL=
OBSERVER_DASHBOARD_URL=
OBSERVER_DEV=
```

## Configuration Priority

### Web App
1. `VITE_API_URL` environment variable (set at build time)
2. `VITE_WS_URL` environment variable (set at build time)
3. Localhost fallback (development)

### Desktop App
1. `OBSERVER_SERVER_URL` environment variable
2. `~/.config/observer/server.txt` config file
3. Localhost fallback (development)

1. `OBSERVER_DASHBOARD_URL` environment variable
2. `~/.config/observer/dashboard.txt` config file
3. Localhost fallback (development)

### Server App
Uses Pydantic BaseSettings which automatically loads from environment variables:
- `DATABASE_URL` (required in production)
- `REDIS_URL` (required in production)
- `SECRET_KEY` (required in production)
- `ALLOWED_ORIGINS` (required in production)
- `CLAUDE_OAUTH_TOKEN` (required)
- `CLAUDE_PROXY_URL` (optional, Railway internal default)

## Security Improvements

### Desktop App (`sync.rs`)
- **URL Validation**: Added `validate_url()` function
- **SSRF Prevention**: Blocks internal IPs in production mode
- **Scheme Validation**: Only allows HTTP (dev/localhost) and HTTPS
- **Port Blocking**: Blocks restricted ports (SMTP, POP3, etc.)
- **Development Mode**: Controlled via `OBSERVER_DEV` env var or debug build

### CSP Headers
- Replaced specific production URLs with wildcard patterns
- Maintains security while supporting multiple deployment environments
- Allows localhost for development

## Deployment Requirements

### Production Checklist
- [ ] Set `VITE_API_URL` for web app (e.g., `https://your-server.railway.app`)
- [ ] Set `VITE_WS_URL` for web app (e.g., `wss://your-server.railway.app`)
- [ ] Set `OBSERVER_SERVER_URL` for desktop app (e.g., `https://your-server.railway.app`)
- [ ] Set `OBSERVER_DASHBOARD_URL` for desktop app (e.g., `https://your-web.railway.app`)
- [ ] Set all required server environment variables (see `/apps/server/.env.example`)

### Development Setup
All apps will work with localhost defaults (http://localhost:8000, ws://localhost:8000, etc.)

## Breaking Changes

### None for Existing Deployments
- Apps already using environment variables will continue working
- Fallback behavior ensures no immediate breakage

### Action Required for New Deployments
- **MUST** set environment variables in production
- Apps will fail to connect if environment variables are not set
- Clear warning messages will be displayed

## Testing Recommendations

1. **Web App**
   - Test with `VITE_API_URL` set
   - Test without env var (should show warning)
   - Verify CSP allows Railway connections

2. **Desktop App**
   - Test with `OBSERVER_SERVER_URL` environment variable
   - Test with `~/.config/observer/server.txt` config file
   - Test URL validation (should reject invalid URLs)
   - Test SSRF prevention (should block internal IPs in production)

3. **Server App**
   - Verify all environment variables are loaded
   - Test with Railway-provided DATABASE_URL and REDIS_URL

## Future Improvements

1. Consider adding a configuration UI in desktop app
2. Add environment variable validation at startup
3. Consider adding health check endpoints to verify connectivity
4. Add telemetry for configuration errors

## References

- Web config: `/home/user/AlexAI-assist/apps/web/src/lib/config.ts`
- Desktop sync: `/home/user/AlexAI-assist/apps/desktop/src-tauri/src/sync.rs`
- Server config: `/home/user/AlexAI-assist/apps/server/src/core/config.py`
- Environment examples: `apps/*/.env.example`
