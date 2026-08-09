import { describe, expect, it } from 'vitest';

import type { VersionCreatedEvent, VersionRolledBackEvent } from '@/api';
import { seedComponents, seedProduct } from '@/mocks';
import type { Timeline, Version } from '@/types';

import { applyVersionCreated, applyVersionRolledBack } from './event-cache';

function buildTimeline(): Timeline {
  return { product: seedProduct(), components: seedComponents() };
}

describe('applyVersionCreated', () => {
  it('appends the version, marks it active, and demotes the previous active', () => {
    const timeline = buildTimeline();
    const incoming: Version = {
      id: 'comp-api-v5',
      component_id: 'comp-api',
      major: 2,
      minor: 5,
      patch: 0,
      prerelease: null,
      status: 'active',
      created_at: '2026-05-13T12:00:00.000Z',
    };
    const event: VersionCreatedEvent = { component_id: 'comp-api', version: incoming };

    const next = applyVersionCreated(timeline, event);
    const api = next.components.find((component) => component.id === 'comp-api');

    expect(api?.versions).toHaveLength(6);
    expect(api?.versions.at(-1)).toMatchObject({ id: 'comp-api-v5', status: 'active' });
    // Previously active 2.4.0 is now superseded.
    const prevActive = api?.versions.find((version) => version.id === 'comp-api-v4');
    expect(prevActive?.status).toBe('superseded');
    // Exactly one active version remains for that component.
    expect(api?.versions.filter((version) => version.status === 'active')).toHaveLength(1);
  });

  it('does not touch other components', () => {
    const timeline = buildTimeline();
    const event: VersionCreatedEvent = {
      component_id: 'comp-api',
      version: {
        id: 'comp-api-v5',
        component_id: 'comp-api',
        major: 2,
        minor: 5,
        patch: 0,
        prerelease: null,
        status: 'active',
        created_at: '2026-05-13T12:00:00.000Z',
      },
    };

    const next = applyVersionCreated(timeline, event);
    const ui = next.components.find((component) => component.id === 'comp-ui');

    expect(ui).toBe(timeline.components.find((component) => component.id === 'comp-ui'));
  });

  it('does not mutate the input timeline', () => {
    const timeline = buildTimeline();
    const before = structuredClone(timeline);
    const event: VersionCreatedEvent = {
      component_id: 'comp-api',
      version: {
        id: 'comp-api-v5',
        component_id: 'comp-api',
        major: 2,
        minor: 5,
        patch: 0,
        prerelease: null,
        status: 'active',
        created_at: '2026-05-13T12:00:00.000Z',
      },
    };

    const next = applyVersionCreated(timeline, event);

    expect(timeline).toEqual(before);
    expect(next).not.toBe(timeline);
    expect(next.components).not.toBe(timeline.components);
  });
});

describe('applyVersionRolledBack', () => {
  it('flips the rolled-back and reactivated statuses', () => {
    const timeline = buildTimeline();
    const event: VersionRolledBackEvent = {
      component_id: 'comp-api',
      version_id: 'comp-api-v4',
      reactivated_version_id: 'comp-api-v3',
    };

    const next = applyVersionRolledBack(timeline, event);
    const api = next.components.find((component) => component.id === 'comp-api');

    expect(api?.versions.find((version) => version.id === 'comp-api-v4')?.status).toBe(
      'rolled_back',
    );
    expect(api?.versions.find((version) => version.id === 'comp-api-v3')?.status).toBe('active');
  });

  it('does not mutate the input timeline', () => {
    const timeline = buildTimeline();
    const before = structuredClone(timeline);
    const event: VersionRolledBackEvent = {
      component_id: 'comp-api',
      version_id: 'comp-api-v4',
      reactivated_version_id: 'comp-api-v3',
    };

    const next = applyVersionRolledBack(timeline, event);

    expect(timeline).toEqual(before);
    expect(next).not.toBe(timeline);
  });
});
