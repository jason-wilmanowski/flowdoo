import { createStore } from "zustand/vanilla";

import {
  clampCursor,
  firstStep,
  isAtEnd,
  lastStep,
  nextStep,
  previousStep,
  type Cursor,
} from "@/lib/replay/cursor";

/** Steps per second while playing. */
export const REPLAY_SPEEDS = [0.5, 1, 2, 4, 8] as const;
export type ReplaySpeed = (typeof REPLAY_SPEEDS)[number];

export interface ReplayState {
  /** Position in seq order, or null for a trace without steps. */
  cursor: Cursor;
  stepCount: number;
  playing: boolean;
  speed: ReplaySpeed;
  /** New trace: cursor on the first step, paused. */
  reset: (stepCount: number) => void;
  first: () => void;
  last: () => void;
  next: () => void;
  previous: () => void;
  goTo: (position: number) => void;
  play: () => void;
  pause: () => void;
  toggle: () => void;
  setSpeed: (speed: ReplaySpeed) => void;
  /** One playback step (driven by a timer in the UI); stops at the last step. */
  tick: () => void;
}

export function createReplayStore() {
  return createStore<ReplayState>()((set, get) => ({
    cursor: null,
    stepCount: 0,
    playing: false,
    speed: 1,
    reset: (stepCount) => {
      set({ stepCount, cursor: firstStep(stepCount), playing: false });
    },
    first: () => {
      set({ cursor: firstStep(get().stepCount) });
    },
    last: () => {
      set({ cursor: lastStep(get().stepCount), playing: false });
    },
    next: () => {
      set(({ cursor, stepCount }) => ({ cursor: nextStep(cursor, stepCount) }));
    },
    previous: () => {
      set(({ cursor, stepCount }) => ({ cursor: previousStep(cursor, stepCount) }));
    },
    goTo: (position) => {
      set(({ stepCount }) => ({ cursor: clampCursor(position, stepCount) }));
    },
    play: () => {
      const { cursor, stepCount } = get();
      if (stepCount === 0) return;
      // playing from the end starts over
      set({ playing: true, cursor: isAtEnd(cursor, stepCount) ? firstStep(stepCount) : cursor });
    },
    pause: () => {
      set({ playing: false });
    },
    toggle: () => {
      if (get().playing) get().pause();
      else get().play();
    },
    setSpeed: (speed) => {
      set({ speed });
    },
    tick: () => {
      const { cursor, stepCount, playing } = get();
      if (!playing) return;
      const next = nextStep(cursor, stepCount);
      set({ cursor: next, playing: !isAtEnd(next, stepCount) });
    },
  }));
}
