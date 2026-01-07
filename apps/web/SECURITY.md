# Frontend Security Guidelines

## Overview

This document outlines the security measures implemented in the Observer web frontend and best practices for maintaining secure client-side code.

## Security Measures Implemented

### 1. Secure Storage

**Location:** `/home/user/AlexAI-assist/apps/web/src/lib/secureStorage.ts`

- **SecureStorage class**: Wrapper around localStorage/sessionStorage with validation and optional encryption
- **StorageValidator**: Validates data before storage to prevent injection attacks
- **SecureCookies**: Cookie utilities with secure flags enabled by default

**Features:**
- Data validation before storage
- Optional encryption for sensitive data
- Support for both localStorage and sessionStorage
- Automatic sanitization to prevent XSS
- Secure cookie flags (Secure, SameSite=Strict)

**Usage Example:**
```typescript
import { secureStorage } from '@/lib/secureStorage';

// Store non-sensitive data
secureStorage.setItem('user-preferences', preferences, {
  type: 'local',
  encrypt: false
});

// Store sensitive data
secureStorage.setItem('sensitive-data', data, {
  type: 'session',
  encrypt: true
});
```

### 2. Authentication Token Storage

**Location:** `/home/user/AlexAI-assist/apps/web/src/lib/authStorage.ts`

- **AuthStorage class**: Manages authentication tokens securely
- Stores access tokens in sessionStorage (cleared on browser close)
- Encrypts tokens before storage
- Automatic token expiration checking
- Clears tokens on 401 responses

**Features:**
- Session-based access token storage
- Encrypted token storage
- Automatic expiration validation
- Refresh token support
- API key management (with warnings)

**Usage Example:**
```typescript
import { AuthStorage } from '@/lib/authStorage';

// Store token
AuthStorage.setToken({
  accessToken: 'token',
  expiresAt: Date.now() + 3600000,
  tokenType: 'Bearer'
});

// Check authentication
if (AuthStorage.isAuthenticated()) {
  // User is authenticated
}

// Clear on logout
AuthStorage.clearToken();
```

### 3. Secure API Client

**Location:** `/home/user/AlexAI-assist/apps/web/src/lib/api.ts`

- Automatically includes authentication headers when tokens are available
- Handles 401 responses by clearing invalid tokens
- HTTPS enforcement in production
- Content-Type validation

**Features:**
- Automatic Bearer token injection
- 401 response handling
- Error sanitization
- HTTPS URLs in production

### 4. Data Validation

**Current Implementation:**
- Settings data validated before storage
- URL validation to prevent javascript: protocol
- HTML sanitization to prevent XSS
- Type checking for all stored data

## Current Storage Usage

### localStorage
**File:** `/home/user/AlexAI-assist/apps/web/src/pages/Settings.tsx`

Stores only **non-sensitive** user preferences:
- notifications (boolean)
- autoStart (boolean)
- syncInterval (string)
- theme (string)
- dataRetention (string)

**Security:** Uses validation via `StorageValidator.validateSettings()`

### sessionStorage
Currently not used. Reserved for future session-specific data.

### Cookies
Currently not used. `SecureCookies` class available with secure defaults:
- Secure flag: enabled by default
- SameSite: Strict by default
- HttpOnly: should be set server-side for sensitive cookies

## Security Best Practices

### DO:
1. ✅ Use `secureStorage` instead of direct localStorage/sessionStorage access
2. ✅ Store authentication tokens in sessionStorage with encryption
3. ✅ Validate all data before storage
4. ✅ Use HTTPS in production
5. ✅ Clear sensitive data on logout
6. ✅ Sanitize user input before rendering
7. ✅ Use short token expiration times
8. ✅ Validate URLs before navigation
9. ✅ Set secure cookie flags (Secure, SameSite, HttpOnly)
10. ✅ Use Content Security Policy headers

### DON'T:
1. ❌ Store sensitive data in localStorage (use sessionStorage instead)
2. ❌ Store API keys client-side (use backend proxy)
3. ❌ Trust data from localStorage without validation
4. ❌ Store passwords or credit card data
5. ❌ Use HTTP in production
6. ❌ Store tokens without encryption
7. ❌ Store refresh tokens client-side (use HttpOnly cookies server-side)
8. ❌ Render user input without sanitization
9. ❌ Allow javascript: or data: URLs
10. ❌ Store personal identifiable information (PII) client-side

## Content Security Policy (CSP)

**Recommended CSP headers** (to be set in backend or CDN):

```
Content-Security-Policy:
  default-src 'self';
  script-src 'self' 'unsafe-inline' 'unsafe-eval';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:;
  font-src 'self' data:;
  connect-src 'self' https://*.railway.app wss://*.railway.app http://localhost:* ws://localhost:*;
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self';
```

**Note:** Adjust `unsafe-inline` and `unsafe-eval` as needed once inline scripts are eliminated.

## HTTPS Enforcement

### Production Configuration
**File:** `/home/user/AlexAI-assist/apps/web/src/lib/config.ts`

- Production server uses HTTPS (configured via VITE_API_URL environment variable)
- WebSocket uses WSS (configured via VITE_WS_URL environment variable)
- Development uses HTTP/WS for localhost
- All production URLs must be configured via environment variables

### Upgrade Insecure Requests
Add this meta tag to `/home/user/AlexAI-assist/apps/web/index.html`:

```html
<meta http-equiv="Content-Security-Policy" content="upgrade-insecure-requests">
```

## XSS Prevention

### Implemented Measures:
1. React's automatic XSS protection (escapes by default)
2. URL validation before navigation
3. HTML sanitization utility
4. No `dangerouslySetInnerHTML` usage
5. Input validation on storage

### Additional Recommendations:
1. Enable strict TypeScript mode (already enabled)
2. Validate all API responses
3. Sanitize markdown before rendering
4. Use DOMPurify for rich text if needed

## Sensitive Data Checklist

When adding new features, check:

- [ ] Does it store user credentials? → Use `AuthStorage` with sessionStorage
- [ ] Does it store API keys? → Avoid client-side storage, use backend proxy
- [ ] Does it store PII? → Minimize storage, use encryption, prefer sessionStorage
- [ ] Does it store payment info? → Never store client-side, use tokenization
- [ ] Does it store preferences? → OK to use localStorage without encryption
- [ ] Does it use cookies? → Use `SecureCookies` with secure flags
- [ ] Does it handle authentication? → Use `AuthStorage` and secure tokens

## Security Audit Log

| Date | Change | File |
|------|--------|------|
| 2026-01-07 | Created SecureStorage utility | secureStorage.ts |
| 2026-01-07 | Created AuthStorage utility | authStorage.ts |
| 2026-01-07 | Updated Settings to use secure storage | Settings.tsx |
| 2026-01-07 | Updated API client with auth headers | api.ts |
| 2026-01-07 | Created security documentation | SECURITY.md |

## Future Improvements

1. Implement Web Crypto API for stronger encryption
2. Add Content Security Policy headers (backend/CDN)
3. Implement CSRF protection for state-changing operations
4. Add rate limiting on API calls
5. Implement Subresource Integrity (SRI) for CDN assets
6. Add security headers (X-Frame-Options, X-Content-Type-Options)
7. Implement proper refresh token rotation (backend)
8. Add security.txt file for vulnerability disclosure

## Vulnerability Reporting

If you discover a security vulnerability, please:
1. Do not create a public issue
2. Contact the maintainers privately
3. Provide detailed reproduction steps
4. Allow time for fixes before disclosure

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Web Security Guidelines](https://infosec.mozilla.org/guidelines/web_security)
- [Content Security Policy](https://content-security-policy.com/)
- [Secure Cookie Flags](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies)
