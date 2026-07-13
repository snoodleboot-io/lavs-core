import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderOptions, type RenderResult } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';

import { AuthProvider } from '@/features/auth';

export interface RenderWithProvidersOptions extends Omit<RenderOptions, 'wrapper'> {
  /** Initial router entry (default '/'). */
  readonly route?: string;
  /** Inject a pre-seeded client; otherwise a retry-disabled one is created. */
  readonly client?: QueryClient;
}

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
      mutations: { retry: false },
    },
  });
}

/** Render a component inside the app's providers (query cache + auth + router). */
export function renderWithProviders(
  ui: ReactElement,
  options: RenderWithProvidersOptions = {},
): RenderResult & { readonly client: QueryClient } {
  const { route = '/', client = createTestQueryClient(), ...rest } = options;

  function Wrapper({ children }: { readonly children: ReactNode }): ReactNode {
    return (
      <QueryClientProvider client={client}>
        <AuthProvider>
          <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );
  }

  return { ...render(ui, { wrapper: Wrapper, ...rest }), client };
}
