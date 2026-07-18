import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';

import { useFocusTrap } from './use-focus-trap';

import styles from './command-palette.module.css';

export interface PaletteAction {
  readonly id: string;
  readonly label: string;
  readonly hint?: string;
  readonly run: () => void;
}

export interface CommandPaletteProps {
  readonly actions: readonly PaletteAction[];
  readonly open: boolean;
  readonly onClose: () => void;
}

/**
 * ⌘K command palette: a modal dialog with a filter input and a keyboard-navigable
 * option list. ArrowUp/Down move the active option, Enter runs it, Esc closes. Focus is
 * trapped while open and restored to the previously-focused element on close.
 */
export function CommandPalette({ actions, open, onClose }: CommandPaletteProps): ReactNode {
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);

  useFocusTrap(dialogRef, open);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return actions;
    return actions.filter((action) => action.label.toLowerCase().includes(needle));
  }, [actions, query]);

  // Reset transient state each time the palette opens; keep the active option in range.
  useEffect(() => {
    if (open) {
      setQuery('');
      setActiveIndex(0);
    }
  }, [open]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    setActiveIndex((current) => {
      if (filtered.length === 0) return 0;
      return Math.min(current, filtered.length - 1);
    });
  }, [filtered.length]);

  if (!open) return null;

  const activeAction = filtered[activeIndex];
  const activeId = activeAction ? `command-option-${activeAction.id}` : undefined;

  function onKeyDown(event: React.KeyboardEvent<HTMLDivElement>): void {
    if (event.key === 'Escape') {
      event.preventDefault();
      onClose();
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      if (filtered.length > 0) setActiveIndex((current) => (current + 1) % filtered.length);
      return;
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      if (filtered.length > 0) {
        setActiveIndex((current) => (current - 1 + filtered.length) % filtered.length);
      }
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      if (activeAction) {
        activeAction.run();
        onClose();
      }
    }
  }

  return (
    <div
      className={styles.overlay}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        onKeyDown={onKeyDown}
      >
        <input
          ref={inputRef}
          className={styles.input}
          type="text"
          role="combobox"
          aria-expanded="true"
          aria-controls="command-listbox"
          aria-activedescendant={activeId}
          aria-label="Filter commands"
          placeholder="Type a command…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />

        <ul id="command-listbox" className={styles.list} role="listbox" aria-label="Commands">
          {filtered.length === 0 ? (
            <li className={styles.empty} role="option" aria-selected="false" aria-disabled="true">
              No matching commands
            </li>
          ) : (
            filtered.map((action, index) => (
              <li
                key={action.id}
                id={`command-option-${action.id}`}
                className={index === activeIndex ? styles.optionActive : styles.option}
                role="option"
                aria-selected={index === activeIndex}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => {
                  action.run();
                  onClose();
                }}
              >
                <span className={styles.optionLabel}>{action.label}</span>
                {action.hint ? <span className={styles.optionHint}>{action.hint}</span> : null}
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}
