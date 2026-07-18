import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { db } from '@/mocks';

import { App } from './app';

// Full app boot through the real providers + router (covers providers/query-client/routes/require-auth).
describe('App', () => {
  it('renders the constellation for an authenticated session at /', async () => {
    window.history.pushState({}, '', '/');
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Aurora Platform · 4 components/)).toBeInTheDocument();
    });
    expect(screen.getByRole('slider', { name: /release meridian/i })).toBeInTheDocument();
  });

  it('redirects an unauthenticated visitor from / to the login screen', async () => {
    db.principal = null;
    window.history.pushState({}, '', '/');
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Sign in/i })).toBeInTheDocument();
    });
  });
});
