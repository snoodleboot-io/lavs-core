import { QueryClientProvider, type QueryClient } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';

import { AuthProvider } from '@/features/auth';

import { createQueryClient } from './query-client';

interface ProvidersProps {
  readonly children: ReactNode;
  /** Injectable client for tests; a fresh one is created per app otherwise. */
  readonly client?: QueryClient;
}

/** Composition root for cross-cutting context: server-state cache + auth session. */
export function Providers({ children, client }: ProvidersProps): ReactNode {
  const [queryClient] = useState(() => client ?? createQueryClient());
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
}
