/**
 * Runtime configuration.
 * Priority: env vars (build time) > Railway derivation > localhost
 */

// Debug: log what env vars we have
const envApiUrl = import.meta.env.VITE_API_URL;
const envWsUrl = import.meta.env.VITE_WS_URL;
console.log('[Config] VITE_API_URL:', envApiUrl || '(not set)');
console.log('[Config] VITE_WS_URL:', envWsUrl || '(not set)');

function getApiUrl(): string {
  // 1. Environment variable (set at build time)
  if (envApiUrl) return envApiUrl;

  // 2. Development
  if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    return 'http://localhost:8000';
  }

  // 3. Railway fallback - try to derive server URL
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;

    if (hostname.includes('.up.railway.app')) {
      return 'https://server-production-0b14.up.railway.app';
    }
  }

  return 'http://localhost:8000';
}

function getWsUrl(): string {
  // 1. Environment variable (set at build time)
  if (envWsUrl) return envWsUrl;

  // 2. Development
  if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    return 'ws://localhost:8000';
  }

  // 3. Railway fallback
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

    if (hostname.includes('.up.railway.app')) {
      return 'wss://server-production-0b14.up.railway.app';
    }
  }

  return 'ws://localhost:8000';
}

export const config = {
  apiUrl: getApiUrl(),
  wsUrl: getWsUrl(),
};

console.log('[Config] Final API URL:', config.apiUrl);
console.log('[Config] Final WS URL:', config.wsUrl);
