import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

export function NotFoundPage(): ReactNode {
  return (
    <div style={{ display: 'grid', placeItems: 'center', minHeight: '100vh', gap: 12 }}>
      <h1 style={{ margin: 0 }}>Lost in the void</h1>
      <Link to="/" style={{ color: 'var(--meridian)' }}>
        Return to the constellation
      </Link>
    </div>
  );
}
