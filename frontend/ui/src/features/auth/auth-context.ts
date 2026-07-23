import { createContext } from 'react';

import type { Credentials } from '@/api';
import type { Meta, Principal, Result } from '@/types';

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';

export interface AuthContextValue {
  readonly principal: Principal | null;
  readonly meta: Meta | null;
  readonly status: AuthStatus;
  readonly login: (credentials: Credentials) => Promise<Result<Principal>>;
  /**
   * EE: exchange a Stytch session token for a LAVS session and update auth state,
   * mirroring how `login` promotes the returned principal into the cache.
   */
  readonly completeStytchLogin: (stytchToken: string) => Promise<Result<Principal>>;
  readonly logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
