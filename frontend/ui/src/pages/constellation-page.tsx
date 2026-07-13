import type { ReactNode } from 'react';

import { AppShell } from '@/app/app-shell';
import { useProducts, useTimeline } from '@/features/products';

import styles from './constellation-page.module.css';

/**
 * Foundation placeholder: loads the first product's timeline and renders a minimal
 * component summary. The R1 Constellation view, R2 cut/ledger panel and R3 live layer
 * mount here (composed by the aggregator).
 */
export function ConstellationPage(): ReactNode {
  const productsQuery = useProducts();
  const productId = productsQuery.data?.[0]?.id;
  const timelineQuery = useTimeline(productId);
  const timeline = timelineQuery.data;

  const productLabel = timeline
    ? `${timeline.product.name} · ${timeline.components.length} components`
    : undefined;

  return (
    <AppShell productLabel={productLabel}>
      {timelineQuery.isLoading ? (
        <p role="status" className={styles.status}>
          Charting the constellation…
        </p>
      ) : timelineQuery.isError ? (
        <p role="alert" className={styles.status}>
          Could not load the timeline.
        </p>
      ) : timeline ? (
        <section className={styles.panel} aria-label="Component streams">
          <h2 className={styles.heading}>Streams</h2>
          <ul className={styles.list}>
            {timeline.components.map((component) => (
              <li key={component.id} className={styles.row}>
                <span className={styles.name}>{component.name}</span>
                <span className={styles.kind}>{component.kind}</span>
                <span className={`${styles.count} mono`}>{component.versions.length} versions</span>
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <p className={styles.status}>No products yet.</p>
      )}
    </AppShell>
  );
}
