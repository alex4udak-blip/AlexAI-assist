/**
 * Runtime configuration.
 * Env vars are injected at build time via vite.config.ts loadEnv.
 */

const envApiUrl = import.meta.env.VITE_API_URL;
const envWsUrl = import.meta.env.VITE_WS_URL;

function getApiUrl(): string {
  if (envApiUrl) return envApiUrl;

  // Development fallback
  if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    return 'http://localhost:8000';
  }

  return 'http://localhost:8000';
}

function getWsUrl(): string {
  if (envWsUrl) return envWsUrl;

  // Development fallback
  if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    return 'ws://localhost:8000';
  }

  return 'ws://localhost:8000';
}

export const config = {
  apiUrl: getApiUrl(),
  wsUrl: getWsUrl(),
};
