import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '@/test';

import { ConstellationPage } from './constellation-page';

describe('ConstellationPage (foundation smoke)', () => {
  it('loads the seeded product timeline and lists component streams', async () => {
    renderWithProviders(<ConstellationPage />);

    // Product context appears in the shell once the timeline resolves.
    await waitFor(() => {
      expect(screen.getByText(/Aurora Platform · 4 components/)).toBeInTheDocument();
    });

    // Each seeded component stream is listed.
    expect(screen.getByText('lavs-api')).toBeInTheDocument();
    expect(screen.getByText('lavs-ui')).toBeInTheDocument();
    expect(screen.getByText('lavs-helm')).toBeInTheDocument();
    expect(screen.getByText('lavs-cli')).toBeInTheDocument();
  });
});
