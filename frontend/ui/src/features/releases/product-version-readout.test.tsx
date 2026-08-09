import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ProductVersionReadout } from './product-version-readout';

describe('ProductVersionReadout', () => {
  it('renders the derived product version and the tick readout', () => {
    render(<ProductVersionReadout productVersion="5.1.0" tick={13} />);

    expect(screen.getByTestId('product-version')).toHaveTextContent('5.1.0');
    expect(screen.getByTestId('meridian-tick')).toHaveTextContent('t = 13');
    expect(screen.getByText(/derived product version/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /release meridian/i })).toBeInTheDocument();
  });
});
