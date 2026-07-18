import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { useReducedMotion } from './use-reduced-motion';

interface MockMedia {
  readonly mql: MediaQueryList;
  fire: (matches: boolean) => void;
}

function installMatchMedia(matches: boolean): MockMedia {
  let changeHandler: ((event: MediaQueryListEvent) => void) | null = null;
  const mql = {
    matches,
    media: '(prefers-reduced-motion: reduce)',
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn((_type: string, handler: (event: MediaQueryListEvent) => void) => {
      changeHandler = handler;
    }),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(() => false),
  } as unknown as MediaQueryList;

  window.matchMedia = vi.fn(() => mql);

  return {
    mql,
    fire: (next: boolean) => changeHandler?.({ matches: next } as MediaQueryListEvent),
  };
}

const originalMatchMedia = window.matchMedia;

afterEach(() => {
  window.matchMedia = originalMatchMedia;
  vi.restoreAllMocks();
});

describe('useReducedMotion', () => {
  it('returns the current matchMedia value', () => {
    installMatchMedia(true);
    const { result } = renderHook(() => useReducedMotion());
    expect(result.current).toBe(true);
  });

  it('returns false when reduced motion is not requested', () => {
    installMatchMedia(false);
    const { result } = renderHook(() => useReducedMotion());
    expect(result.current).toBe(false);
  });

  it('updates when the media query changes', () => {
    const media = installMatchMedia(false);
    const { result } = renderHook(() => useReducedMotion());
    expect(result.current).toBe(false);

    act(() => media.fire(true));
    expect(result.current).toBe(true);
  });
});
