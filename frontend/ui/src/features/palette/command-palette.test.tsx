import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { CommandPalette, type PaletteAction } from './index';

function makeActions(): { actions: PaletteAction[]; runAlpha: () => void; runBeta: () => void } {
  const runAlpha = vi.fn();
  const runBeta = vi.fn();
  const actions: PaletteAction[] = [
    { id: 'alpha', label: 'Alpha command', hint: '⌘1', run: runAlpha },
    { id: 'beta', label: 'Beta command', hint: '⌘2', run: runBeta },
  ];
  return { actions, runAlpha, runBeta };
}

describe('CommandPalette', () => {
  it('renders nothing when closed', () => {
    const { actions } = makeActions();
    render(<CommandPalette actions={actions} open={false} onClose={vi.fn()} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders an accessible modal dialog when open', () => {
    const { actions } = makeActions();
    render(<CommandPalette actions={actions} open onClose={vi.fn()} />);

    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(screen.getByRole('listbox')).toBeInTheDocument();
    expect(screen.getAllByRole('option')).toHaveLength(2);
  });

  it('filters options by the typed query', async () => {
    const { actions } = makeActions();
    const user = userEvent.setup();
    render(<CommandPalette actions={actions} open onClose={vi.fn()} />);

    await user.keyboard('Alpha');
    expect(screen.getByText('Alpha command')).toBeInTheDocument();
    expect(screen.queryByText('Beta command')).not.toBeInTheDocument();
  });

  it('runs the active option on ArrowDown + Enter and closes', async () => {
    const { actions, runAlpha, runBeta } = makeActions();
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<CommandPalette actions={actions} open onClose={onClose} />);

    await user.keyboard('{ArrowDown}{Enter}');

    expect(runBeta).toHaveBeenCalledTimes(1);
    expect(runAlpha).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('runs the first option on Enter by default', async () => {
    const { actions, runAlpha } = makeActions();
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<CommandPalette actions={actions} open onClose={onClose} />);

    await user.keyboard('{Enter}');
    expect(runAlpha).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('closes on Escape', async () => {
    const { actions } = makeActions();
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<CommandPalette actions={actions} open onClose={onClose} />);

    await user.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('shows an empty state when nothing matches', async () => {
    const { actions } = makeActions();
    const user = userEvent.setup();
    render(<CommandPalette actions={actions} open onClose={vi.fn()} />);

    await user.keyboard('zzz');
    expect(screen.getByText(/no matching commands/i)).toBeInTheDocument();
  });

  it('runs an option on click and closes', async () => {
    const { actions, runBeta } = makeActions();
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<CommandPalette actions={actions} open onClose={onClose} />);

    await user.click(screen.getByText('Beta command'));
    expect(runBeta).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('activates an option on mouse enter, then Enter runs it', async () => {
    const { actions, runBeta } = makeActions();
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<CommandPalette actions={actions} open onClose={onClose} />);

    await user.hover(screen.getByText('Beta command'));
    await user.keyboard('{Enter}');
    expect(runBeta).toHaveBeenCalledTimes(1);
  });

  it('closes when the overlay backdrop is clicked', async () => {
    const { actions } = makeActions();
    const onClose = vi.fn();
    const user = userEvent.setup();
    const { container } = render(<CommandPalette actions={actions} open onClose={onClose} />);

    const overlay = container.firstElementChild as HTMLElement;
    await user.pointer({ keys: '[MouseLeft]', target: overlay });
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
