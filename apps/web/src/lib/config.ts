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

  // In production on Railway - use the actual server domain
  const hostname = window.location.hostname;
  if (hostname.includes('.up.railway.app')) {
    // Railway assigns different IDs to each service, so we hardcode the server URL
    return 'https://server-production-0b14.up.railway.app';
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

  // In production on Railway - use the actual server domain
  const hostname = window.location.hostname;
  if (hostname.includes('.up.railway.app')) {
    return 'wss://server-production-0b14.up.railway.app';
  }

  // Fallback
  return '';
}

export const config = {
  apiUrl: getApiUrl(),
  wsUrl: getWsUrl(),
};
