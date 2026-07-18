import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse, http } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { SEED_PRODUCT_ID, server } from '@/mocks';
import { renderWithProviders } from '@/test';
import type { Release } from '@/types';

import { CutReleaseButton } from './cut-release-button';

function forceCutError(): void {
  server.use(
    http.post('*/api/products/:id/releases', () =>
      HttpResponse.json(
        { error: { code: 'validation_error', message: 'Nothing to cut', details: null } },
        { status: 422 },
      ),
    ),
  );
}

describe('CutReleaseButton', () => {
  it('cuts a release on click and fires onCut with the frozen release', async () => {
    const onCut = vi.fn<(release: Release) => void>();
    renderWithProviders(
      <CutReleaseButton productId={SEED_PRODUCT_ID} label="Aurora 5.1" onCut={onCut} />,
    );

    await userEvent.click(screen.getByRole('button', { name: /cut release/i }));

    await waitFor(() => expect(onCut).toHaveBeenCalledTimes(1));
    expect(onCut.mock.calls[0]?.[0].product_version).toBe('5.1.0');
  });

  it('cuts when the `c` hotkey is pressed outside a text field', async () => {
    const onCut = vi.fn<(release: Release) => void>();
    renderWithProviders(<CutReleaseButton productId={SEED_PRODUCT_ID} onCut={onCut} />);

    await userEvent.keyboard('c');

    await waitFor(() => expect(onCut).toHaveBeenCalledTimes(1));
  });

  it('does NOT cut when `c` is typed inside an input', async () => {
    const onCut = vi.fn<(release: Release) => void>();
    renderWithProviders(
      <>
        <input aria-label="notes" />
        <CutReleaseButton productId={SEED_PRODUCT_ID} onCut={onCut} />
      </>,
    );

    await userEvent.click(screen.getByLabelText('notes'));
    await userEvent.keyboard('c');

    // Give any accidental async cut a chance to resolve, then assert it never happened.
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(onCut).not.toHaveBeenCalled();
    expect(screen.getByLabelText('notes')).toHaveValue('c');
  });

  it('disables both the button and the hotkey when `disabled`', async () => {
    const onCut = vi.fn<(release: Release) => void>();
    renderWithProviders(<CutReleaseButton productId={SEED_PRODUCT_ID} disabled onCut={onCut} />);

    expect(screen.getByRole('button', { name: /cut release/i })).toBeDisabled();

    await userEvent.keyboard('c');
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(onCut).not.toHaveBeenCalled();
  });

  it('surfaces an alert when the cut fails', async () => {
    forceCutError();
    const onCut = vi.fn<(release: Release) => void>();
    renderWithProviders(<CutReleaseButton productId={SEED_PRODUCT_ID} onCut={onCut} />);

    await userEvent.click(screen.getByRole('button', { name: /cut release/i }));

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    expect(screen.getByRole('alert')).toHaveTextContent(/nothing to cut/i);
    expect(onCut).not.toHaveBeenCalled();
  });
});
