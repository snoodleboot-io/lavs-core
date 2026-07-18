import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { useScrub } from './use-scrub';

describe('useScrub', () => {
  it('defaults the position to maxTick ("now")', () => {
    const { result } = renderHook(() => useScrub(11));

    expect(result.current.position).toBe(11);
  });

  it('honours an explicit initial position (clamped)', () => {
    const { result } = renderHook(() => useScrub(11, 3));
    expect(result.current.position).toBe(3);

    const clamped = renderHook(() => useScrub(11, 99));
    expect(clamped.result.current.position).toBe(11);
  });

  it('stepRight clamps at maxTick', () => {
    const { result } = renderHook(() => useScrub(11, 10));

    act(() => result.current.stepRight());
    expect(result.current.position).toBe(11);

    act(() => result.current.stepRight());
    expect(result.current.position).toBe(11);
  });

  it('stepLeft clamps at 0', () => {
    const { result } = renderHook(() => useScrub(11, 1));

    act(() => result.current.stepLeft());
    expect(result.current.position).toBe(0);

    act(() => result.current.stepLeft());
    expect(result.current.position).toBe(0);
  });

  it('setPosition clamps into [0, maxTick]', () => {
    const { result } = renderHook(() => useScrub(11, 5));

    act(() => result.current.setPosition(20));
    expect(result.current.position).toBe(11);

    act(() => result.current.setPosition(-4));
    expect(result.current.position).toBe(0);

    act(() => result.current.setPosition(6.5));
    expect(result.current.position).toBe(6.5);
  });

  it('steps by whole ticks from a fractional position', () => {
    const { result } = renderHook(() => useScrub(11, 5.5));

    // ceil(5.5) - 1 == 5 (mirrors the mockup's ← behaviour).
    act(() => result.current.stepLeft());
    expect(result.current.position).toBe(5);

    // floor(5) + 1 == 6.
    act(() => result.current.stepRight());
    expect(result.current.position).toBe(6);
  });
});
