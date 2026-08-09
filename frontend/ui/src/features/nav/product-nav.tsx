import type { ChangeEvent, ReactNode } from 'react';

import { useProducts } from '@/features/products';

import styles from './product-nav.module.css';

export interface ProductNavProps {
  readonly productId: string | undefined;
  readonly onSelect: (productId: string) => void;
}

/**
 * Accessible product picker: a labelled native `<select>` (fully keyboardable) over the
 * product list, with loading / empty states and a product count.
 */
export function ProductNav({ productId, onSelect }: ProductNavProps): ReactNode {
  const { data: products, isLoading, isError } = useProducts();

  function onChange(event: ChangeEvent<HTMLSelectElement>): void {
    onSelect(event.target.value);
  }

  if (isLoading) {
    return (
      <div className={styles.nav} role="status">
        <span className={styles.status}>Loading products…</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className={styles.nav} role="alert">
        <span className={styles.status}>Could not load products.</span>
      </div>
    );
  }

  const items = products ?? [];

  if (items.length === 0) {
    return (
      <div className={styles.nav} role="status">
        <span className={styles.status}>No products yet.</span>
      </div>
    );
  }

  return (
    <nav className={styles.nav} aria-label="Product navigation">
      <label className={styles.label} htmlFor="product-nav-select">
        Product
      </label>
      <select
        id="product-nav-select"
        className={styles.select}
        value={productId ?? ''}
        onChange={onChange}
      >
        {productId ? null : (
          <option value="" disabled>
            Select a product…
          </option>
        )}
        {items.map((product) => (
          <option key={product.id} value={product.id}>
            {product.name}
          </option>
        ))}
      </select>
      <span className={styles.count}>
        {items.length} {items.length === 1 ? 'product' : 'products'}
      </span>
    </nav>
  );
}
