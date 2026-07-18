import type { Release, ReleaseComponent } from '@/types';

/** A flattened, display-ready row for one pinned component in a frozen release. */
export interface FrozenManifestEntry {
  readonly componentId: string;
  readonly name: string;
  readonly versionId: string;
  readonly version: string;
}

/** Map a release's frozen `components[]` to a stable display list (e.g. for reopen). */
export function frozenManifestOf(release: Release): FrozenManifestEntry[] {
  return release.components.map((component: ReleaseComponent) => ({
    componentId: component.component_id,
    name: component.name,
    versionId: component.version_id,
    version: component.version,
  }));
}
