import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { listProducts } from '@/api';
import { queryKeys, unwrap } from '@/lib';
import type { Product } from '@/types';

export function useProducts(): UseQueryResult<Product[]> {
  return useQuery({
    queryKey: queryKeys.products,
    queryFn: ({ signal }) => unwrap(listProducts(signal)),
  });
}
