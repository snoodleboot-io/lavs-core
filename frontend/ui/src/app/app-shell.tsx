import type { ReactNode } from 'react';

import { useAuth } from '@/features/auth';

import styles from './app-shell.module.css';

interface AppShellProps {
  readonly children: ReactNode;
  /** Optional slot rendered on the right of the header (command palette, product nav…). */
  readonly headerActions?: ReactNode;
  /** Short product context line (e.g. "Aurora Platform · 4 components"). */
  readonly productLabel?: string;
}

/**
 * The persistent chrome: brand, product context, keyboard hints, logout. Lanes render
 * their views as `children`; foundation owns this layout so lanes compose consistently.
 */
export function AppShell({ children, headerActions, productLabel }: AppShellProps): ReactNode {
  const { principal, logout } = useAuth();

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <div className={styles.brand}>
          <b>LAVS</b>
          <span className={styles.tag}>Constellation</span>
        </div>
        {productLabel ? (
          <div className={styles.product}>
            <span className={styles.dot} aria-hidden="true" />
            <span>{productLabel}</span>
          </div>
        ) : null}
        <div className={styles.spacer} />
        <p className={styles.kbd} aria-hidden="true">
          <b>←</b>
          <b>→</b> scrub <b>C</b> cut <b>⌘K</b> palette
        </p>
        {headerActions}
        {principal ? (
          <button type="button" className={styles.logout} onClick={() => void logout()}>
            Sign out
          </button>
        ) : null}
      </header>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
