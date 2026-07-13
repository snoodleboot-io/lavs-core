import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { getProduct, listProducts } from '@/api';
import { queryKeys, unwrap } from '@/lib';
import type { Product } from '@/types';

export function useProducts(): UseQueryResult<Product[]> {
  return useQuery({
    queryKey: queryKeys.products,
    queryFn: ({ signal }) => unwrap(listProducts(signal)),
  });
}

export function useProduct(productId: string | undefined): UseQueryResult<Product> {
  return useQuery({
    queryKey: productId ? queryKeys.product(productId) : queryKeys.product('none'),
    queryFn: ({ signal }) => unwrap(getProduct(productId ?? '', signal)),
    enabled: Boolean(productId),
  });
}
