import type { Product, Result, Timeline } from '@/types';

import { http } from './http';

export function listProducts(signal?: AbortSignal): Promise<Result<Product[]>> {
  return http.get<Product[]>('/products', { signal });
}

/** Composite: product + components + their versions — one call for the Constellation view. */
export function getTimeline(productId: string, signal?: AbortSignal): Promise<Result<Timeline>> {
  return http.get<Timeline>(`/products/${productId}/timeline`, { signal });
}
