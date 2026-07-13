import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';

import { useAuth } from '@/features/auth';

/** Route gate: sends unauthenticated users to /login; shows a quiet loading state meanwhile. */
export function RequireAuth({ children }: { readonly children: ReactNode }): ReactNode {
  const { status } = useAuth();

  if (status === 'loading') {
    return (
      <div role="status" aria-live="polite" style={{ padding: 24, color: 'var(--muted)' }}>
        Aligning the instruments…
      </div>
    );
  }

  if (status === 'unauthenticated') {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
