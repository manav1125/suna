import { createClient } from '@/lib/supabase/client';
import type { Session, User } from '@supabase/supabase-js';

const DEFAULT_AUTH_TIMEOUT_MS = 3500;
const TOKEN_EXPIRY_SKEW_MS = 30_000;
const STORAGE_SCAN_COOLDOWN_MS = 750;

let cachedToken: string | null = null;
let cachedTokenExpiryMs = 0;
let lastStorageScanMs = 0;

function decodeBase64Url(input: string): string | null {
  try {
    const normalized = input.replace(/-/g, '+').replace(/_/g, '/');
    const padding = normalized.length % 4;
    const base64 = padding ? `${normalized}${'='.repeat(4 - padding)}` : normalized;

    if (typeof atob === 'function') {
      return atob(base64);
    }

  } catch {
    // Ignore decode errors.
  }

  return null;
}

type JwtPayload = {
  exp?: number;
  sub?: string;
  role?: string;
  aud?: string | string[];
  iss?: string;
  ref?: string;
};

const EXPECTED_SUPABASE_REF = (() => {
  const rawUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  if (!rawUrl) return null;
  try {
    const hostname = new URL(rawUrl).hostname.toLowerCase();
    const ref = hostname.split('.')[0];
    return ref || null;
  } catch {
    return null;
  }
})();

function parseJwtPayload(token: string): JwtPayload | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payloadJson = decodeBase64Url(parts[1]);
    if (!payloadJson) return null;
    const payload = JSON.parse(payloadJson);
    if (!payload || typeof payload !== 'object') return null;
    return payload as JwtPayload;
  } catch {
    return null;
  }
}

function getTokenExpiryMs(token: string): number {
  const payload = parseJwtPayload(token);
  if (!payload?.exp || typeof payload.exp !== 'number') {
    return 0;
  }
  return payload.exp * 1000;
}

function looksLikeJwt(value: unknown): value is string {
  return typeof value === 'string' && value.split('.').length === 3;
}

function isUserAccessToken(token: string): boolean {
  const payload = parseJwtPayload(token);
  if (!payload) return false;
  if (typeof payload.sub !== 'string' || payload.sub.trim().length === 0) return false;
  const role = typeof payload.role === 'string' ? payload.role.toLowerCase() : '';
  if (role === 'anon' || role === 'service_role') return false;
  if (EXPECTED_SUPABASE_REF) {
    const ref = typeof payload.ref === 'string' ? payload.ref.toLowerCase() : '';
    if (ref && ref !== EXPECTED_SUPABASE_REF) return false;
    const issuer = typeof payload.iss === 'string' ? payload.iss.toLowerCase() : '';
    if (issuer && !issuer.includes(`${EXPECTED_SUPABASE_REF}.supabase.`)) return false;
  }
  return true;
}

function isTokenFresh(token: string): boolean {
  const expiry = getTokenExpiryMs(token);
  if (!expiry) return true;
  return expiry > Date.now() + TOKEN_EXPIRY_SKEW_MS;
}

function setCachedToken(token: string | null) {
  if (token && (!isUserAccessToken(token) || !isTokenFresh(token))) {
    cachedToken = null;
    cachedTokenExpiryMs = 0;
    return;
  }
  cachedToken = token;
  cachedTokenExpiryMs = token ? getTokenExpiryMs(token) : 0;
}

function getCachedToken(): string | null {
  if (!cachedToken) return null;
  if (!isUserAccessToken(cachedToken)) {
    cachedToken = null;
    cachedTokenExpiryMs = 0;
    return null;
  }
  if (!cachedTokenExpiryMs) return cachedToken;

  if (cachedTokenExpiryMs <= Date.now() + TOKEN_EXPIRY_SKEW_MS) {
    cachedToken = null;
    cachedTokenExpiryMs = 0;
    return null;
  }

  return cachedToken;
}

function extractTokenFromUnknown(value: unknown): string | null {
  if (!value) return null;

  if (looksLikeJwt(value)) {
    return isUserAccessToken(value) ? value : null;
  }

  if (Array.isArray(value)) {
    for (const item of value) {
      const token = extractTokenFromUnknown(item);
      if (token) return token;
    }
    return null;
  }

  if (typeof value === 'object') {
    const record = value as Record<string, unknown>;
    const directCandidates = [
      record.access_token,
      record.token,
      record.jwt,
      record.id_token,
    ];

    for (const candidate of directCandidates) {
      if (looksLikeJwt(candidate) && isUserAccessToken(candidate)) {
        return candidate;
      }
    }

    const nestedCandidates = [
      record.currentSession,
      record.session,
      (record.data as Record<string, unknown> | undefined)?.session,
      record.auth,
      record.user,
      record.currentState,
    ];

    for (const candidate of nestedCandidates) {
      const token = extractTokenFromUnknown(candidate);
      if (token) return token;
    }
  }

  return null;
}

function looksLikeSession(value: unknown): value is Session {
  return (
    !!value &&
    typeof value === 'object' &&
    typeof (value as Record<string, unknown>).access_token === 'string'
  );
}

function extractSessionFromUnknown(value: unknown): Session | null {
  if (!value) return null;

  if (looksLikeSession(value)) {
    return value;
  }

  if (Array.isArray(value)) {
    for (const item of value) {
      const session = extractSessionFromUnknown(item);
      if (session) return session;
    }
    return null;
  }

  if (typeof value === 'object') {
    const record = value as Record<string, unknown>;
    const candidates = [
      record.currentSession,
      record.session,
      (record.data as Record<string, unknown> | undefined)?.session,
      record.auth,
    ];

    for (const candidate of candidates) {
      const session = extractSessionFromUnknown(candidate);
      if (session) return session;
    }
  }

  return null;
}

function parseStorageValue(raw: string): unknown {
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

function getStorageKeys(): string[] {
  if (typeof window === 'undefined') return [];

  const keys: string[] = [];
  for (let i = 0; i < window.localStorage.length; i += 1) {
    const key = window.localStorage.key(i);
    if (!key) continue;
    if (
      EXPECTED_SUPABASE_REF &&
      key.startsWith('sb-') &&
      key.includes('auth-token') &&
      !key.startsWith(`sb-${EXPECTED_SUPABASE_REF}-`)
    ) {
      continue;
    }
    keys.push(key);
  }
  return keys;
}

function rankStorageKey(key: string): number {
  if (key.startsWith('sb-') && key.includes('auth-token')) return 0;
  if (key.includes('supabase') && key.includes('auth')) return 1;
  if (key === 'auth') return 2;
  return 3;
}

function readSnapshotFromStorage(): { token: string | null; session: Session | null } {
  if (typeof window === 'undefined') {
    return { token: null, session: null };
  }

  const now = Date.now();
  if (now - lastStorageScanMs < STORAGE_SCAN_COOLDOWN_MS) {
    const token = getCachedToken();
    return { token, session: null };
  }
  lastStorageScanMs = now;

  const keys = getStorageKeys().sort((a, b) => rankStorageKey(a) - rankStorageKey(b));

  for (const key of keys) {
    if (!key.includes('auth') && !key.startsWith('sb-')) {
      continue;
    }

    try {
      const rawValue = window.localStorage.getItem(key);
      if (!rawValue) continue;
      const parsed = parseStorageValue(rawValue);

      const session = extractSessionFromUnknown(parsed);
      const token =
        (session?.access_token &&
        looksLikeJwt(session.access_token) &&
        isUserAccessToken(session.access_token)
          ? session.access_token
          : null) ||
        extractTokenFromUnknown(parsed);

      if (!token || !isUserAccessToken(token) || !isTokenFresh(token)) {
        continue;
      }

      setCachedToken(token);
      return { token, session };
    } catch {
      // Ignore malformed storage entries.
    }
  }

  return { token: null, session: null };
}

export function cacheAuthTokenFromSession(session: Session | null | undefined): void {
  const token =
    session?.access_token &&
    looksLikeJwt(session.access_token) &&
    isUserAccessToken(session.access_token)
      ? session.access_token
      : null;
  if (!token) {
    setCachedToken(null);
    return;
  }

  if (!isTokenFresh(token)) {
    return;
  }
  setCachedToken(token);
}

export function getStoredAuthSnapshot(): { token: string | null; session: Session | null; user: User | null } {
  const snapshot = readSnapshotFromStorage();
  return {
    token: snapshot.token,
    session: snapshot.session,
    user: snapshot.session?.user ?? null,
  };
}

export async function getAuthSessionWithTimeout(timeoutMs: number = DEFAULT_AUTH_TIMEOUT_MS): Promise<Session | null> {
  const supabase = createClient();

  try {
    const sessionResult = await Promise.race([
      supabase.auth.getSession(),
      new Promise<null>((resolve) => setTimeout(() => resolve(null), timeoutMs)),
    ]);

    if (!sessionResult || !('data' in sessionResult)) {
      return null;
    }

    const session = sessionResult.data?.session || null;
    if (session?.access_token) {
      cacheAuthTokenFromSession(session);
    }

    return session;
  } catch {
    return null;
  }
}

export async function getAuthTokenWithTimeout(timeoutMs: number = DEFAULT_AUTH_TIMEOUT_MS): Promise<string | null> {
  const memoryToken = getCachedToken();
  if (memoryToken) return memoryToken;

  const storedSnapshot = readSnapshotFromStorage();
  if (storedSnapshot.token) return storedSnapshot.token;

  const session = await getAuthSessionWithTimeout(timeoutMs);
  const token = session?.access_token || null;

  if (token && isUserAccessToken(token) && isTokenFresh(token)) {
    setCachedToken(token);
    return token;
  }

  // One extended retry for cold starts / delayed session refreshes.
  const extendedTimeout = Math.max(8000, timeoutMs);
  if (extendedTimeout !== timeoutMs) {
    const extendedSession = await getAuthSessionWithTimeout(extendedTimeout);
    const extendedToken = extendedSession?.access_token || null;
    if (extendedToken && isUserAccessToken(extendedToken) && isTokenFresh(extendedToken)) {
      setCachedToken(extendedToken);
      return extendedToken;
    }
  }

  return null;
}
