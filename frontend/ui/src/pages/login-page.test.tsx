import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { db } from '@/mocks';
import { renderWithProviders } from '@/test';

import { LoginPage } from './login-page';

describe('LoginPage', () => {
  it('renders the brand chrome around the adaptive login form', async () => {
    db.principal = null;
    renderWithProviders(<LoginPage />, { route: '/login' });

    expect(screen.getByRole('heading', { name: /LAVS/ })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    });
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });
});
