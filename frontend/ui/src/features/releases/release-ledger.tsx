import type { ReactNode } from 'react';

import type { Release } from '@/types';

import { frozenManifestOf } from './frozen-manifest';
import { useReleases } from './use-releases';

import styles from './release-ledger.module.css';

export interface ReleaseLedgerProps {
  readonly productId: string;
  /** Called when a ledger card is activated — reopen/freeze on that frozen release. */
  readonly onReopen?: (release: Release) => void;
}

/** Human codename for a release: its label, falling back to the product version. */
function codenameOf(release: Release): string {
  if (release.label && release.label.trim().length > 0) return release.label;
  return `v${release.product_version}`;
}

/** A compact one-line manifest summary of the frozen components. */
function manifestSummary(release: Release): string {
  const entries = frozenManifestOf(release);
  if (entries.length === 0) return 'no components';
  return entries.map((entry) => `${entry.name} ${entry.version}`).join(' · ');
}

/**
 * The Release Ledger: a horizontal scroll of frozen releases, newest first. Each card is a real
 * keyboard-operable button that reopens the release. Renders loading / error / empty states.
 */
export function ReleaseLedger({ productId, onReopen }: ReleaseLedgerProps): ReactNode {
  const { data: releases, isPending, isError, error } = useReleases(productId);

  const count = releases?.length ?? 0;

  return (
    <section className={styles.footer} aria-labelledby="ledger-title">
      <div className={styles.head}>
        <h3 id="ledger-title" className={styles.title}>
          Release Ledger
        </h3>
        <span className={styles.count}>
          {count} release{count === 1 ? '' : 's'}
        </span>
      </div>

      {isPending ? (
        <p className={styles.status}>Loading ledger…</p>
      ) : isError ? (
        <p className={styles.status} data-tone="error" role="alert">
          Couldn’t load the ledger: {error.message}
        </p>
      ) : count === 0 ? (
        <p className={styles.empty}>No releases cut yet — pin a manifest and cut one.</p>
      ) : (
        <div className={styles.list}>
          {releases.map((release) => (
            <button
              key={release.id}
              type="button"
              className={styles.card}
              onClick={() => onReopen?.(release)}
              title={`Reopen ${codenameOf(release)}`}
            >
              <span className={styles.codename}>{codenameOf(release)}</span>
              <span className={styles.pv}>v{release.product_version}</span>
              <span className={styles.manifest}>{manifestSummary(release)}</span>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
