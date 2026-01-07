/**
 * Runtime configuration that works in both dev and production.
 * Uses environment variables baked at build time.
 */

function getApiUrl(): string {
  // Environment variable set at build time
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl) return envUrl;

  // Development fallback
  if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    return 'http://localhost:8000';
  }

  // Production fallback - use same origin with /api path
  // This requires a reverse proxy or the server to be on same domain
  if (typeof window !== 'undefined') {
    return `${window.location.protocol}//${window.location.host}`;
  }

  return 'http://localhost:8000';
}

function getWsUrl(): string {
  // Environment variable set at build time
  const envUrl = import.meta.env.VITE_WS_URL;
  if (envUrl) return envUrl;

  // Development fallback
  if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    return 'ws://localhost:8000';
  }

  // Production fallback
  if (typeof window !== 'undefined') {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${wsProtocol}//${window.location.host}`;
  }

  return 'ws://localhost:8000';
}

export const config = {
  apiUrl: getApiUrl(),
  wsUrl: getWsUrl(),
};
