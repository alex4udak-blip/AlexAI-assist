/**
 * Runtime configuration.
 * Env vars are injected at build time via vite.config.ts loadEnv.
 */

const envApiUrl = import.meta.env.VITE_API_URL;
const envWsUrl = import.meta.env.VITE_WS_URL;

// Development defaults
const DEV_API_URL = 'http://localhost:8000';
const DEV_WS_URL = 'ws://localhost:8000';

function getApiUrl(): string {
  // Priority 1: Environment variable (set at build time or runtime)
  if (envApiUrl) return envApiUrl;

  // Priority 2: Development fallback
  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') {
      return DEV_API_URL;
    }
  }

  // Priority 3: Default to development
  // Note: Production deployments MUST set VITE_API_URL environment variable
  console.warn('[Config] VITE_API_URL not set, using development default');
  return DEV_API_URL;
}

function getWsUrl(): string {
  // Priority 1: Environment variable (set at build time or runtime)
  if (envWsUrl) return envWsUrl;

  // Priority 2: Development fallback
  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') {
      return DEV_WS_URL;
    }
  }

  // Priority 3: Default to development
  // Note: Production deployments MUST set VITE_WS_URL environment variable
  console.warn('[Config] VITE_WS_URL not set, using development default');
  return DEV_WS_URL;
}

export const config = {
  apiUrl: getApiUrl(),
  wsUrl: getWsUrl(),
};
