import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse, http } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { server } from '@/mocks';
import { renderWithProviders } from '@/test';

import { LoginForm } from './login-form';

// Stub the Stytch SDK — the prebuilt widget is Stytch's code; these tests only
// assert which login paths LoginForm renders per /meta auth_modes.
vi.mock('@stytch/vanilla-js', () => {
  class StytchUIClient {
    readonly session = { getTokens: (): null => null };
    mountLogin(): void {}
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

describe('LoginForm', () => {
  it('renders the password form under default meta (password,apikey)', () => {
    renderWithProviders(<LoginForm />);

    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('calls onSuccess after a successful login', async () => {
    const onSuccess = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<LoginForm onSuccess={onSuccess} />);

    await user.type(screen.getByLabelText('Email'), 'astronomer@snoodleboot.com');
    await user.type(screen.getByLabelText('Password'), 'correct-horse');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1));
  });

  it('shows an alert when credentials are rejected (401)', async () => {
    const onSuccess = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<LoginForm onSuccess={onSuccess} />);

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
    renderWithProviders(<LoginForm />);

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /configured API key/i })).toBeInTheDocument(),
    );
    expect(screen.queryByLabelText('Password')).not.toBeInTheDocument();
  });

  it('renders the Stytch managed sign-in for stytch-only deployments', async () => {
    server.use(
      http.get('*/api/meta', () =>
        HttpResponse.json({
          edition: 'ee',
          auth_modes: ['stytch'],
          stytch_public_token: 'pk-test-token',
        }),
      ),
    );
    renderWithProviders(<LoginForm />);

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /managed sign-in/i })).toBeInTheDocument(),
    );
    expect(screen.getByTestId('stytch-widget')).toBeInTheDocument();
    expect(screen.queryByLabelText('Password')).not.toBeInTheDocument();
  });

  it('renders both password and Stytch paths in mixed mode', async () => {
    server.use(
      http.get('*/api/meta', () =>
        HttpResponse.json({
          edition: 'ee',
          auth_modes: ['password', 'stytch'],
          stytch_public_token: 'pk-test-token',
        }),
      ),
    );
    renderWithProviders(<LoginForm />);

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /managed sign-in/i })).toBeInTheDocument(),
    );
    expect(screen.getByRole('heading', { name: /^sign in$/i })).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByRole('separator')).toBeInTheDocument();
    expect(screen.getByTestId('stytch-widget')).toBeInTheDocument();
  });

  it('prefers Stytch over the API-key notice when both are enabled', async () => {
    server.use(
      http.get('*/api/meta', () =>
        HttpResponse.json({
          edition: 'ee',
          auth_modes: ['stytch', 'apikey'],
          stytch_public_token: 'pk-test-token',
        }),
      ),
    );
    renderWithProviders(<LoginForm />);

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /managed sign-in/i })).toBeInTheDocument(),
    );
    expect(screen.queryByRole('heading', { name: /configured API key/i })).not.toBeInTheDocument();
  });

  it('explains when no interactive auth mode is enabled', async () => {
    server.use(http.get('*/api/meta', () => HttpResponse.json({ edition: 'oss', auth_modes: [] })));
    renderWithProviders(<LoginForm />);

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /sign-in unavailable/i })).toBeInTheDocument(),
    );
    expect(screen.queryByLabelText('Password')).not.toBeInTheDocument();
  });
});
