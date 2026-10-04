import { useEffect } from "react";
import { useStore } from "zustand";

import { useShortcut } from "@/app/shortcuts/shortcutContext";
import { REPLAY_SPEEDS, type ReplaySpeed } from "@/stores";
import type { AppStores } from "@/stores";
import { ReplayControls } from "@/ui";

const isSpeed = (value: number): value is ReplaySpeed =>
  (REPLAY_SPEEDS as readonly number[]).includes(value);

/** Replay controls bound to the replay store, its timer and its keyboard shortcuts. */
export function ReplayBar({ replay }: { replay: AppStores["replay"] }) {
  const cursor = useStore(replay, (state) => state.cursor);
  const count = useStore(replay, (state) => state.stepCount);
  const playing = useStore(replay, (state) => state.playing);
  const speed = useStore(replay, (state) => state.speed);
  const actions = replay.getState();

  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(() => {
      replay.getState().tick();
    }, 1000 / speed);
    return () => {
      clearInterval(timer);
    };
  }, [replay, playing, speed]);

  const group = "Replay";
  useShortcut(
    { id: "replay-toggle", key: " ", label: "Space", description: "Play or pause", group },
    actions.toggle,
  );
  useShortcut(
    { id: "replay-previous", key: "ArrowLeft", label: "←", description: "Previous step", group },
    actions.previous,
  );
  useShortcut(
    { id: "replay-next", key: "ArrowRight", label: "→", description: "Next step", group },
    actions.next,
  );
  useShortcut(
    { id: "replay-first", key: "Home", label: "Home", description: "First step", group },
    actions.first,
  );
  useShortcut(
    { id: "replay-last", key: "End", label: "End", description: "Last step", group },
    actions.last,
  );

  return (
    <ReplayControls
      position={cursor}
      count={count}
      playing={playing}
      speed={speed}
      speeds={REPLAY_SPEEDS}
      onFirst={actions.first}
      onPrevious={actions.previous}
      onToggle={actions.toggle}
      onNext={actions.next}
      onLast={actions.last}
      onSeek={actions.goTo}
      onSpeed={(value) => {
        if (isSpeed(value)) actions.setSpeed(value);
      }}
    />
  );
}
