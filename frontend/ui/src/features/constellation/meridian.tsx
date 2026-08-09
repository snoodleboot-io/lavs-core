import type { KeyboardEvent, ReactNode } from 'react';

import { LANE_TOP, VIEWBOX } from './geometry';
import styles from './constellation-view.module.css';

/** The luminous, keyboard-operable release meridian (a slider over the tick range). */
export interface MeridianProps {
  readonly x: number;
  readonly position: number;
  readonly maxTick: number;
  readonly onKeyDown: (event: KeyboardEvent<SVGGElement>) => void;
}

export function Meridian(props: MeridianProps): ReactNode {
  const { x, position, maxTick, onKeyDown } = props;
  const top = LANE_TOP - 12;
  const bottom = VIEWBOX.height - VIEWBOX.padBottom;
  const now = Math.round(position);

  return (
    <g
      className={styles.meridian}
      role="slider"
      tabIndex={0}
      aria-label="Release meridian"
      aria-valuemin={0}
      aria-valuemax={maxTick}
      aria-valuenow={now}
      aria-valuetext={`tick ${now} of ${maxTick}`}
      onKeyDown={onKeyDown}
    >
      <line x1={x} y1={top} x2={x} y2={bottom} className={styles.meridianLine} />
      <polygon
        points={`${x - 7},${LANE_TOP - 20} ${x + 7},${LANE_TOP - 20} ${x},${LANE_TOP - 8}`}
        className={styles.meridianHandle}
      />
    </g>
  );
}
