import { ChevronDown, ChevronRight } from "lucide-react";
import {
  memo,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";

import { Icon } from "./Icon";
import styles from "./Tree.module.css";

/** One visible row of a tree (the caller flattens the tree and leaves out collapsed parts). */
export interface TreeRow {
  id: string;
  /** 0 = top level. */
  depth: number;
  parentId: string | null;
  hasChildren: boolean;
  expanded: boolean;
}

export interface TreeProps {
  /** Accessible name, e.g. "Steps". */
  label: string;
  rows: readonly TreeRow[];
  /** Keep it stable (useCallback) so unchanged rows do not re-render. */
  renderRow: (id: string) => ReactNode;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onToggle: (id: string, expanded: boolean) => void;
}

interface ItemProps {
  row: TreeRow;
  /** Offset in px when the tree is virtualized; undefined renders in normal flow. */
  top: number | undefined;
  domId: string;
  selected: boolean;
  renderRow: (id: string) => ReactNode;
  onSelect: (id: string) => void;
  onToggle: (id: string, expanded: boolean) => void;
}

const TreeItem = memo(function TreeItem({
  row,
  top,
  domId,
  selected,
  renderRow,
  onSelect,
  onToggle,
}: ItemProps) {
  return (
    <li
      id={domId}
      role="treeitem"
      aria-level={row.depth + 1}
      aria-selected={selected}
      aria-expanded={row.hasChildren ? row.expanded : undefined}
      className={[
        styles.item,
        selected ? styles.selected : "",
        top === undefined ? "" : styles.placed,
      ]
        .join(" ")
        .trim()}
      style={top === undefined ? undefined : { top: `${String(top)}px` }}
      onClick={() => {
        onSelect(row.id);
      }}
    >
      {Array.from({ length: row.depth }, (_, level) => (
        <span key={level} className={styles.guide} aria-hidden="true" />
      ))}
      {row.hasChildren ? (
        <span
          className={styles.toggle}
          aria-hidden="true"
          onClick={(event) => {
            event.stopPropagation();
            onToggle(row.id, !row.expanded);
          }}
        >
          <Icon icon={row.expanded ? ChevronDown : ChevronRight} compact />
        </span>
      ) : (
        <span className={styles.toggle} aria-hidden="true" />
      )}
      <span className={styles.content}>{renderRow(row.id)}</span>
    </li>
  );
});

/** Rows rendered above and below the visible part when virtualized. */
const OVERSCAN = 12;
/** Below this many rows everything is rendered. */
const VIRTUALIZE_FROM = 200;

function rowHeightOf(element: HTMLElement): number {
  const value = Number.parseFloat(getComputedStyle(element).getPropertyValue("--row-h"));
  return Number.isFinite(value) && value > 0 ? value : 28;
}

/**
 * Tree with one tab stop (tree pattern): ↑/↓ move, → expands or goes to the first child,
 * ← collapses or goes to the parent, Home/End jump. Keys it handles do not reach global
 * shortcuts.
 *
 * The tree scrolls itself. Large trees are virtualized: only the rows in view (plus a
 * margin and the selected row) are in the DOM, so tens of thousands of rows stay fast.
 * Without a measured layout (e.g. in tests) every row is rendered.
 */
export function Tree({ label, rows, renderRow, selectedId, onSelect, onToggle }: TreeProps) {
  const prefix = useId();
  const viewportRef = useRef<HTMLDivElement>(null);
  const [view, setView] = useState({ top: 0, height: 0, rowHeight: 28 });
  const position = selectedId === null ? -1 : rows.findIndex((row) => row.id === selectedId);
  const current = rows[position];
  const virtual = view.height > 0 && rows.length >= VIRTUALIZE_FROM;

  useLayoutEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    const measure = () => {
      setView({
        top: viewport.scrollTop,
        height: viewport.clientHeight,
        rowHeight: rowHeightOf(viewport),
      });
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(viewport);
    return () => {
      observer.disconnect();
    };
  }, []);

  // keep the selected row in view (it may not be in the DOM yet when virtualized)
  useLayoutEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport || position === -1) return;
    const rowHeight = view.rowHeight;
    const rowTop = position * rowHeight;
    if (viewport.clientHeight === 0) {
      viewport.ownerDocument
        .getElementById(`${prefix}-${rows[position]?.id ?? ""}`)
        ?.scrollIntoView({ block: "nearest" });
    } else if (rowTop < viewport.scrollTop) {
      viewport.scrollTop = rowTop;
    } else if (rowTop + rowHeight > viewport.scrollTop + viewport.clientHeight) {
      viewport.scrollTop = rowTop + rowHeight - viewport.clientHeight;
    }
    // not on scroll: the user may scroll away from the selection
  }, [position, prefix, rows, view.rowHeight]);

  const onKeyDown = (event: KeyboardEvent<HTMLUListElement>) => {
    if (event.altKey || event.ctrlKey || event.metaKey || rows.length === 0) return;
    const go = (index: number) => {
      const row = rows[Math.min(Math.max(index, 0), rows.length - 1)];
      if (row) onSelect(row.id);
    };
    const actions: Record<string, () => void> = {
      ArrowDown: () => {
        go(position + 1);
      },
      ArrowUp: () => {
        go(position === -1 ? 0 : position - 1);
      },
      Home: () => {
        go(0);
      },
      End: () => {
        go(rows.length - 1);
      },
      ArrowRight: () => {
        if (!current) go(0);
        else if (current.hasChildren && !current.expanded) onToggle(current.id, true);
        else if (current.hasChildren) go(position + 1);
      },
      ArrowLeft: () => {
        if (!current) return;
        if (current.hasChildren && current.expanded) onToggle(current.id, false);
        else if (current.parentId !== null) onSelect(current.parentId);
      },
    };
    const action = actions[event.key];
    if (action) {
      event.preventDefault();
      action();
    }
  };

  let indexes: number[];
  if (virtual) {
    const first = Math.max(0, Math.floor(view.top / view.rowHeight) - OVERSCAN);
    const last = Math.min(
      rows.length,
      Math.ceil((view.top + view.height) / view.rowHeight) + OVERSCAN,
    );
    indexes = Array.from({ length: last - first }, (_, i) => first + i);
    // the active descendant must exist in the DOM
    if (position !== -1 && (position < first || position >= last)) indexes.push(position);
  } else {
    indexes = rows.map((_, i) => i);
  }

  return (
    <div
      ref={viewportRef}
      className={styles.viewport}
      onScroll={(event) => {
        const top = event.currentTarget.scrollTop;
        setView((current) => (current.top === top ? current : { ...current, top }));
      }}
    >
      <ul
        role="tree"
        aria-label={label}
        aria-activedescendant={current ? `${prefix}-${current.id}` : undefined}
        tabIndex={0}
        className={styles.tree}
        style={virtual ? { height: `${String(rows.length * view.rowHeight)}px` } : undefined}
        onKeyDown={onKeyDown}
      >
        {indexes.map((i) => {
          const row = rows[i];
          if (!row) return null;
          return (
            <TreeItem
              key={row.id}
              row={row}
              top={virtual ? i * view.rowHeight : undefined}
              domId={`${prefix}-${row.id}`}
              selected={row.id === selectedId}
              renderRow={renderRow}
              onSelect={onSelect}
              onToggle={onToggle}
            />
          );
        })}
      </ul>
    </div>
  );
}
