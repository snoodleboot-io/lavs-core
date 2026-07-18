import { act, fireEvent, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { useCommandPalette } from './use-command-palette';

describe('useCommandPalette', () => {
  it('is closed initially', () => {
    const { result } = renderHook(() => useCommandPalette());
    expect(result.current.open).toBe(false);
  });

  it('toggles open with ⌘K / Ctrl+K', () => {
    const { result } = renderHook(() => useCommandPalette());

    act(() => {
      fireEvent.keyDown(window, { key: 'k', metaKey: true });
    });
    expect(result.current.open).toBe(true);

    act(() => {
      fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
    });
    expect(result.current.open).toBe(false);
  });

  it('closes on Escape', () => {
    const { result } = renderHook(() => useCommandPalette());

    act(() => result.current.setOpen(true));
    expect(result.current.open).toBe(true);

    act(() => {
      fireEvent.keyDown(window, { key: 'Escape' });
    });
    expect(result.current.open).toBe(false);
  });

  it('exposes an imperative toggle', () => {
    const { result } = renderHook(() => useCommandPalette());

    act(() => result.current.toggle());
    expect(result.current.open).toBe(true);
    act(() => result.current.toggle());
    expect(result.current.open).toBe(false);
  });

  it('removes its key listener on unmount', () => {
    const { result, unmount } = renderHook(() => useCommandPalette());
    unmount();

    act(() => {
      fireEvent.keyDown(window, { key: 'k', metaKey: true });
    });
    // No throw and no state update after unmount.
    expect(result.current.open).toBe(false);
  });
});
