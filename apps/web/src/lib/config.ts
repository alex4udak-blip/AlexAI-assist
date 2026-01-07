/**
 * Runtime configuration.
 * Env vars are injected at build time via vite.config.ts loadEnv.
 */

const envApiUrl = import.meta.env.VITE_API_URL;
const envWsUrl = import.meta.env.VITE_WS_URL;

// Production URLs (Railway)
const PRODUCTION_API_URL = 'https://server-production-20d71.up.railway.app';
const PRODUCTION_WS_URL = 'wss://server-production-20d71.up.railway.app';

function getApiUrl(): string {
  if (envApiUrl) return envApiUrl;

  if (typeof window !== 'undefined') {
    // Development fallback
    if (window.location.hostname === 'localhost') {
      return 'http://localhost:8000';
    }
    // Production fallback
    return PRODUCTION_API_URL;
  }

  return 'http://localhost:8000';
}

function getWsUrl(): string {
  if (envWsUrl) return envWsUrl;

  if (typeof window !== 'undefined') {
    // Development fallback
    if (window.location.hostname === 'localhost') {
      return 'ws://localhost:8000';
    }
    // Production fallback
    return PRODUCTION_WS_URL;
  }

  return 'ws://localhost:8000';
}

export const config = {
  apiUrl: getApiUrl(),
  wsUrl: getWsUrl(),
};
