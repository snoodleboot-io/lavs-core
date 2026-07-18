import { ApiError, err, ok, type ApiErrorCode, type Result } from '@/types';

/**
 * API base. In dev the Vite proxy maps `/api` -> the backend so the HttpOnly session
 * cookie stays same-origin; a reverse proxy does the same in prod. Override with an
 * absolute `VITE_LAVS_API_URL` to point one build at any backend (CORS + credentials).
 */
export const API_BASE: string = import.meta.env.VITE_LAVS_API_URL
  ? import.meta.env.VITE_LAVS_API_URL.replace(/\/+$/, '')
  : '/api';

const STATUS_TO_CODE: Readonly<Record<number, ApiErrorCode>> = {
  401: 'unauthorized',
  403: 'forbidden',
  404: 'not_found',
  409: 'conflict',
  422: 'validation_error',
};

interface WireError {
  error?: { code?: string; message?: string; details?: Record<string, unknown> | null };
}

interface RequestOptions {
  readonly body?: unknown;
  readonly headers?: Record<string, string>;
  readonly signal?: AbortSignal;
  /** Prevents a double-cut on retries (POST /releases). */
  readonly idempotencyKey?: string;
}

function isApiErrorCode(value: string | undefined): value is ApiErrorCode {
  return (
    value === 'unauthorized' ||
    value === 'forbidden' ||
    value === 'domain_not_allowed' ||
    value === 'not_found' ||
    value === 'conflict' ||
    value === 'validation_error'
  );
}

async function toApiError(response: Response): Promise<ApiError> {
  const fallback = STATUS_TO_CODE[response.status] ?? 'unknown';
  let body: WireError = {};
  try {
    body = (await response.json()) as WireError;
  } catch {
    // Non-JSON error body — fall back to status mapping.
  }
  const wire = body.error;
  const code = isApiErrorCode(wire?.code) ? wire.code : fallback;
  const message = wire?.message ?? `Request failed with status ${response.status}`;
  return new ApiError(code, message, response.status, wire?.details ?? null);
}

async function request<T>(
  method: string,
  path: string,
  options: RequestOptions = {},
): Promise<Result<T>> {
  const headers: Record<string, string> = { Accept: 'application/json', ...options.headers };
  const init: RequestInit = {
    method,
    headers,
    // Send/receive the HttpOnly session cookie.
    credentials: 'include',
  };
  if (options.signal) init.signal = options.signal;
  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(options.body);
  }
  if (options.idempotencyKey) headers['Idempotency-Key'] = options.idempotencyKey;

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, init);
  } catch (cause) {
    const message = cause instanceof Error ? cause.message : 'Network request failed';
    return err(new ApiError('network_error', message, 0));
  }

  if (!response.ok) {
    return err(await toApiError(response));
  }

  if (response.status === 204) {
    return ok(undefined as T);
  }

  try {
    return ok((await response.json()) as T);
  } catch (cause) {
    const message = cause instanceof Error ? cause.message : 'Malformed response body';
    return err(new ApiError('unknown', message, response.status));
  }
}

export const http = {
  get: <T>(path: string, options?: RequestOptions): Promise<Result<T>> =>
    request<T>('GET', path, options),
  post: <T>(path: string, body?: unknown, options?: RequestOptions): Promise<Result<T>> =>
    request<T>('POST', path, { ...options, body }),
};
