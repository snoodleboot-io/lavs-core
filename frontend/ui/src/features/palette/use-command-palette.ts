import { useCallback, useEffect, useState } from 'react';

export interface UseCommandPalette {
  readonly open: boolean;
  readonly setOpen: (open: boolean) => void;
  readonly toggle: () => void;
}

/**
 * Owns the open/closed state of the ⌘K command palette and its global key listener:
 * ⌘K / Ctrl+K toggles it (preventing the browser default), Esc closes it.
 */
export function useCommandPalette(): UseCommandPalette {
  const [open, setOpen] = useState(false);

  const toggle = useCallback((): void => setOpen((current) => !current), []);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent): void {
      const isToggle = (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k';
      if (isToggle) {
        event.preventDefault();
        setOpen((current) => !current);
        return;
      }
      if (event.key === 'Escape') {
        setOpen(false);
      }
    }

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  return { open, setOpen, toggle };
}
