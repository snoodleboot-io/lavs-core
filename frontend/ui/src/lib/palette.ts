import type { ComponentKind } from '@/types';

// Semantic hue per component kind (mirrors the CSS tokens in src/styles/tokens.css).
export const KIND_HUE: Readonly<Record<ComponentKind, string>> = {
  service: '#5ad1ff',
  ui: '#b78cff',
  library: '#7cffb0',
  cli: '#ffd166',
};

// Collision-free rotation for the constellation streams, ordered to match the mockup.
const CONSTELLATION_HUES: readonly string[] = [
  '#5ad1ff',
  '#b78cff',
  '#7cffb0',
  '#ffd166',
  '#ff8fab',
  '#8fd0ff',
  '#c3f584',
  '#ffb27a',
];

/** Stable hue for a component's stream by its position in the timeline. */
export function hueForIndex(index: number): string {
  const hue = CONSTELLATION_HUES[index % CONSTELLATION_HUES.length];
  return hue ?? '#5ad1ff';
}
