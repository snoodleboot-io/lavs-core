import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { describe, expect, it } from 'vitest';

import { db } from '@/mocks';
import { renderWithProviders } from '@/test';

import { useAuth } from './use-auth';

function AuthProbe(): ReactNode {
  const { status, principal, meta, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="email">{principal?.email ?? 'none'}</span>
      <span data-testid="modes">{meta?.auth_modes.join(',') ?? 'none'}</span>
      <button type="button" onClick={() => void login({ email: 'a@b.com', password: 'ok' })}>
        login
      </button>
      <button type="button" onClick={() => void logout()}>
        logout
      </button>
    </div>
  );
}

describe('AuthProvider / useAuth', () => {
  it('exposes the authenticated principal and meta from the API', async () => {
    renderWithProviders(<AuthProbe />);

    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('authenticated'));
    expect(screen.getByTestId('email')).toHaveTextContent('astronomer@snoodleboot.com');
    expect(screen.getByTestId('modes')).toHaveTextContent('password,apikey');
  });

  it('reports unauthenticated when there is no session', async () => {
    db.principal = null;
    renderWithProviders(<AuthProbe />);

    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('unauthenticated'));
    expect(screen.getByTestId('email')).toHaveTextContent('none');
  });

  it('logs in and then out, updating status', async () => {
    db.principal = null;
    const user = userEvent.setup();
    renderWithProviders(<AuthProbe />);

    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('unauthenticated'));

    await user.click(screen.getByRole('button', { name: 'login' }));
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('authenticated'));

    await user.click(screen.getByRole('button', { name: 'logout' }));
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('unauthenticated'));
  });
});
