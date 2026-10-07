import { ChevronDown, ChevronRight } from "lucide-react";
import { memo, useEffect, useId, useRef, type KeyboardEvent, type ReactNode } from "react";

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
  domId: string;
  selected: boolean;
  renderRow: (id: string) => ReactNode;
  onSelect: (id: string) => void;
  onToggle: (id: string, expanded: boolean) => void;
}

const TreeItem = memo(function TreeItem({
  row,
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
      className={[styles.item, selected ? styles.selected : ""].join(" ").trim()}
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

/**
 * Tree with one tab stop (tree pattern): ↑/↓ move, → expands or goes to the first child,
 * ← collapses or goes to the parent, Home/End jump. Keys it handles do not reach global
 * shortcuts.
 */
export function Tree({ label, rows, renderRow, selectedId, onSelect, onToggle }: TreeProps) {
  const prefix = useId();
  const listRef = useRef<HTMLUListElement>(null);
  const position = selectedId === null ? -1 : rows.findIndex((row) => row.id === selectedId);
  const current = rows[position];

  useEffect(() => {
    if (selectedId === null) return;
    listRef.current?.ownerDocument
      .getElementById(`${prefix}-${selectedId}`)
      ?.scrollIntoView({ block: "nearest" });
  }, [prefix, selectedId]);

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

  return (
    <ul
      ref={listRef}
      role="tree"
      aria-label={label}
      aria-activedescendant={current ? `${prefix}-${current.id}` : undefined}
      tabIndex={0}
      className={styles.tree}
      onKeyDown={onKeyDown}
    >
      {rows.map((row) => (
        <TreeItem
          key={row.id}
          row={row}
          domId={`${prefix}-${row.id}`}
          selected={row.id === selectedId}
          renderRow={renderRow}
          onSelect={onSelect}
          onToggle={onToggle}
        />
      ))}
    </ul>
  );
}
