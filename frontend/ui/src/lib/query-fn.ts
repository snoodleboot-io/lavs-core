import type { ApiError, Result } from '@/types';

/**
 * Adapter from the api/* modules' `Result<T, ApiError>` to the throw-based contract
 * TanStack Query expects. Keep this the ONLY place a Result becomes a throw.
 */
export async function unwrap<T>(promise: Promise<Result<T, ApiError>>): Promise<T> {
  const result = await promise;
  if (result.ok) return result.value;
  throw result.error;
}
