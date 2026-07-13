import type { Product, Result, Timeline } from '@/types';

import { http } from './http';

export interface CreateProductInput {
  readonly name: string;
  readonly description?: string;
}

export function listProducts(signal?: AbortSignal): Promise<Result<Product[]>> {
  return http.get<Product[]>('/products', { signal });
}

export function getProduct(id: string, signal?: AbortSignal): Promise<Result<Product>> {
  return http.get<Product>(`/products/${id}`, { signal });
}

/** Composite: product + components + their versions — one call for the Constellation view. */
export function getTimeline(productId: string, signal?: AbortSignal): Promise<Result<Timeline>> {
  return http.get<Timeline>(`/products/${productId}/timeline`, { signal });
}

export function createProduct(input: CreateProductInput): Promise<Result<Product>> {
  return http.post<Product>('/products', input);
}
