/**
 * Runtime configuration.
 * Env vars are injected at build time via vite.config.ts loadEnv.
 */

const envApiUrl = import.meta.env.VITE_API_URL;
const envWsUrl = import.meta.env.VITE_WS_URL;

// Railway server URL for production fallback
const RAILWAY_SERVER_URL = 'https://server-production-6bb7.up.railway.app';

function getApiUrl(): string {
  if (envApiUrl) return envApiUrl;

  if (typeof window !== 'undefined') {
    const host = window.location.hostname;

    // Development fallback
    if (host === 'localhost' || host === '127.0.0.1') {
      return 'http://localhost:8000';
    }

    // Production fallback: infer from current host
    const isRailway = host.includes('railway.app');
    if (isRailway) {
      return RAILWAY_SERVER_URL;
    }
  }

  // Default fallback
  return 'http://localhost:8000';
}

function getWsUrl(): string {
  if (envWsUrl) return envWsUrl;

  if (typeof window !== 'undefined') {
    const host = window.location.hostname;

    // Development fallback
    if (host === 'localhost' || host === '127.0.0.1') {
      return 'ws://localhost:8000';
    }

    // Production fallback: infer from current host
    const isRailway = host.includes('railway.app');
    if (isRailway) {
      return RAILWAY_SERVER_URL.replace('https://', 'wss://');
    }
  }

  // Default fallback
  return 'ws://localhost:8000';
}

export const config = {
  apiUrl: getApiUrl(),
  wsUrl: getWsUrl(),
};
