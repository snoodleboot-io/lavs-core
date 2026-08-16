import { describe, expect, it } from 'vitest';

import type { Version } from '@/types';

import { bumpMinor, compareVersions, formatVersion, parseVersion } from './semver';

function version(overrides: Partial<Version>): Version {
  return {
    id: 'v',
    component_id: 'c',
    major: 1,
    minor: 2,
    patch: 3,
    prerelease: null,
    status: 'active',
    created_at: '2026-05-01T00:00:00.000Z',
    ...overrides,
  };
}

describe('formatVersion', () => {
  it('renders major.minor.patch', () => {
    expect(formatVersion(version({ major: 2, minor: 4, patch: 0 }))).toBe('2.4.0');
  });

  it('appends a prerelease when present', () => {
    expect(formatVersion(version({ prerelease: 'rc.1' }))).toBe('1.2.3-rc.1');
  });
});

describe('parseVersion', () => {
  it('parses a plain semver', () => {
    expect(parseVersion('3.1.4')).toEqual({ major: 3, minor: 1, patch: 4, prerelease: null });
  });

  it('parses a prerelease', () => {
    expect(parseVersion('1.0.0-beta.2')).toEqual({
      major: 1,
      minor: 0,
      patch: 0,
      prerelease: 'beta.2',
    });
  });

  it('returns null for a non-semver string', () => {
    expect(parseVersion('not-a-version')).toBeNull();
  });
});

describe('compareVersions', () => {
  it('orders by major then minor then patch', () => {
    const a = parseVersion('1.2.0')!;
    const b = parseVersion('1.10.0')!;
    expect(compareVersions(a, b)).toBeLessThan(0);
  });

  it('sorts a prerelease before its release', () => {
    const pre = parseVersion('1.0.0-rc.1')!;
    const release = parseVersion('1.0.0')!;
    expect(compareVersions(pre, release)).toBeLessThan(0);
  });
});

describe('bumpMinor', () => {
  it('bumps the minor and resets patch (client mirror of the server rule)', () => {
    expect(bumpMinor('5.0.0')).toBe('5.1.0');
    expect(bumpMinor('5.3.7')).toBe('5.4.0');
  });

  it('returns the input unchanged when it is not semver', () => {
    expect(bumpMinor('unknown')).toBe('unknown');
  });
});
