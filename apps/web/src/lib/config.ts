/**
 * Runtime configuration that works in both dev and production.
 * Uses environment variables if available, otherwise derives from current hostname.
 */

// Track if we've already warned (to avoid spam)
let warnedApi = false;
let warnedWs = false;

function getApiUrl(): string {
  // First try environment variable (set at build time on Railway)
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl) return envUrl;

  // In development, use localhost
  if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    return 'http://localhost:8000';
  }

  // In production - derive from current hostname
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;

    // If on Railway, env vars MUST be set during build
    if (hostname.includes('.up.railway.app')) {
      if (!warnedApi) {
        warnedApi = true;
        console.error('VITE_API_URL not set in Railway build variables');
      }
      // Try to derive from server service name pattern
      // This is a fallback - proper fix is to set env vars
      const serverUrl = hostname.replace('web-', 'server-');
      return `${protocol}//${serverUrl}`;
    }

    return `${protocol}//${hostname}:8000`;
  }

  return 'http://localhost:8000';
}

function getWsUrl(): string {
  // First try environment variable (set at build time on Railway)
  const envUrl = import.meta.env.VITE_WS_URL;
  if (envUrl) return envUrl;

  // In development, use localhost
  if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    return 'ws://localhost:8000';
  }

  // In production - derive from current hostname
  if (typeof window !== 'undefined') {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const hostname = window.location.hostname;

    if (hostname.includes('.up.railway.app')) {
      if (!warnedWs) {
        warnedWs = true;
        console.error('VITE_WS_URL not set in Railway build variables');
      }
      // Try to derive from server service name pattern
      const serverUrl = hostname.replace('web-', 'server-');
      return `${wsProtocol}//${serverUrl}`;
    }

    return `${wsProtocol}//${hostname}:8000`;
  }

  return 'ws://localhost:8000';
}

export const config = {
  apiUrl: getApiUrl(),
  wsUrl: getWsUrl(),
};
