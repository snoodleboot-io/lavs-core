import { useCallback, useState } from 'react';

/** Meridian scrub controller over the ordinal tick range `[0, maxTick]`. */
export interface Scrub {
  /** Current meridian position (may be fractional after a half-tick drag snap). */
  readonly position: number;
  /** Clamp and set the position directly (used by pointer drag). */
  readonly setPosition: (next: number) => void;
  /** Move one whole tick towards 0 (mockup's ← key). */
  readonly stepLeft: () => void;
  /** Move one whole tick towards `maxTick` (mockup's → key). */
  readonly stepRight: () => void;
}

function clamp(value: number, maxTick: number): number {
  return Math.max(0, Math.min(maxTick, value));
}

/**
 * Manage the meridian position over `[0, maxTick]`. Defaults to `maxTick` ("now",
 * the right edge). Stepping moves by whole ticks and clamps to the range.
 */
export function useScrub(maxTick: number, initial?: number): Scrub {
  const [position, setPositionState] = useState<number>(() => clamp(initial ?? maxTick, maxTick));

  const setPosition = useCallback(
    (next: number): void => setPositionState(clamp(next, maxTick)),
    [maxTick],
  );

  const stepRight = useCallback(
    (): void => setPositionState((prev) => clamp(Math.floor(prev) + 1, maxTick)),
    [maxTick],
  );

  const stepLeft = useCallback(
    (): void => setPositionState((prev) => clamp(Math.ceil(prev) - 1, maxTick)),
    [maxTick],
  );

  return { position, setPosition, stepLeft, stepRight };
}
