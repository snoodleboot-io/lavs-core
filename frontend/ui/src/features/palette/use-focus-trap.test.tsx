import { fireEvent, render, screen } from '@testing-library/react';
import { useRef, useState, type ReactNode } from 'react';
import { describe, expect, it } from 'vitest';

import { useFocusTrap } from './use-focus-trap';

function Harness({ initialActive, empty }: { initialActive: boolean; empty?: boolean }): ReactNode {
  const ref = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(initialActive);
  useFocusTrap(ref, active);
  return (
    <div>
      <button type="button" data-testid="outside">
        outside
      </button>
      <button type="button" onClick={() => setActive((value) => !value)}>
        toggle
      </button>
      <div ref={ref} data-testid="trap">
        {empty ? null : (
          <>
            <button type="button" data-testid="first">
              first
            </button>
            <button type="button" data-testid="last">
              last
            </button>
          </>
        )}
      </div>
    </div>
  );
}

describe('useFocusTrap', () => {
  it('wraps Tab from the last element back to the first', () => {
    render(<Harness initialActive />);
    const trap = screen.getByTestId('trap');
    const last = screen.getByTestId('last');
    last.focus();

    fireEvent.keyDown(trap, { key: 'Tab' });
    expect(document.activeElement).toBe(screen.getByTestId('first'));
  });

  it('wraps Shift+Tab from the first element back to the last', () => {
    render(<Harness initialActive />);
    const trap = screen.getByTestId('trap');
    const first = screen.getByTestId('first');
    first.focus();

    fireEvent.keyDown(trap, { key: 'Tab', shiftKey: true });
    expect(document.activeElement).toBe(screen.getByTestId('last'));
  });

  it('ignores non-Tab keys', () => {
    render(<Harness initialActive />);
    const trap = screen.getByTestId('trap');
    const first = screen.getByTestId('first');
    first.focus();

    fireEvent.keyDown(trap, { key: 'a' });
    expect(document.activeElement).toBe(first);
  });

  it('prevents Tab when the container has no focusable children', () => {
    render(<Harness initialActive empty />);
    const trap = screen.getByTestId('trap');
    // No throw and focus is not moved into the (empty) trap.
    fireEvent.keyDown(trap, { key: 'Tab' });
    expect(trap).toBeEmptyDOMElement();
  });

  it('restores focus to the previously-focused element when deactivated', () => {
    render(<Harness initialActive={false} />);
    const outside = screen.getByTestId('outside');
    outside.focus();

    // Activating traps focus; deactivating should restore it to `outside`.
    fireEvent.click(screen.getByRole('button', { name: 'toggle' }));
    fireEvent.click(screen.getByRole('button', { name: 'toggle' }));
    expect(document.activeElement).toBe(outside);
  });
});
