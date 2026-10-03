import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
  type ReactNode,
} from "react";

import styles from "./SplitPanel.module.css";

/** Pixels per arrow key press on a resize handle. */
const KEYBOARD_STEP_PX = 16;
const STORAGE_PREFIX = "flowdoo.split.";

export interface SidePane {
  content: ReactNode;
  /** Accessible name of the pane and its handle, e.g. "Steps". */
  label: string;
  /** CSS width before the user resizes, e.g. "var(--panel-left-w)". */
  defaultWidth: string;
  minWidth: number;
  maxWidth: number;
}

export interface SplitPanelProps {
  /** Key for the persisted sizes, unique per layout, e.g. "trace". */
  id: string;
  start?: SidePane;
  end?: SidePane;
  children: ReactNode;
}

type Side = "start" | "end";
interface PaneState {
  width: number | null; // null = default width
  collapsed: boolean;
}
type Stored = Partial<Record<Side, PaneState>>;

function readStored(id: string): Stored {
  try {
    const raw = localStorage.getItem(STORAGE_PREFIX + id);
    return raw ? (JSON.parse(raw) as Stored) : {};
  } catch {
    return {};
  }
}

function writeStored(id: string, value: Stored) {
  try {
    localStorage.setItem(STORAGE_PREFIX + id, JSON.stringify(value));
  } catch {
    // not persisted; the layout still works for this session
  }
}

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

/**
 * Up to three columns: an optional start pane, the main area, an optional end pane. Side
 * panes are resized by dragging or with the keyboard on their handle (arrow keys, Home/End,
 * Enter to collapse) and remember width and collapsed state.
 */
export function SplitPanel({ id, start, end, children }: SplitPanelProps) {
  const [state, setState] = useState<Stored>(() => readStored(id));
  // rendered widths, so keyboard steps start from what the user sees
  const [measured, setMeasured] = useState<Partial<Record<Side, number>>>({});
  const startRef = useRef<HTMLElement>(null);
  const endRef = useRef<HTMLElement>(null);

  useEffect(() => {
    writeStored(id, state);
  }, [id, state]);

  useEffect(() => {
    const observer = new ResizeObserver((entries) => {
      setMeasured((current) => {
        const next = { ...current };
        for (const entry of entries) {
          const side: Side = entry.target === startRef.current ? "start" : "end";
          next[side] = Math.round(entry.contentRect.width);
        }
        return next;
      });
    });
    for (const element of [startRef.current, endRef.current]) {
      if (element) observer.observe(element);
    }
    return () => {
      observer.disconnect();
    };
  }, []);

  const update = useCallback((side: Side, change: Partial<PaneState>) => {
    setState((current) => ({
      ...current,
      [side]: { width: null, collapsed: false, ...current[side], ...change },
    }));
  }, []);

  function currentWidth(side: Side): number {
    return state[side]?.width ?? measured[side] ?? 0;
  }

  function renderPane(side: Side, pane: SidePane) {
    const paneState = state[side];
    const collapsed = paneState?.collapsed ?? false;
    const width = paneState?.width;
    const resize = (next: number) => {
      update(side, {
        width: clamp(Math.round(next), pane.minWidth, pane.maxWidth),
        collapsed: false,
      });
    };
    // dragging the start handle right grows the start pane, the end handle the opposite
    const direction = side === "start" ? 1 : -1;

    const onKeyDown = (event: KeyboardEvent) => {
      const keys: Record<string, () => void> = {
        ArrowLeft: () => {
          resize(currentWidth(side) - KEYBOARD_STEP_PX * direction);
        },
        ArrowRight: () => {
          resize(currentWidth(side) + KEYBOARD_STEP_PX * direction);
        },
        Home: () => {
          resize(pane.minWidth);
        },
        End: () => {
          resize(pane.maxWidth);
        },
        Enter: () => {
          update(side, { collapsed: !collapsed });
        },
      };
      const action = keys[event.key];
      if (action) {
        event.preventDefault();
        action();
      }
    };

    const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
      if (event.button !== 0) return;
      const handle = event.currentTarget;
      const startX = event.clientX;
      const startWidth = collapsed ? pane.minWidth : currentWidth(side);
      handle.setPointerCapture(event.pointerId);
      const onMove = (move: globalThis.PointerEvent) => {
        resize(startWidth + (move.clientX - startX) * direction);
      };
      const onUp = () => {
        handle.removeEventListener("pointermove", onMove);
        handle.removeEventListener("pointerup", onUp);
      };
      handle.addEventListener("pointermove", onMove);
      handle.addEventListener("pointerup", onUp);
    };

    const paneElement = (
      <section
        ref={side === "start" ? startRef : endRef}
        className={styles.pane}
        aria-label={pane.label}
        hidden={collapsed}
        style={{
          width: width === null || width === undefined ? pane.defaultWidth : `${String(width)}px`,
        }}
      >
        {pane.content}
      </section>
    );
    const handle = (
      <div
        role="separator"
        aria-orientation="vertical"
        aria-label={`Resize ${pane.label}`}
        aria-valuemin={pane.minWidth}
        aria-valuemax={pane.maxWidth}
        aria-valuenow={collapsed ? 0 : currentWidth(side)}
        aria-expanded={!collapsed}
        tabIndex={0}
        className={styles.handle}
        onKeyDown={onKeyDown}
        onPointerDown={onPointerDown}
        onDoubleClick={() => {
          update(side, { collapsed: !collapsed });
        }}
      />
    );
    return side === "start" ? (
      <>
        {paneElement}
        {handle}
      </>
    ) : (
      <>
        {handle}
        {paneElement}
      </>
    );
  }

  return (
    <div className={styles.split}>
      {start ? renderPane("start", start) : null}
      <main className={styles.main}>{children}</main>
      {end ? renderPane("end", end) : null}
    </div>
  );
}
