import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { getTimeline } from '@/api';
import { queryKeys, unwrap } from '@/lib';
import type { Timeline } from '@/types';

/** The composite Constellation feed: product + components + versions in one query. */
export function useTimeline(productId: string | undefined): UseQueryResult<Timeline> {
  return useQuery({
    queryKey: productId ? queryKeys.timeline(productId) : queryKeys.timeline('none'),
    queryFn: ({ signal }) => unwrap(getTimeline(productId ?? '', signal)),
    enabled: Boolean(productId),
  });
}
