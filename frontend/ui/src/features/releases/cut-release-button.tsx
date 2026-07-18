import { useCallback, useEffect, useState, type ReactNode } from 'react';

import type { Release } from '@/types';

import { useCutRelease } from './use-cut-release';

import styles from './cut-release-button.module.css';

export interface CutReleaseButtonProps {
  readonly productId: string;
  /** Optional human label persisted with the cut release. */
  readonly label?: string;
  /** Disable the action (e.g. nothing is pinned). Blocks both the button and the hotkey. */
  readonly disabled?: boolean;
  /** Called with the freshly cut release on success. */
  readonly onCut?: (release: Release) => void;
}

const BUTTON_TEXT = '⟡ Cut Release';

/** True when keyboard focus is inside a text-entry surface (so `c` shouldn't fire). */
function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target.isContentEditable;
}

/**
 * The "⟡ Cut Release" action. Wires the cut mutation, a global `c`/`C` hotkey (ignored while
 * typing or when disabled), a pending state, a crystallize flash on success, and an error alert.
 */
export function CutReleaseButton({
  productId,
  label,
  disabled = false,
  onCut,
}: CutReleaseButtonProps): ReactNode {
  const mutation = useCutRelease(productId);
  const [flashing, setFlashing] = useState(false);

  const isPending = mutation.isPending;
  const blocked = disabled || isPending;

  const handleCut = useCallback(async (): Promise<void> => {
    if (disabled || mutation.isPending) return;
    try {
      const release = await mutation.mutateAsync(label === undefined ? {} : { label });
      setFlashing(true);
      onCut?.(release);
    } catch {
      // The mutation records the error; the alert below surfaces it. Swallow to avoid an
      // unhandled rejection from mutateAsync.
    }
  }, [disabled, label, mutation, onCut]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent): void {
      if (event.key !== 'c' && event.key !== 'C') return;
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      if (disabled) return;
      if (isTypingTarget(event.target)) return;
      event.preventDefault();
      void handleCut();
    }

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [disabled, handleCut]);

  return (
    <div className={styles.wrap}>
      <button
        type="button"
        className={`${styles.button} ${flashing ? styles.flashing : ''}`}
        onClick={() => void handleCut()}
        onAnimationEnd={() => setFlashing(false)}
        disabled={blocked}
        aria-keyshortcuts="C"
        aria-busy={isPending}
      >
        {isPending ? 'Crystallizing…' : BUTTON_TEXT}
      </button>
      {mutation.isError ? (
        <p className={styles.error} role="alert">
          Couldn’t cut release: {mutation.error.message}
        </p>
      ) : null}
    </div>
  );
}
