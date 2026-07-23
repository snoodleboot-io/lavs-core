import { act, screen, waitFor } from '@testing-library/react';
import { HttpResponse, http } from 'msw';
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { db, server } from '@/mocks';
import { renderWithProviders } from '@/test';

import { StytchLogin } from './stytch-login';
import { useAuth } from './use-auth';

// --- Stytch SDK stub -------------------------------------------------------------
// The prebuilt widget is Stytch's code, not ours: the stub captures what our
// integration hands the SDK (publishable token, config, callbacks) and lets tests
// drive the auth-complete event without any real Stytch traffic.

interface StubCallbacks {
  onEvent?: (event: { type: string; data: unknown }) => void;
  onError?: (error: unknown) => void;
}

interface StubMountProps {
  callbacks?: StubCallbacks;
  config?: { products?: unknown[] };
}

const stytchStub = vi.hoisted(() => {
  const state: {
    callbacks: StubCallbacks | null;
    tokens: { session_token: string; session_jwt: string } | null;
    publicTokens: string[];
  } = { callbacks: null, tokens: null, publicTokens: [] };
  const mountLogin = vi.fn((props: StubMountProps) => {
    state.callbacks = props.callbacks ?? null;
  });
  return { state, mountLogin };
});

vi.mock('@stytch/vanilla-js', () => {
  class StytchUIClient {
    readonly session = {
      getTokens: (): { session_token: string; session_jwt: string } | null =>
        stytchStub.state.tokens,
    };
    constructor(publicToken: string) {
      stytchStub.state.publicTokens.push(publicToken);
    }
    mountLogin(props: StubMountProps): void {
      stytchStub.mountLogin(props);
    }
  }
  return {
    StytchUIClient,
    Products: {
      emailMagicLinks: { id: 'emailMagicLinks', screens: {} },
      oauth: { id: 'oauth', screens: {} },
    },
    StytchEventType: { AuthenticateFlowComplete: 'AUTHENTICATE_FLOW_COMPLETE' },
  };
});

// --- helpers ---------------------------------------------------------------------

/** Point `/meta` at a stytch-only EE deployment with the given publishable token. */
function useStytchMeta(stytchPublicToken: string | null = 'pk-test-token'): void {
  server.use(
    http.get('*/api/meta', () =>
      HttpResponse.json({
        edition: 'ee',
        auth_modes: ['stytch'],
        stytch_public_token: stytchPublicToken,
      }),
    ),
  );
}

/** Point `/meta` at a stytch-only EE deployment that omits the token field entirely. */
function useStytchMetaWithoutToken(): void {
  server.use(
    http.get('*/api/meta', () => HttpResponse.json({ edition: 'ee', auth_modes: ['stytch'] })),
  );
}

/** StytchLogin next to a probe so tests can observe the shared auth state. */
function Harness({ onSuccess }: { readonly onSuccess?: () => void }): ReactNode {
  const { status, principal } = useAuth();
  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="edition">{principal?.edition ?? 'none'}</span>
      <StytchLogin onSuccess={onSuccess} />
    </div>
  );
}

function fireAuthComplete(): void {
  act(() => {
    stytchStub.state.callbacks?.onEvent?.({ type: 'AUTHENTICATE_FLOW_COMPLETE', data: {} });
  });
}

describe('StytchLogin', () => {
  beforeEach(() => {
    stytchStub.state.callbacks = null;
    stytchStub.state.tokens = null;
    stytchStub.state.publicTokens = [];
    stytchStub.mountLogin.mockClear();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('renders an accessible notice when no publishable token is configured', async () => {
    db.principal = null;
    useStytchMeta(null);
    renderWithProviders(<StytchLogin />);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/publishable token/i);
    expect(stytchStub.mountLogin).not.toHaveBeenCalled();
  });

  it('mounts the prebuilt widget with the token from /meta (magic links + OAuth)', async () => {
    db.principal = null;
    useStytchMeta('pk-from-meta');
    renderWithProviders(<StytchLogin />);

    await waitFor(() => expect(stytchStub.mountLogin).toHaveBeenCalledTimes(1));
    expect(stytchStub.state.publicTokens).toEqual(['pk-from-meta']);
    expect(screen.getByRole('heading', { name: /managed sign-in/i })).toBeInTheDocument();
    expect(screen.getByTestId('stytch-widget')).toBeInTheDocument();

    const props = stytchStub.mountLogin.mock.calls[0]![0];
    expect(props.config?.products).toHaveLength(2);
  });

  it('falls back to VITE_STYTCH_PUBLIC_TOKEN when /meta has no token', async () => {
    db.principal = null;
    vi.stubEnv('VITE_STYTCH_PUBLIC_TOKEN', 'pk-from-env');
    useStytchMetaWithoutToken();
    renderWithProviders(<StytchLogin />);

    await waitFor(() => expect(stytchStub.mountLogin).toHaveBeenCalledTimes(1));
    expect(stytchStub.state.publicTokens).toEqual(['pk-from-env']);
  });

  it('exchanges the Stytch session for a LAVS session and updates auth state', async () => {
    db.principal = null;
    useStytchMeta();
    const onSuccess = vi.fn();
    renderWithProviders(<Harness onSuccess={onSuccess} />);

    await waitFor(() => expect(stytchStub.mountLogin).toHaveBeenCalledTimes(1));
    await waitFor(() =>
      expect(screen.getByTestId('status')).toHaveTextContent(/^unauthenticated$/),
    );

    stytchStub.state.tokens = { session_token: 'opaque-token', session_jwt: 'stytch-jwt' };
    fireAuthComplete();

    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent(/^authenticated$/));
    expect(screen.getByTestId('edition')).toHaveTextContent('ee');
    expect(onSuccess).toHaveBeenCalledTimes(1);
  });

  it('surfaces the API error when the callback exchange is rejected (401)', async () => {
    db.principal = null;
    useStytchMeta();
    const onSuccess = vi.fn();
    renderWithProviders(<Harness onSuccess={onSuccess} />);

    await waitFor(() => expect(stytchStub.mountLogin).toHaveBeenCalledTimes(1));

    stytchStub.state.tokens = { session_token: 'opaque-token', session_jwt: 'stytch-invalid' };
    fireAuthComplete();

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/stytch session rejected/i);
    expect(onSuccess).not.toHaveBeenCalled();
    expect(screen.getByTestId('status')).toHaveTextContent(/^unauthenticated$/);
  });

  it('reports when the widget completes without producing a session token', async () => {
    db.principal = null;
    useStytchMeta();
    renderWithProviders(<StytchLogin />);

    await waitFor(() => expect(stytchStub.mountLogin).toHaveBeenCalledTimes(1));

    stytchStub.state.tokens = null;
    fireAuthComplete();

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/did not produce a session token/i);
  });

  it('shows an alert when the Stytch SDK reports an error', async () => {
    db.principal = null;
    useStytchMeta();
    renderWithProviders(<StytchLogin />);

    await waitFor(() => expect(stytchStub.mountLogin).toHaveBeenCalledTimes(1));

    act(() => {
      stytchStub.state.callbacks?.onError?.(new Error('widget exploded'));
    });

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/managed sign-in failed/i);
  });

  it('ignores non-authenticate widget events', async () => {
    db.principal = null;
    useStytchMeta();
    renderWithProviders(<Harness />);

    await waitFor(() => expect(stytchStub.mountLogin).toHaveBeenCalledTimes(1));

    stytchStub.state.tokens = { session_token: 'opaque-token', session_jwt: 'stytch-jwt' };
    act(() => {
      stytchStub.state.callbacks?.onEvent?.({ type: 'MAGIC_LINK_LOGIN_OR_CREATE', data: {} });
    });

    await waitFor(() =>
      expect(screen.getByTestId('status')).toHaveTextContent(/^unauthenticated$/),
    );
  });
});
