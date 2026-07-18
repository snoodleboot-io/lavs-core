import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { getRelease, listReleases } from '@/api';
import { queryKeys, unwrap } from '@/lib';
import type { Release } from '@/types';

/** The release ledger for a product (newest first, as the server returns it). */
export function useReleases(productId: string | undefined): UseQueryResult<Release[]> {
  return useQuery({
    queryKey: productId ? queryKeys.releases(productId) : queryKeys.releases('none'),
    queryFn: ({ signal }) => unwrap(listReleases(productId ?? '', signal)),
    enabled: Boolean(productId),
  });
}

/** A single frozen release + its pinned manifest. */
export function useRelease(releaseId: string | undefined): UseQueryResult<Release> {
  return useQuery({
    queryKey: releaseId ? queryKeys.release(releaseId) : queryKeys.release('none'),
    queryFn: ({ signal }) => unwrap(getRelease(releaseId ?? '', signal)),
    enabled: Boolean(releaseId),
  });
}
