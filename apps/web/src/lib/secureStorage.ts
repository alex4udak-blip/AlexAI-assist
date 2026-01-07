/**
 * Secure client-side storage utilities with encryption support.
 * Use these utilities instead of directly accessing localStorage/sessionStorage.
 */

// Simple XOR encryption for client-side storage (not cryptographically secure, but better than plaintext)
// For production, consider using Web Crypto API with a key derived from user session
const STORAGE_KEY = 'observer_secure_key';

/**
 * Encrypts a string using simple XOR cipher.
 * NOTE: This is NOT cryptographically secure. For sensitive data,
 * implement proper encryption using Web Crypto API.
 */
function encrypt(text: string, key: string): string {
  let result = '';
  for (let i = 0; i < text.length; i++) {
    result += String.fromCharCode(text.charCodeAt(i) ^ key.charCodeAt(i % key.length));
  }
  return btoa(result); // Base64 encode
}

/**
 * Decrypts a string encrypted with the encrypt function.
 */
function decrypt(encrypted: string, key: string): string {
  const decoded = atob(encrypted); // Base64 decode
  let result = '';
  for (let i = 0; i < decoded.length; i++) {
    result += String.fromCharCode(decoded.charCodeAt(i) ^ key.charCodeAt(i % key.length));
  }
  return result;
}

/**
 * Storage type for sensitive vs non-sensitive data
 */
export type StorageType = 'local' | 'session';

/**
 * Storage options
 */
interface StorageOptions {
  type?: StorageType;
  encrypt?: boolean;
}

/**
 * Validates and sanitizes data before storage
 */
function sanitizeData(data: unknown): string {
  if (typeof data === 'string') {
    return data;
  }
  return JSON.stringify(data);
}

/**
 * Gets the appropriate storage based on type
 */
function getStorage(type: StorageType): Storage {
  return type === 'session' ? sessionStorage : localStorage;
}

/**
 * Secure storage wrapper for client-side data
 */
export class SecureStorage {
  private key: string;

  constructor(key: string = STORAGE_KEY) {
    this.key = key;
  }

  /**
   * Store data securely
   */
  setItem(name: string, value: unknown, options: StorageOptions = {}): void {
    const { type = 'local', encrypt: shouldEncrypt = false } = options;

    try {
      const storage = getStorage(type);
      const data = sanitizeData(value);
      const finalValue = shouldEncrypt ? encrypt(data, this.key) : data;

      storage.setItem(name, finalValue);
    } catch (error) {
      console.error('Failed to store data:', error);
      throw new Error('Storage failed. Check browser storage limits.');
    }
  }

  /**
   * Retrieve data from storage
   */
  getItem<T = string>(name: string, options: StorageOptions = {}): T | null {
    const { type = 'local', encrypt: isEncrypted = false } = options;

    try {
      const storage = getStorage(type);
      const value = storage.getItem(name);

      if (value === null) {
        return null;
      }

      const decrypted = isEncrypted ? decrypt(value, this.key) : value;

      // Try to parse as JSON, otherwise return as-is
      try {
        return JSON.parse(decrypted) as T;
      } catch {
        return decrypted as T;
      }
    } catch (error) {
      console.error('Failed to retrieve data:', error);
      return null;
    }
  }

  /**
   * Remove item from storage
   */
  removeItem(name: string, type: StorageType = 'local'): void {
    try {
      const storage = getStorage(type);
      storage.removeItem(name);
    } catch (error) {
      console.error('Failed to remove data:', error);
    }
  }

  /**
   * Clear all storage (use with caution)
   */
  clear(type: StorageType = 'local'): void {
    try {
      const storage = getStorage(type);
      storage.clear();
    } catch (error) {
      console.error('Failed to clear storage:', error);
    }
  }

  /**
   * Check if storage is available
   */
  static isAvailable(type: StorageType = 'local'): boolean {
    try {
      const storage = getStorage(type);
      const testKey = '__storage_test__';
      storage.setItem(testKey, 'test');
      storage.removeItem(testKey);
      return true;
    } catch {
      return false;
    }
  }
}

/**
 * Default secure storage instance
 */
export const secureStorage = new SecureStorage();

/**
 * Cookie utilities with secure flags
 */
export class SecureCookies {
  /**
   * Set a cookie with secure flags
   */
  static set(
    name: string,
    value: string,
    options: {
      maxAge?: number; // seconds
      expires?: Date;
      path?: string;
      domain?: string;
      secure?: boolean;
      sameSite?: 'Strict' | 'Lax' | 'None';
      httpOnly?: boolean; // Note: Can't be set from JavaScript
    } = {}
  ): void {
    const {
      maxAge,
      expires,
      path = '/',
      domain,
      secure = true, // Always secure by default
      sameSite = 'Strict', // Strict by default
    } = options;

    let cookie = `${encodeURIComponent(name)}=${encodeURIComponent(value)}`;

    if (maxAge !== undefined) {
      cookie += `; Max-Age=${maxAge}`;
    }

    if (expires) {
      cookie += `; Expires=${expires.toUTCString()}`;
    }

    cookie += `; Path=${path}`;

    if (domain) {
      cookie += `; Domain=${domain}`;
    }

    if (secure) {
      cookie += '; Secure';
    }

    cookie += `; SameSite=${sameSite}`;

    document.cookie = cookie;
  }

  /**
   * Get a cookie value
   */
  static get(name: string): string | null {
    const matches = document.cookie.match(
      new RegExp(`(?:^|; )${encodeURIComponent(name)}=([^;]*)`)
    );
    return matches ? decodeURIComponent(matches[1]) : null;
  }

  /**
   * Delete a cookie
   */
  static delete(name: string, path: string = '/'): void {
    this.set(name, '', { maxAge: -1, path });
  }

  /**
   * Check if cookies are enabled
   */
  static isEnabled(): boolean {
    try {
      const testKey = '__cookie_test__';
      this.set(testKey, 'test', { secure: false });
      const result = this.get(testKey) === 'test';
      this.delete(testKey);
      return result;
    } catch {
      return false;
    }
  }
}

/**
 * Validator for stored data
 */
export class StorageValidator {
  /**
   * Validate settings object
   */
  static validateSettings(data: unknown): boolean {
    if (!data || typeof data !== 'object') {
      return false;
    }

    const settings = data as Record<string, unknown>;

    // Define expected schema
    const schema = {
      notifications: 'boolean',
      autoStart: 'boolean',
      syncInterval: 'string',
      theme: 'string',
      dataRetention: 'string',
    };

    // Check all required fields
    for (const [key, expectedType] of Object.entries(schema)) {
      if (!(key in settings) || typeof settings[key] !== expectedType) {
        return false;
      }
    }

    return true;
  }

  /**
   * Sanitize HTML to prevent XSS
   */
  static sanitizeHtml(html: string): string {
    const div = document.createElement('div');
    div.textContent = html;
    return div.innerHTML;
  }

  /**
   * Validate URL to prevent javascript: protocol and XSS
   */
  static isValidUrl(url: string): boolean {
    try {
      const parsed = new URL(url);
      return ['http:', 'https:', 'wss:', 'ws:'].includes(parsed.protocol);
    } catch {
      return false;
    }
  }
}
