import { createContext } from 'react';

import type { Credentials } from '@/api';
import type { Meta, Principal, Result } from '@/types';

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';

export interface AuthContextValue {
  readonly principal: Principal | null;
  readonly meta: Meta | null;
  readonly status: AuthStatus;
  readonly login: (credentials: Credentials) => Promise<Result<Principal>>;
  readonly logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
