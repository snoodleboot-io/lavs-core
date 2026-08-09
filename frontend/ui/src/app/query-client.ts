import { QueryClient } from '@tanstack/react-query';

import { ApiError } from '@/types';

/** App-wide QueryClient. Don't retry auth/validation failures — only transient ones. */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 10_000,
        refetchOnWindowFocus: false,
        retry: (failureCount, error) => {
          if (error instanceof ApiError && error.code !== 'network_error') return false;
          return failureCount < 2;
        },
      },
    },
  });
}
