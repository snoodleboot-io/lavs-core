import { useEffect, useState } from 'react';

// Honour `prefers-reduced-motion` so the Constellation can collapse pulses to instant.
const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';

function readReducedMotion(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false;
  return window.matchMedia(REDUCED_MOTION_QUERY).matches;
}

/** `true` when the user has requested reduced motion; updates live on OS/browser changes. */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState<boolean>(readReducedMotion);

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;

    const query = window.matchMedia(REDUCED_MOTION_QUERY);
    setReduced(query.matches);

    const onChange = (event: MediaQueryListEvent): void => setReduced(event.matches);
    query.addEventListener('change', onChange);
    return (): void => query.removeEventListener('change', onChange);
  }, []);

  return reduced;
}
