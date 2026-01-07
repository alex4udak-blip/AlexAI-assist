/**
 * Authentication token storage utilities.
 * Use this module for storing authentication tokens securely.
 *
 * Security best practices:
 * 1. Store tokens in sessionStorage (not localStorage) for better security
 * 2. Use encryption for sensitive tokens
 * 3. Clear tokens on logout
 * 4. Set short expiration times
 * 5. Use HttpOnly cookies for refresh tokens (backend implementation required)
 */

import { secureStorage } from './secureStorage';

const AUTH_TOKEN_KEY = 'observer_auth_token';
const REFRESH_TOKEN_KEY = 'observer_refresh_token';

export interface AuthToken {
  accessToken: string;
  refreshToken?: string;
  expiresAt: number; // Unix timestamp
  tokenType: string;
}

/**
 * Authentication storage manager
 */
export class AuthStorage {
  /**
   * Store authentication token
   * NOTE: Stores in sessionStorage for better security (cleared when browser closes)
   */
  static setToken(token: AuthToken): void {
    try {
      // Store access token in sessionStorage with encryption
      secureStorage.setItem(
        AUTH_TOKEN_KEY,
        {
          accessToken: token.accessToken,
          expiresAt: token.expiresAt,
          tokenType: token.tokenType,
        },
        {
          type: 'session',
          encrypt: true, // Encrypt the token
        }
      );

      // Store refresh token separately if provided
      // In production, refresh tokens should be HttpOnly cookies set by the backend
      if (token.refreshToken) {
        secureStorage.setItem(
          REFRESH_TOKEN_KEY,
          token.refreshToken,
          {
            type: 'local', // Refresh tokens can persist longer
            encrypt: true,
          }
        );
      }
    } catch (error) {
      console.error('Failed to store auth token:', error);
      throw new Error('Failed to store authentication token');
    }
  }

  /**
   * Retrieve authentication token
   */
  static getToken(): AuthToken | null {
    try {
      const stored = secureStorage.getItem<{
        accessToken: string;
        expiresAt: number;
        tokenType: string;
      }>(AUTH_TOKEN_KEY, {
        type: 'session',
        encrypt: true,
      });

      if (!stored) {
        return null;
      }

      // Check if token is expired
      if (stored.expiresAt < Date.now()) {
        this.clearToken();
        return null;
      }

      // Get refresh token if exists
      const refreshToken = secureStorage.getItem<string>(
        REFRESH_TOKEN_KEY,
        {
          type: 'local',
          encrypt: true,
        }
      );

      return {
        accessToken: stored.accessToken,
        expiresAt: stored.expiresAt,
        tokenType: stored.tokenType,
        refreshToken: refreshToken || undefined,
      };
    } catch (error) {
      console.error('Failed to retrieve auth token:', error);
      return null;
    }
  }

  /**
   * Get access token string for Authorization header
   */
  static getAccessToken(): string | null {
    const token = this.getToken();
    return token ? token.accessToken : null;
  }

  /**
   * Check if user is authenticated
   */
  static isAuthenticated(): boolean {
    const token = this.getToken();
    return token !== null && token.expiresAt > Date.now();
  }

  /**
   * Clear authentication tokens
   */
  static clearToken(): void {
    try {
      secureStorage.removeItem(AUTH_TOKEN_KEY, 'session');
      secureStorage.removeItem(REFRESH_TOKEN_KEY, 'local');
    } catch (error) {
      console.error('Failed to clear auth token:', error);
    }
  }

  /**
   * Check if token is about to expire (within 5 minutes)
   */
  static isTokenExpiringSoon(): boolean {
    const token = this.getToken();
    if (!token) return false;

    const fiveMinutesFromNow = Date.now() + 5 * 60 * 1000;
    return token.expiresAt < fiveMinutesFromNow;
  }
}

/**
 * API key storage for external services
 * NOTE: Avoid storing API keys client-side when possible.
 * Use backend proxy endpoints instead.
 */
export class ApiKeyStorage {
  /**
   * Store API key (encrypted)
   * WARNING: Client-side API key storage is not secure.
   * Only use for non-critical services or development.
   */
  static setApiKey(service: string, apiKey: string): void {
    console.warn(
      'WARNING: Storing API keys client-side is not secure. Consider using a backend proxy.'
    );

    secureStorage.setItem(`api_key_${service}`, apiKey, {
      type: 'local',
      encrypt: true,
    });
  }

  /**
   * Retrieve API key
   */
  static getApiKey(service: string): string | null {
    return secureStorage.getItem<string>(`api_key_${service}`, {
      type: 'local',
      encrypt: true,
    });
  }

  /**
   * Remove API key
   */
  static removeApiKey(service: string): void {
    secureStorage.removeItem(`api_key_${service}`, 'local');
  }
}
