import { screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';

import { NotFoundPage } from './not-found-page';

describe('NotFoundPage', () => {
  it('shows a not-found message and a link home', () => {
    render(
      <MemoryRouter>
        <NotFoundPage />
      </MemoryRouter>,
    );
    expect(screen.getByRole('heading', { name: /lost in the void/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /constellation/i })).toHaveAttribute('href', '/');
  });
});
