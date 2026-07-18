import { useMutation, useQueryClient, type UseMutationResult } from '@tanstack/react-query';

import { cutRelease, type CutReleaseInput } from '@/api';
import { queryKeys, unwrap } from '@/lib';
import type { ApiError, Release } from '@/types';

/**
 * The write that matters: cut a release. The server owns the product version and the frozen
 * manifest — the client may pass only an optional `label`/`notes`. On success we optimistically
 * prepend the returned release to the ledger cache, then invalidate the releases + timeline
 * queries so every lane converges on the server's truth.
 */
export function useCutRelease(
  productId: string,
): UseMutationResult<Release, ApiError, CutReleaseInput, unknown> {
  const client = useQueryClient();

  return useMutation<Release, ApiError, CutReleaseInput>({
    mutationFn: (input: CutReleaseInput = {}) => unwrap(cutRelease(productId, input)),
    onSuccess: (release) => {
      client.setQueryData<Release[]>(queryKeys.releases(productId), (previous) =>
        previous ? [release, ...previous] : [release],
      );
      void client.invalidateQueries({ queryKey: queryKeys.releases(productId) });
      void client.invalidateQueries({ queryKey: queryKeys.timeline(productId) });
    },
  });
}
