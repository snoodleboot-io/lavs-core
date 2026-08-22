import type { Release, Result } from '@/types';

import { http } from './http';

/** The client may set only an optional label/notes — the server owns the version + manifest. */
export interface CutReleaseInput {
  readonly label?: string;
  readonly notes?: string;
  /** Optional idempotency key to prevent a double-cut. */
  readonly idempotencyKey?: string;
}

export function listReleases(productId: string, signal?: AbortSignal): Promise<Result<Release[]>> {
  return http.get<Release[]>(`/products/${productId}/releases`, { signal });
}

export function getRelease(releaseId: string, signal?: AbortSignal): Promise<Result<Release>> {
  return http.get<Release>(`/releases/${releaseId}`, { signal });
}

/** Cut a release: snapshots each component's active version; server assigns the version. */
export function cutRelease(
  productId: string,
  input: CutReleaseInput = {},
): Promise<Result<Release>> {
  const { idempotencyKey, ...body } = input;
  return http.post<Release>(`/products/${productId}/releases`, body, { idempotencyKey });
}
