import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse, http } from 'msw';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { server } from '@/mocks';
import { renderWithProviders } from '@/test';

import { LoginForm } from './login-form';
import {
  ManagedSignInContext,
  type ManagedSignInProps,
  type ManagedSignInRegistry,
} from './managed-sign-in-context';

// A fake managed sign-in renderer standing in for whatever an external (EE) build
// injects into the login slot. LoginForm knows nothing about it beyond the contract.
function FakeManagedSignIn({ onSuccess }: ManagedSignInProps): ReactNode {
  return (
    <section aria-labelledby="fake-managed-title">
      <h2 id="fake-managed-title">Managed sign-in</h2>
      <button type="button" data-testid="fake-managed-widget" onClick={() => onSuccess?.()}>
        Continue with managed identity
      </button>
    </section>
  );
}

function renderLoginForm(
  registry: ManagedSignInRegistry = {},
  props: { readonly onSuccess?: () => void } = {},
): void {
  renderWithProviders(
    <ManagedSignInContext.Provider value={registry}>
      <LoginForm onSuccess={props.onSuccess} />
    </ManagedSignInContext.Provider>,
  );
}

describe('LoginForm', () => {
  it('renders the password form under default meta (password,apikey)', () => {
    renderLoginForm();

    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('calls onSuccess after a successful login', async () => {
    const onSuccess = vi.fn();
    const user = userEvent.setup();
    renderLoginForm({}, { onSuccess });

    await user.type(screen.getByLabelText('Email'), 'astronomer@snoodleboot.com');
    await user.type(screen.getByLabelText('Password'), 'correct-horse');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1));
  });

  it('shows an alert when credentials are rejected (401)', async () => {
    const onSuccess = vi.fn();
    const user = userEvent.setup();
    renderLoginForm({}, { onSuccess });

    await user.type(screen.getByLabelText('Email'), 'astronomer@snoodleboot.com');
    await user.type(screen.getByLabelText('Password'), 'wrong');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/invalid credentials/i);
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it('explains the configured API key when password is not enabled', async () => {
    server.use(
      http.get('*/api/meta', () => HttpResponse.json({ edition: 'oss', auth_modes: ['apikey'] })),
    );
    renderLoginForm();

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /configured API key/i })).toBeInTheDocument(),
    );
    expect(screen.queryByLabelText('Password')).not.toBeInTheDocument();
  });

  it('renders an injected managed sign-in for a managed-only deployment', async () => {
    server.use(
      http.get('*/api/meta', () => HttpResponse.json({ edition: 'ee', auth_modes: ['managed'] })),
    );
    renderLoginForm({ managed: FakeManagedSignIn });

    await waitFor(() => expect(screen.getByTestId('fake-managed-widget')).toBeInTheDocument());
    expect(screen.queryByLabelText('Password')).not.toBeInTheDocument();
  });

  it('renders both password and the injected managed sign-in in mixed mode', async () => {
    server.use(
      http.get('*/api/meta', () =>
        HttpResponse.json({ edition: 'ee', auth_modes: ['password', 'managed'] }),
      ),
    );
    renderLoginForm({ managed: FakeManagedSignIn });

    await waitFor(() => expect(screen.getByTestId('fake-managed-widget')).toBeInTheDocument());
    expect(screen.getByRole('heading', { name: /^sign in$/i })).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByRole('separator')).toBeInTheDocument();
  });

  it('prefers the injected managed sign-in over the API-key notice when both are enabled', async () => {
    server.use(
      http.get('*/api/meta', () =>
        HttpResponse.json({ edition: 'ee', auth_modes: ['managed', 'apikey'] }),
      ),
    );
    renderLoginForm({ managed: FakeManagedSignIn });

    await waitFor(() => expect(screen.getByTestId('fake-managed-widget')).toBeInTheDocument());
    expect(screen.queryByRole('heading', { name: /configured API key/i })).not.toBeInTheDocument();
  });

  it('ignores managed modes with no registered renderer (OSS injects nothing)', async () => {
    server.use(
      http.get('*/api/meta', () => HttpResponse.json({ edition: 'ee', auth_modes: ['managed'] })),
    );
    // Empty registry: the advertised managed mode has no renderer, so we fall through
    // to the "no interactive auth mode" notice — no crash, no leaked widget.
    renderLoginForm({});

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /sign-in unavailable/i })).toBeInTheDocument(),
    );
    expect(screen.queryByTestId('fake-managed-widget')).not.toBeInTheDocument();
  });

  it('explains when no interactive auth mode is enabled', async () => {
    server.use(http.get('*/api/meta', () => HttpResponse.json({ edition: 'oss', auth_modes: [] })));
    renderLoginForm();

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /sign-in unavailable/i })).toBeInTheDocument(),
    );
    expect(screen.queryByLabelText('Password')).not.toBeInTheDocument();
  });
});
