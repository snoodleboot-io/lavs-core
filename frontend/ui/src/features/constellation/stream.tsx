import type { ReactNode } from 'react';

import { formatVersion } from '@/lib';
import type { ComponentWithVersions } from '@/types';

import { xOf, yOf, type TimeAxis } from './geometry';
import { Station } from './station';
import styles from './constellation-view.module.css';

/** A component's horizontal timeline: its stream line, stations and pinned connector. */
export interface StreamProps {
  readonly component: ComponentWithVersions;
  readonly laneIndex: number;
  readonly laneCount: number;
  readonly axis: TimeAxis;
  readonly tick: number;
  readonly hue: string;
  readonly pinnedVersionId: string | null;
  readonly meridianX: number;
  readonly freshVersionIds: ReadonlySet<string>;
  readonly rolledBackVersionIds: ReadonlySet<string>;
}

export function Stream(props: StreamProps): ReactNode {
  const {
    component,
    laneIndex,
    laneCount,
    axis,
    tick,
    hue,
    pinnedVersionId,
    meridianX,
    freshVersionIds,
    rolledBackVersionIds,
  } = props;

  const y = yOf(laneIndex, laneCount);
  const { maxTick } = axis;
  const ticks = component.versions.map((version) => axis.tickOf(version.id));
  const firstX = xOf(Math.min(...ticks), maxTick);
  const lastX = xOf(Math.max(...ticks), maxTick);
  const pinnedX = pinnedVersionId ? xOf(axis.tickOf(pinnedVersionId), maxTick) : null;

  return (
    <g data-testid={`stream-${component.id}`} aria-label={component.name}>
      <line
        x1={firstX}
        y1={y}
        x2={lastX}
        y2={y}
        className={styles.streamLine}
        style={{ stroke: hue }}
      />

      {pinnedX !== null ? (
        <g className={styles.connector} data-testid={`connector-${component.id}`}>
          <line
            x1={pinnedX}
            y1={y}
            x2={meridianX}
            y2={y}
            className={styles.connectorLine}
            style={{ stroke: hue }}
          />
          <circle
            cx={meridianX}
            cy={y}
            r={3}
            className={styles.connectorDot}
            style={{ fill: hue }}
          />
        </g>
      ) : null}

      {component.versions.map((version) => {
        const versionTick = axis.tickOf(version.id);
        return (
          <Station
            key={version.id}
            versionId={version.id}
            label={formatVersion(version)}
            cx={xOf(versionTick, maxTick)}
            cy={y}
            hue={hue}
            pinned={version.id === pinnedVersionId}
            reached={versionTick <= tick}
            fresh={freshVersionIds.has(version.id)}
            rolledBack={rolledBackVersionIds.has(version.id)}
          />
        );
      })}
    </g>
  );
}
