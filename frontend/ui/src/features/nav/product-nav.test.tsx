import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse, http } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { server } from '@/mocks';
import { renderWithProviders } from '@/test';

import { ProductNav } from './product-nav';

describe('ProductNav', () => {
  it('renders products from the seed and reports the count', async () => {
    renderWithProviders(<ProductNav productId={undefined} onSelect={vi.fn()} />);

    await waitFor(() =>
      expect(screen.getByRole('option', { name: 'Aurora Platform' })).toBeInTheDocument(),
    );
    expect(screen.getByText('1 product')).toBeInTheDocument();
  });

  it('calls onSelect with the chosen product id', async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<ProductNav productId={undefined} onSelect={onSelect} />);

    const select = await screen.findByLabelText('Product');
    await user.selectOptions(select, 'prod-aurora');

    expect(onSelect).toHaveBeenCalledWith('prod-aurora');
  });

  it('shows an empty state when there are no products', async () => {
    server.use(http.get('*/api/products', () => HttpResponse.json([])));
    renderWithProviders(<ProductNav productId={undefined} onSelect={vi.fn()} />);

    await waitFor(() => expect(screen.getByText(/no products yet/i)).toBeInTheDocument());
  });

  it('surfaces a load error', async () => {
    server.use(
      http.get('*/api/products', () =>
        HttpResponse.json(
          { error: { code: 'unknown', message: 'boom', details: null } },
          { status: 500 },
        ),
      ),
    );
    renderWithProviders(<ProductNav productId={undefined} onSelect={vi.fn()} />);

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/could not load/i));
  });
});
