import type { ReactNode } from 'react';

import styles from './product-version-readout.module.css';

export interface ProductVersionReadoutProps {
  /** The client-derived product version for the current meridian position. */
  readonly productVersion: string;
  /** The meridian tick (ordinal time position) being read out. */
  readonly tick: number;
}

/**
 * The "Release Meridian" card: a big luminous derived product version plus a `t = N` tick
 * readout. Purely presentational — the derivation happens upstream (R1).
 */
export function ProductVersionReadout({
  productVersion,
  tick,
}: ProductVersionReadoutProps): ReactNode {
  return (
    <section className={styles.card} aria-labelledby="meridian-title">
      <div className={styles.head}>
        <h3 id="meridian-title" className={styles.title}>
          Release Meridian
        </h3>
        <span className={styles.tick} data-testid="meridian-tick">
          t = {tick}
        </span>
      </div>
      <div className={styles.pv}>
        <span className={styles.pvLabel}>Derived product version</span>
        <span className={styles.pvValue} data-testid="product-version">
          {productVersion}
        </span>
      </div>
    </section>
  );
}
