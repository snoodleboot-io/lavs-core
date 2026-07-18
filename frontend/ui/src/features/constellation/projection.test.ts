import { describe, expect, it } from 'vitest';

import { seedComponents, seedProduct } from '@/mocks';
import type { ComponentWithVersions, Timeline } from '@/types';

import { buildTimeAxis } from './geometry';
import {
  DEFAULT_PRODUCT_BASE,
  deriveManifest,
  derivedProductVersion,
  pinnedFor,
} from './projection';

function makeTimeline(): Timeline {
  return { product: seedProduct(), components: seedComponents() };
}

function componentById(timeline: Timeline, id: string): ComponentWithVersions {
  const found = timeline.components.find((component) => component.id === id);
  if (!found) throw new Error(`missing component ${id}`);
  return found;
}

describe('pinnedFor', () => {
  it('pins the latest version at or before the tick', () => {
    const timeline = makeTimeline();
    const axis = buildTimeAxis(timeline);
    const api = componentById(timeline, 'comp-api');

    // day 5 == tick 4 → api 2.2.0 (comp-api-v2).
    expect(pinnedFor(api, axis, 4)?.id).toBe('comp-api-v2');
    // At maxTick, the active (latest) version is pinned.
    expect(pinnedFor(api, axis, axis.maxTick)?.id).toBe('comp-api-v4');
  });

  it('pins the earliest reached station and null for streams not yet reached at tick 0', () => {
    const timeline = makeTimeline();
    const axis = buildTimeAxis(timeline);

    // api + helm have a day-1 (tick 0) station.
    expect(pinnedFor(componentById(timeline, 'comp-api'), axis, 0)?.id).toBe('comp-api-v0');
    expect(pinnedFor(componentById(timeline, 'comp-helm'), axis, 0)?.id).toBe('comp-helm-v0');
    // ui (day 2) and cli (day 3) have no station at tick 0.
    expect(pinnedFor(componentById(timeline, 'comp-ui'), axis, 0)).toBeNull();
    expect(pinnedFor(componentById(timeline, 'comp-cli'), axis, 0)).toBeNull();
  });
});

describe('deriveManifest', () => {
  it('returns one entry per component', () => {
    const timeline = makeTimeline();
    const axis = buildTimeAxis(timeline);

    const manifest = deriveManifest(timeline, axis, axis.maxTick);

    expect(manifest).toHaveLength(timeline.components.length);
    expect(manifest.every((entry) => entry.version !== null)).toBe(true);
  });

  it('leaves not-yet-reached components unpinned at tick 0', () => {
    const timeline = makeTimeline();
    const axis = buildTimeAxis(timeline);

    const manifest = deriveManifest(timeline, axis, 0);
    const uiEntry = manifest.find((entry) => entry.component.id === 'comp-ui');

    expect(uiEntry?.version).toBeNull();
  });
});

describe('derivedProductVersion', () => {
  it('bumps the minor when anything is pinned', () => {
    expect(derivedProductVersion('5.0.0', true)).toBe('5.1.0');
    expect(derivedProductVersion('5.3.0', true)).toBe('5.4.0');
  });

  it('returns the base unchanged when nothing is pinned', () => {
    expect(derivedProductVersion('5.0.0', false)).toBe('5.0.0');
  });

  it('falls back to the default base when given an empty string', () => {
    expect(derivedProductVersion('', true)).toBe('5.1.0');
    expect(DEFAULT_PRODUCT_BASE).toBe('5.0.0');
  });
});
