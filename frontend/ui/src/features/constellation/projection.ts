import { bumpMinor } from '@/lib';
import type { ComponentWithVersions, Timeline, Version } from '@/types';

import type { TimeAxis } from './geometry';

/** One component pinned (or not yet reached) by the current meridian position. */
export interface ManifestEntry {
  readonly component: ComponentWithVersions;
  readonly version: Version | null;
}

/** Default product base for the live readout when the server has no prior release. */
export const DEFAULT_PRODUCT_BASE = '5.0.0';

/**
 * The scrub-to-derive rule: the latest version on a component's stream whose tick
 * is at or before `tick`, or `null` when the meridian has not reached any station.
 */
export function pinnedFor(
  component: ComponentWithVersions,
  axis: TimeAxis,
  tick: number,
): Version | null {
  let best: Version | null = null;
  let bestTick = -1;

  for (const version of component.versions) {
    const versionTick = axis.tickOf(version.id);
    if (versionTick >= 0 && versionTick <= tick && versionTick >= bestTick) {
      best = version;
      bestTick = versionTick;
    }
  }

  return best;
}

/** Derive the pinned manifest across every component at the given meridian tick. */
export function deriveManifest(timeline: Timeline, axis: TimeAxis, tick: number): ManifestEntry[] {
  return timeline.components.map((component) => ({
    component,
    version: pinnedFor(component, axis, tick),
  }));
}

/**
 * Client mirror of the server's default minor bump for the live "derived product
 * version" readout (G-P5e). Returns `base` when nothing is pinned (no release
 * possible); otherwise the bumped value. The authoritative value comes from the
 * server on cut.
 */
export function derivedProductVersion(base: string, hasAnyPinned: boolean): string {
  const resolved = base.length > 0 ? base : DEFAULT_PRODUCT_BASE;
  return hasAnyPinned ? bumpMinor(resolved) : resolved;
}
