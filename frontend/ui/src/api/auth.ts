import type { Meta, Principal, Result } from '@/types';

import { http } from './http';

export interface Credentials {
  readonly email: string;
  readonly password: string;
}

/** Current principal; the session cookie is sent automatically. 401 -> unauthorized error. */
export function getMe(signal?: AbortSignal): Promise<Result<Principal>> {
  return http.get<Principal>('/auth/me', { signal });
}

/** Sets the HttpOnly session cookie on success. */
export function login(credentials: Credentials): Promise<Result<Principal>> {
  return http.post<Principal>('/auth/login', credentials);
}

export function logout(): Promise<Result<void>> {
  return http.post<void>('/auth/logout');
}

/**
 * EE: exchange a Stytch session token/JWT for a LAVS session. The backend verifies the
 * token with Stytch, sets the HttpOnly `lavs_session` cookie, and returns the principal.
 */
export function stytchCallback(stytchToken: string): Promise<Result<Principal>> {
  return http.post<Principal>('/auth/stytch/callback', { stytch_token: stytchToken });
}

/** Deploy config: edition + enabled auth modes, so the UI renders the right login. */
export function getMeta(signal?: AbortSignal): Promise<Result<Meta>> {
  return http.get<Meta>('/meta', { signal });
}
