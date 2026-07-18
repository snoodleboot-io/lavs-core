import type { ReactNode } from 'react';

import styles from './constellation-view.module.css';

/** A single version node on a component stream. */
export interface StationProps {
  readonly versionId: string;
  readonly label: string;
  readonly cx: number;
  readonly cy: number;
  readonly hue: string;
  /** Pinned by the current meridian (enlarged + glowing). */
  readonly pinned: boolean;
  /** The meridian has reached this station (else dimmed as "not yet"). */
  readonly reached: boolean;
  /** Freshly created — pulse for emphasis (collapsed under reduced-motion). */
  readonly fresh: boolean;
  /** Rolled back — dimmed + struck through. */
  readonly rolledBack: boolean;
}

export function Station(props: StationProps): ReactNode {
  const { versionId, label, cx, cy, hue, pinned, reached, fresh, rolledBack } = props;

  const radius = pinned ? 8 : 5.5;
  const className = [
    styles.station,
    pinned ? styles.stationPinned : '',
    reached ? '' : styles.stationUnreached,
    fresh ? styles.stationFresh : '',
    rolledBack ? styles.stationRolledBack : '',
  ]
    .filter(Boolean)
    .join(' ');

  const ariaLabel = `${label}${pinned ? ' (pinned)' : ''}${rolledBack ? ' (rolled back)' : ''}`;

  return (
    <g
      className={className}
      role="img"
      aria-label={ariaLabel}
      data-testid={`station-${versionId}`}
      data-pinned={pinned}
      data-reached={reached}
      data-fresh={fresh}
      data-rolled-back={rolledBack}
    >
      <circle
        cx={cx}
        cy={cy}
        r={radius}
        className={styles.stationDot}
        style={{ stroke: hue, fill: pinned ? hue : 'var(--panel-solid)' }}
      />
      <text
        x={cx}
        y={cy - 13}
        textAnchor="middle"
        className={`${styles.stationLabel} mono`}
        style={pinned ? { fill: hue } : undefined}
      >
        {label}
      </text>
    </g>
  );
}
