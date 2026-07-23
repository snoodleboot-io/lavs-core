import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, type ReactNode } from 'react';

import {
  getMe,
  getMeta,
  login as loginRequest,
  logout as logoutRequest,
  stytchCallback,
} from '@/api';
import type { Credentials } from '@/api';
import { queryKeys, unwrap } from '@/lib';
import { ApiError } from '@/types';

import { AuthContext, type AuthContextValue, type AuthStatus } from './auth-context';

export function AuthProvider({ children }: { readonly children: ReactNode }): ReactNode {
  const queryClient = useQueryClient();

  const meQuery = useQuery({
    queryKey: queryKeys.me,
    queryFn: ({ signal }) => unwrap(getMe(signal)),
    // A 401 is an expected "logged out" state, not a transient failure.
    retry: false,
    staleTime: 30_000,
  });

  const metaQuery = useQuery({
    queryKey: queryKeys.meta,
    queryFn: ({ signal }) => unwrap(getMeta(signal)),
    staleTime: Infinity,
  });

  const loginMutation = useMutation({
    mutationFn: (credentials: Credentials) => loginRequest(credentials),
    onSuccess: (result) => {
      if (result.ok) queryClient.setQueryData(queryKeys.me, result.value);
    },
  });

  const login = useCallback(
    (credentials: Credentials) => loginMutation.mutateAsync(credentials),
    [loginMutation],
  );

  const stytchMutation = useMutation({
    mutationFn: (stytchToken: string) => stytchCallback(stytchToken),
    onSuccess: (result) => {
      if (result.ok) queryClient.setQueryData(queryKeys.me, result.value);
    },
  });

  const completeStytchLogin = useCallback(
    (stytchToken: string) => stytchMutation.mutateAsync(stytchToken),
    [stytchMutation],
  );

  const logout = useCallback(async (): Promise<void> => {
    await logoutRequest();
    queryClient.setQueryData(queryKeys.me, null);
    await queryClient.invalidateQueries();
  }, [queryClient]);

  const status: AuthStatus = meQuery.isLoading
    ? 'loading'
    : meQuery.data
      ? 'authenticated'
      : 'unauthenticated';

  const isUnauthorized = meQuery.error instanceof ApiError && meQuery.error.code === 'unauthorized';

  const value = useMemo<AuthContextValue>(
    () => ({
      principal: meQuery.data ?? null,
      meta: metaQuery.data ?? null,
      // A non-401 error still resolves to unauthenticated for gating purposes.
      status: meQuery.isError && !isUnauthorized ? 'unauthenticated' : status,
      login,
      completeStytchLogin,
      logout,
    }),
    [
      meQuery.data,
      meQuery.isError,
      metaQuery.data,
      isUnauthorized,
      status,
      login,
      completeStytchLogin,
      logout,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
