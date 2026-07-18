import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse, http } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { server } from '@/mocks';
import { renderWithProviders } from '@/test';

import { LoginForm } from './login-form';

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

  it('shows a managed sign-in placeholder for stytch-only deployments', async () => {
    server.use(
      http.get('*/api/meta', () => HttpResponse.json({ edition: 'ee', auth_modes: ['stytch'] })),
    );
    renderWithProviders(<LoginForm />);

    await waitFor(() => expect(screen.getByText(/coming soon/i)).toBeInTheDocument());
    expect(screen.queryByLabelText('Password')).not.toBeInTheDocument();
  });
});
