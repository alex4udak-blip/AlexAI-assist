/**
 * Runtime configuration that works in both dev and production.
 * Uses environment variables if available, otherwise derives from current hostname.
 */

function getApiUrl(): string {
  // First try environment variable (set at build time on Railway)
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl) return envUrl;

  // In development, use localhost
  if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    return 'http://localhost:8000';
  }

  // In production - derive from current hostname
  // Assume server is on same domain with /api prefix or separate subdomain
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;

    // If on Railway, try environment variable first (should be set)
    // Otherwise construct URL dynamically
    if (hostname.includes('.up.railway.app')) {
      // Use VITE_API_URL env var - MUST be set in Railway build variables
      console.warn('VITE_API_URL not set - API calls may fail');
      return '';
    }

    return `${protocol}//${hostname}:8000`;
  }

  return '';
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
      // Use VITE_WS_URL env var - MUST be set in Railway build variables
      console.warn('VITE_WS_URL not set - WebSocket may fail');
      return '';
    }

    return `${wsProtocol}//${hostname}:8000`;
  }

  return '';
}

export const config = {
  apiUrl: getApiUrl(),
  wsUrl: getWsUrl(),
};
