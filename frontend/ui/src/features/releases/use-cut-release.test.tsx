import { QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it } from 'vitest';

import { SEED_PRODUCT_ID } from '@/mocks';
import { createTestQueryClient } from '@/test';

import { useCutRelease } from './use-cut-release';
import { useReleases } from './use-releases';

function makeWrapper(): (props: { children: ReactNode }) => ReactNode {
  const client = createTestQueryClient();
  return function Wrapper({ children }: { children: ReactNode }): ReactNode {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

describe('useCutRelease', () => {
  it('cuts a release and the ledger query reflects it after invalidation', async () => {
    const wrapper = makeWrapper();
    const { result } = renderHook(
      () => ({
        cut: useCutRelease(SEED_PRODUCT_ID),
        releases: useReleases(SEED_PRODUCT_ID),
      }),
      { wrapper },
    );

    // Ledger starts empty (seed has no releases).
    await waitFor(() => expect(result.current.releases.isSuccess).toBe(true));
    expect(result.current.releases.data).toHaveLength(0);

    // Cut a release — MSW returns 201 with the first server-assigned version 5.1.0.
    await act(async () => {
      await result.current.cut.mutateAsync({ label: 'Aurora 5.1' });
    });

    await waitFor(() => expect(result.current.releases.data).toHaveLength(1));
    const [release] = result.current.releases.data ?? [];
    expect(release?.product_version).toBe('5.1.0');
    expect(release?.label).toBe('Aurora 5.1');
  });
});
