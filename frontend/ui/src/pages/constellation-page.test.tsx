import { screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '@/test';

import { ConstellationPage } from './constellation-page';

describe('ConstellationPage (integration)', () => {
  it('composes the seeded product into the constellation workspace', async () => {
    renderWithProviders(<ConstellationPage />);

    // Shell shows the resolved product context.
    await waitFor(() => {
      expect(screen.getByText(/Aurora Platform · 4 components/)).toBeInTheDocument();
    });

    // R1: the SVG streams render (one per seeded component).
    expect(screen.getByTestId('stream-comp-api')).toBeInTheDocument();
    expect(screen.getByTestId('stream-comp-ui')).toBeInTheDocument();
    expect(screen.getByTestId('stream-comp-helm')).toBeInTheDocument();
    expect(screen.getByTestId('stream-comp-cli')).toBeInTheDocument();

    // R1: the meridian is a keyboard-operable slider.
    expect(screen.getByRole('slider', { name: /release meridian/i })).toBeInTheDocument();

    // R2: the derived product-version readout + cut control are present.
    expect(screen.getByRole('button', { name: /cut release/i })).toBeInTheDocument();

    // R4: the product nav is in the shell.
    const nav = screen.getByRole('combobox', { name: /product/i });
    expect(within(nav).getByText(/Aurora Platform/)).toBeInTheDocument();
  });
});
