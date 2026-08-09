import { useState, type ReactNode } from 'react';

import { AppShell } from '@/app/app-shell';
import { ProductNav } from '@/features/nav';
import { useProducts, useTimeline } from '@/features/products';

import { ConstellationWorkspace } from './constellation-workspace';
import styles from './constellation-page.module.css';

/**
 * Constellation route: resolves the active product (first product by default, switchable via
 * the nav) and its timeline, then hands a guaranteed timeline to the workspace. Loading and
 * error states keep the shell chrome so the nav stays usable.
 */
export function ConstellationPage(): ReactNode {
  const productsQuery = useProducts();
  const [selectedId, setSelectedId] = useState<string | undefined>(undefined);
  const productId = selectedId ?? productsQuery.data?.[0]?.id;
  const timelineQuery = useTimeline(productId);
  const timeline = timelineQuery.data;

  if (productId && timeline) {
    return (
      <ConstellationWorkspace
        key={productId}
        productId={productId}
        timeline={timeline}
        onSelectProduct={setSelectedId}
      />
    );
  }

  return (
    <AppShell headerActions={<ProductNav productId={productId} onSelect={setSelectedId} />}>
      {productsQuery.isError || timelineQuery.isError ? (
        <p role="alert" className={styles.status}>
          Could not load the constellation.
        </p>
      ) : productsQuery.data && productsQuery.data.length === 0 ? (
        <p role="status" className={styles.status}>
          No products yet.
        </p>
      ) : (
        <p role="status" className={styles.status}>
          Charting the constellation…
        </p>
      )}
    </AppShell>
  );
}
