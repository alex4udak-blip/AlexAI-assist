/**
 * Runtime configuration.
 * Env vars are injected at build time via vite.config.ts loadEnv.
 */

const envApiUrl = import.meta.env.VITE_API_URL;
const envWsUrl = import.meta.env.VITE_WS_URL;
const envApiKey = import.meta.env.VITE_API_KEY;

// Development defaults
const DEV_API_URL = 'http://localhost:8000';
const DEV_WS_URL = 'ws://localhost:8000';

function getApiUrl(): string {
  // Priority 1: Environment variable
  if (envApiUrl) return envApiUrl;

  // Priority 2: Development (localhost)
  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') {
      return DEV_API_URL;
    }

    // Priority 3: Railway auto-detection
    if (host.includes('railway.app')) {
      // Replace web service name with server service name
      const serverHost = host.replace(/web-production[^.]*/, 'server-production-0b14');
      return `https://${serverHost}`;
    }
  }

  console.warn('[Config] VITE_API_URL not set, using development default');
  return DEV_API_URL;
}

function getWsUrl(): string {
  // Priority 1: Environment variable
  if (envWsUrl) return envWsUrl;

  // Priority 2: Development (localhost)
  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') {
      return DEV_WS_URL;
    }

    // Priority 3: Railway auto-detection
    if (host.includes('railway.app')) {
      const serverHost = host.replace(/web-production[^.]*/, 'server-production-0b14');
      return `wss://${serverHost}`;
    }
  }

  console.warn('[Config] VITE_WS_URL not set, using development default');
  return DEV_WS_URL;
}

function getApiKey(): string | undefined {
  // Priority 1: Environment variable
  if (envApiKey) return envApiKey;

  // Priority 2: Session storage (for user-entered key)
  if (typeof window !== 'undefined') {
    const stored = sessionStorage.getItem('observer_api_key');
    if (stored) return stored;
  }

  return undefined;
}

export const config = {
  apiUrl: getApiUrl(),
  wsUrl: getWsUrl(),
  apiKey: getApiKey(),
};

/**
 * Fetch wrapper with authentication headers.
 */
export async function apiFetch(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const url = path.startsWith('http') ? path : `${config.apiUrl}${path}`;
  const apiKey = getApiKey();

  const headers = new Headers(options.headers);
  headers.set('Content-Type', 'application/json');
  if (apiKey) {
    headers.set('X-API-Key', apiKey);
  }

  return fetch(url, {
    ...options,
    headers,
  });
}
