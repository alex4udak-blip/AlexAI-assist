/**
 * Runtime configuration that works in both dev and production.
 * Uses environment variables if available, otherwise derives from current hostname.
 */

function getApiUrl(): string {
  // First try environment variable
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl) return envUrl;

  // In development, use localhost
  if (window.location.hostname === 'localhost') {
    return 'http://localhost:8000';
  }

  // In production on Railway, derive server URL from web URL
  // web-production-XXXX.up.railway.app -> server-production-XXXX.up.railway.app
  const hostname = window.location.hostname;
  if (hostname.includes('.up.railway.app')) {
    const serverHostname = hostname.replace('web-', 'server-');
    return `https://${serverHostname}`;
  }

  // Fallback
  return '';
}

function getWsUrl(): string {
  // First try environment variable
  const envUrl = import.meta.env.VITE_WS_URL;
  if (envUrl) return envUrl;

  // In development, use localhost
  if (window.location.hostname === 'localhost') {
    return 'ws://localhost:8000';
  }

  // In production on Railway, derive from API URL
  const hostname = window.location.hostname;
  if (hostname.includes('.up.railway.app')) {
    const serverHostname = hostname.replace('web-', 'server-');
    return `wss://${serverHostname}`;
  }

  // Fallback
  return '';
}

export const config = {
  apiUrl: getApiUrl(),
  wsUrl: getWsUrl(),
};
