import { Pause, Play, SkipBack, SkipForward, StepBack, StepForward } from "lucide-react";

import { IconButton } from "./IconButton";
import styles from "./ReplayControls.module.css";
import { Select } from "./Select";

export interface ReplayControlsProps {
  /** 0-based position, or null without steps. */
  position: number | null;
  count: number;
  playing: boolean;
  speed: number;
  speeds: readonly number[];
  onFirst: () => void;
  onPrevious: () => void;
  onToggle: () => void;
  onNext: () => void;
  onLast: () => void;
  onSeek: (position: number) => void;
  onSpeed: (speed: number) => void;
}

/** Play, pause, step, jump and speed for a replay; the keys are listed in the help (?). */
export function ReplayControls({
  position,
  count,
  playing,
  speed,
  speeds,
  onFirst,
  onPrevious,
  onToggle,
  onNext,
  onLast,
  onSeek,
  onSpeed,
}: ReplayControlsProps) {
  const empty = position === null || count === 0;
  const atStart = empty || position === 0;
  const atEnd = empty || position === count - 1;
  return (
    <div className={styles.controls}>
      <div className={styles.transport} role="group" aria-label="Replay">
        <IconButton
          icon={SkipBack}
          label="First step (Home)"
          compact
          disabled={atStart}
          onClick={onFirst}
        />
        <IconButton
          icon={StepBack}
          label="Previous step (←)"
          compact
          disabled={atStart}
          onClick={onPrevious}
        />
        <IconButton
          icon={playing ? Pause : Play}
          label={playing ? "Pause (Space)" : "Play (Space)"}
          variant="secondary"
          compact
          disabled={empty}
          onClick={onToggle}
        />
        <IconButton
          icon={StepForward}
          label="Next step (→)"
          compact
          disabled={atEnd}
          onClick={onNext}
        />
        <IconButton
          icon={SkipForward}
          label="Last step (End)"
          compact
          disabled={atEnd}
          onClick={onLast}
        />
      </div>
      <input
        type="range"
        className={styles.scrubber}
        aria-label="Replay position"
        min={1}
        max={Math.max(count, 1)}
        value={empty ? 1 : position + 1}
        disabled={empty}
        onChange={(event) => {
          onSeek(Number(event.target.value) - 1);
        }}
      />
      <span className={styles.position} aria-live="off">
        Step {empty ? 0 : position + 1} of {count}
      </span>
      <Select
        aria-label="Replay speed"
        compact
        value={String(speed)}
        options={speeds.map((value) => ({ value: String(value), label: `${String(value)}×` }))}
        onChange={(event) => {
          onSpeed(Number(event.target.value));
        }}
      />
    </div>
  );
}
