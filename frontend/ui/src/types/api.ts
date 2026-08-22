// Result-style typed errors — library code returns errors, never throws (TS conventions).

export type ApiErrorCode =
  | 'unauthorized'
  | 'forbidden'
  | 'domain_not_allowed'
  | 'not_found'
  | 'conflict'
  | 'validation_error'
  | 'network_error'
  | 'unknown';

/**
 * A typed API failure. It extends Error so the TanStack Query boundary can rethrow it
 * (queries surface `Error`s), but the api/* modules RETURN it inside a Result rather
 * than throwing — the throw happens only at the query-fn adapter (see lib/query-fn).
 */
export class ApiError extends Error {
  readonly code: ApiErrorCode;
  readonly httpStatus: number;
  readonly details: Record<string, unknown> | null;

  constructor(
    code: ApiErrorCode,
    message: string,
    httpStatus: number,
    details: Record<string, unknown> | null = null,
  ) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.httpStatus = httpStatus;
    this.details = details;
  }
}

export type Result<T, E = ApiError> =
  { readonly ok: true; readonly value: T } | { readonly ok: false; readonly error: E };

export const ok = <T>(value: T): Result<T, never> => ({ ok: true, value });

export const err = <E>(error: E): Result<never, E> => ({ ok: false, error });

export function isOk<T, E>(
  result: Result<T, E>,
): result is { readonly ok: true; readonly value: T } {
  return result.ok;
}
