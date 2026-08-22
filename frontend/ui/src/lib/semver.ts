import type { Version } from '@/types';

export interface SemVer {
  readonly major: number;
  readonly minor: number;
  readonly patch: number;
  readonly prerelease: string | null;
}

const SEMVER_RE = /^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$/;

/** Render a Version's numeric fields as a `major.minor.patch(-prerelease)` string. */
export function formatVersion(version: Version): string {
  const base = `${version.major}.${version.minor}.${version.patch}`;
  return version.prerelease ? `${base}-${version.prerelease}` : base;
}

/** Parse a `x.y.z(-pre)` string; returns null if it doesn't match the contract's shape. */
export function parseVersion(value: string): SemVer | null {
  const match = SEMVER_RE.exec(value);
  if (!match) return null;
  const [, major, minor, patch, prerelease] = match;
  return {
    major: Number(major),
    minor: Number(minor),
    patch: Number(patch),
    prerelease: prerelease ?? null,
  };
}

/** Ordering: by major, then minor, then patch. A prerelease sorts before its release. */
export function compareVersions(a: SemVer, b: SemVer): number {
  if (a.major !== b.major) return a.major - b.major;
  if (a.minor !== b.minor) return a.minor - b.minor;
  if (a.patch !== b.patch) return a.patch - b.patch;
  if (a.prerelease === b.prerelease) return 0;
  if (a.prerelease === null) return 1;
  if (b.prerelease === null) return -1;
  return a.prerelease < b.prerelease ? -1 : 1;
}

/**
 * Client mirror of the server's default bump (minor) for the live "derived product version"
 * readout while scrubbing (G-P5e). The authoritative value still comes from the server on cut.
 */
export function bumpMinor(current: string): string {
  const parsed = parseVersion(current);
  if (!parsed) return current;
  return `${parsed.major}.${parsed.minor + 1}.0`;
}
